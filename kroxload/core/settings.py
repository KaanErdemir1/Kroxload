"""Kullanıcı ayarlarının okunması ve kaydedilmesi."""
import json
from pathlib import Path

from .paths import AYAR_DOSYASI

_INDIRILENLER = str(Path.home() / "Downloads")

VARSAYILAN = {
    "klasor": _INDIRILENLER,          # indirme klasörü
    "format": "MP4",
    "kalite": None,
    "tema": "koyu",                   # "koyu" | "acik"
    "liste": False,                   # playlist linkinde tüm videoları indir
    "donusum_klasor": "",             # boş = kaynak dosyanın klasörü
    "pano_otomatik": True,            # pencere odaklanınca panodaki linki yapıştır
    "bitince_klasor_ac": False,       # indirme/dönüştürme bitince klasörü aç
    "bildirimler": True,              # köşe bildirimleri
    "animasyonlar": True,             # arayüz animasyonları
    "donusum_ses_format": "MP3",
    "donusum_video_format": "MP4",
}


def ayar_oku():
    """Ayarları okur; bozuksa veya eksikse varsayılanlarla tamamlar."""
    try:
        veri = json.loads(AYAR_DOSYASI.read_text(encoding="utf-8"))
    except Exception:
        veri = {}
    if not isinstance(veri, dict):
        veri = {}
    # Eski sürüm uyumu: "koyu" (bool) -> "tema" ("koyu"/"acik")
    if "koyu" in veri:
        veri.setdefault("tema", "koyu" if veri.pop("koyu") else "acik")
    sonuc = dict(VARSAYILAN)
    sonuc.update(veri)
    return sonuc


def ayar_yaz(veri):
    """Verilen anahtarları mevcut ayarlarla birleştirip kaydeder."""
    try:
        tam = ayar_oku()
        tam.update(veri)
        AYAR_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
        gecici = AYAR_DOSYASI.with_suffix(".tmp")
        gecici.write_text(json.dumps(tam, ensure_ascii=False, indent=2), encoding="utf-8")
        gecici.replace(AYAR_DOSYASI)
    except Exception:
        pass
