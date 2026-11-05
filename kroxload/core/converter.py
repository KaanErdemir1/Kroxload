"""Arayüzden bağımsız dosya dönüştürme motoru (FFmpeg + FFprobe).

Kullanıcının kendi bilgisayarındaki ses/video dosyalarını dönüştürür.
Yalnızca paketlenmiş FFmpeg'in GERÇEKTEN içerdiği kodlayıcılar sunulur
(`kodlayicilar()` ffmpeg -encoders çıktısını okur); olmayan seçenek listeden düşer.

Olaylar (on_olay geri çağırması, sözlük):
  {"tip": "basladi",   "sira", "toplam"}
  {"tip": "ilerleme",  "sira", "oran": 0..1, "hiz": "2.3x", "kalan": "00:12", "boyut": int}
  {"tip": "oge_bitti", "sira", "basarili", "iptal", "hata": str|None,
                       "dosya": str|None, "boyut": int}
  {"tip": "bitti",     "basarili", "toplam", "hatalar": [str], "iptal": bool}

İş tanımı (dict), `donustur(isler)` listesindeki her öge:
  kaynak, hedef_tur ("ses"|"video"), format, ses_codec, ses_bitrate (kbps|None),
  ornekleme (Hz|None), kanal (1|2|None), video_codec, kalite, cozunurluk (yükseklik|None),
  gorsel (ses→video için kapak resmi yolu|None), klasor (çıktı klasörü)
"""
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from .errors import donusum_hata_turkce
from .logs import kayit as log
from .paths import ffmpeg_klasoru

_PENCERESIZ = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ARKA_PLAN = "0x0F0F14"  # görselsiz ses→video için düz koyu arka plan

# ---------------------------------------------------------------- format tabloları
CODEC_ADI = {
    "libmp3lame": "MP3 (LAME)", "pcm_s16le": "PCM 16-bit", "pcm_s24le": "PCM 24-bit",
    "flac": "FLAC", "aac": "AAC", "libvorbis": "Vorbis", "libopus": "Opus",
    "libopenh264": "H.264", "mpeg4": "MPEG-4", "libvpx-vp9": "VP9", "libvpx": "VP8",
}
SES_BITRATELER = ["320", "256", "192", "160", "128", "96"]

SES_HEDEFLERI = {
    "MP3": {"uzanti": ".mp3", "codec": ["libmp3lame"], "bitrate": True},
    "WAV": {"uzanti": ".wav", "codec": ["pcm_s16le", "pcm_s24le"], "bitrate": False},
    "FLAC": {"uzanti": ".flac", "codec": ["flac"], "bitrate": False},
    "AAC": {"uzanti": ".aac", "codec": ["aac"], "bitrate": True},
    "OGG": {"uzanti": ".ogg", "codec": ["libvorbis", "libopus"], "bitrate": True},
    "M4A": {"uzanti": ".m4a", "codec": ["aac"], "bitrate": True},
}
VIDEO_HEDEFLERI = {
    "MP4": {"uzanti": ".mp4", "video": ["libopenh264", "mpeg4"], "ses": ["aac", "libmp3lame"]},
    "MKV": {"uzanti": ".mkv", "video": ["libopenh264", "libvpx-vp9", "mpeg4"],
            "ses": ["aac", "libopus", "libvorbis", "libmp3lame", "flac"]},
    "AVI": {"uzanti": ".avi", "video": ["mpeg4", "libopenh264"], "ses": ["libmp3lame", "aac"]},
    "MOV": {"uzanti": ".mov", "video": ["libopenh264", "mpeg4"], "ses": ["aac"]},
    "WEBM": {"uzanti": ".webm", "video": ["libvpx-vp9", "libvpx"], "ses": ["libopus", "libvorbis"]},
}
# "Video → Ses" için sunulan ses formatları (isteğe göre M4A da kullanılabilir)
VIDEODAN_SESE = ["MP3", "WAV", "FLAC", "AAC", "OGG", "M4A"]

KALITELER = {"Yüksek": 0, "Dengeli": 1, "Küçük dosya": 2}
# 1080p için hedef bit hızı (kbps); diğer çözünürlüklerde piksel oranıyla ölçeklenir
_VIDEO_KBPS = (8000, 4000, 1800)
_MPEG4_Q = (3, 6, 10)
_VP9_CRF = (24, 31, 38)
COZUNURLUKLER = {"Orijinal": None, "2160p": 2160, "1440p": 1440, "1080p": 1080,
                 "720p": 720, "480p": 480, "360p": 360}

SES_UZANTILARI = (".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus", ".m4a", ".wma", ".aiff", ".aif")
VIDEO_UZANTILARI = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".ts", ".mpg", ".mpeg", ".3gp")

_kodlayici_onbellek = None


def _arac(ad):
    ff = ffmpeg_klasoru()
    if not ff:
        raise FileNotFoundError("FFmpeg bulunamadı")
    return os.path.join(ff, ad + ".exe")


def kodlayicilar():
    """Paketlenmiş FFmpeg'in sunduğu kodlayıcı adları kümesi (bir kez okunur)."""
    global _kodlayici_onbellek
    if _kodlayici_onbellek is None:
        try:
            c = subprocess.run([_arac("ffmpeg"), "-hide_banner", "-encoders"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=30, creationflags=_PENCERESIZ)
            adlar = set()
            for satir in c.stdout.splitlines():
                parca = satir.split()
                if len(parca) >= 2 and re.fullmatch(r"[VAS.][A-Z.]{5}", parca[0]):
                    adlar.add(parca[1])
            _kodlayici_onbellek = adlar
        except Exception:
            log.exception("Kodlayıcılar okunamadı")
            _kodlayici_onbellek = set()
    return _kodlayici_onbellek


def mevcut(adaylar):
    """Aday kodlayıcılardan FFmpeg'de gerçekten bulunanları döndürür."""
    var = kodlayicilar()
    return [a for a in adaylar if a in var]


def ses_formatlari():
    """Sesi hedefleyebileceğimiz formatlar (kodlayıcısı olanlar)."""
    return [f for f, d in SES_HEDEFLERI.items() if mevcut(d["codec"])]


def video_formatlari():
    return [f for f, d in VIDEO_HEDEFLERI.items() if mevcut(d["video"]) and mevcut(d["ses"])]


# ---------------------------------------------------------------- kaynak analizi
def sure_yaz(saniye):
    try:
        s = int(float(saniye))
    except (TypeError, ValueError):
        return ""
    h, kalan = divmod(s, 3600)
    m, sn = divmod(kalan, 60)
    return f"{h}:{m:02d}:{sn:02d}" if h else f"{m}:{sn:02d}"


def boyut_yaz(bayt):
    try:
        bayt = float(bayt)
    except (TypeError, ValueError):
        return ""
    for birim in ("B", "KB", "MB", "GB", "TB"):
        if bayt < 1024 or birim == "TB":
            return f"{bayt:.0f} {birim}" if birim == "B" else f"{bayt:.1f} {birim}"
        bayt /= 1024
    return ""


def sonda(yol):
    """FFprobe ile dosyayı inceler.

    Dönüş: {"yol", "ad", "boyut", "sure", "format", "video": {...}|None, "ses": {...}|None}
    Medya olmayan/bozuk dosyada ValueError (Türkçe mesajlı) yükseltir.
    """
    yol = str(yol)
    if not os.path.isfile(yol):
        raise ValueError("Dosya bulunamadı.")
    try:
        c = subprocess.run(
            [_arac("ffprobe"), "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", yol],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, creationflags=_PENCERESIZ)
    except FileNotFoundError:
        raise ValueError("FFprobe bulunamadı. Uygulamayı yeniden kurmayı dene.")
    except subprocess.TimeoutExpired:
        raise ValueError("Dosya incelenirken zaman aşımı oldu.")
    if c.returncode != 0:
        raise ValueError(donusum_hata_turkce(c.stderr) or "Bu dosya okunamadı; medya dosyası olmayabilir.")
    try:
        veri = json.loads(c.stdout)
    except ValueError:
        raise ValueError("Bu dosya okunamadı; medya dosyası olmayabilir.")

    akimlar = veri.get("streams") or []
    fmt = veri.get("format") or {}
    video = ses = None
    for a in akimlar:
        tur = a.get("codec_type")
        # kapak resmi (attached_pic) video sayılmaz
        if tur == "video" and not (a.get("disposition") or {}).get("attached_pic") and video is None:
            fps = a.get("avg_frame_rate") or "0/1"
            try:
                p, q = fps.split("/")
                fps = round(float(p) / float(q), 2) if float(q) else 0
            except Exception:
                fps = 0
            video = {"codec": a.get("codec_name"), "genislik": a.get("width"),
                     "yukseklik": a.get("height"), "fps": fps}
        elif tur == "audio" and ses is None:
            ses = {"codec": a.get("codec_name"),
                   "bitrate": int(a["bit_rate"]) // 1000 if str(a.get("bit_rate", "")).isdigit() else None,
                   "hz": int(a["sample_rate"]) if str(a.get("sample_rate", "")).isdigit() else None,
                   "kanal": a.get("channels")}
    if video is None and ses is None:
        raise ValueError("Bu dosyada ses veya video akışı bulunamadı.")
    try:
        sure = float(fmt.get("duration") or 0)
    except ValueError:
        sure = 0.0
    try:
        boyut = int(fmt.get("size") or os.path.getsize(yol))
    except (ValueError, OSError):
        boyut = 0
    return {"yol": yol, "ad": os.path.basename(yol), "boyut": boyut, "sure": sure,
            "format": (fmt.get("format_long_name") or fmt.get("format_name") or "").split(",")[0],
            "video": video, "ses": ses}


# ---------------------------------------------------------------- komut kurma
def _video_kbps(kalite_no, yukseklik, genislik):
    oran = (max(yukseklik, 1) * max(genislik, 1)) / (1920 * 1080)
    return max(250, int(_VIDEO_KBPS[kalite_no] * oran))


def _hedef_boyut(bilgi, ayar):
    """Çıktı çözünürlüğünü (g, y) kestirir (bit hızı hesabı için)."""
    v = (bilgi or {}).get("video")
    g, y = (v or {}).get("genislik") or 1280, (v or {}).get("yukseklik") or 720
    h = ayar.get("cozunurluk")
    if h and h < y:
        g, y = int(g * h / y), h
    return g, y


def cikti_yolu(kaynak, klasor, uzanti):
    """Var olan dosyanın üzerine yazmayan çıktı yolu üretir: ad.mp3, ad (1).mp3 ..."""
    kaynak = Path(kaynak)
    klasor = Path(klasor)
    taban = kaynak.stem
    aday = klasor / (taban + uzanti)
    n = 1
    while aday.exists() or aday.resolve() == kaynak.resolve():
        aday = klasor / f"{taban} ({n}){uzanti}"
        n += 1
    return aday


def dogrula(ayar, bilgi):
    """Ayar kaynak dosyayla uyumsuzsa Türkçe hata metni, uygunsa None döndürür."""
    tur = ayar.get("hedef_tur")
    fmt = ayar.get("format")
    if tur == "ses":
        if fmt not in SES_HEDEFLERI or not mevcut(SES_HEDEFLERI[fmt]["codec"]):
            return f"{fmt} biçimi bu FFmpeg sürümünde desteklenmiyor."
        if not bilgi.get("ses"):
            return "Bu dosyada ses akışı yok; sese dönüştürülemez."
    elif tur == "video":
        if fmt not in VIDEO_HEDEFLERI or not mevcut(VIDEO_HEDEFLERI[fmt]["video"]):
            return f"{fmt} biçimi bu FFmpeg sürümünde desteklenmiyor."
        if not bilgi.get("video") and not bilgi.get("ses"):
            return "Bu dosyada dönüştürülecek bir akış yok."
    else:
        return "Bilinmeyen dönüştürme türü."
    g = ayar.get("gorsel")
    if g and not os.path.isfile(g):
        return "Seçilen görsel dosyası bulunamadı."
    return None


def komut_kur(ayar, bilgi, cikti):
    """FFmpeg komutunu (liste) üretir. Kabuk kullanılmaz; yollar olduğu gibi geçer."""
    ff = _arac("ffmpeg")
    kom = [ff, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
           "-progress", "pipe:1", "-nostats"]
    tur = ayar["hedef_tur"]
    fmt = ayar["format"]
    kaynak = bilgi["yol"]

    if tur == "ses":
        d = SES_HEDEFLERI[fmt]
        codec = ayar.get("ses_codec") or mevcut(d["codec"])[0]
        kom += ["-i", kaynak, "-vn", "-map", "0:a:0", "-c:a", codec]
        if d["bitrate"] and ayar.get("ses_bitrate"):
            kom += ["-b:a", f"{ayar['ses_bitrate']}k"]
        if ayar.get("ornekleme"):
            kom += ["-ar", str(ayar["ornekleme"])]
        if ayar.get("kanal"):
            kom += ["-ac", str(ayar["kanal"])]
        kom += [str(cikti)]
        return kom

    # ---- video hedefi ----
    d = VIDEO_HEDEFLERI[fmt]
    vcodec = ayar.get("video_codec") or mevcut(d["video"])[0]
    acodec = ayar.get("ses_codec") or mevcut(d["ses"])[0]
    kalite_no = KALITELER.get(ayar.get("kalite") or "Dengeli", 1)
    h = ayar.get("cozunurluk")

    gorselden = not bilgi.get("video")   # kaynak yalnızca ses → görselli video üret
    if gorselden:
        yuk = h or 720
        gen = int(round(yuk * 16 / 9 / 2)) * 2
        if ayar.get("gorsel"):
            kom += ["-loop", "1", "-framerate", "5", "-i", ayar["gorsel"]]
        else:
            kom += ["-f", "lavfi", "-i", f"color=c={ARKA_PLAN}:s={gen}x{yuk}:r=5"]
        kom += ["-i", kaynak, "-map", "0:v:0", "-map", "1:a:0", "-shortest"]
        vf = (f"scale={gen}:{yuk}:force_original_aspect_ratio=decrease,"
              f"pad={gen}:{yuk}:(ow-iw)/2:(oh-ih)/2:color={ARKA_PLAN},format=yuv420p")
        g_out, y_out = gen, yuk
        kom += ["-r", "5"]
    else:
        kom += ["-i", kaynak, "-map", "0:v:0", "-map", "0:a:0?"]
        if h:
            vf = f"scale=w=-2:h=min({h}\\,ih),format=yuv420p"
        else:
            vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"
        g_out, y_out = _hedef_boyut(bilgi, ayar)
    kom += ["-vf", vf, "-c:v", vcodec]

    kbps = _video_kbps(kalite_no, y_out, g_out)
    if gorselden:
        kbps = max(250, kbps // 8)  # durağan görüntü az bit ister
    if vcodec == "libopenh264":
        kom += ["-b:v", f"{kbps}k"]
    elif vcodec == "mpeg4":
        kom += ["-q:v", str(_MPEG4_Q[kalite_no])]
    elif vcodec == "libvpx-vp9":
        kom += ["-crf", str(_VP9_CRF[kalite_no]), "-b:v", "0",
                "-deadline", "good", "-cpu-used", "5", "-row-mt", "1"]
    elif vcodec == "libvpx":
        kom += ["-b:v", f"{kbps}k", "-deadline", "good", "-cpu-used", "4"]

    kom += ["-c:a", acodec]
    if acodec not in ("flac",) and ayar.get("ses_bitrate"):
        kom += ["-b:a", f"{ayar['ses_bitrate']}k"]
    if ayar.get("ornekleme"):
        kom += ["-ar", str(ayar["ornekleme"])]
    if ayar.get("kanal"):
        kom += ["-ac", str(ayar["kanal"])]
    if d["uzanti"] == ".mp4" or d["uzanti"] == ".mov":
        kom += ["-movflags", "+faststart"]
    kom += [str(cikti)]
    return kom


# ---------------------------------------------------------------- motor
class DonusumMotoru:
    """Dönüştürme kuyruğunu sırayla işler; tümü veya tek öge iptal edilebilir."""

    def __init__(self, on_olay=None):
        self.on_olay = on_olay
        self._iptal = threading.Event()
        self._oge_iptal = set()
        self._proc = None
        self._sira = 0
        self.calisiyor = False
        self._kilit = threading.Lock()

    def _olay(self, olay):
        if self.on_olay:
            try:
                self.on_olay(olay)
            except Exception:
                log.exception("Dönüştürme olay geri çağrısı hata verdi")

    def _oldur(self):
        with self._kilit:
            p = self._proc
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    def iptal_et(self):
        self._iptal.set()
        self._oldur()

    def oge_iptal_et(self, sira):
        self._oge_iptal.add(sira)
        if sira == self._sira:
            self._oldur()

    def donustur(self, isler):
        """Bloklayarak çalışır; arayüz ayrı thread'de çağırmalıdır."""
        self.calisiyor = True
        self._iptal.clear()
        self._oge_iptal.clear()
        toplam = len(isler)
        basarili = 0
        hatalar = []
        try:
            for i, is_ in enumerate(isler, 1):
                if self._iptal.is_set():
                    break
                self._sira = i
                if i in self._oge_iptal:
                    self._olay({"tip": "oge_bitti", "sira": i, "basarili": False, "iptal": True,
                                "hata": None, "dosya": None, "boyut": 0})
                    continue
                self._olay({"tip": "basladi", "sira": i, "toplam": toplam})
                sonuc = self._tek(i, is_)
                if sonuc["basarili"]:
                    basarili += 1
                elif sonuc.get("hata"):
                    hatalar.append(sonuc["hata"])
                self._olay({"tip": "oge_bitti", "sira": i, **sonuc})
        finally:
            self.calisiyor = False
        sonuc = {"basarili": basarili, "toplam": toplam, "hatalar": hatalar,
                 "iptal": self._iptal.is_set()}
        self._olay({"tip": "bitti", **sonuc})
        return sonuc

    def _tek(self, sira, ayar):
        bos = {"basarili": False, "iptal": False, "hata": None, "dosya": None, "boyut": 0}
        try:
            bilgi = sonda(ayar["kaynak"])
        except ValueError as e:
            bos["hata"] = str(e)
            return bos
        hata = dogrula(ayar, bilgi)
        if hata:
            bos["hata"] = hata
            return bos

        klasor = Path(ayar.get("klasor") or Path(ayar["kaynak"]).parent)
        try:
            klasor.mkdir(parents=True, exist_ok=True)
        except OSError:
            bos["hata"] = "Çıktı klasörü oluşturulamadı. Başka bir klasör seç."
            return bos
        d = SES_HEDEFLERI[ayar["format"]] if ayar["hedef_tur"] == "ses" else VIDEO_HEDEFLERI[ayar["format"]]
        son = cikti_yolu(ayar["kaynak"], klasor, d["uzanti"])
        gecici = son.with_name(son.stem + ".kroxload-tmp" + son.suffix)
        try:
            kom = komut_kur(ayar, bilgi, gecici)
        except FileNotFoundError:
            bos["hata"] = "FFmpeg bulunamadı. Uygulamayı yeniden kurmayı dene."
            return bos

        log.info("Dönüştürme başladı: %s -> %s", ayar["kaynak"], son)
        sure = bilgi.get("sure") or 0
        hata_satirlari = []
        try:
            with self._kilit:
                self._proc = subprocess.Popen(
                    kom, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    encoding="utf-8", errors="replace", creationflags=_PENCERESIZ)
            proc = self._proc

            def stderr_oku():
                for satir in proc.stderr:
                    hata_satirlari.append(satir.strip())
                    del hata_satirlari[:-30]
            t = threading.Thread(target=stderr_oku, daemon=True)
            t.start()

            son_olay = 0.0
            ilerleme = {}
            for satir in proc.stdout:
                anahtar, _, deger = satir.strip().partition("=")
                ilerleme[anahtar] = deger
                if anahtar != "progress":
                    continue
                simdi = time.monotonic()
                if deger == "continue" and simdi - son_olay < 0.1:
                    continue
                son_olay = simdi
                us = ilerleme.get("out_time_us") or ilerleme.get("out_time_ms") or "0"
                try:
                    islenen = max(float(us), 0) / 1_000_000
                except ValueError:
                    islenen = 0
                oran = min(islenen / sure, 1.0) if sure else 0.0
                try:
                    hiz_say = float((ilerleme.get("speed") or "0x").rstrip("x"))
                except ValueError:
                    hiz_say = 0
                kalan = sure_yaz((sure - islenen) / hiz_say) if sure and hiz_say > 0 else ""
                try:
                    boyut = int(ilerleme.get("total_size") or 0)
                except ValueError:
                    boyut = 0
                self._olay({"tip": "ilerleme", "sira": sira, "oran": oran,
                            "hiz": f"{hiz_say:.1f}x" if hiz_say else "", "kalan": kalan,
                            "boyut": boyut})
            proc.wait()
            t.join(2)
        except Exception as e:
            log.exception("Dönüştürme çalıştırılamadı")
            self._sil(gecici)
            bos["hata"] = donusum_hata_turkce(str(e)) or "Dönüştürme başlatılamadı."
            return bos
        finally:
            with self._kilit:
                self._proc = None

        iptal = self._iptal.is_set() or sira in self._oge_iptal
        if iptal:
            self._sil(gecici)
            bos["iptal"] = True
            return bos
        if proc.returncode != 0 or not gecici.exists():
            ham = " ".join(hata_satirlari[-6:])
            log.error("Dönüştürme hatası (%s): %s", ayar["kaynak"], ham)
            self._sil(gecici)
            bos["hata"] = donusum_hata_turkce(ham) or "Dönüştürme başarısız oldu. Ayrıntı günlükte."
            return bos
        try:
            os.replace(gecici, son)
        except OSError:
            self._sil(gecici)
            bos["hata"] = "Çıktı dosyası kaydedilemedi. Klasör izinlerini kontrol et."
            return bos
        boyut = son.stat().st_size
        log.info("Dönüştürüldü: %s (%s)", son, boyut_yaz(boyut))
        return {"basarili": True, "iptal": False, "hata": None, "dosya": str(son), "boyut": boyut}

    @staticmethod
    def _sil(yol):
        try:
            Path(yol).unlink()
        except OSError:
            pass

