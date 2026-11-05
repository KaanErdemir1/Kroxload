"""yt-dlp modülünü yükler.

Önce %APPDATA%\\Kroxload altındaki "Yenile" ile indirilmiş güncel sürüm
(yt-dlp.zip), yoksa paketle gelen sürüm kullanılır. Güncel dosya bozuksa
silinir ve paketlenmiş sürüme dönülür.
"""
import sys

from .paths import GUNCEL_ZIP


def _yukle():
    if GUNCEL_ZIP.exists():
        sys.path.insert(0, str(GUNCEL_ZIP))
    import yt_dlp
    return yt_dlp


try:
    yt_dlp = _yukle()
    from yt_dlp.version import __version__ as YTDLP_SURUM
except Exception:
    # Güncel zip bozuksa: yoldan çıkar, modülleri temizle, dosyayı sil, yeniden dene
    if str(GUNCEL_ZIP) in sys.path:
        sys.path.remove(str(GUNCEL_ZIP))
    for ad in [k for k in sys.modules if k.startswith("yt_dlp")]:
        del sys.modules[ad]
    try:
        GUNCEL_ZIP.unlink()
    except Exception:
        pass
    import yt_dlp
    from yt_dlp.version import __version__ as YTDLP_SURUM
