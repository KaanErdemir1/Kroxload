"""yt-dlp ve sistem hatalarını anlaşılır Türkçe mesajlara çevirir.

Kural listesi sırayla denenir; ilk eşleşen mesaj döndürülür. Eşleşme
yoksa None döner ve çağıran taraf kısaltılmış orijinal hatayı gösterir.
Ayrıntılar günlük dosyasına yazılır (bkz. logs.py).
"""

# (aranacak metin parçaları, Türkçe mesaj) — sıra önemli, en özgül olanlar üstte
_KURALLAR = (
    (
        ("is not a valid url", "unable to extract url"),
        "Bu geçerli bir link değil. Linki kontrol edip yeniden yapıştır.",
    ),
    (
        ("unsupported url",),
        "Bu site veya sayfa desteklenmiyor.",
    ),
    (
        ("confirm you're not a bot", "sign in to confirm you"),
        "YouTube bot koruması tetikledi. Birkaç dakika bekleyip Yenile'ye bas, sonra tekrar dene.",
    ),
    (
        ("sign in to confirm your age", "age-restricted", "age restricted"),
        "Bu video yaş sınırına takılıyor ve oturum açılmadan indirilemiyor.",
    ),
    (
        ("private video",),
        "Bu video gizli olduğu için indirilemez.",
    ),
    (
        ("members-only", "join this channel"),
        "Bu içerik yalnızca kanal üyelerine açık.",
    ),
    (
        ("video unavailable", "has been removed", "no longer available"),
        "Video kullanılamıyor; silinmiş veya gizlenmiş olabilir.",
    ),
    (
        ("not available in your country", "geo-restricted", "geo restricted", "geo-restriction"),
        "Bu video bulunduğun ülkede engelli.",
    ),
    (
        ("this live event will begin", "is live and will be available", "premieres in", "live stream"),
        "Canlı yayın henüz bitmedi. Yayın bittikten sonra tekrar dene.",
    ),
    (
        ("no space left", "errno 28", "disk quota"),
        "Diskte yeterli alan yok. Yer açıp tekrar dene.",
    ),
    (
        ("permission denied", "access is denied", "errno 13", "permission_error"),
        "Kayıt klasörüne yazılamadı. Başka bir klasör seç veya izinleri düzelt.",
    ),
    (
        ("unable to create", "failed to create"),
        "Dosya oluşturulamadı. Kayıt klasörünü ve disk alanını kontrol et.",
    ),
    (
        ("ffmpeg",),
        "Ses/video dönüştürmesi için FFmpeg bulunamadı. Uygulamayı yeniden kurmayı dene.",
    ),
    (
        ("http error 429", "too many requests"),
        "Çok fazla istek gönderildi. Bir süre bekleyip tekrar dene.",
    ),
    (
        ("http error 403",),
        "Sunucu erişimi reddetti. Yenile'ye basıp tekrar dene.",
    ),
    (
        ("http error 404", "not found"),
        "İçerik bulunamadı. Link silinmiş veya yanlış olabilir.",
    ),
    (
        ("timed out", "timeout", "temporary failure in name resolution", "getaddrinfo",
         "connection reset", "connection refused", "connection aborted", "network",
         "urlopen error", "ssl:", "certificate verify failed", "unable to download webpage"),
        "İnternet bağlantısı kurulamadı. Bağlantını kontrol edip tekrar dene.",
    ),
    (
        ("drm",),
        "Bu içerik kopya korumalı (DRM) olduğu için indirilemez.",
    ),
)


def hata_turkce(hata):
    """Hatayı Türkçe mesaja çevirir; eşleşmezse None döner."""
    metin = str(hata or "").lower()
    for anahtarlar, mesaj in _KURALLAR:
        for anahtar in anahtarlar:
            if anahtar in metin:
                return mesaj
    return None


# ---- Dosya dönüştürme (FFmpeg) hataları ----
_DONUSUM_KURALLARI = (
    (("invalid data found", "moov atom not found", "could not find codec parameters",
      "error while decoding", "end of file", "invalid argument for input"),
     "Dosya bozuk veya desteklenmeyen bir biçimde. Başka bir dosya dene."),
    (("no such file", "does not exist"),
     "Dosya bulunamadı. Taşınmış veya silinmiş olabilir."),
    (("permission denied", "access is denied"),
     "Dosyaya erişilemedi. Başka bir program kullanıyor olabilir veya izin yok."),
    (("no space left", "errno 28"),
     "Diskte yeterli alan yok. Yer açıp tekrar dene."),
    (("unknown encoder", "encoder not found", "' not found", "unable to find a suitable output format",
      "could not write header", "codec not currently supported in container",
      "not supported in container"),
     "Seçilen codec bu biçimle birlikte kullanılamıyor. Başka bir codec veya biçim seç."),
    (("matches no streams", "output file does not contain any stream", "stream map"),
     "Dosyada seçilen dönüştürme için uygun ses/video akışı yok."),
    (("cannot find an unused", "failed to open", "error opening output"),
     "Çıktı dosyası oluşturulamadı. Klasörü ve disk alanını kontrol et."),
)


def donusum_hata_turkce(metin):
    """FFmpeg/FFprobe hata çıktısını Türkçe mesaja çevirir; eşleşmezse None."""
    kucuk = str(metin or "").lower()
    for anahtarlar, mesaj in _DONUSUM_KURALLARI:
        if any(a in kucuk for a in anahtarlar):
            return mesaj
    return None
