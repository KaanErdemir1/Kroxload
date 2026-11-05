"""Arayüzden bağımsız indirme motoru.

Bu modül hiçbir arayüz kütüphanesi import etmez. İleride bir web arayüzü
(ör. FastAPI) veya mobil katman, aynı motoru şu olaylarla kullanabilir:

    on_olay(olay)  -> tek geri çağırma; olay bir sözlük:
      {"tip": "basladi",    "sira", "toplam"}
      {"tip": "ilerleme",   "sira", "toplam",
                           "asama": "indiriliyor"|"donusturuluyor"|"hazirlaniyor",
                           "asama_metni": str|None, "oran": 0..1,
                           "hiz": str, "kalan": str,
                           "indirilen": int, "toplam_byte": int,
                           "baslik": str|None,
                           "video_sira": int|None, "video_toplam": int|None}
      {"tip": "oge_bitti",  "sira", "basarili": bool, "baslik",
                           "dosyalar": [str],          # indirilen dosya(lar)
                           "hata": str|None,           # Türkçe mesaj
                           "iptal": bool}              # öge kullanıcı tarafından atlandı
      {"tip": "bitti",      "basarili": int, "toplam": int,
                           "hatalar": [str], "iptal": bool}

`indir()` bloklayarak çalışır; arayüz onu ayrı bir thread'de çağırır.
İptal için `iptal_et()` (tüm kuyruk) veya `oge_iptal_et(sira)` (tek öge).
"""
import re
import shutil
import threading
import time
from pathlib import Path

from .errors import hata_turkce
from .formats import KALITELER
from .logs import kayit as log
from .paths import ffmpeg_klasoru
from .ytdlp import yt_dlp

ANSI = re.compile(r"\x1b\[[0-9;]*m")
PARCA_DESEN = re.compile(r"\.f\d+\.\w+$")  # "video.f137.mp4" gibi ara dosyalar
MIN_DISK = 100 * 1024 * 1024  # indirmeye başlamak için gereken en az boş alan
ILERLEME_ARALIGI = 0.1  # saniyede en fazla 10 ilerleme olayı


class IptalEdildi(Exception):
    """Kullanıcı tüm kuyruğu iptal etti."""


class OgeIptal(Exception):
    """Kullanıcı bu ögeyi atladı; kuyruk bir sonraki ögeyle devam eder."""


class OgeDuraklat(Exception):
    """Kullanıcı bu ögeyi duraklattı: indirme durur ama .part dosyaları KALIR.

    Devam ettirmek için aynı link yeni bir indir() çağrısıyla verilir; yt-dlp
    yarım dosyayı (sunucu Range destekliyorsa) kaldığı yerden sürdürür.
    """


def temizle(metin):
    """yt-dlp çıktısındaki ANSI renk kodlarını temizler."""
    return ANSI.sub("", str(metin or "")).strip()


def boyut_yaz(bayt):
    """Bayt sayısını okunur boyuta çevirir (45.2 MB gibi)."""
    try:
        bayt = float(bayt)
    except (TypeError, ValueError):
        return ""
    for birim in ("B", "KB", "MB", "GB", "TB"):
        if bayt < 1024 or birim == "TB":
            return f"{bayt:.0f} {birim}" if birim == "B" else f"{bayt:.1f} {birim}"
        bayt /= 1024
    return ""


def _kirp(metin, sinir=220):
    """Hata mesajını tek satıra indirip kısaltır."""
    metin = " ".join(str(metin or "").split())
    return metin if len(metin) <= sinir else metin[: sinir - 1] + "…"


def _yazilabilir(klasor):
    """Klasöre gerçekten yazılabiliyor mu? (geçici dosya denemesi)"""
    try:
        deneme = Path(klasor) / f".kroxload-deneme-{threading.get_ident()}"
        deneme.write_text("", encoding="utf-8")
        deneme.unlink()
        return True
    except Exception:
        return False


def on_kontrol(klasor):
    """İndirme başlamadan önce klasör/disk kontrolü. Hata varsa Türkçe mesaj."""
    yol = Path(klasor)
    if not yol.is_dir():
        return "Kayıt klasörü bulunamadı. Ayarlardan yeni bir klasör seç."
    if not _yazilabilir(yol):
        return "Kayıt klasörüne yazılamadı. Başka bir klasör seç veya izinleri düzelt."
    try:
        bos = shutil.disk_usage(yol).free
    except OSError:
        return None
    if bos < MIN_DISK:
        return f"Diskte yeterli alan yok (boş: {boyut_yaz(bos)}). Yer açıp tekrar dene."
    return None


def son_dosyalar(bilgi):
    """İndirme + dönüştürme bitince oluşan nihai dosyaları bulur.

    yt-dlp, indirilen her öge için 'requested_downloads' listesinde gerçek
    (dönüştürme sonrası) dosya yolunu verir; liste linklerinde her girdinin
    altında olur.
    """
    dosyalar = []

    def gez(girdi):
        if not girdi:
            return
        for istek in girdi.get("requested_downloads") or []:
            yol = (istek or {}).get("filepath")
            if yol and yol not in dosyalar:
                dosyalar.append(yol)

    if (bilgi or {}).get("_type") == "playlist":
        for girdi in bilgi.get("entries") or []:
            gez(girdi)
    else:
        gez(bilgi)
    return dosyalar


def secenekler_hazirla(fmt, kalite, klasor, liste, ilerleme_hook=None, donusum_hook=None):
    """yt-dlp seçeneklerini oluşturur (motoru doğrudan kullanmak isteyen
    başka arayüzler de bu fonksiyonu çağırabilir)."""
    if liste:
        sablon = "%(playlist_title&{}/|)s%(playlist_index&{} - |)s%(title)s.%(ext)s"
    else:
        sablon = "%(title)s.%(ext)s"
    secenek = {
        "outtmpl": str(Path(klasor) / sablon),
        "noplaylist": not liste,
        "progress_hooks": [ilerleme_hook] if ilerleme_hook else [],
        "postprocessor_hooks": [donusum_hook] if donusum_hook else [],
        "quiet": True,
        "no_warnings": True,
        "retries": 15,
        "fragment_retries": 15,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "socket_timeout": 30,
    }
    if not liste:
        secenek["playlist_items"] = "1"  # saf liste linkinde yalnızca ilk video

    ff = ffmpeg_klasoru()
    if ff:
        secenek["ffmpeg_location"] = ff

    if fmt == "MP4":
        h = KALITELER["MP4"][kalite]
        f = f"[height<={h}]" if h else ""
        secenek["format"] = f"bv*{f}[ext=mp4]+ba[ext=m4a]/bv*{f}+ba/b{f}"
        secenek["merge_output_format"] = "mp4"
    else:
        pp = {"key": "FFmpegExtractAudio", "preferredcodec": fmt.lower()}
        deger = KALITELER[fmt][kalite]
        if deger:
            pp["preferredquality"] = deger
        secenek["postprocessors"] = [pp]
        secenek["format"] = "bestaudio[ext=m4a]/bestaudio/best" if fmt == "M4A" else "bestaudio/best"
    return secenek


class IndirmeMotoru:
    """Tek seferde bir kuyruk indirir; tümü veya tek öge iptal edilebilir."""

    def __init__(self, on_olay=None):
        self.on_olay = on_olay
        self._iptal = threading.Event()
        self._oge_iptal = set()
        self._oge_duraklat = set()
        self.calisiyor = False
        self._sira = 0
        self._toplam = 0
        self._baslik = None
        self._parcalar = []  # yarım kalırsa silinecek dosyalar
        self._son_olay = 0.0

    # ---- iptal ----
    def iptal_et(self):
        """Tüm kuyruğu iptal eder."""
        self._iptal.set()

    def oge_iptal_et(self, sira):
        """Yalnızca belirtilen ögeyi atlar; kuyruk devam eder."""
        self._oge_iptal.add(sira)

    def oge_duraklat(self, sira):
        """Belirtilen ögeyi duraklatır (yarım dosya saklanır); kuyruk devam eder.

        Yalnızca indirme aşamasında etkilidir; dönüştürme/birleştirme
        başladıysa öge normal şekilde bitirilir.
        """
        self._oge_duraklat.add(sira)

    # ---- olaylar ----
    def _olay(self, olay):
        if not self.on_olay:
            return
        try:
            self.on_olay(olay)
        except Exception:
            log.exception("Olay geri çağrısı hata verdi")

    def _hook(self, d):
        if self._iptal.is_set():
            raise IptalEdildi()
        if self._sira in self._oge_iptal:
            raise OgeIptal()
        if self._sira in self._oge_duraklat and d.get("status") == "downloading":
            raise OgeDuraklat()
        dosya = d.get("filename")
        if dosya and dosya not in self._parcalar:
            self._parcalar.append(dosya)
        if d["status"] == "downloading":
            simdi = time.monotonic()
            if simdi - self._son_olay < ILERLEME_ARALIGI:
                return
            self._son_olay = simdi
            toplam = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            indirilen = d.get("downloaded_bytes") or 0
            oran = min(indirilen / toplam, 1.0) if toplam else 0.0
            bilgi = d.get("info_dict") or {}
            if bilgi.get("title"):
                self._baslik = bilgi["title"]
            self._olay({
                "tip": "ilerleme",
                "sira": self._sira,
                "toplam": self._toplam,
                "asama": "indiriliyor",
                "asama_metni": None,
                "oran": oran,
                "hiz": temizle(d.get("_speed_str")),
                "kalan": temizle(d.get("_eta_str")),
                "indirilen": indirilen,
                "toplam_byte": toplam,
                "baslik": self._baslik,
                "video_sira": bilgi.get("playlist_index"),
                "video_toplam": bilgi.get("n_entries"),
            })
        elif d["status"] == "finished":
            self._son_olay = 0.0
            self._olay({
                "tip": "ilerleme",
                "sira": self._sira,
                "toplam": self._toplam,
                "asama": "hazirlaniyor",
                "asama_metni": None,
                "oran": 1.0,
                "baslik": self._baslik,
            })

    def _donusum_hook(self, d):
        if self._iptal.is_set():
            raise IptalEdildi()
        if self._sira in self._oge_iptal:
            raise OgeIptal()
        if d.get("status") != "started":
            return
        ad = str(d.get("postprocessor") or "")
        if "ExtractAudio" in ad:
            metin = "Sese dönüştürülüyor"
        elif "Merger" in ad or "Remux" in ad:
            metin = "Video ve ses birleştiriliyor"
        else:
            metin = "Dosya işleniyor"
        self._son_olay = 0.0
        self._olay({
            "tip": "ilerleme",
            "sira": self._sira,
            "toplam": self._toplam,
            "asama": "donusturuluyor",
            "asama_metni": metin,
            "oran": 1.0,
            "baslik": self._baslik,
        })

    # ---- yarım dosya temizliği ----
    def _parcalari_temizle(self):
        """İptal/hata halinde .part ve ara dosyalarını siler; tamamlanmış
        dosyalara dokunmaz."""
        for dosya in self._parcalar:
            kok = Path(dosya)
            try:
                adaylar = list(kok.parent.glob(kok.name + ".part*"))
                adaylar += list(kok.parent.glob(kok.name + ".ytdl*"))
                if PARCA_DESEN.search(kok.name):
                    adaylar.append(kok)
                for aday in adaylar:
                    aday.unlink()
                    log.info("Yarım kalan dosya silindi: %s", aday)
            except Exception:
                pass
        self._parcalar = []

    # ---- ana akış ----
    def indir(self, linkler, fmt, kalite, klasor, liste):
        """Kuyruğu bloklayarak indirir. Çağıran taraf ayrı thread kullanmalı."""
        self.calisiyor = True
        self._iptal.clear()
        self._oge_iptal.clear()
        self._oge_duraklat.clear()
        self._parcalar = []
        self._toplam = len(linkler)
        basarili = 0
        hatalar = []
        try:
            hata = on_kontrol(klasor)
            if hata:
                log.error("Ön kontrol hatası: %s", hata)
                for i, link in enumerate(linkler, 1):
                    self._olay({
                        "tip": "oge_bitti", "sira": i, "basarili": False,
                        "baslik": link, "dosyalar": [], "hata": hata, "iptal": False,
                    })
                hatalar = [hata]
                return self._bitir(basarili, hatalar)

            for i, link in enumerate(linkler, 1):
                if self._iptal.is_set():
                    break
                self._sira = i
                self._baslik = None
                self._parcalar = []
                if i in self._oge_iptal:
                    self._olay({
                        "tip": "oge_bitti", "sira": i, "basarili": False,
                        "baslik": link, "dosyalar": [], "hata": None, "iptal": True,
                    })
                    continue

                self._olay({"tip": "basladi", "sira": i, "toplam": self._toplam})
                try:
                    secenek = secenekler_hazirla(
                        fmt, kalite, klasor, liste,
                        ilerleme_hook=self._hook, donusum_hook=self._donusum_hook,
                    )
                    with yt_dlp.YoutubeDL(secenek) as ydl:
                        bilgi = ydl.extract_info(link, download=True)
                    dosyalar = son_dosyalar(bilgi)
                    baslik = (bilgi or {}).get("title") or self._baslik or link
                    basarili += 1
                    log.info("İndirildi (%s): %s", fmt, "; ".join(dosyalar) or baslik)
                    self._olay({
                        "tip": "oge_bitti", "sira": i, "basarili": True,
                        "baslik": baslik, "dosyalar": dosyalar, "hata": None, "iptal": False,
                    })
                except OgeDuraklat:
                    # Yarım dosyalar bilerek silinmez: devam ettirilince kullanılır
                    self._parcalar = []
                    log.info("İndirme duraklatıldı: %s", link)
                    self._olay({
                        "tip": "oge_bitti", "sira": i, "basarili": False,
                        "baslik": self._baslik or link, "dosyalar": [], "hata": None,
                        "iptal": False, "duraklatildi": True,
                    })
                except OgeIptal:
                    self._parcalari_temizle()
                    self._olay({
                        "tip": "oge_bitti", "sira": i, "basarili": False,
                        "baslik": self._baslik or link, "dosyalar": [], "hata": None, "iptal": True,
                    })
                except IptalEdildi:
                    self._parcalari_temizle()
                    break
                except Exception as e:
                    self._parcalari_temizle()
                    if self._iptal.is_set():
                        break
                    ham = temizle(e)
                    mesaj = hata_turkce(ham) or _kirp(ham)
                    log.error("İndirme hatası (%s): %s", link, ham)
                    hatalar.append(mesaj)
                    self._olay({
                        "tip": "oge_bitti", "sira": i, "basarili": False,
                        "baslik": self._baslik or link, "dosyalar": [], "hata": mesaj, "iptal": False,
                    })
        finally:
            self.calisiyor = False
        return self._bitir(basarili, hatalar)

    def _bitir(self, basarili, hatalar):
        sonuc = {
            "basarili": basarili,
            "toplam": self._toplam,
            "hatalar": hatalar,
            "iptal": self._iptal.is_set(),
        }
        self._olay({"tip": "bitti", **sonuc})
        return sonuc
