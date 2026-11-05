"""dist/Kroxload klasöründen release/Kroxload_Portable.zip üretir.

Zip içinde tek üst klasör (Kroxload/) bulunur; açıp Kroxload.exe çalıştırmak yeterlidir.
Portable sürümde de veriler %APPDATA%\\Kroxload altında tutulur.
"""
import os
import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
KAYNAK = KOK / "dist" / "Kroxload"
HEDEF = KOK / "release" / "Kroxload_Portable.zip"

OKU = """Kroxload 1.1.0 - Tasinabilir surum

1. Zip dosyasini bir klasore cikarin.
2. Kroxload.exe dosyasini calistirin.

Python veya FFmpeg kurmaniz gerekmez; FFmpeg _internal\\ffmpeg klasorunde gelir.
Ayarlar ve gecmis %APPDATA%\\Kroxload altinda tutulur.
Kaldirmak icin klasoru silmeniz yeterlidir (istenirse %APPDATA%\\Kroxload da silinebilir).
"""


def main():
    if not (KAYNAK / "Kroxload.exe").exists():
        sys.exit("dist/Kroxload/Kroxload.exe yok; once PyInstaller çalıştırın.")
    HEDEF.parent.mkdir(exist_ok=True)
    if HEDEF.exists():
        HEDEF.unlink()
    with zipfile.ZipFile(HEDEF, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for kok, _, dosyalar in os.walk(KAYNAK):
            for ad in dosyalar:
                tam = Path(kok) / ad
                z.write(tam, Path("Kroxload") / tam.relative_to(KAYNAK))
        z.writestr("Kroxload/OKU-BENI.txt", OKU)
    print("OK:", HEDEF, round(HEDEF.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()

