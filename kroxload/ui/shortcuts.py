"""Ana Sayfa hızlı erişim şeridi: sık kullanılan platformlara tek tıkla geçiş.

İkonlar tek renkli, sade geometrik çizimlerdir; renkleri aktif temanın paletinden gelir
(durağan: `muted`, üzerine gelince: `accent_ink`). Marka renkleri kullanılmaz; böylece
şerit iki temada da arayüzün geri kalanıyla uyumlu kalır.
"""
import tkinter as tk
import webbrowser

import customtkinter as ctk

from .theme import SANS, metin_genisligi, olcek, tema

PLATFORMLAR = (
    ("YouTube", "https://www.youtube.com", "youtube"),
    ("YouTube Music", "https://music.youtube.com", "ytmusic"),
    ("TikTok", "https://www.tiktok.com", "tiktok"),
    ("Instagram", "https://www.instagram.com", "instagram"),
    ("SoundCloud", "https://soundcloud.com", "soundcloud"),
    ("X", "https://x.com", "x"),
)

IKON = 16   # mantıksal piksel
YUKSEKLIK = 30


def _yuvarlak_dikdortgen(c, x0, y0, x1, y1, r, **kw):
    pts = [
        x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
        x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
    ]
    return c.create_polygon(pts, smooth=True, **kw)


def _ikon_ciz(c, ad, x, y, k, renk):
    """16x16 mantıksal kutuya, `k` ölçeğiyle tek renkli ikon çizer."""
    g = max(1, round(1.4 * k))

    def P(*v):
        return [x + a * k if i % 2 == 0 else y + a * k for i, a in enumerate(v)]

    if ad in ("youtube", "ytmusic"):
        if ad == "youtube":
            _yuvarlak_dikdortgen(c, *P(0, 2.5, 16, 13.5), 3.5 * k, outline=renk, fill="", width=g)
        else:
            c.create_oval(*P(0.5, 0.5, 15.5, 15.5), outline=renk, width=g)
        c.create_polygon(*P(6.5, 5.2, 6.5, 10.8, 11, 8), fill=renk, outline=renk)
    elif ad == "tiktok":
        c.create_line(*P(9.5, 2, 9.5, 11.5), fill=renk, width=g)
        c.create_oval(*P(4.5, 10, 9.5, 15), outline=renk, width=g)
        c.create_line(*P(9.5, 2, 10.5, 4.5, 13, 5.6), fill=renk, width=g, smooth=True)
    elif ad == "instagram":
        _yuvarlak_dikdortgen(c, *P(0.7, 0.7, 15.3, 15.3), 4.5 * k, outline=renk, fill="", width=g)
        c.create_oval(*P(4.6, 4.6, 11.4, 11.4), outline=renk, width=g)
        c.create_oval(*P(11.4, 3.2, 12.6, 4.4), fill=renk, outline=renk)
    elif ad == "soundcloud":
        for bx, ust, alt in ((1.5, 8, 13), (4.5, 5.5, 13), (7.5, 3, 13), (10.5, 5, 13), (13.5, 8, 13)):
            c.create_line(*P(bx, ust, bx, alt), fill=renk, width=g, capstyle="round")
    elif ad == "x":
        c.create_line(*P(2, 2, 14, 14), fill=renk, width=g + 0.5, capstyle="round")
        c.create_line(*P(14, 2, 2, 14), fill=renk, width=g + 0.5, capstyle="round")


class Kisayol(tk.Canvas):
    """Tek bir platform kısayolu: ikon + ad, temaya duyarlı, tıklayınca tarayıcıda açar."""

    def __init__(self, parent, ad, url, ikon_adi):
        self._k = olcek(parent)
        self.ad, self.url, self.ikon_adi = ad, url, ikon_adi
        self._uzerinde = False
        k = self._k
        self._yazi_boy = 11
        metin_w = metin_genisligi(ad, self._yazi_boy, True)
        self._w_mantiksal = 12 + IKON + 8 + metin_w + 14
        p = tema.p
        super().__init__(
            parent, width=int(self._w_mantiksal * k), height=int(YUKSEKLIK * k),
            highlightthickness=0, bd=0, bg=p["bg"], cursor="hand2",
        )
        self.bind("<Enter>", self._gir, add="+")
        self.bind("<Leave>", self._cik, add="+")
        self.bind("<ButtonRelease-1>", self._birak, add="+")
        tema.bagla_fn(self, self._boya)

    def _boya(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        k = self._k
        self.delete("all")
        self.configure(bg=p["bg"])
        zemin = p["yuzey2"] if self._uzerinde else p["yuzey"]
        kenar = p["accent"] if self._uzerinde else p["kenar"]
        renk = p["accent_ink"] if self._uzerinde else p["muted"]
        yazi = p["ink"] if self._uzerinde else p["muted"]
        w, h = int(self._w_mantiksal * k), int(YUKSEKLIK * k)
        _yuvarlak_dikdortgen(self, 1, 1, w - 1, h - 1, 7 * k, fill=zemin, outline=kenar, width=1)
        _ikon_ciz(self, self.ikon_adi, 12 * k, (YUKSEKLIK - IKON) / 2 * k, k, renk)
        self.create_text(
            (12 + IKON + 8) * k, h / 2, text=self.ad, anchor="w", fill=yazi,
            font=(SANS, -max(1, round(self._yazi_boy * k))),
        )

    def _gir(self, _e=None):
        self._uzerinde = True
        self._boya()

    def _cik(self, _e=None):
        self._uzerinde = False
        self._boya()

    def _birak(self, e):
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.after(1, self.ac)

    def ac(self):
        try:
            webbrowser.open(self.url)
        except Exception:
            pass


class KisayolSeridi(ctk.CTkFrame):
    """Soldan sağa dizilen, yalın 'Hızlı Erişim' şeridi."""

    def __init__(self, parent, bg_anahtar="bg"):
        p0 = tema.p
        super().__init__(parent, corner_radius=0, fg_color=p0[bg_anahtar], bg_color=p0[bg_anahtar])
        tema.bagla(self, fg_color=bg_anahtar)
        from .theme import F

        etiket = ctk.CTkLabel(
            self, text="Hızlı Erişim", font=F(11, True),
            fg_color=p0[bg_anahtar], bg_color=p0[bg_anahtar], text_color=p0["muted"],
        )
        etiket.pack(side="left", padx=(0, 12))
        tema.bagla(etiket, fg_color=bg_anahtar, text_color="muted")
        self.kisayollar = []
        for ad, url, ikon in PLATFORMLAR:
            ks = Kisayol(self, ad, url, ikon)
            ks.pack(side="left", padx=(0, 8))
            self.kisayollar.append(ks)

