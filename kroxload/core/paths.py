"""Dosya yolları: kalıcı veri klasörü, paketlenmiş kaynaklar, ffmpeg, günlükler.

Yol kuralı: kullanıcıya ait değişen veriler (%APPDATA%), salt-okunur program
dosyaları (kurulum klasörü) ve paketlenmiş kaynaklar (PyInstaller) ayrı tutulur.
Boşluk ve Türkçe karakter içeren yollar sorun çıkarmaz; hiçbir yerde kabuk
(dize birleştirmeli) komut kullanılmaz.
"""
import os
import shutil
import sys
from pathlib import Path


def veri_klasoru():
    """Kullanıcı verisi için kalıcı klasör (%APPDATA%\\Kroxload)."""
    kok = Path(os.environ.get("APPDATA") or Path.home()) / "Kroxload"
    try:
        kok.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    _eskiyi_tasi(Path(os.environ.get("APPDATA") or Path.home()) / "YouTubeIndirici", kok)
    return kok


def _eskiyi_tasi(eski, yeni):
    """Eski 'YouTubeIndirici' sürümünden ayar ve güncel yt-dlp'yi taşır (bir kez)."""
    if not eski.is_dir() or (yeni / "ayarlar.json").exists():
        return
    for ad in ("ayarlar.json", "yt-dlp.zip"):
        kaynak, hedef = eski / ad, yeni / ad
        if kaynak.exists() and not hedef.exists():
            try:
                shutil.move(str(kaynak), str(hedef))
            except Exception:
                pass


VERI_KLASORU = veri_klasoru()
AYAR_DOSYASI = VERI_KLASORU / "ayarlar.json"
GUNCEL_ZIP = VERI_KLASORU / "yt-dlp.zip"
GECMIS_DOSYASI = VERI_KLASORU / "gecmis.json"
LOG_KLASORU = VERI_KLASORU / "logs"
LOG_DOSYASI = LOG_KLASORU / "kroxload.log"


def uygulama_klasoru():
    """Çalışan programın (exe veya kaynak) klasörü."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def kaynak_yolu(goreli):
    """Paketlenmiş kaynak dosyanın (ikon vb.) yolu.

    Kaynaktan çalışırken proje köküne, derlenmiş exe'de PyInstaller'ın
    dosyaları yerleştirdiği klasöre (tek dosyada geçici extract, onedir'de
    _internal) bakar.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / goreli
    return Path(__file__).resolve().parent.parent.parent / goreli


def _ffmpeg_adaylari():
    """FFmpeg'in aranacağı klasörler, öncelik sırasıyla."""
    adaylar = [uygulama_klasoru()]  # 1) exe'nin yanı (kurulum / taşınabilir / kendi kopyası)
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            adaylar.append(Path(meipass) / "ffmpeg")  # 2) paketle gelen kopya (_internal/ffmpeg)
    else:
        adaylar.append(uygulama_klasoru() / "deps" / "ffmpeg")  # kaynaktan çalışırken
    return adaylar


def ffmpeg_klasoru():
    """ffmpeg.exe VE ffprobe.exe içeren ilk klasörü döndürür; yoksa None.

    Böylece kullanıcıdan FFmpeg kurması istenmez ve sistem PATH'ine
    bağımlılık kalmaz; uygulama kendi yanındaki kopyayı kullanır.
    """
    for aday in _ffmpeg_adaylari():
        try:
            if (aday / "ffmpeg.exe").exists() and (aday / "ffprobe.exe").exists():
                return str(aday)
        except OSError:
            continue
    return None
