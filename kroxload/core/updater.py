"""yt-dlp güncelleme (uygulamadaki 'Yenile' özelliği).

GitHub'daki son sürümü kontrol eder; varsa %APPDATA%\\Kroxload altına
yt-dlp.zip olarak indirir. Uygulama yeniden başlatıldığında etkin olur.
"""
import json
import os
import shutil
import urllib.request
import zipfile

from .paths import GUNCEL_ZIP
from .ytdlp import YTDLP_SURUM

_BASLIKLAR = {"User-Agent": "Kroxload"}


def guncelle(durum_cb=None):
    """Güncellemeyi kontrol eder ve gerekirse indirir.

    durum_cb(metin) ilerleme bildirir.
    Dönüş: (mesaj, basarili: bool)
    """
    if durum_cb:
        durum_cb("Kontrol ediliyor...")
    try:
        istek = urllib.request.Request(
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", headers=_BASLIKLAR
        )
        with urllib.request.urlopen(istek, timeout=20) as r:
            son = str(json.load(r)["tag_name"]).strip()

        if son == YTDLP_SURUM:
            return ("Zaten güncel, yenilemeye gerek yok.", True)

        if durum_cb:
            durum_cb("Yeni sürüm indiriliyor...")
        istek = urllib.request.Request(
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp", headers=_BASLIKLAR
        )
        gecici = GUNCEL_ZIP.with_suffix(".tmp")
        with urllib.request.urlopen(istek, timeout=60) as r, open(gecici, "wb") as f:
            shutil.copyfileobj(r, f)
        if not zipfile.is_zipfile(gecici):
            raise RuntimeError("indirilen dosya bozuk")
        os.replace(gecici, GUNCEL_ZIP)
        return ("Yenilendi. Geçerli olması için uygulamayı kapatıp yeniden aç.", True)
    except Exception as e:
        from .engine import temizle

        return (f"Yenilenemedi: {temizle(e)}", False)
