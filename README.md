# Kroxload

Modern, hızlı ve profesyonel masaüstü medya indirici ve dönüştürücü (**KXR YAZILIM**).
YouTube ve `yt-dlp` tarafından desteklenen yüzlerce platformdan video/ses indirir; yerleşik **FFmpeg & FFprobe** motoruyla yerel ses ve video dosyalarını dönüştürür.

## Temel Özellikler (v1.1.0)

- **Ana Sayfa (Medya İndirici):**
  - Çoklu URL kuyruğu, otomatik pano algılama ve canlı medya önizlemesi (küçük resim, kanal, süre).
  - Format ve kalite seçimi (`MP3`, `WAV`, `MP4`, `M4A`), oynatma listesi desteği.
  - Her indirme için canlı hız, boyut, kalan süre (ETA), **Duraklat / Devam Et**, **İptal**, **Yeniden Dene**, **Dosyayı Aç** ve **Klasörde Göster** aksiyonları.
- **Dönüştürücü (Yerel FFmpeg & FFprobe):**
  - **Ses → Ses:** `MP3`, `WAV`, `FLAC`, `AAC`, `OGG`, `M4A`
  - **Video → Video:** `MP4`, `MKV`, `AVI`, `MOV`, `WEBM`
  - **Video → Ses:** `MP3`, `WAV`, `FLAC`, `AAC`, `OGG`, `M4A`
  - **Ses → Video:** Ses dosyası + kapak görseli (`PNG`/`JPG`/`WEBP`) birleştirerek video üretimi (`MP4`, `MKV`, `WEBM`, `MOV`, `AVI`)
  - Sürükle-bırak (`tkinterdnd2`), çoklu dosya kuyruğu, FFprobe akış analizi, dinamik codec/bitrate/çözünürlük/örnekleme hızı seçimi ve canlı ilerleme yüzdesi.
- **Geçmiş:**
  - Kalıcı indirme ve dönüştürme geçmişi (`%APPDATA%\Kroxload\gecmis.json`), kategori filtreleri (`Tümü`, `İndirmeler`, `Dönüştürmeler`, `Başarısız`) ve anlık arama.
- **Ayarlar & Tema:**
  - **Koyu Tema (Dark Mode)** ve **Açık Tema (Light Mode)** — yumuşak renk geçiş animasyonlu.
  - Tek tıkla `yt-dlp` motoru güncelleme, FFmpeg/FFprobe durum doğrulaması ve bildirim/animasyon tercihleri.

## Derleme

Gereksinimler: Python 3.10+, `pip install customtkinter yt-dlp pillow tkinterdnd2 pyinstaller`, Inno Setup 6 ve `deps/ffmpeg/` (LGPL shared FFmpeg).

```bash
build.bat
```

Çıktılar:
- `release/Kroxload_Setup.exe`
- `release/Kroxload_Portable.zip`

FFmpeg ve FFprobe uygulamayla birlikte paketlenir (`_internal/ffmpeg`); kullanıcının ayrıca Python veya FFmpeg kurmasına gerek yoktur.

## Testler

```bash
python tests/test_engine.py
python tests/test_converter.py
python tests/test_ui.py
```


## Proje Yapısı

```
main.py                      Giriş noktası (exe bu dosyadan derlenir)
kroxload/
  core/                      Arayüzden bağımsız çekirdek katman
    engine.py                Olay tabanlı indirme motoru (duraklat/iptal/kuyruk)
    converter.py             FFmpeg & FFprobe medya dönüştürme motoru
    info.py                  Medya önizleme ve meta veri sorgulama
    history.py               Kalıcı indirme ve dönüştürme geçmişi
    settings.py              Kalıcı kullanıcı ayarları
    errors.py                Türkçe kullanıcı dostu hata çevirici
    logs.py                  Dönen log sistemi ve çökme yakalayıcı
    updater.py               yt-dlp motor güncelleyici
    formats.py               İndirme format ve kalite tanımları
    paths.py                 Veri klasörü, kaynak yolları ve paketli FFmpeg çözümü
    ytdlp.py                 Dinamik yt-dlp yükleyici
  ui/                        Modern masaüstü arayüz katmanı
    theme.py                 Koyu/Açık renk paletleri, tipografi ve tema animatörü
    widgets.py               Özel bileşenler (Segment, Anahtar, Buton, Bildirim vb.)
    desktop.py               Ana pencere, sol navigasyon ve sayfa geçiş yöneticisi
    page_home.py             Ana Sayfa (İndirme merkezi)
    page_converter.py        Dönüştürücü sayfası (Sürükle-bırak & FFmpeg kuyruğu)
    page_history.py          Geçmiş sayfası
    page_settings.py         Ayarlar ve Hakkında sayfası
assets/                      Kroxload logo ve ikon dosyaları (png + ico)
installer/Kroxload.iss       Inno Setup 6 kurulum betiği
tools/make_icon.py           Logo ve ikon üreteci
tools/make_portable.py       Taşınabilir (portable) ZIP paketleyici
tests/                       Otomatik motor, dönüştürücü ve arayüz testleri
```
