"""Kroxload motor testleri — internetsiz, yerel HTTP sunucusuyla çalışır.

Çalıştırma:  python tests/test_engine.py
Kaynak ortamda deps/ffmpeg, paketlenmiş exe klasöründe yandaki ffmpeg kullanılır.
Her test PASS/FAIL yazar; herhangi biri başarısızsa çıkış kodu 1 olur.
"""
import http.server
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
# Gerçek kullanıcı verisine (geçmiş/ayar/log) dokunmamak için APPDATA geçici klasöre yönlendirilir
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="kroxload_appdata_")

from kroxload.core import errors, history, paths  # noqa: E402
from kroxload.core.engine import IndirmeMotoru  # noqa: E402

FF = Path(paths.ffmpeg_klasoru() or "")
SONUCLAR = []


def kontrol(ad, kosul, ayrinti=""):
    SONUCLAR.append(bool(kosul))
    print(("PASS" if kosul else "FAIL"), "-", ad, ayrinti)


def ornek_uret(hedef, sure=3):
    subprocess.run(
        [str(FF / "ffmpeg.exe"), "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=15:duration={sure}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={sure}",
         "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(hedef)],
        check=True)


class Isleyici(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/yavas"):  # iptal testi: yavaş akan büyük dosya
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(50_000_000))
            self.end_headers()
            try:
                for _ in range(500):
                    self.wfile.write(b"\0" * 100_000)
                    self.wfile.flush()
                    time.sleep(0.05)
            except Exception:
                pass
            return
        super().do_GET()


def olaylari_topla():
    olaylar = []
    return olaylar, olaylar.append


def indir(link_listesi, fmt, kalite, klasor, liste=False):
    olaylar, ekle = olaylari_topla()
    motor = IndirmeMotoru(on_olay=ekle)
    sonuc = motor.indir(link_listesi, fmt, kalite, str(klasor), liste)
    return sonuc, olaylar


def main():
    kontrol("FFmpeg/FFprobe bulundu", FF.is_dir() and (FF / "ffmpeg.exe").exists()
            and (FF / "ffprobe.exe").exists(), f"({FF})")
    if not FF.is_dir():
        return

    gecici = Path(tempfile.mkdtemp(prefix="kroxload_test_"))
    sunucu_kok = gecici / "www"
    cikti = gecici / "cikti"
    sunucu_kok.mkdir()
    cikti.mkdir()
    ornek_uret(sunucu_kok / "ornek.mp4")
    ornek_uret(sunucu_kok / "ornek2.mp4", 2)
    os.chdir(sunucu_kok)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    taban = f"http://127.0.0.1:{port}"

    # --- Biçim testleri ---
    for fmt, kalite, uzanti in (("MP4", "En iyi", ".mp4"), ("MP3", "192 kbps", ".mp3"),
                                ("WAV", "Standart", ".wav"), ("M4A", "Orijinal", ".m4a")):
        k = cikti / fmt
        k.mkdir()
        sonuc, olaylar = indir([f"{taban}/ornek.mp4"], fmt, kalite, k)
        dosyalar = list(k.glob(f"*{uzanti}"))
        kontrol(f"{fmt} indirme", sonuc["basarili"] == 1 and len(dosyalar) == 1
                and dosyalar[0].stat().st_size > 1000,
                f"({dosyalar[0].name if dosyalar else sonuc['hatalar']})")
        if dosyalar and fmt != "MP4":
            # Dönüşümün gerçekten paketlenmiş ffprobe ile geçerli ses ürettiğini doğrula
            p = subprocess.run([str(FF / "ffprobe.exe"), "-v", "error", "-show_entries",
                                "stream=codec_name", "-of", "csv=p=0", str(dosyalar[0])],
                               capture_output=True, text=True)
            beklenen = {"MP3": "mp3", "WAV": "pcm_", "M4A": "aac"}[fmt]
            kontrol(f"{fmt} codec doğrulama (ffprobe)", beklenen in p.stdout, f"({p.stdout.strip()})")
        tipler = [o["tip"] for o in olaylar]
        kontrol(f"{fmt} olay akışı", tipler[0] == "basladi" and "ilerleme" in tipler
                and tipler[-1] == "bitti")

    # --- Çoklu link kuyruğu ---
    k = cikti / "kuyruk"
    k.mkdir()
    sonuc, olaylar = indir([f"{taban}/ornek.mp4", f"{taban}/ornek2.mp4"], "MP3", "128 kbps", k)
    kontrol("Çoklu link kuyruğu (2 ögeli)", sonuc["basarili"] == 2 and len(list(k.glob("*.mp3"))) == 2)

    # --- Oynatma listesi (RSS akışı = yt-dlp generic playlist) ---
    (sunucu_kok / "liste.xml").write_text(
        f'<?xml version="1.0"?><rss version="2.0"><channel><title>Deneme Listesi</title>'
        f'<item><title>Bir</title><enclosure url="{taban}/ornek.mp4" type="video/mp4"/></item>'
        f'<item><title>Iki</title><enclosure url="{taban}/ornek2.mp4" type="video/mp4"/></item>'
        f'</channel></rss>', encoding="utf-8")
    k = cikti / "liste"
    k.mkdir()
    sonuc, olaylar = indir([f"{taban}/liste.xml"], "MP3", "128 kbps", k, liste=True)
    mp3ler = list(k.rglob("*.mp3"))
    kontrol("Oynatma listesi (tüm ögeler)", len(mp3ler) == 2,
            f"({len(mp3ler)} dosya; hata={sonuc['hatalar']})")
    kl = cikti / "liste_tek"
    kl.mkdir()
    sonuc, _ = indir([f"{taban}/liste.xml"], "MP3", "128 kbps", kl, liste=False)
    kontrol("Liste kapalıyken yalnızca ilk video", len(list(kl.rglob("*.mp3"))) == 1)

    # --- İptal: tüm kuyruk ---
    k = cikti / "iptal"
    k.mkdir()
    olaylar, ekle = olaylari_topla()
    motor = IndirmeMotoru(on_olay=ekle)
    t = threading.Thread(target=motor.indir,
                         args=([f"{taban}/yavas1.mp4"], "MP4", "En iyi", str(k), False))
    t.start()
    bas = time.time()
    while time.time() - bas < 15 and not any(o["tip"] == "ilerleme" for o in olaylar):
        time.sleep(0.1)
    motor.iptal_et()
    t.join(20)
    kalan = [p.name for p in k.iterdir()]
    bitti = [o for o in olaylar if o["tip"] == "bitti"]
    kontrol("İptal (tüm kuyruk) — motor durdu", not t.is_alive() and bitti and bitti[-1]["iptal"])
    kontrol("İptal sonrası yarım dosya kalmadı", not kalan, f"({kalan})")

    # --- İptal: tek öge atlanır, sıradaki devam eder ---
    k = cikti / "oge_iptal"
    k.mkdir()
    olaylar, ekle = olaylari_topla()
    motor = IndirmeMotoru(on_olay=ekle)
    t = threading.Thread(target=motor.indir,
                         args=([f"{taban}/yavas2.mp4", f"{taban}/ornek.mp4"], "MP4", "En iyi",
                               str(k), False))
    t.start()
    bas = time.time()
    while time.time() - bas < 15 and not any(o["tip"] == "ilerleme" for o in olaylar):
        time.sleep(0.1)
    motor.oge_iptal_et(1)
    t.join(30)
    bitenler = {o["sira"]: o for o in olaylar if o["tip"] == "oge_bitti"}
    kontrol("Tek öge iptali: 1. öge atlandı", bitenler.get(1, {}).get("iptal") is True)
    kontrol("Tek öge iptali: 2. öge indi", bitenler.get(2, {}).get("basarili") is True)

    # --- Duraklat: tek öge duraklatılır (.part korunur), sıradaki devam eder ---
    k = cikti / "oge_duraklat"
    k.mkdir()
    olaylar, ekle = olaylari_topla()
    motor = IndirmeMotoru(on_olay=ekle)
    t = threading.Thread(target=motor.indir,
                         args=([f"{taban}/yavas3.mp4", f"{taban}/ornek.mp4"], "MP4", "En iyi",
                               str(k), False))
    t.start()
    bas = time.time()
    while time.time() - bas < 15 and not any(o["tip"] == "ilerleme" for o in olaylar):
        time.sleep(0.1)
    motor.oge_duraklat(1)
    t.join(30)
    bitenler = {o["sira"]: o for o in olaylar if o["tip"] == "oge_bitti"}
    kontrol("Tek öge duraklatma: 1. öge duraklatıldı", bitenler.get(1, {}).get("duraklatildi") is True)
    kontrol("Tek öge duraklatma: 2. öge indi", bitenler.get(2, {}).get("basarili") is True)

    # --- Hata mesajları ---
    sonuc, olaylar = indir([f"{taban}/yok.mp4"], "MP4", "En iyi", cikti)
    hata = sonuc["hatalar"][0] if sonuc["hatalar"] else ""
    kontrol("Hata Türkçe ve kullanıcı dostu", sonuc["basarili"] == 0 and hata
            and "HTTP" not in hata and "Traceback" not in hata and "FFmpeg" not in hata,
            f"({hata})")
    kontrol("Hatalı klasör ön kontrolü", "klasör" in (indir([f"{taban}/ornek.mp4"], "MP4", "En iyi",
                                                          cikti / "yok_klasor")[0]["hatalar"] or [""])[0].lower())
    kontrol("errors.hata_turkce bot koruması",
            "bot" in (errors.hata_turkce("Sign in to confirm you're not a bot") or "").lower())

    # --- Geçmiş ---
    history.temizle()
    history.ekle("Deneme", str(cikti / "a.mp3"), str(cikti), "MP3", "192 kbps")
    history.ekle("Deneme 2", str(cikti / "b.mp3"), str(cikti), "MP3", "192 kbps")
    kontrol("Geçmiş ekle/listele", [k["baslik"] for k in history.liste()][:2] == ["Deneme 2", "Deneme"])
    history.cikar(str(cikti / "a.mp3"))
    kontrol("Geçmişten çıkarma", len(history.liste()) == 1)
    history.temizle()
    kontrol("Geçmişi temizleme", history.liste() == [])

    srv.shutdown()


if __name__ == "__main__":
    main()
    gecen = sum(SONUCLAR)
    print(f"\nSONUÇ: {gecen}/{len(SONUCLAR)} test geçti")
    sys.exit(0 if gecen == len(SONUCLAR) else 1)
