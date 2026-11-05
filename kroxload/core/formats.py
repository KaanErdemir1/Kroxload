"""Desteklenen formatlar ve kalite seçenekleri."""

# format -> {görünen ad: yt-dlp değeri}
KALITELER = {
    "MP4": {"En iyi": None, "1080p": 1080, "720p": 720, "480p": 480, "360p": 360},
    "MP3": {"320 kbps": "320", "256 kbps": "256", "192 kbps": "192", "128 kbps": "128"},
    "WAV": {"Standart": None},
    "M4A": {"Orijinal": None},
}

ETIKET = {"MP4": "Video (MP4)", "MP3": "MP3", "WAV": "WAV", "M4A": "M4A"}
ETIKET_TERS = {v: k for k, v in ETIKET.items()}


def kaliteler(fmt):
    """Bir formatın kalite seçeneklerini (görünen adlar) listeler."""
    return list(KALITELER.get(fmt, KALITELER["MP4"]))
