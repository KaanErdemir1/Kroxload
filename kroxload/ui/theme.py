"""Kroxload tasarım sistemi: renk paletleri, tipografi, ikon glifleri, animasyon ve tema geçişi.

Renkler kimliği logodan alır: logo indigosu #4E5AE6 (ton ≈235°); arayüz vurgusu aynı
ailenin biraz mora çekilmiş hâlidir (ton ≈246°). Koyu temada vurgu okunabilirlik için
açılır, açık temada koyulur. Nötrler çok hafif mor-mavi tonludur; gradyan, parıltı,
cam efekti kullanılmaz.

Tema değişimi iki palet arasında zamana bağlı ara değerlerle yapılır; hızlı tuval
boyayıcı (`hizli_boya`) sayesinde her kare ~3 ms içinde doğrudan çizilir ve
`update_idletasks()` ile anında ekrana yansıtılır.
"""
import time
import tkinter as tk
import tkinter.font as tkfont
import weakref

import customtkinter as ctk

from kroxload.core.logs import kayit as log

PALETLER = {
    "koyu": {
        "bg": "#0E0E13",        # ana yüzey
        "yan": "#0A0A0E",       # yan panel
        "yuzey": "#16161D",     # girişler, seçili satır
        "yuzey2": "#1F1F28",    # hover / yükseltilmiş
        "kenar": "#2A2A35",
        "iz": "#262631",        # ilerleme çubuğu zemini
        "ink": "#F1F1F6",
        "muted": "#9B9BAB",
        "soluk": "#64646F",
        "accent": "#7467F0",
        "accent_h": "#8579F7",
        "accent_a": "#6558E0",
        "accent_bg": "#211E3D",  # vurgunun düşük yoğunluklu zemini
        "accent_ink": "#A79EFF",  # koyu zeminde metin olarak kullanılan vurgu
        "on_accent": "#FFFFFF",
        "ok": "#5FD38D", "ok_bg": "#14261C",
        "err": "#F0716C", "err_bg": "#2C1A1C",
        "seg": "#16161D", "seg_sec": "#2A2A36",
        "toast": "#1C1C25",
    },
    "acik": {
        "bg": "#F7F7FA",
        "yan": "#EEEEF3",
        "yuzey": "#FFFFFF",
        "yuzey2": "#ECECF2",
        "kenar": "#DEDEE7",
        "iz": "#E3E3EC",
        "ink": "#15151C",
        "muted": "#62626F",
        "soluk": "#9B9BA7",
        "accent": "#5B4DE0",
        "accent_h": "#6B5EEE",
        "accent_a": "#4C3FCB",
        "accent_bg": "#E9E6FC",
        "accent_ink": "#5143D1",
        "on_accent": "#FFFFFF",
        "ok": "#1E8A4C", "ok_bg": "#E2F3E9",
        "err": "#C73A3A", "err_bg": "#FBE7E7",
        "seg": "#E9E9F0", "seg_sec": "#FFFFFF",
        "toast": "#FFFFFF",
    },
}

# ------------------------------------------------------------------ tipografi / ikonlar
SANS = "Segoe UI"
SANS_KALIN = "Segoe UI Semibold"


def F(boy, kalin=False):
    """Metin fontu (piksel boyutu; CTk DPI'a göre ölçekler)."""
    return (SANS_KALIN if kalin else SANS, boy)


_ikon_ailesi = None


def ikon_fontu(boy):
    """Segoe Fluent Icons (Win11) veya Segoe MDL2 Assets (Win10)."""
    global _ikon_ailesi
    if _ikon_ailesi is None:
        aileler = set(tkfont.families())
        _ikon_ailesi = "Segoe Fluent Icons" if "Segoe Fluent Icons" in aileler else "Segoe MDL2 Assets"
    return (_ikon_ailesi, boy)


GLIF = {
    "ev": "\uE80F", "gecmis": "\uE81C", "ayar": "\uE713", "donustur": "\uE8AB",
    "indir": "\uE896", "yukle": "\uE898", "yapistir": "\uE77F", "klasor": "\uE8B7",
    "klasor_ac": "\uED25", "oynat": "\uE768", "duraklat": "\uE769", "kapat": "\uE711",
    "tamam": "\uE73E", "sil": "\uE74D", "dosya_ac": "\uE8E5", "ekle": "\uE710",
    "link": "\uE71B", "gunes": "\uE706", "ay": "\uE708", "muzik": "\uE8D6",
    "video": "\uE714", "resim": "\uE91B", "belge": "\uE8A5", "kopya": "\uE8C8",
    "yenile": "\uE72C", "bilgi": "\uE946", "hata": "\uE783", "uyari": "\uE7BA",
    "ara": "\uE721", "saat": "\uE916", "senk": "\uE895", "dosya": "\uE7C3",
}


def metin_genisligi(metin, boy, kalin=False, ikon=False):
    """Mantıksal piksel cinsinden metin genişliği (CTk ölçeklemesinden bağımsız)."""
    try:
        if ikon:
            ad = ikon_fontu(boy)[0]
            f = tkfont.Font(family=ad, size=-boy)
        else:
            f = tkfont.Font(family=SANS_KALIN if kalin else SANS, size=-boy)
        return f.measure(metin)
    except Exception:
        return int(len(metin) * boy * 0.55)


def kirp(metin, maks, boy, kalin=False):
    """Metni `maks` mantıksal pikseli aşıyorsa sonuna … koyarak kısaltır."""
    metin = " ".join(str(metin or "").split())
    if maks <= 20 or metin_genisligi(metin, boy, kalin) <= maks:
        return metin
    alt, ust = 0, len(metin)
    while alt < ust:
        orta = (alt + ust + 1) // 2
        if metin_genisligi(metin[:orta] + "…", boy, kalin) <= maks:
            alt = orta
        else:
            ust = orta - 1
    return metin[:alt].rstrip() + "…"


# ------------------------------------------------------------------ renk yardımcıları
def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(r, g, b):
    return f"#{int(round(r)):02X}{int(round(g)):02X}{int(round(b)):02X}"


def karistir(a, b, t):
    """İki hex rengi arasında t (0..1) oranında ara renk."""
    if a == b:
        return a
    ra, rb = _rgb(a), _rgb(b)
    return _hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def dogrusal(t):
    return t


def _ust_zemin_rengi(w, varsayilan="#0E0E13"):
    """Üst bileşen zincirinden gerçek hex arka plan rengini O(1) sürede bulur."""
    m = getattr(w, "master", None)
    while m is not None:
        fg = getattr(m, "_fg_color", None)
        if isinstance(fg, str) and fg.startswith("#"):
            return fg
        bg = getattr(m, "_bg_color", None)
        if isinstance(bg, str) and bg.startswith("#"):
            return bg
        m = getattr(m, "master", None)
    return varsayilan


def hizli_boya(w, fg_color=None, border_color=None, text_color=None, bg_color=None):
    """CTkFrame ve CTkLabel renklerini alt ağaç taraması yapmadan doğrudan günceller.

    CustomTkinter'ın standart `configure(fg_color=...)` metodu her çağrıda tüm alt
    bileşenleri özyinelemeli olarak yeniden çizdiği ve `tk.Frame(bg=...)` nedeniyle
    Windows GDI'da gecikmeye yol açtığı için, bu fonksiyon doğrudan iç `_canvas` ve
    `_label` öğelerini boyar.
    """
    if not w.winfo_exists():
        return
    p = tema.p
    gercek_bg = bg_color if (isinstance(bg_color, str) and bg_color.startswith("#")) else _ust_zemin_rengi(w, p["bg"])
    w._bg_color = gercek_bg

    if fg_color is not None:
        w._fg_color = gercek_bg if fg_color == "transparent" else fg_color

    mevcut_fg = getattr(w, "_fg_color", None)
    gercek_fg = mevcut_fg if (isinstance(mevcut_fg, str) and mevcut_fg.startswith("#")) else gercek_bg

    if isinstance(w, ctk.CTkFrame):
        if border_color is not None:
            w._border_color = border_color
        canvas = getattr(w, "_canvas", None)
        if canvas is not None:
            canvas.itemconfig("inner_parts", fill=gercek_fg, outline=gercek_fg)
            if getattr(w, "_border_width", 0) > 0:
                bc = getattr(w, "_border_color", None)
                if isinstance(bc, str) and bc.startswith("#"):
                    canvas.itemconfig("border_parts", fill=bc, outline=bc)
            if getattr(w, "_corner_radius", 0) > 0 or gercek_fg != gercek_bg:
                canvas.configure(bg=gercek_bg)
            else:
                canvas.configure(bg=gercek_fg)
        return

    if isinstance(w, ctk.CTkLabel):
        if text_color is not None:
            w._text_color = text_color
        canvas = getattr(w, "_canvas", None)
        if canvas is not None:
            canvas.itemconfig("inner_parts", fill=gercek_fg, outline=gercek_fg)
            canvas.configure(bg=gercek_bg if getattr(w, "_corner_radius", 0) > 0 else gercek_fg)
        lbl = getattr(w, "_label", None)
        if lbl is not None:
            tc = getattr(w, "_text_color", None)
            if isinstance(tc, str) and tc.startswith("#"):
                lbl.configure(fg=tc, bg=gercek_fg)
            else:
                lbl.configure(bg=gercek_fg)
        return

    # Diğer CTk bileşenleri (CTk, CTkEntry, CTkTextbox vb.)
    kw = {}
    if fg_color is not None:
        kw["fg_color"] = gercek_fg
    if border_color is not None:
        kw["border_color"] = border_color
    if text_color is not None:
        kw["text_color"] = text_color
    if bg_color is not None:
        kw["bg_color"] = gercek_bg
    if kw:
        w.configure(**kw)


# ------------------------------------------------------------------ tema + animasyon
class Tema:
    """Tek örnekli (modül düzeyinde `tema`) palet, kayıt defteri ve animatör."""

    def __init__(self):
        self.kok = None
        self.ad = "koyu"
        self.p = dict(PALETLER["koyu"])
        self.animasyon = True
        self._kayit = []          # [(weakref(widget), fn, sayfa_kodu)]
        self._anims = {}          # anahtar -> durum
        self._tik_job = None
        self._kirli_sayfalar = set()

    # ---- kurulum ----
    def baslat(self, kok, ad="koyu", animasyon=True):
        self.kok = kok
        self.ad = ad if ad in PALETLER else "koyu"
        self.p = dict(PALETLER[self.ad])
        self.animasyon = animasyon
        self._kirli_sayfalar.clear()

    def _sayfa_bul(self, w):
        """Bileşenin hangi sayfaya ('ana', 'gecmis', 'ayarlar', 'donusturucu') ait olduğunu bulur."""
        sayfalar = getattr(self.kok, "sayfalar", None)
        if not sayfalar:
            return None
        ters = {v: k for k, v in sayfalar.items()}
        m = w
        while m is not None:
            if m in ters:
                return ters[m]
            m = getattr(m, "master", None)
        return None

    # ---- bağlama ----
    def bagla(self, w, **kurallar):
        """w bileşenini palet jetonlarına bağlar:  bagla(frm, fg_color="yuzey")"""
        hizli_mi = isinstance(w, (ctk.CTkFrame, ctk.CTkLabel)) and not isinstance(w, ctk.CTkScrollableFrame)
        ozel_anahtarlar = set(kurallar.keys()) - {"fg_color", "border_color", "text_color", "bg_color"}
        if hizli_mi and not ozel_anahtarlar:
            # İlk kurulumda hem standart configure hem hizli_boya uygulansın
            ilk_degerler = {k: (v(self.p) if callable(v) else self.p[v]) for k, v in kurallar.items()}
            try:
                w.configure(**ilk_degerler)
            except Exception:
                pass

            def fn(p):
                if w.winfo_exists():
                    cozulmus = {k: (v(p) if callable(v) else p[v]) for k, v in kurallar.items()}
                    hizli_boya(w, **cozulmus)
        else:
            def fn(p):
                if w.winfo_exists():
                    cozulmus = {k: (v(p) if callable(v) else p[v]) for k, v in kurallar.items()}
                    if "bg_color" not in cozulmus:
                        cozulmus["bg_color"] = _ust_zemin_rengi(w, p["bg"])
                    w.configure(**cozulmus)

        self.bagla_fn(w, fn)
        return w

    def bagla_fn(self, w, fn):
        """Palet değişince fn(palet) çağrılır; ilk uygulama hemen yapılır."""
        try:
            fn(self.p)
        except tk.TclError:
            return
        sayfa_kodu = self._sayfa_bul(w)
        self._kayit.append([weakref.ref(w), fn, sayfa_kodu])

    def sayfa_guncelle(self, sayfa_kodu):
        """Görünür hâle gelmek üzere olan sayfanın renklerini güncel paletle senkronlar."""
        if sayfa_kodu not in self._kirli_sayfalar:
            return
        self._kirli_sayfalar.discard(sayfa_kodu)
        p = self.p
        for giris in self._kayit:
            ref, fn, sk = giris
            w = ref()
            if w is None or not w.winfo_exists():
                continue
            if sk is None:
                sk = self._sayfa_bul(w)
                giris[2] = sk
            if sk == sayfa_kodu:
                try:
                    fn(p)
                except Exception:
                    pass

    def _uygula(self, p, sadece_aktif_sayfa=False):
        aktif_sayfa = getattr(self.kok, "aktif_sayfa", None) if sadece_aktif_sayfa else None
        canli = []
        for giris in self._kayit:
            ref, fn, sk = giris
            w = ref()
            if w is None:
                continue
            try:
                if not w.winfo_exists():
                    continue
                if sk is None and getattr(self.kok, "sayfalar", None):
                    sk = self._sayfa_bul(w)
                    giris[2] = sk
                if sadece_aktif_sayfa and sk is not None and sk != aktif_sayfa:
                    self._kirli_sayfalar.add(sk)
                    canli.append(giris)
                    continue
                fn(p)
            except tk.TclError:
                continue
            except Exception:
                log.exception("Tema uygulanamadı")
            canli.append(giris)
        self._kayit = canli

    # ---- tema geçişi ----
    def _capraz_gecis(self, ad, hedef, bitti, sure=0.26):
        """Eski ve yeni ekran görüntüsünü tek bir örtüde harmanlayan çapraz geçiş.

        Onlarca Tk penceresini her karede yeniden boyamak (≈45 ms/kare) takılma yaptığından:
        eski görüntü tıklanamaz, yakalamadan hariç tutulan bir örtü penceresinde gösterilir,
        tema altta tek seferde uygulanır, yeni görüntü yakalanır ve iki görüntü harmanlanır.
        Her karede yalnızca tek bir görüntü güncellendiği için geçiş akıcıdır.
        Herhangi bir adım başarısız olursa False döner ve klasik animasyon kullanılır.
        """
        import ctypes

        from PIL import Image, ImageChops, ImageGrab, ImageTk

        kok = self.kok
        ov = None
        try:
            kok.update_idletasks()
            if kok.state() == "iconic" or not kok.winfo_viewable():
                return False
            x, y, w, h = kok.winfo_rootx(), kok.winfo_rooty(), kok.winfo_width(), kok.winfo_height()
            if w < 100 or h < 100:
                return False
            bbox = (x, y, x + w, y + h)
            eski = ImageGrab.grab(bbox=bbox).convert("RGB")
            if eski.size != (w, h):
                eski = eski.resize((w, h))

            u32 = ctypes.windll.user32
            ov = tk.Toplevel(kok)
            ov.overrideredirect(True)
            ov.geometry(f"{w}x{h}+{x}+{y}")
            foto = ImageTk.PhotoImage(eski)
            lbl = tk.Label(ov, image=foto, bd=0, highlightthickness=0)
            lbl.image = foto
            lbl.place(x=0, y=0, width=w, height=h)
            ov.attributes("-alpha", 1.0)
            ov.update_idletasks()
            hwnd = u32.GetAncestor(ov.winfo_id(), 2)
            # Yakalamadan hariç tut (WDA_EXCLUDEFROMCAPTURE) + tıklamayı alttaki pencereye geçir
            if not u32.SetWindowDisplayAffinity(hwnd, 0x11):
                ov.destroy()
                return False
            gwl_exstyle = -20
            stil = u32.GetWindowLongW(hwnd, gwl_exstyle)
            u32.SetWindowLongW(hwnd, gwl_exstyle, stil | 0x08000000 | 0x20 | 0x80)  # NOACTIVATE|TRANSPARENT|TOOLWINDOW
            ov.update()
            time.sleep(0.015)

            # Temayı altta anında uygula (örtü ekranı eski hâlde tutar)
            self.ad = ad
            self.p = dict(hedef)
            self._uygula(self.p, sadece_aktif_sayfa=False)
            self._kirli_sayfalar.clear()
            kok.update_idletasks()
            time.sleep(0.02)
            yeni = ImageGrab.grab(bbox=bbox).convert("RGB")
            if yeni.size != (w, h):
                yeni = yeni.resize((w, h))
            # Yakalama örtüyü içermemeli: iki görüntü aynıysa hariç tutma çalışmamıştır
            if ImageChops.difference(yeni, eski).getbbox() is None:
                # Örtü yakalamadan hariç tutulamadı veya tema görsel olarak değişmedi: anında uygula
                self._uygula(self.p, sadece_aktif_sayfa=False)
                ov.destroy()
                if bitti:
                    bitti()
                return True
        except Exception:
            log.exception("Çapraz tema geçişi başlatılamadı")
            try:
                if ov is not None:
                    ov.destroy()
            except Exception:
                pass
            return False

        self._capraz_ov = ov
        if bitti:
            bitti()
        t0 = time.perf_counter()

        def kare():
            if getattr(self, "_capraz_ov", None) is not ov:
                return
            try:
                t = min((time.perf_counter() - t0) / sure, 1.0)
                foto.paste(Image.blend(eski, yeni, ease_in_out(t)))
                ov.update_idletasks()
                if t >= 1.0:
                    self._capraz_ov = None
                    ov.destroy()
                else:
                    kok.after(1, kare)
            except tk.TclError:
                self._capraz_ov = None
            except Exception:
                log.exception("Çapraz geçiş karesi")
                self._capraz_ov = None
                try:
                    ov.destroy()
                except Exception:
                    pass

        kare()
        return True

    def gecis(self, ad, bitti=None, sure=0.22):
        """Paleti yumuşakça `ad` temasına geçirir."""
        if ad not in PALETLER:
            return
        hedef = PALETLER[ad]
        eski_ov = getattr(self, "_capraz_ov", None)
        if eski_ov is not None:
            # Süren çapraz geçiş varsa iptal et ve hedefi anında uygula
            self._capraz_ov = None
            try:
                eski_ov.destroy()
            except Exception:
                pass
            self.ad = ad
            self.p = dict(hedef)
            self._uygula(self.p, sadece_aktif_sayfa=False)
            self._kirli_sayfalar.clear()
            if bitti:
                bitti()
            return
        if self.animasyon and self.kok is not None and self._capraz_gecis(ad, hedef, bitti):
            return
        self.ad = ad
        if not self.animasyon or self.kok is None:
            self.p = dict(hedef)
            self._uygula(self.p, sadece_aktif_sayfa=False)
            self._kirli_sayfalar.clear()
            if bitti:
                bitti()
            return
        baslangic = dict(self.p)

        def adim(t):
            self.p = {k: karistir(baslangic[k], hedef[k], t) for k in hedef}
            self._uygula(self.p, sadece_aktif_sayfa=True)

        def son():
            self.p = dict(hedef)
            self._uygula(self.p, sadece_aktif_sayfa=True)
            if bitti:
                bitti()

        self.anim("tema", int(sure * 1000), adim, son, ease_in_out)

    # ---- animatör ----
    def anim(self, anahtar, sure_ms, adim, bitis=None, ease=ease_out):
        """Zamana bağlı animasyon. Aynı anahtarla yeni çağrı eskisinin yerini alır."""
        if not self.animasyon or self.kok is None or sure_ms <= 0:
            self._anims.pop(anahtar, None)
            try:
                adim(1.0)
                if bitis:
                    bitis()
            except tk.TclError:
                pass
            return
        self._anims[anahtar] = {
            "t0": time.perf_counter(),
            "sure": sure_ms / 1000.0,
            "adim": adim,
            "bitis": bitis,
            "ease": ease,
        }
        if self._tik_job is None:
            self._tik_job = self.kok.after(1, self._tik)

    def anim_iptal(self, anahtar):
        self._anims.pop(anahtar, None)

    def _tik(self):
        self._tik_job = None
        simdi = time.perf_counter()
        for anahtar, a in list(self._anims.items()):
            if self._anims.get(anahtar) is not a:
                continue
            t = min((simdi - a["t0"]) / a["sure"], 1.0)
            try:
                a["adim"](a["ease"](t))
                if t >= 1.0:
                    self._anims.pop(anahtar, None)
                    if a["bitis"]:
                        a["bitis"]()
            except tk.TclError:
                self._anims.pop(anahtar, None)
            except Exception:
                log.exception("Animasyon hatası")
                self._anims.pop(anahtar, None)
        if self.kok is not None and self.kok.winfo_exists():
            try:
                self.kok.update_idletasks()
            except Exception:
                pass
            if self._anims:
                self._tik_job = self.kok.after(14, self._tik)


tema = Tema()


def olcek(w):
    """Widget'ın DPI ölçek katsayısı (mantıksal → fiziksel piksel)."""
    try:
        return ctk.ScalingTracker.get_widget_scaling(w)
    except Exception:
        return 1.0
