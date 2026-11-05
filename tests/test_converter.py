"""Dönüştürme motoru testleri — gerçek FFmpeg/FFprobe ile tüm biçim/codec kombinasyonları.

Çalıştırma:  python tests/test_converter.py
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="kroxload_appdata_")

from kroxload.core import converter as c  # noqa: E402
from kroxload.core.paths import ffmpeg_klasoru  # noqa: E402

FF = Path(ffmpeg_klasoru() or "")
SONUC = []


def kontrol(ad, kosul, ayrinti=""):
    SONUC.append(bool(kosul))
    print(("PASS" if kosul else "FAIL"), "-", ad, ayrinti)


def ff(*args):
    subprocess.run([str(FF / "ffmpeg.exe"), "-y", "-loglevel", "error", *args], check=True)


def calistir(isler):
    olaylar = []
    motor = c.DonusumMotoru(on_olay=olaylar.append)
    sonuc = motor.donustur(isler)
    return sonuc, olaylar


def is_(kaynak, klasor, tur, fmt, **kw):
    d = {"kaynak": str(kaynak), "hedef_tur": tur, "format": fmt, "klasor": str(klasor)}
    d.update(kw)
    return d


def main():
    gecici = Path(tempfile.mkdtemp(prefix="kroxload_conv_"))
    kaynak = gecici / "kaynak"
    kaynak.mkdir()
    # Kaynaklar: Türkçe karakter + boşluklu adlar (yol dayanıklılığı)
    video = kaynak / "Örnek video şğü.mp4"
    ses = kaynak / "ses örnek.wav"
    ff("-f", "lavfi", "-i", "testsrc=size=640x480:rate=15:duration=3",
       "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
       "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(video))
    ff("-f", "lavfi", "-i", "sine=frequency=330:duration=3", str(ses))
    sessiz_video = kaynak / "sessiz.mp4"
    ff("-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2", "-c:v", "mpeg4", str(sessiz_video))
    from PIL import Image
    gorsel = kaynak / "kapak görsel.png"
    Image.new("RGB", (900, 900), (90, 70, 200)).save(gorsel)

    # --- Sonda ---
    b = c.sonda(video)
    kontrol("sonda: video+ses bilgisi", b["video"] and b["ses"] and abs(b["sure"] - 3) < 0.5
            and b["video"]["yukseklik"] == 480, f"({b['video']['codec']}, {b['ses']['codec']})")
    kontrol("sonda: yalnız ses", c.sonda(ses)["video"] is None)
    metin = kaynak / "metin.txt"
    metin.write_text("merhaba", encoding="utf-8")
    try:
        c.sonda(metin)
        kontrol("sonda: medya olmayan dosya reddedilir", False)
    except ValueError as e:
        kontrol("sonda: medya olmayan dosya reddedilir (Türkçe mesaj)", "dosya" in str(e).lower(), f"({e})")

    beklenen_ses = {"MP3": "mp3", "WAV": "pcm_s16le", "FLAC": "flac", "AAC": "aac",
                    "OGG": "vorbis", "M4A": "aac"}

    # --- Ses -> Ses ve Video -> Ses (tüm formatlar) ---
    for kaynak_adi, yol in (("ses", ses), ("video", video)):
        for fmt in c.ses_formatlari():
            k = gecici / f"o_{kaynak_adi}_{fmt}"
            ayar = is_(yol, k, "ses", fmt, ses_bitrate="192" if c.SES_HEDEFLERI[fmt]["bitrate"] else None)
            sonuc, olaylar = calistir([ayar])
            dosyalar = list(k.glob("*" + c.SES_HEDEFLERI[fmt]["uzanti"])) if k.exists() else []
            ok = sonuc["basarili"] == 1 and len(dosyalar) == 1
            kontrol(f"{kaynak_adi} -> {fmt}", ok, f"({sonuc['hatalar']})" if not ok else "")
            if ok:
                bi = c.sonda(dosyalar[0])
                kontrol(f"  {fmt} codec={bi['ses']['codec']} süre={bi['sure']:.1f}s",
                        bi["ses"]["codec"].startswith(beklenen_ses[fmt][:4]) and abs(bi["sure"] - 3) < 0.6)
                kontrol(f"  {fmt} geçici dosya kalmadı", not list(k.glob("*tmp*")))

    # Codec seçenekleri
    k = gecici / "o_wav24"
    sonuc, _ = calistir([is_(ses, k, "ses", "WAV", ses_codec="pcm_s24le")])
    kontrol("WAV 24-bit codec seçimi", sonuc["basarili"] == 1 and
            c.sonda(next(k.glob("*.wav")))["ses"]["codec"] == "pcm_s24le")
    k = gecici / "o_opus"
    sonuc, _ = calistir([is_(ses, k, "ses", "OGG", ses_codec="libopus", ses_bitrate="128")])
    kontrol("OGG içinde Opus codec seçimi", sonuc["basarili"] == 1 and
            c.sonda(next(k.glob("*.ogg")))["ses"]["codec"] == "opus")
    k = gecici / "o_ornek"
    sonuc, _ = calistir([is_(ses, k, "ses", "MP3", ses_bitrate="128", ornekleme=48000, kanal=1)])
    bi = c.sonda(next(k.glob("*.mp3"))) if sonuc["basarili"] else None
    kontrol("Örnekleme 48 kHz + mono", bi and bi["ses"]["hz"] == 48000 and bi["ses"]["kanal"] == 1)

    # --- Video -> Video (tüm kapsayıcı x codec) ---
    for fmt in c.video_formatlari():
        d = c.VIDEO_HEDEFLERI[fmt]
        for vc in c.mevcut(d["video"]):
            ac = c.mevcut(d["ses"])[0]
            k = gecici / f"o_v_{fmt}_{vc}"
            ayar = is_(video, k, "video", fmt, video_codec=vc, ses_codec=ac, ses_bitrate="128",
                       kalite="Dengeli", cozunurluk=360)
            sonuc, _ = calistir([ayar])
            dosyalar = list(k.glob("*" + d["uzanti"])) if k.exists() else []
            ok = sonuc["basarili"] == 1 and len(dosyalar) == 1
            kontrol(f"video -> {fmt} ({vc} + {ac})", ok, f"({sonuc['hatalar']})" if not ok else "")
            if ok:
                bi = c.sonda(dosyalar[0])
                kontrol(f"  {fmt}/{vc}: çözünürlük 360p, ses var, süre uygun",
                        bi["video"]["yukseklik"] == 360 and bi["ses"] and abs(bi["sure"] - 3) < 0.8,
                        f"({bi['video']['genislik']}x{bi['video']['yukseklik']}, {bi['video']['codec']})")

    # Orijinal çözünürlük + sessiz video
    k = gecici / "o_orijinal"
    sonuc, _ = calistir([is_(sessiz_video, k, "video", "MP4", video_codec="libopenh264",
                             ses_codec="aac", ses_bitrate="128", kalite="Yüksek")])
    bi = c.sonda(next(k.glob("*.mp4"))) if sonuc["basarili"] else None
    kontrol("Sessiz video -> MP4 (orijinal çözünürlük korunur)",
            bi and bi["video"]["yukseklik"] == 240 and bi["ses"] is None, f"({sonuc['hatalar']})")

    # --- Ses -> Video (görselli ve görselsiz) ---
    k = gecici / "o_sv_gorselli"
    sonuc, _ = calistir([is_(ses, k, "video", "MP4", video_codec="libopenh264", ses_codec="aac",
                             ses_bitrate="128", kalite="Dengeli", cozunurluk=480, gorsel=str(gorsel))])
    bi = c.sonda(next(k.glob("*.mp4"))) if sonuc["basarili"] else None
    kontrol("Ses -> Video (görselle)", bi and bi["video"] and bi["ses"] and abs(bi["sure"] - 3) < 0.8
            and bi["video"]["yukseklik"] == 480, f"({sonuc['hatalar']})")
    k = gecici / "o_sv_duz"
    sonuc, _ = calistir([is_(ses, k, "video", "WEBM", video_codec="libvpx-vp9", ses_codec="libopus",
                             ses_bitrate="128", kalite="Küçük dosya", cozunurluk=360)])
    bi = c.sonda(next(k.glob("*.webm"))) if sonuc["basarili"] else None
    kontrol("Ses -> Video (görselsiz, düz arka plan, WEBM)", bi and bi["video"] and bi["ses"],
            f"({sonuc['hatalar']})")

    # --- Doğrulamalar ve hata mesajları ---
    sonuc, olaylar = calistir([is_(sessiz_video, gecici / "o_x", "ses", "MP3")])
    hata = sonuc["hatalar"][0] if sonuc["hatalar"] else ""
    kontrol("Sessiz videoyu sese çevirme: anlaşılır hata", "ses akışı yok" in hata, f"({hata})")
    sonuc, _ = calistir([is_(metin, gecici / "o_y", "ses", "MP3")])
    kontrol("Medya olmayan dosya: hata, çökme yok", sonuc["basarili"] == 0 and sonuc["hatalar"])
    sonuc, _ = calistir([is_(gecici / "yok.mp3", gecici / "o_z", "ses", "MP3")])
    kontrol("Olmayan dosya: hata", sonuc["basarili"] == 0 and "bulunamadı" in sonuc["hatalar"][0].lower())

    # --- Çakışma: var olan dosyanın üzerine yazmaz ---
    k = gecici / "o_cakisma"
    calistir([is_(ses, k, "ses", "MP3", ses_bitrate="128")])
    calistir([is_(ses, k, "ses", "MP3", ses_bitrate="128")])
    kontrol("Aynı ad varsa '(1)' eklenir, üzerine yazılmaz", len(list(k.glob("*.mp3"))) == 2)
    # Kaynağın kendisiyle aynı yol: kaynak klasörüne aynı biçime çevirme
    sonuc, _ = calistir([is_(ses, kaynak, "ses", "WAV")])
    kontrol("Kaynakla aynı yol üzerine yazılmaz", sonuc["basarili"] == 1 and ses.exists()
            and (kaynak / "ses örnek (1).wav").exists())

    # --- Çoklu kuyruk, olay akışı ---
    k = gecici / "o_coklu"
    sonuc, olaylar = calistir([is_(ses, k, "ses", "MP3", ses_bitrate="128"),
                               is_(video, k, "ses", "FLAC"),
                               is_(metin, k, "ses", "MP3")])
    tipler = [o["tip"] for o in olaylar]
    kontrol("Kuyruk: 2 başarılı, 1 başarısız", sonuc["basarili"] == 2 and len(sonuc["hatalar"]) == 1)
    kontrol("Kuyruk: ilerleme olayları %100'e ulaştı",
            any(o["tip"] == "ilerleme" for o in olaylar) and tipler[-1] == "bitti")

    # --- İptal (tüm kuyruk ve tek öge) ---
    uzun = kaynak / "uzun.wav"
    ff("-f", "lavfi", "-i", "sine=frequency=220:duration=600", "-ar", "48000", str(uzun))
    k = gecici / "o_iptal"
    olaylar = []
    motor = c.DonusumMotoru(on_olay=olaylar.append)
    t = threading.Thread(target=motor.donustur,
                         args=([is_(uzun, k, "video", "WEBM", video_codec="libvpx-vp9",
                                    ses_codec="libopus", kalite="Yüksek", cozunurluk=1080)],))
    t.start()
    bas = time.time()
    while time.time() - bas < 20 and not any(o["tip"] == "ilerleme" for o in olaylar):
        time.sleep(0.1)
    motor.iptal_et()
    t.join(20)
    kalan = [p.name for p in k.iterdir()] if k.exists() else []
    kontrol("İptal: işlem durdu", not t.is_alive() and olaylar[-1]["iptal"])
    kontrol("İptal: yarım çıktı bırakılmadı", not kalan, f"({kalan})")

    k = gecici / "o_oge_iptal"
    olaylar = []
    motor = c.DonusumMotoru(on_olay=olaylar.append)
    t = threading.Thread(target=motor.donustur,
                         args=([is_(uzun, k, "video", "WEBM", video_codec="libvpx-vp9",
                                    ses_codec="libopus", kalite="Yüksek", cozunurluk=1080),
                                is_(ses, k, "ses", "MP3", ses_bitrate="128")],))
    t.start()
    bas = time.time()
    while time.time() - bas < 20 and not any(o["tip"] == "ilerleme" for o in olaylar):
        time.sleep(0.1)
    motor.oge_iptal_et(1)
    t.join(30)
    bit = {o["sira"]: o for o in olaylar if o["tip"] == "oge_bitti"}
    kontrol("Tek öge iptali: 1. atlandı, 2. tamamlandı",
            bit.get(1, {}).get("iptal") is True and bit.get(2, {}).get("basarili") is True)

    # --- Hata çevirisi ---
    from kroxload.core.errors import donusum_hata_turkce
    kontrol("hata çevirisi: bozuk dosya", "bozuk" in (donusum_hata_turkce("Invalid data found when processing input") or ""))
    kontrol("hata çevirisi: codec uyumsuz", "codec" in (donusum_hata_turkce("Encoder 'x' not found") or "").lower())


if __name__ == "__main__":
    main()
    gecen = sum(SONUC)
    print(f"\nSONUÇ: {gecen}/{len(SONUC)} test geçti")
    sys.exit(0 if gecen == len(SONUC) else 1)

