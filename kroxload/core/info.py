"""Link önizleme bilgisi: başlık, kanal, süre, kapak görüntüsü.

Arayüzden bağımsızdır; kapak görüntüsünü bayt olarak döndürür, görüntüleme
biçimine (tkinter, web <img>, mobil bileşen) karışmaz.
"""
import urllib.request

from .ytdlp import yt_dlp


def sure_yaz(saniye):
    try:
        s = int(saniye)
    except Exception:
        return ""
    h, kalan = divmod(s, 3600)
    m, sn = divmod(kalan, 60)
    return f"{h}:{m:02d}:{sn:02d}" if h else f"{m}:{sn:02d}"


def bilgi_getir(link, liste):
    """Bir link hakkında önizleme bilgisi döndürür.

    Dönüş: {"baslik": str, "alt": str, "kapak": bytes|None}
    Hata olursa exception yükseltir; çağıran taraf yakalar.
    """
    secenek = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": not liste,
        "extract_flat": "in_playlist",
        "socket_timeout": 15,
    }
    with yt_dlp.YoutubeDL(secenek) as ydl:
        info = ydl.extract_info(link, download=False)

    ie = str(info.get("extractor_key") or "")
    if info.get("_type") == "playlist":
        baslik = info.get("title") or "Liste"
        girdiler = info.get("entries") or []
        n = info.get("playlist_count") or len(girdiler)
        if liste:
            alt = f"Liste, {n} video"
        else:
            alt = f"Liste linki ({n} video). Hepsini indirmek için liste anahtarını aç."
        kapak_id = girdiler[0].get("id") if girdiler else None
        kapak_url = f"https://i.ytimg.com/vi/{kapak_id}/mqdefault.jpg" if kapak_id and ie.startswith("Youtube") else None
    else:
        baslik = info.get("title") or "Video"
        parcalar = [p for p in (info.get("uploader") or info.get("channel"), sure_yaz(info.get("duration"))) if p]
        alt = ", ".join(parcalar)
        if ie.startswith("Youtube") and info.get("id"):
            kapak_url = f"https://i.ytimg.com/vi/{info['id']}/mqdefault.jpg"
        else:
            kapak_url = info.get("thumbnail")

    return {"baslik": baslik, "alt": alt, "kapak": _kapak_indir(kapak_url)}


def _kapak_indir(url):
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.read()
    except Exception:
        return None
