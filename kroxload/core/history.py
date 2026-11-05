"""İşlem geçmişi: indirme ve dönüştürme kayıtları %APPDATA%\\Kroxload\\gecmis.json'da tutulur.

Arayüzden bağımsızdır; kayıtlar sözlük olarak saklanır:
    {"id", "tur": "indirme"|"donusum", "durum": "tamam"|"hata",
     "baslik", "dosya", "klasor", "format", "kalite", "tarih", "hata"}
Eski sürümlerin kayıtlarında tur/durum/id yoktur; okunurken tamamlanır.
"""
import json
import uuid
from datetime import datetime

from .paths import GECMIS_DOSYASI

SINIR = 300  # en fazla bu kadar kayıt tutulur


def _tamamla(k):
    """Eski kayıtları yeni şemaya getirir."""
    k.setdefault("tur", "indirme")
    k.setdefault("durum", "tamam")
    k.setdefault("hata", None)
    if not k.get("id"):
        k["id"] = uuid.uuid4().hex[:12]
    return k


def _oku():
    try:
        veri = json.loads(GECMIS_DOSYASI.read_text(encoding="utf-8"))
        if isinstance(veri, list):
            return [_tamamla(k) for k in veri if isinstance(k, dict)]
    except Exception:
        pass
    return []


def _yaz(kayitlar):
    try:
        GECMIS_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
        gecici = GECMIS_DOSYASI.with_suffix(".tmp")
        gecici.write_text(
            json.dumps(kayitlar[:SINIR], ensure_ascii=False, indent=2), encoding="utf-8")
        gecici.replace(GECMIS_DOSYASI)  # yarım yazılmış dosya bırakmaz
    except Exception:
        pass


def ekle(baslik, dosya, klasor, fmt, kalite, tur="indirme", durum="tamam", hata=None):
    """Bir işlemi geçmişe ekler (en yenisi başta)."""
    kayit = {
        "id": uuid.uuid4().hex[:12],
        "tur": tur,
        "durum": durum,
        "baslik": baslik,
        "dosya": dosya,
        "klasor": klasor,
        "format": fmt,
        "kalite": kalite,
        "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "hata": hata,
    }
    kayitlar = _oku()
    if dosya:  # aynı dosya zaten geçmişteyse eskisini kaldır (en üste tazesini koy)
        kayitlar = [k for k in kayitlar if k.get("dosya") != dosya]
    kayitlar.insert(0, kayit)
    _yaz(kayitlar)
    return kayit


def liste(sinir=None, tur=None):
    """Geçmiş kayıtlarını (en yeni önce) döndürür; tur verilirse süzer."""
    kayitlar = _oku()
    if tur:
        kayitlar = [k for k in kayitlar if k.get("tur") == tur]
    return kayitlar[:sinir] if sinir else kayitlar


def cikar(dosya):
    """Belirli bir dosyaya ait kaydı geçmişten siler."""
    _yaz([k for k in _oku() if k.get("dosya") != dosya])


def cikar_id(kayit_id):
    """Kimliğiyle bir kaydı siler (dosyası olmayan başarısız kayıtlar için de çalışır)."""
    _yaz([k for k in _oku() if k.get("id") != kayit_id])


def temizle():
    """Tüm geçmişi siler."""
    try:
        GECMIS_DOSYASI.unlink()
    except Exception:
        pass
