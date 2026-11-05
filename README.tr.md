# Kroxload

[🇬🇧 English](README.md) | [🇹🇷 Türkçe](README.tr.md)

**KXR YAZILIM** tarafından geliştirilen modern, hızlı ve profesyonel masaüstü medya indirici ve dönüştürücü.

YouTube ve `yt-dlp` tarafından desteklenen yüzlerce platformdan video ve ses indirin. Yerleşik **FFmpeg & FFprobe** motoruyla yerel ses ve video dosyalarınızı kolayca dönüştürün.

## Temel Özellikler (v1.1.0)

- **Ana Sayfa (Medya İndirici):**
  - Çoklu URL kuyruğu, otomatik pano algılama ve canlı medya önizlemesi (küçük resim, kanal, süre).
  - Format ve kalite seçimi (`MP3`, `WAV`, `MP4`, `M4A`) ve oynatma listesi desteği.
  - Her indirme için canlı hız, dosya boyutu ve tahmini kalan süre (ETA) takibi.
  - **Duraklat / Devam Et**, **İptal**, **Yeniden Dene**, **Dosyayı Aç** ve **Klasörde Göster** işlemleri.

- **Dönüştürücü (Yerel FFmpeg & FFprobe):**
  - **Ses → Ses:** `MP3`, `WAV`, `FLAC`, `AAC`, `OGG`, `M4A`
  - **Video → Video:** `MP4`, `MKV`, `AVI`, `MOV`, `WEBM`
  - **Video → Ses:** `MP3`, `WAV`, `FLAC`, `AAC`, `OGG`, `M4A`
  - **Ses → Video:** Ses dosyası ve kapak görselini (`PNG`/`JPG`/`WEBP`) birleştirerek video oluşturma (`MP4`, `MKV`, `WEBM`, `MOV`, `AVI`).
  - Sürükle-bırak desteği (`tkinterdnd2`), çoklu dosya kuyruğu, FFprobe akış analizi, dinamik codec/bitrate/çözünürlük/örnekleme hızı seçimi ve canlı ilerleme takibi.

- **Geçmiş:**
  - Kalıcı indirme ve dönüştürme geçmişi (`%APPDATA%\Kroxload\gecmis.json`).
  - Kategori filtreleri (`Tümü`, `İndirmeler`, `Dönüştürmeler`, `Başarısız`) ve anlık arama.

- **Ayarlar & Temalar:**
  - **Koyu Tema (Dark Mode)** ve **Açık Tema (Light Mode)** seçenekleri, yumuşak renk geçiş animasyonlarıyla birlikte.
  - Tek tıkla `yt-dlp` motoru güncelleme.
  - FFmpeg/FFprobe durum doğrulaması.
  - Bildirim ve animasyon tercihlerini yönetme.

## Derleme

**Gereksinimler:**

- Python 3.10+
- `customtkinter`
- `yt-dlp`
- `pillow`
- `tkinterdnd2`
- `pyinstaller`
- Inno Setup 6
- `deps/ffmpeg/` (LGPL shared FFmpeg)

Gerekli Python paketlerini yüklemek için:

```bash
pip install customtkinter yt-dlp pillow tkinterdnd2 pyinstaller
```

Projeyi derlemek için:

```bash
build.bat
```

**Derleme çıktıları:**

- `release/Kroxload_Setup.exe`
- `release/Kroxload_Portable.zip`

FFmpeg ve FFprobe uygulamayla birlikte paketlenir (`_internal/ffmpeg`). Bu sayede kullanıcıların ayrıca Python veya FFmpeg kurmasına gerek kalmaz.

## Testler

Testleri çalıştırmak için:

```bash
python tests/test_engine.py
python tests/test_converter.py
python tests/test_ui.py
```

## Proje Yapısı

```text
main.py                      Giriş noktası (EXE bu dosyadan derlenir)
kroxload/
  core/                      Arayüzden bağımsız çekirdek katman
    engine.py                Olay tabanlı indirme motoru (duraklatma/iptal/kuyruk)
    converter.py             FFmpeg & FFprobe medya dönüştürme motoru
    info.py                  Medya önizleme ve meta veri sorgulama
    history.py               Kalıcı indirme ve dönüştürme geçmişi
    settings.py              Kalıcı kullanıcı ayarları
    errors.py                Türkçe, kullanıcı dostu hata çevirici
    logs.py                  Dönen log sistemi ve çökme yakalayıcı
    updater.py               yt-dlp motor güncelleyici
    formats.py               İndirme format ve kalite tanımları
    paths.py                 Veri klasörleri, kaynak yolları ve paketli FFmpeg çözümleme
    ytdlp.py                 Dinamik yt-dlp yükleyici
  ui/                        Modern masaüstü arayüz katmanı
    theme.py                 Koyu/açık renk paletleri, tipografi ve tema animatörü
    widgets.py               Özel bileşenler (Segment, Anahtar, Buton, Bildirim vb.)
    desktop.py               Ana pencere, sol navigasyon ve sayfa geçiş yöneticisi
    page_home.py             Ana Sayfa (İndirme merkezi)
    page_converter.py        Dönüştürücü sayfası (Sürükle-bırak ve FFmpeg kuyruğu)
    page_history.py          Geçmiş sayfası
    page_settings.py         Ayarlar ve Hakkında sayfası
assets/                      Kroxload logo ve ikon dosyaları (PNG + ICO)
installer/Kroxload.iss       Inno Setup 6 kurulum betiği
tools/make_icon.py           Logo ve ikon üreticisi
tools/make_portable.py       Taşınabilir (portable) ZIP paketleyici
tests/                       Otomatik motor, dönüştürücü ve arayüz testleri
```
 
 
