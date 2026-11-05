"""Uygulama günlüğü (log) sistemi.

Kayıtlar %APPDATA%\\Kroxload\\logs\\kroxload.log dosyasına yazılır; dosya
1 MB'ı geçince yedeklenir (en fazla 3 yedek). İndirme hataları ve beklenmedik
çökmeler buraya düşer; destek almak isteyen kullanıcıya bu dosya sorulur.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from .paths import LOG_DOSYASI

_kuruldu = False


def kur():
    """Günlük kaydedicini hazırlar ve çökme yakalayıcını takar (bir kez)."""
    global _kuruldu
    kayit = logging.getLogger("kroxload")
    if _kuruldu:
        return kayit

    try:
        LOG_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
        isleyici = RotatingFileHandler(
            LOG_DOSYASI, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        isleyici.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")
        )
        kayit.addHandler(isleyici)
        kayit.setLevel(logging.INFO)
        kayit.propagate = False
    except Exception:
        # Günlük açılamazsa uygulama yine de çalışmalı
        pass

    def _cokme(tip, deger, iz_suresi):
        kayit.critical(
            "Beklenmedik hata: %s: %s", getattr(tip, "__name__", tip), deger,
            exc_info=(tip, deger, iz_suresi),
        )
        sys.__excepthook__(tip, deger, iz_suresi)

    sys.excepthook = _cokme
    _kuruldu = True
    return kayit


kayit = kur()
