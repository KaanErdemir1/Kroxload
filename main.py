"""Kroxload giriş noktası.

Çalıştırma:  python main.py
Derleme:     build.bat  (veya: pyinstaller Kroxload.spec)
"""
import os
import sys

# Konsolsuz (windowed) exe'de stdout/stderr yoktur; indirme motoru çökmesin diye
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


def selftest(cikti):
    """Kurulum doğrulaması: kroxload.exe --selftest <dosya>. Arayüz açmaz; FFmpeg
    yolunu, çalıştığını, yt-dlp sürümünü ve sürümü verilen dosyaya yazar."""
    import subprocess

    from kroxload import SURUM
    from kroxload.core.paths import ffmpeg_klasoru
    from kroxload.core.ytdlp import YTDLP_SURUM

    ff = ffmpeg_klasoru()
    satirlar = [f"surum={SURUM}", f"yt-dlp={YTDLP_SURUM}", f"ffmpeg_klasoru={ff}"]
    for ad in ("ffmpeg", "ffprobe"):
        try:
            c = subprocess.run([os.path.join(ff, ad + ".exe"), "-version"], capture_output=True,
                               text=True, timeout=30,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            satirlar.append(f"{ad}={'OK' if c.returncode == 0 else 'HATA'} "
                            f"{(c.stdout or '').splitlines()[0] if c.stdout else ''}")
        except Exception as e:
            satirlar.append(f"{ad}=HATA {e}")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
        return

    # Windows görev çubuğunda Python yerine Kroxload kimliğiyle gruplanalım;
    # böylece görev çubuğu ve pencere ikonu her zaman Kroxload ikonu olur.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kroxload")
        except Exception:
            pass

    from kroxload.core.logs import kayit  # çökmeleri yakalasın diye erken yüklenir

    kayit.info("Kroxload başlıyor")

    from kroxload.ui.desktop import calistir

    calistir()


if __name__ == "__main__":
    main()
