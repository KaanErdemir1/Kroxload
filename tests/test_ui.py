"""Arayüz (UI/UX) uçtan uca doğrulama ve görsel inceleme testi.

Çalıştırma:  python tests/test_ui.py [ekran_goruntusu_klasoru]
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="kroxload_ui_appdata_")

import tkinter as tk  # noqa: E402
from unittest.mock import patch  # noqa: E402
from PIL import Image, ImageGrab  # noqa: E402

from kroxload.core import history  # noqa: E402
from kroxload.core.paths import ffmpeg_klasoru  # noqa: E402
from kroxload.ui.desktop import MENU_SIRASI, App  # noqa: E402
from kroxload.ui.theme import tema  # noqa: E402

SONUCLAR = []
GORUNTU_KLASORU = Path(sys.argv[1]) if len(sys.argv) > 1 else None
KOYU_RENKLER = {"gray17", "#2b2b2b", "#0e0e13", "#16161d", "#0a0a0e", "#1d1d26", "#23232f"}


def kontrol(ad, kosul, ayrinti=""):
    SONUCLAR.append(bool(kosul))
    print(("PASS" if kosul else "FAIL"), "-", ad, ayrinti)


def bekle(app, ms):
    bitti = [False]
    app.after(ms, lambda: bitti.__setitem__(0, True))
    while not bitti[0]:
        app.update()


def fare_tikla(widget):
    """Tk olay dağıtımı üzerinden gerçek bir tıklama (basma + bırakma) gönderir."""
    widget.update_idletasks()
    hedef = getattr(getattr(widget, "_metin_lbl", None), "_label", None) or widget
    hedef.update_idletasks()
    x, y = max(1, hedef.winfo_width() // 2), max(1, hedef.winfo_height() // 2)
    hedef.event_generate("<Enter>", x=x, y=y)
    hedef.event_generate("<ButtonPress-1>", x=x, y=y)
    hedef.event_generate("<ButtonRelease-1>", x=x, y=y)
    for _ in range(5):
        time.sleep(0.01)
        widget.update()


def koyu_artik_sayisi(kok):
    sayac = 0
    for w in tk.Frame.winfo_children(kok):
        for k in ("fg_color", "bg_color", "bg"):
            try:
                v = str(w.cget(k)).lower()
                if v in KOYU_RENKLER:
                    sayac += 1
            except Exception:
                pass
        if isinstance(w, tk.Canvas):
            for tag in ("inner_parts", "border_parts"):
                try:
                    v = str(w.itemcget(tag, "fill")).lower()
                    if v in KOYU_RENKLER:
                        sayac += 1
                except Exception:
                    pass
        sayac += koyu_artik_sayisi(w)
    return sayac


def metin_var_mi(kok, aranan):
    for w in kok.winfo_children():
        try:
            t = str(w.cget("text"))
            if aranan in t:
                return True
        except Exception:
            pass
        if metin_var_mi(w, aranan):
            return True
    return False


def ekran_yakala(app, dosya_adi):
    if not GORUNTU_KLASORU:
        return
    try:
        GORUNTU_KLASORU.mkdir(parents=True, exist_ok=True)
        app.attributes("-topmost", True)
        app.update()
        bekle(app, 120)
        x = app.winfo_rootx()
        y = app.winfo_rooty()
        w = app.winfo_width()
        h = app.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        img.save(GORUNTU_KLASORU / dosya_adi)
    except Exception as e:
        print("Ekran görüntüsü alınamadı:", e)


def main():
    gecici = Path(tempfile.mkdtemp(prefix="kroxload_ui_media_"))
    ff = Path(ffmpeg_klasoru())
    ornek_video = gecici / "Stüdyo Kaydı 1080p.mp4"
    ornek_ses = gecici / "Akustik Gitar Kaydı.wav"
    subprocess.run(
        [str(ff / "ffmpeg.exe"), "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=640x360:rate=15:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:v", "mpeg4", "-c:a", "aac", "-shortest", str(ornek_video)],
        check=True,
    )
    subprocess.run(
        [str(ff / "ffmpeg.exe"), "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "sine=frequency=330:duration=2", str(ornek_ses)],
        check=True,
    )

    app = App()
    app.geometry("1080x720+80+60")
    bekle(app, 250)

    # 1. Navigasyon sırası kontrolü
    beklenen_sira = ["Ana Sayfa", "Geçmiş", "Ayarlar", "Dönüştürücü"]
    gercek_sira = [baslik for _, baslik, _ in MENU_SIRASI]
    kontrol("Navigasyon sıralaması (Ana Sayfa, Geçmiş, Ayarlar, Dönüştürücü)", gercek_sira == beklenen_sira)
    kontrol("Başlangıç sayfası Ana Sayfa", app.aktif_sayfa == "ana")

    # 2. Ana Sayfa kontrolleri
    ana = app.sayfalar["ana"]
    kontrol("Ana Sayfa: Sağ üstteki YouTube/SoundCloud kutusu kaldırıldı",
            not metin_var_mi(ana, "SoundCloud"))
    ana.format_sb.sec("MP3", bildir=True)
    bekle(app, 80)
    kontrol("Ana Sayfa: MP3 seçilince bitrate seçenekleri geldi",
            "320 kbps" in ana.kalite_sb._secenekler)
    ana.format_sb.sec("Video (MP4)", bildir=True)
    bekle(app, 80)
    kontrol("Ana Sayfa: MP4 seçilince çözünürlük seçenekleri geldi",
            "1080p" in ana.kalite_sb._secenekler)

    # Hızlı erişim kısayolları
    ks = ana.kisayol_seridi.kisayollar
    kontrol("Ana Sayfa: 6 platform kısayolu var", len(ks) == 6, [k.ad for k in ks])
    with patch("kroxload.ui.shortcuts.webbrowser.open") as m_web:
        e = type("E", (), {"x": 5, "y": 5})()
        ks[0]._birak(e)
        bekle(app, 60)
        kontrol("Ana Sayfa: YouTube kısayolu tarayıcıyı açtı",
                m_web.called and "youtube.com" in m_web.call_args[0][0])

    # Klasör Değiştir butonu fare tıklama testi (Issue #4)
    yeni_kl_1 = str(gecici / "TestKlasorAna")
    os.makedirs(yeni_kl_1, exist_ok=True)
    with patch("kroxload.ui.page_home.filedialog.askdirectory", return_value=yeni_kl_1) as m_ask:
        fare_tikla(ana.klasor_degistir_btn)
        kontrol("Ana Sayfa: Klasör Değiştir butonu fare tıklamasıyla diyaloğu açtı ve klasörü güncelledi",
                m_ask.called and os.path.normpath(app.klasor) == os.path.normpath(yeni_kl_1))

    # Örnek kuyruk satırları (görsel ve işlevsel doğrulama)
    s1 = ana._satir_ekle(99, 1, "https://youtube.com/watch?v=ornek1", "MP4", "1080p", str(gecici), False,
                         "KXR YAZILIM — Masaüstü Medya Mimarisi ve Ses İşleme Rehberi (4K 60fps)")
    s1.ilerleme_guncelle({
        "asama": "indiriliyor", "oran": 0.64, "hiz": "11.8 MB/s", "kalan": "00:04",
        "indirilen": 42_500_000, "toplam_byte": 66_400_000,
    })
    s2 = ana._satir_ekle(98, 1, "https://youtube.com/watch?v=ornek2", "MP3", "320 kbps", str(gecici), False,
                         "Synthwave Gece Sürüşü — Kayıpsız Stüdyo Miksi")
    s2.bitti_guncelle({"basarili": True, "dosyalar": [str(ornek_video)]})
    bekle(app, 200)
    ekran_yakala(app, "01_ana_sayfa_koyu.png")

    ana.bitenleri_temizle()
    kontrol("Ana Sayfa: tamamlananları temizle çalıştı", s2 not in ana.satirlar and s1 in ana.satirlar)
    ana.satir_kaldir(s1)

    # 3. Dönüştürücü sayfası ve gerçek FFmpeg dönüştürmesi
    app.sayfa_sec("donusturucu")
    bekle(app, 220)
    kontrol("Dönüştürücü sayfasına geçiş", app.aktif_sayfa == "donusturucu")

    don = app.sayfalar["donusturucu"]
    with patch("kroxload.ui.page_converter.filedialog.askopenfilenames",
               return_value=(str(ornek_video), str(ornek_ses))) as m_files:
        fare_tikla(don.dosya_ekle_btn)
        kontrol("Dönüştürücü: Dosya Seç butonu fare tıklamasıyla diyaloğu açtı",
                m_files.called)

    yeni_kl_don = str(gecici / "TestKlasorDon")
    os.makedirs(yeni_kl_don, exist_ok=True)
    with patch("kroxload.ui.page_converter.filedialog.askdirectory", return_value=yeni_kl_don) as m_dkl:
        fare_tikla(don.cikti_klasor_btn)
        kontrol("Dönüştürücü: Çıktı Klasörü Seç butonu fare tıklamasıyla çalıştı",
                m_dkl.called and os.path.normpath(app.ayarlar.get("donusum_klasor", "")) == os.path.normpath(yeni_kl_don))
    app.ayar_guncelle(donusum_klasor="")
    don.cikti_etiketi_guncelle()

    # FFprobe incelemesinin tamamlanmasını bekle
    for _ in range(40):
        bekle(app, 100)
        if all(s.bilgi is not None for s in don.satirlar):
            break
    kontrol("Dönüştürücü: FFprobe ile kaynak dosyalar incelendi",
            len(don.satirlar) == 2 and all(s.bilgi is not None for s in don.satirlar))

    don.mod_sb.sec("Video → Ses", bildir=True)
    don.hedef_fmt_sb.sec("MP3", bildir=True)
    bekle(app, 150)
    ekran_yakala(app, "04_donusturucu_koyu.png")

    don.baslat()
    for _ in range(100):
        bekle(app, 120)
        if not (don.motor and don.motor.calisiyor):
            break
    kontrol("Dönüştürücü: 2 dosya arayüz üzerinden MP3'e dönüştürüldü",
            all(s.durum_kodu == "tamam" for s in don.satirlar))

    # 4. Geçmiş sayfası doğrulaması
    app.sayfa_sec("gecmis")
    bekle(app, 240)
    gecmis = app.sayfalar["gecmis"]
    kontrol("Geçmiş: dönüştürülen dosyalar kalıcı geçmişe eklendi",
            len(history.liste()) >= 2 and len(gecmis.satir_widgetlar) >= 2)
    ekran_yakala(app, "02_gecmis_koyu.png")

    gecmis.filtre_sb.sec("Dönüştürmeler", bildir=True)
    bekle(app, 100)
    kontrol("Geçmiş: Dönüştürmeler filtresi çalışıyor", len(gecmis.satir_widgetlar) >= 2)
    gecmis.filtre_sb.sec("Tümü", bildir=True)

    # 5. Ayarlar sayfası, klasör butonları ve Açık/Koyu tema geçişi
    app.sayfa_sec("ayarlar")
    bekle(app, 240)
    ayarlar_s = app.sayfalar["ayarlar"]
    yeni_kl_ayar = str(gecici / "TestKlasorAyar")
    os.makedirs(yeni_kl_ayar, exist_ok=True)
    with patch("kroxload.ui.page_settings.filedialog.askdirectory", return_value=yeni_kl_ayar) as m_akl1:
        fare_tikla(ayarlar_s.indir_kl_degistir_btn)
        kontrol("Ayarlar: İndirme Klasörü Değiştir butonu fare tıklamasıyla çalıştı",
                m_akl1.called and os.path.normpath(app.klasor) == os.path.normpath(yeni_kl_ayar))
    with patch("kroxload.ui.page_settings.filedialog.askdirectory", return_value=yeni_kl_ayar) as m_akl2:
        fare_tikla(ayarlar_s.don_kl_sec_btn)
        kontrol("Ayarlar: Dönüştürücü Klasörü Seç butonu fare tıklamasıyla çalıştı",
                m_akl2.called and os.path.normpath(app.ayarlar.get("donusum_klasor", "")) == os.path.normpath(yeni_kl_ayar))
    ayarlar_s._don_klasor_sifirla()

    ekran_yakala(app, "03_ayarlar_koyu.png")

    app.tema_ayarla("acik")
    bekle(app, 320)
    kontrol("Tema geçişi: Açık tema etkinleşti", tema.ad == "acik" and app.ayarlar["tema"] == "acik")
    kontrol("Açık tema (Ayarlar): Siyah/koyu renk artığı yok", koyu_artik_sayisi(ayarlar_s) == 0)
    ekran_yakala(app, "05_ayarlar_acik.png")

    app.sayfa_sec("ana")
    bekle(app, 180)
    # Açık temada segment tıklamaları (Issue #2)
    ana.format_sb.sec("MP3", bildir=True)
    ana.format_sb.sec("WAV", bildir=True)
    ana.format_sb.sec("Video (MP4)", bildir=True)
    ana.kalite_sb.sec("720p", bildir=True)
    bekle(app, 120)
    kontrol("Açık tema (Ana Sayfa): Tıklama sonrası siyah/koyu renk artığı yok",
            koyu_artik_sayisi(ana) == 0)
    ekran_yakala(app, "06_ana_sayfa_acik.png")

    app.sayfa_sec("gecmis")
    bekle(app, 180)
    gecmis.filtre_sb.sec("Dönüştürmeler", bildir=True)
    gecmis.filtre_sb.sec("Tümü", bildir=True)
    bekle(app, 100)
    kontrol("Açık tema (Geçmiş): Tıklama sonrası siyah/koyu renk artığı yok",
            koyu_artik_sayisi(gecmis) == 0)
    ekran_yakala(app, "07_gecmis_acik.png")

    app.sayfa_sec("donusturucu")
    bekle(app, 180)
    don.mod_sb.sec("Ses → Ses", bildir=True)
    don.mod_sb.sec("Video → Ses", bildir=True)
    bekle(app, 100)
    kontrol("Açık tema (Dönüştürücü): Tıklama sonrası siyah/koyu renk artığı yok",
            koyu_artik_sayisi(don) == 0)
    ekran_yakala(app, "08_donusturucu_acik.png")

    app.tema_ayarla("koyu")
    bekle(app, 320)
    kontrol("Tema geçişi: Koyu temaya geri dönüldü", tema.ad == "koyu")

    app.kapat()


if __name__ == "__main__":
    main()
    gecen = sum(SONUCLAR)
    print(f"\nSONUÇ: {gecen}/{len(SONUCLAR)} UI testi geçti")
    sys.exit(0 if gecen == len(SONUCLAR) else 1)

