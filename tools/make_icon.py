"""Kroxload ikonunu üretir: assets/kroxload.png ve assets/kroxload.ico

Kroxload işareti: K harfinin dikey çizgisi aynı zamanda bir indirme okuna
dönüşür — "K'ını indir". Tek düz marka rengi, beyaz işaret, yuvarlatılmış
kare. Bilinçli olarak gradyan/efekt kullanılmaz.

Kullanım:  python tools/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parent.parent
ASSETS = KOK / "assets"
S = 1024            # temel çözünürlük
R = 232             # köşe yarıçapı
MARKA = (78, 90, 230, 255)   # #4E5AE6 — Kroxload indigosu
BEYAZ = (255, 255, 255, 255)


def logo_ciz():
    taban = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Düz renkli yuvarlatılmış kare
    d = ImageDraw.Draw(taban)
    d.rounded_rectangle([8, 8, S - 9, S - 9], radius=R, fill=MARKA)

    # ---- K harfi: gövde = indirme oku ----
    # Gövde: dikey şaft + ok başı (K'nın dikey çizgisi okun kendisi)
    sx, yarim = 320, 80          # şaft merkezi ve yarı genişliği
    d.rounded_rectangle([sx - yarim, 180, sx + yarim, 780], radius=yarim, fill=BEYAZ)
    d.polygon([(sx - 160, 730), (sx + 160, 730), (sx, 950)], fill=BEYAZ)

    # Üst kol: gövdenin içinden başlar (birleşim boşluksuz), sağ üste uzanır
    d.polygon([(340, 520), (700, 160), (802, 262), (442, 622)], fill=BEYAZ)

    # Alt kol: üst kolun orta noktasından çıkar, sağ alta uzanır
    d.polygon([(440, 520), (545, 470), (812, 788), (700, 905), (390, 640)], fill=BEYAZ)

    # Birleşim dolgusu (kollar gövdeye değerken minik boşluk kalmasın)
    d.polygon([(380, 500), (500, 500), (500, 660), (380, 660)], fill=BEYAZ)

    return taban


def main():
    ASSETS.mkdir(exist_ok=True)
    logo = logo_ciz()
    logo.save(ASSETS / "kroxload.png")
    logo.save(
        ASSETS / "kroxload.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    onizleme = logo.resize((512, 512), Image.LANCZOS)
    onizleme.save(ASSETS / "_onizleme.png")
    print("OK:", ASSETS / "kroxload.ico")


if __name__ == "__main__":
    main()
