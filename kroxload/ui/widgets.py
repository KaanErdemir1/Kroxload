"""Yeniden kullanılabilir arayüz bileşenleri.

Tasarım ilkeleri:
- Gereksiz kart/kutu kalabalığı, gradyan, neon parlama ve cam efekti yoktur.
- Köşe yuvarlaklıkları tutarlıdır: kontrol elemanları 6px, yüzey panelleri 8px.
- Mor vurgu rengi (`accent`) yalnızca birincil eylem butonlarında, aktif menü/anahtar
  durumlarında ve ilerleme çubuğunda kullanılır; ikincil kontroller nötr antrasit/gri
  tonlardadır.
- Tüm bileşenler `tema` sistemine bağlıdır; Açık/Koyu tema geçişinde ve tıklamalarda
  karanlık artefakt bırakmadan yumuşakça boyanır.
"""
import tkinter as tk
import customtkinter as ctk

from .theme import F, GLIF, _ust_zemin_rengi, ease_out, hizli_boya, ikon_fontu, karistir, tema


def _fare_icinde_mi(widget, olay=None):
    """Fare imlecinin şu anda verilen bileşenin sınırları içinde olup olmadığını döndürür.

    Olay verilmişse imleç konumu olayın ekran koordinatlarından (x_root/y_root) alınır;
    böylece sınır denetimi, olayı alan alt bileşenden bağımsız ve güvenilir çalışır.
    """
    try:
        if not widget.winfo_exists():
            return False
        xr, yr = getattr(olay, "x_root", None), getattr(olay, "y_root", None)
        if isinstance(xr, int) and isinstance(yr, int):
            px, py = xr, yr
        else:
            px, py = widget.winfo_pointerxy()
        rx, ry = widget.winfo_rootx(), widget.winfo_rooty()
        return rx <= px <= rx + widget.winfo_width() and ry <= py <= ry + widget.winfo_height()
    except Exception:
        return True


class Ipucu:
    """İkon butonları ve kısaltılmış metinler için gecikmeli, sade araç ipucu."""

    def __init__(self, widget, metin="", gecikme=420):
        self.widget = widget
        self.metin = metin
        self.gecikme = gecikme
        self._job = None
        self._pencere = None
        widget.bind("<Enter>", self._gir, add="+")
        widget.bind("<Leave>", self._cik, add="+")
        widget.bind("<ButtonPress>", self._cik, add="+")
        widget.bind("<Destroy>", self._cik, add="+")

    def guncelle(self, metin):
        self.metin = metin or ""
        if not self.metin:
            self._gizle()

    def _gir(self, _e=None):
        self._iptal()
        if self.metin:
            self._job = self.widget.after(self.gecikme, self._goster)

    def _cik(self, _e=None):
        self._iptal()
        self._gizle()

    def _iptal(self):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _goster(self):
        self._job = None
        if not self.metin or not self.widget.winfo_exists() or not self.widget.winfo_viewable():
            return
        self._gizle()
        try:
            p = tema.p
            tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            cerceve = tk.Frame(tw, bg=p["kenar"], bd=0, padx=1, pady=1)
            cerceve.pack()
            ic = tk.Label(
                cerceve, text=self.metin, bg=p["toast"], fg=p["ink"],
                font=F(11), padx=8, pady=4, justify="left"
            )
            ic.pack()
            tw.update_idletasks()
            x = self.widget.winfo_rootx() + (self.widget.winfo_width() - tw.winfo_reqwidth()) // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            ekran_g = self.widget.winfo_screenwidth()
            x = max(8, min(x, ekran_g - tw.winfo_reqwidth() - 8))
            tw.wm_geometry(f"+{x}+{y}")
            self._pencere = tw
        except Exception:
            self._pencere = None

    def _gizle(self):
        if self._pencere is not None:
            try:
                self._pencere.destroy()
            except Exception:
                pass
            self._pencere = None


class Ayirici(ctk.CTkFrame):
    """1 piksellik yatay veya dikey ayırıcı çizgi."""

    def __init__(self, parent, dikey=False, **kw):
        boyut = {"width": 1} if dikey else {"height": 1}
        super().__init__(
            parent, corner_radius=0, fg_color=tema.p["kenar"],
            bg_color=tema.p["kenar"], **boyut, **kw
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        tema.bagla(self, fg_color="kenar")


def kaydirilabilir_alan(parent, jeton="bg", **kw):
    """Temaya tam bağlı, hızlı yeniden boyanan CTkScrollableFrame."""
    p0 = tema.p
    alan = ctk.CTkScrollableFrame(
        parent, corner_radius=0,
        fg_color=p0[jeton],
        bg_color=p0[jeton],
        scrollbar_button_color=p0["kenar"],
        scrollbar_button_hover_color=p0["muted"],
        **kw,
    )

    def _alan_boya(p):
        if not alan.winfo_exists():
            return
        renk = p[jeton]
        alan._fg_color = renk
        alan._bg_color = renk
        try:
            tk.Frame.configure(alan, bg=renk)
        except Exception:
            pass
        pf = getattr(alan, "_parent_frame", None)
        if pf is not None:
            hizli_boya(pf, fg_color=renk, bg_color=renk)
        pc = getattr(alan, "_parent_canvas", None)
        if pc is not None:
            try:
                pc.configure(bg=renk)
            except Exception:
                pass
        lbl = getattr(alan, "_label", None)
        if lbl is not None:
            hizli_boya(lbl, fg_color=renk, bg_color=renk, text_color=p["ink"])
        sb = getattr(alan, "_scrollbar", None)
        if sb is not None:
            sb._fg_color = renk
            sb._bg_color = renk
            sb._button_color = p["kenar"]
            sb._button_hover_color = p["muted"]
            sc = getattr(sb, "_canvas", None)
            if sc is not None:
                sc.configure(bg=renk)
                sc.itemconfig("border_parts", fill=renk, outline=renk)
                sc.itemconfig("scrollbar_parts", fill=p["kenar"], outline=p["kenar"])

    tema.bagla_fn(alan, _alan_boya)
    return alan


class Buton(ctk.CTkFrame):
    """Tutarlı, mikro-etkileşimli buton bileşeni.

    tur:
      - "birincil": Mor vurgu dolgulu ana eylem butonu (İndir, Dönüştür).
      - "ikincil":  İnce kenarlıklı, yüzey dolgulu standart buton (Yapıştır, Değiştir).
      - "hayalet":  Kenarlıksız, üzerine gelince beliren sade buton (Temizle, Sıfırla).
      - "tehlike":  Silme/iptal eylemleri için düşük yoğunluklu kırmızı vurgulu buton.
    """

    def __init__(self, parent, metin="", ikon=None, komut=None, tur="ikincil",
                 yukseklik=32, genislik=None, font_boy=12, kalin=None, ipucu="", **kw):
        self.tur = tur
        self.komut = komut
        self.etkin = True
        self._hover_t = 0.0
        self._basili = False
        self._anim_id = f"btn_{id(self)}"
        self._kalin = (tur == "birincil") if kalin is None else kalin
        self._font_boy = font_boy
        self._ust_ref = parent

        ilk_ust = _ust_zemin_rengi(parent, tema.p["bg"])
        zemin0, yazi0, kenar0 = self._renkler(tema.p, ilk_ust)
        kenar_kalinligi = 1 if tur in ("ikincil", "tehlike") else 0

        super().__init__(
            parent, height=yukseklik, corner_radius=6,
            border_width=kenar_kalinligi, fg_color=zemin0,
            border_color=kenar0, bg_color=ilk_ust, cursor="hand2", **kw
        )
        if genislik:
            self.configure(width=genislik)
            self.pack_propagate(False)
            self.grid_propagate(False)
        else:
            self.pack_propagate(True)

        self._ic = ctk.CTkFrame(
            self, corner_radius=0, border_width=0,
            fg_color=zemin0, bg_color=zemin0, cursor="hand2"
        )
        if genislik:
            self._ic.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._ic.pack(padx=12, pady=max(2, (yukseklik - 20) // 2))

        self._ikon_lbl = None
        if ikon:
            glif = GLIF.get(ikon, ikon)
            self._ikon_lbl = ctk.CTkLabel(
                self._ic, text=glif, font=ikon_fontu(font_boy + 1), width=16,
                fg_color=zemin0, bg_color=zemin0, text_color=yazi0, cursor="hand2"
            )
            self._ikon_lbl.pack(side="left", padx=(0, 6 if metin else 0))

        self._metin_lbl = ctk.CTkLabel(
            self._ic, text=metin, font=F(font_boy, self._kalin),
            fg_color=zemin0, bg_color=zemin0, text_color=yazi0, cursor="hand2"
        )
        if metin:
            self._metin_lbl.pack(side="left")

        for w in (self, self._ic, self._ikon_lbl, self._metin_lbl):
            if w is not None:
                w.bind("<Enter>", self._uzerinde_gir, add="+")
                w.bind("<Leave>", self._uzerinde_cik, add="+")
                w.bind("<ButtonPress-1>", self._bas, add="+")
                w.bind("<ButtonRelease-1>", self._birak, add="+")

        self.ipucu = Ipucu(self, ipucu) if ipucu else None
        tema.bagla_fn(self, self._boya)

    def _renkler(self, p, ust_zemin=None):
        ust_zemin = ust_zemin or _ust_zemin_rengi(self, p["bg"])
        if not self.etkin:
            return p["yuzey"], p["soluk"], p["kenar"]
        t = self._hover_t
        if self.tur == "birincil":
            zemin = p["accent_a"] if self._basili else karistir(p["accent"], p["accent_h"], t)
            return zemin, p["on_accent"], zemin
        if self.tur == "tehlike":
            zemin = karistir(p["yuzey"], p["err_bg"], 1.0 if self._basili else t)
            kenar = karistir(p["kenar"], p["err"], t * 0.6)
            return zemin, p["err"], kenar
        if self.tur == "hayalet":
            oran = 1.0 if self._basili else t
            zemin = ust_zemin if oran < 0.03 else karistir(ust_zemin, p["yuzey2"], max(oran, 0.35))
            yazi = karistir(p["muted"], p["ink"], oran)
            return zemin, yazi, zemin
        # ikincil
        zemin = karistir(p["yuzey"], p["yuzey2"], 1.0 if self._basili else t)
        kenar = karistir(p["kenar"], p["muted"], t * 0.35)
        return zemin, p["ink"], kenar

    def _boya(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        ust_zemin = _ust_zemin_rengi(self, p["bg"])
        zemin, yazi, kenar = self._renkler(p, ust_zemin)
        hizli_boya(self, fg_color=zemin, border_color=kenar, bg_color=ust_zemin)
        hizli_boya(self._ic, fg_color=zemin, bg_color=zemin)
        if self._ikon_lbl is not None:
            hizli_boya(self._ikon_lbl, fg_color=zemin, bg_color=zemin, text_color=yazi)
        hizli_boya(self._metin_lbl, fg_color=zemin, bg_color=zemin, text_color=yazi)

    def _uzerinde_gir(self, _e=None):
        if not self.etkin:
            return
        if self._hover_t >= 0.99:
            return
        bas = self._hover_t
        tema.anim(self._anim_id, 110, lambda k: self._hover_adim(bas + (1.0 - bas) * k))

    def _uzerinde_cik(self, _e=None):
        if _fare_icinde_mi(self, _e):
            return
        self._basili = False
        bas = self._hover_t
        tema.anim(self._anim_id, 130, lambda k: self._hover_adim(bas * (1.0 - k)))

    def _hover_adim(self, deger):
        self._hover_t = max(0.0, min(1.0, deger))
        self._boya()

    def _bas(self, _e=None):
        if not self.etkin:
            return
        self._basili = True
        self._boya()

    def _birak(self, _e=None):
        if not self.etkin:
            return
        self._basili = False
        icerde = _fare_icinde_mi(self, _e)
        if not icerde:
            self._hover_t = 0.0
        self._boya()
        if icerde and self.komut:
            # Komutu olay işleyicisinin dışında çalıştır: yerel pencereler (klasör/dosya
            # seçici) bağlama dağıtımı içinde değil, ana döngüde açılır.
            self.after(1, self.komut)

    def metin_ayarla(self, metin, ikon=None):
        self._metin_lbl.configure(text=metin)
        if ikon is not None and self._ikon_lbl is not None:
            self._ikon_lbl.configure(text=GLIF.get(ikon, ikon))
        self._boya()

    def durum_ayarla(self, etkin, metin=None):
        self.etkin = bool(etkin)
        imlec = "hand2" if self.etkin else "arrow"
        for w in (self, self._ic, self._ikon_lbl, self._metin_lbl):
            if w is not None:
                w.configure(cursor=imlec)
        if metin is not None:
            self._metin_lbl.configure(text=metin)
        if not self.etkin:
            self._hover_t = 0.0
            self._basili = False
        self._boya()


class IkonButon(ctk.CTkFrame):
    """Satır içi işlemler için kompakt kare ikon butonu (28x28)."""

    def __init__(self, parent, ikon, komut=None, ipucu="", boy=28, tur="hayalet", **kw):
        self.komut = komut
        self.tur = tur
        self.etkin = True
        self._hover_t = 0.0
        self._anim_id = f"ibtn_{id(self)}"

        ilk_ust = _ust_zemin_rengi(parent, tema.p["bg"])
        zemin0, yazi0, kenar0 = self._renk_hesapla(tema.p, ilk_ust)

        super().__init__(
            parent, width=boy, height=boy, corner_radius=6,
            border_width=1 if tur == "ikincil" else 0,
            fg_color=zemin0, border_color=kenar0, bg_color=ilk_ust,
            cursor="hand2", **kw
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        glif = GLIF.get(ikon, ikon)
        self._lbl = ctk.CTkLabel(
            self, text=glif, font=ikon_fontu(max(12, boy - 14)),
            fg_color=zemin0, bg_color=zemin0, text_color=yazi0, cursor="hand2"
        )
        self._lbl.place(relx=0.5, rely=0.5, anchor="center")

        for w in (self, self._lbl):
            w.bind("<Enter>", self._gir, add="+")
            w.bind("<Leave>", self._cik, add="+")
            w.bind("<ButtonRelease-1>", self._tikla, add="+")

        self.ipucu = Ipucu(self, ipucu) if ipucu else None
        tema.bagla_fn(self, self._boya)

    def ikon_ayarla(self, ikon, ipucu=None):
        self._lbl.configure(text=GLIF.get(ikon, ikon))
        if ipucu is not None and self.ipucu is not None:
            self.ipucu.guncelle(ipucu)
        self._boya()

    def _renk_hesapla(self, p, ust_zemin):
        t = self._hover_t if self.etkin else 0.0
        if self.tur == "tehlike":
            zemin = ust_zemin if t < 0.04 else karistir(ust_zemin, p["err_bg"], t)
            yazi = karistir(p["muted"], p["err"], max(0.35, t))
            kenar = p["kenar"]
        elif self.tur == "vurgu":
            zemin = karistir(p["accent_bg"], p["accent"], t * 0.25)
            yazi = p["accent_ink"]
            kenar = p["kenar"]
        elif self.tur == "ikincil":
            zemin = karistir(p["yuzey"], p["yuzey2"], t)
            yazi = karistir(p["muted"], p["ink"], t)
            kenar = p["kenar"]
        else:
            zemin = ust_zemin if t < 0.04 else karistir(ust_zemin, p["yuzey2"], max(0.45, t))
            yazi = karistir(p["muted"], p["ink"], t) if self.etkin else p["soluk"]
            kenar = p["kenar"]
        return zemin, yazi, kenar

    def _boya(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        ust_zemin = _ust_zemin_rengi(self, p["bg"])
        zemin, yazi, kenar = self._renk_hesapla(p, ust_zemin)
        hizli_boya(self, fg_color=zemin, border_color=kenar, bg_color=ust_zemin)
        hizli_boya(self._lbl, fg_color=zemin, bg_color=zemin, text_color=yazi)

    def _gir(self, _e=None):
        if not self.etkin or self._hover_t >= 0.99:
            return
        bas = self._hover_t
        tema.anim(self._anim_id, 110, lambda k: self._adim(bas + (1.0 - bas) * k))

    def _cik(self, _e=None):
        if _fare_icinde_mi(self, _e):
            return
        bas = self._hover_t
        tema.anim(self._anim_id, 130, lambda k: self._adim(bas * (1.0 - k)))

    def _adim(self, deger):
        self._hover_t = max(0.0, min(1.0, deger))
        self._boya()

    def _tikla(self, _e=None):
        if self.etkin and _fare_icinde_mi(self, _e) and self.komut:
            self.after(1, self.komut)


class Segment(ctk.CTkFrame):
    """Kompakt, akıcı geçişli segment seçici.

    Buton havuzu (`_havuz`) sayesinde seçenekler güncellendiğinde bileşenler
    yıkılıp yeniden oluşturulmaz; açık temada tıklama sırasında siyah parlama oluşmaz.
    """

    def __init__(self, parent, secenekler, komut=None, aktif=None, yukseklik=30, font_boy=12, **kw):
        p0 = tema.p
        ilk_ust = _ust_zemin_rengi(parent, p0["bg"])
        super().__init__(
            parent, height=yukseklik, corner_radius=6, border_width=1,
            fg_color=p0["seg"], border_color=p0["kenar"], bg_color=ilk_ust, **kw
        )
        self.komut = komut
        self._yukseklik = yukseklik
        self._font_boy = font_boy
        self._secenekler = list(secenekler or [])
        self._aktif = aktif if aktif in self._secenekler else (self._secenekler[0] if self._secenekler else None)
        self._havuz = []      # [(kutu, lbl)]
        self._dugmeler = {}   # ad -> (kutu, lbl)
        self._hover_idx = None
        self._insa_et()
        tema.bagla_fn(self, self._boya)

    def _slot_olustur(self, idx):
        p = tema.p
        kutu = ctk.CTkFrame(
            self, height=self._yukseklik - 6, corner_radius=5,
            fg_color=p["seg"], bg_color=p["seg"], cursor="hand2"
        )
        lbl = ctk.CTkLabel(
            kutu, text="", font=F(self._font_boy, True),
            fg_color=p["seg"], bg_color=p["seg"], text_color=p["muted"], cursor="hand2"
        )
        lbl.pack(padx=10, pady=3)
        for w in (kutu, lbl):
            w.bind("<Enter>", lambda _e, i=idx: self._uzerine(i), add="+")
            w.bind("<Leave>", lambda _e, i=idx: self._ayril(i), add="+")
            w.bind("<ButtonRelease-1>", lambda _e, i=idx: self._slot_tiklandi(i), add="+")
        self._havuz.append((kutu, lbl))
        return kutu, lbl

    def _insa_et(self):
        self._dugmeler.clear()
        toplam = len(self._secenekler)
        while len(self._havuz) < toplam:
            self._slot_olustur(len(self._havuz))

        for i, (kutu, lbl) in enumerate(self._havuz):
            if i < toplam:
                ad = self._secenekler[i]
                self.grid_columnconfigure(i, weight=1)
                lbl.configure(text=ad)
                kutu.grid(
                    row=0, column=i, sticky="ew",
                    padx=(3 if i == 0 else 1, 3 if i == toplam - 1 else 1), pady=3
                )
                self._dugmeler[ad] = (kutu, lbl)
            else:
                self.grid_columnconfigure(i, weight=0)
                kutu.grid_remove()

    def _slot_tiklandi(self, idx):
        if 0 <= idx < len(self._secenekler):
            kutu, _ = self._havuz[idx]
            if _fare_icinde_mi(kutu):
                self.sec(self._secenekler[idx], bildir=True)

    def _uzerine(self, idx):
        if self._hover_idx != idx:
            self._hover_idx = idx
            self._boya()

    def _ayril(self, idx):
        if idx < len(self._havuz):
            kutu, _ = self._havuz[idx]
            if _fare_icinde_mi(kutu):
                return
        if self._hover_idx == idx:
            self._hover_idx = None
            self._boya()

    def _boya(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        ust_zemin = _ust_zemin_rengi(self, p["bg"])
        hizli_boya(self, fg_color=p["seg"], border_color=p["kenar"], bg_color=ust_zemin)
        for i, ad in enumerate(self._secenekler):
            kutu, lbl = self._havuz[i]
            secili = (ad == self._aktif)
            uzerinde = (i == self._hover_idx)
            if secili:
                zemin = p["seg_sec"]
                yazi = p["ink"]
            elif uzerinde:
                zemin = karistir(p["seg"], p["seg_sec"], 0.45)
                yazi = p["ink"]
            else:
                zemin = p["seg"]
                yazi = p["muted"]
            hizli_boya(kutu, fg_color=zemin, bg_color=p["seg"])
            hizli_boya(lbl, fg_color=zemin, bg_color=zemin, text_color=yazi)

    def sec(self, ad, bildir=False):
        if ad not in self._secenekler:
            return
        degisti = (ad != self._aktif)
        self._aktif = ad
        self._boya()
        if bildir and degisti and self.komut:
            self.komut(ad)

    def set(self, ad):
        self.sec(ad, bildir=False)

    def get(self):
        return self._aktif

    def secenekleri_guncelle(self, secenekler, aktif=None):
        yeni = list(secenekler or [])
        secim = aktif if aktif in yeni else (self._aktif if self._aktif in yeni else (yeni[0] if yeni else None))
        if yeni == self._secenekler:
            self.sec(secim, bildir=False)
            return
        self._secenekler = yeni
        self._aktif = secim
        self._hover_idx = None
        self._insa_et()
        self._boya()


class Rozet(ctk.CTkFrame):
    """Durum veya tür gösteren sade, kompakt etiket."""

    _HARITA = {
        "sirada": ("iz", "muted"),
        "aktif": ("accent_bg", "accent_ink"),
        "duraklatildi": ("iz", "ink"),
        "tamam": ("ok_bg", "ok"),
        "hata": ("err_bg", "err"),
        "iptal": ("iz", "muted"),
        "notr": ("yuzey2", "muted"),
    }

    def __init__(self, parent, metin="", durum="notr", **kw):
        p0 = tema.p
        ilk_ust = _ust_zemin_rengi(parent, p0["bg"])
        zemin_k, yazi_k = self._HARITA.get(durum, self._HARITA["notr"])
        super().__init__(
            parent, corner_radius=5,
            fg_color=p0[zemin_k], bg_color=ilk_ust, **kw
        )
        self._durum = durum
        self._lbl = ctk.CTkLabel(
            self, text=metin, font=F(11, True),
            fg_color=p0[zemin_k], bg_color=p0[zemin_k], text_color=p0[yazi_k]
        )
        self._lbl.pack(padx=7, pady=2)
        tema.bagla_fn(self, self._boya)

    def ayarla(self, metin, durum=None):
        if durum is not None:
            self._durum = durum
        self._lbl.configure(text=metin)
        self._boya()

    def _boya(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        ust_zemin = _ust_zemin_rengi(self, p["bg"])
        zemin_k, yazi_k = self._HARITA.get(self._durum, self._HARITA["notr"])
        zemin = p[zemin_k]
        yazi = p[yazi_k]
        hizli_boya(self, fg_color=zemin, bg_color=ust_zemin)
        hizli_boya(self._lbl, fg_color=zemin, bg_color=zemin, text_color=yazi)


class IlerlemeCubugu(tk.Canvas):
    """Yumuşak değer geçişli, ince (4px) ilerleme çubuğu."""

    def __init__(self, parent, yukseklik=4, **kw):
        super().__init__(
            parent, height=yukseklik, bd=0, highlightthickness=0, relief="flat", **kw
        )
        self._yukseklik = yukseklik
        self._gosterilen = 0.0
        self._hedef = 0.0
        self._renk_k = "accent"
        self._anim_id = f"prog_{id(self)}"
        self.bind("<Configure>", lambda _e: self._ciz(), add="+")
        tema.bagla_fn(self, self._ciz)

    def set(self, deger, animasyonlu=True, renk=None):
        if renk is not None:
            self._renk_k = renk
        hedef = max(0.0, min(1.0, float(deger or 0.0)))
        self._hedef = hedef
        if not animasyonlu or abs(hedef - self._gosterilen) < 0.008:
            tema.anim_iptal(self._anim_id)
            self._gosterilen = hedef
            self._ciz()
            return
        bas = self._gosterilen
        fark = hedef - bas
        tema.anim(self._anim_id, 140, lambda t: self._adim(bas + fark * t))

    def _adim(self, deger):
        self._gosterilen = max(0.0, min(1.0, deger))
        self._ciz()

    def _ciz(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), self._yukseklik)
        self.configure(bg=p["iz"])
        self.delete("all")
        if self._gosterilen > 0.002:
            dolgu = max(4, int(round(w * self._gosterilen)))
            self.create_rectangle(0, 0, dolgu, h, fill=p.get(self._renk_k, p["accent"]), width=0)


class Anahtar(tk.Canvas):
    """Yumuşak kayma animasyonlu modern anahtar (toggle switch)."""

    def __init__(self, parent, deger=False, komut=None, **kw):
        super().__init__(
            parent, width=38, height=20, bd=0, highlightthickness=0,
            relief="flat", cursor="hand2", **kw
        )
        self._deger = bool(deger)
        self._t = 1.0 if self._deger else 0.0
        self.komut = komut
        self._ust_renk_k = "bg"
        self._anim_id = f"sw_{id(self)}"
        self.bind("<ButtonRelease-1>", self._degistir, add="+")
        self.bind("<Configure>", lambda _e: self._ciz(), add="+")
        tema.bagla_fn(self, self._ciz)

    def zemin_jetonu(self, jeton):
        self._ust_renk_k = jeton
        self._ciz()

    def get(self):
        return self._deger

    def set(self, deger, animasyonlu=True):
        yeni = bool(deger)
        self._deger = yeni
        hedef = 1.0 if yeni else 0.0
        if not animasyonlu:
            self._t = hedef
            self._ciz()
            return
        bas = self._t
        fark = hedef - bas
        tema.anim(self._anim_id, 150, lambda k: self._adim(bas + fark * k), ease=ease_out)

    def select(self):
        self.set(True, animasyonlu=False)

    def deselect(self):
        self.set(False, animasyonlu=False)

    def _degistir(self, _e=None):
        self.set(not self._deger, animasyonlu=True)
        if self.komut:
            self.komut(self._deger)

    def _adim(self, deger):
        self._t = max(0.0, min(1.0, deger))
        self._ciz()

    def _ciz(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        w = max(self.winfo_width(), 38)
        h = max(self.winfo_height(), 20)
        self.configure(bg=p.get(self._ust_renk_k, p["bg"]))
        self.delete("all")
        iz_renk = karistir(p["iz"], p["accent"], self._t)
        r = h // 2
        self.create_oval(1, 1, h - 1, h - 1, fill=iz_renk, outline="")
        self.create_oval(w - h + 1, 1, w - 1, h - 1, fill=iz_renk, outline="")
        self.create_rectangle(r, 1, w - r, h - 1, fill=iz_renk, outline="")
        cap = h - 6
        x0 = 3 + (w - cap - 6) * self._t
        self.create_oval(x0, 3, x0 + cap, 3 + cap, fill="#FFFFFF", outline="")


class BildirimYoneticisi:
    """Sağ alt köşede beliren ve kendiliğinden kaybolan zarif bildirim çubuğu."""

    def __init__(self, kok):
        self.kok = kok
        self._kutu = None
        self._kapat_job = None
        self._anim_id = "toast_anim"

    def goster(self, metin, tur="bilgi", sure=3600):
        self.gizle(aninda=True)
        if not self.kok.winfo_exists():
            return
        p = tema.p
        ikon_harita = {"tamam": ("tamam", "ok"), "hata": ("hata", "err"), "bilgi": ("bilgi", "accent_ink")}
        glif_ad, renk_k = ikon_harita.get(tur, ikon_harita["bilgi"])

        kutu = ctk.CTkFrame(
            self.kok, corner_radius=8, border_width=1,
            fg_color=p["toast"], border_color=p["kenar"], bg_color=p["bg"]
        )
        ic = ctk.CTkFrame(kutu, corner_radius=0, fg_color=p["toast"], bg_color=p["toast"])
        ic.pack(padx=14, pady=10)
        ikon_lbl = ctk.CTkLabel(
            ic, text=GLIF[glif_ad], font=ikon_fontu(14),
            fg_color=p["toast"], bg_color=p["toast"], text_color=p[renk_k]
        )
        ikon_lbl.pack(side="left", padx=(0, 9))
        yazi_lbl = ctk.CTkLabel(
            ic, text=metin, font=F(12, True),
            fg_color=p["toast"], bg_color=p["toast"], text_color=p["ink"],
            justify="left", wraplength=380
        )
        yazi_lbl.pack(side="left")

        for w in (kutu, ic, ikon_lbl, yazi_lbl):
            w.bind("<ButtonRelease-1>", lambda _e: self.gizle(), add="+")

        self._kutu = kutu
        tema.bagla(kutu, fg_color="toast", border_color="kenar")
        tema.bagla(ic, fg_color="toast")
        tema.bagla(ikon_lbl, fg_color="toast", text_color=renk_k)
        tema.bagla(yazi_lbl, fg_color="toast", text_color="ink")

        def adim(t):
            if self._kutu is kutu and kutu.winfo_exists():
                kutu.place(relx=1.0, rely=1.0, x=-24, y=int(-6 - 16 * t), anchor="se")

        tema.anim(self._anim_id, 160, adim)
        self._kapat_job = self.kok.after(sure, self.gizle)

    def gizle(self, aninda=False):
        if self._kapat_job is not None:
            try:
                self.kok.after_cancel(self._kapat_job)
            except Exception:
                pass
            self._kapat_job = None
        kutu = self._kutu
        self._kutu = None
        if kutu is None or not kutu.winfo_exists():
            return
        if aninda or not tema.animasyon:
            try:
                kutu.destroy()
            except Exception:
                pass
            return

        def adim(t):
            if kutu.winfo_exists():
                kutu.place(relx=1.0, rely=1.0, x=-24, y=int(-22 + 18 * t), anchor="se")

        def bitis():
            try:
                if kutu.winfo_exists():
                    kutu.destroy()
            except Exception:
                pass

        tema.anim(self._anim_id, 130, adim, bitis)
