"""Geçmiş Sayfası: Kalıcı İndirme ve Dönüştürme Geçmişi.

Veriler `%APPDATA%\\Kroxload\\gecmis.json` dosyasından (`kroxload.core.history`)
okunur. İndirme ve dönüştürme işlemleri ayrı rozet ve filtrelerle ayırt edilir.
"""
from pathlib import Path

import customtkinter as ctk

from kroxload.core import history
from kroxload.core.engine import boyut_yaz

from .theme import F, GLIF, ikon_fontu, kirp, tema
from .widgets import Ayirici, Buton, IkonButon, Ipucu, Rozet, Segment, kaydirilabilir_alan

FILTRELER = ("Tümü", "İndirmeler", "Dönüştürmeler", "Başarısız")


class GecmisSatiri(ctk.CTkFrame):
    """Geçmiş listesindeki tek bir işlem kaydı."""

    def __init__(self, parent, sayfa, kayit):
        p0 = tema.p
        super().__init__(
            parent, corner_radius=6, border_width=1,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"]
        )
        self.sayfa = sayfa
        self.kayit = kayit
        self.kayit_id = kayit.get("id")
        self.dosya = kayit.get("dosya") or ""
        self.klasor = kayit.get("klasor") or (str(Path(self.dosya).parent) if self.dosya else "")
        self.baslik_tam = kayit.get("baslik") or (Path(self.dosya).name if self.dosya else "Kayıt")

        tema.bagla(self, fg_color="yuzey", border_color="kenar")
        self.grid_columnconfigure(1, weight=1)

        tur = kayit.get("tur", "indirme")
        ikon_ad = "donustur" if tur == "donusum" else "indir"
        ikon_renk_k = "accent_ink" if tur == "donusum" else "muted"
        self.tur_ikon = ctk.CTkLabel(
            self, text=GLIF[ikon_ad], font=ikon_fontu(15), width=28, height=28,
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0[ikon_renk_k]
        )
        self.tur_ikon.grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=10, sticky="n")
        tema.bagla(self.tur_ikon, fg_color="yuzey", text_color=ikon_renk_k)

        orta = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        orta.grid(row=0, column=1, rowspan=2, sticky="ew", pady=(9, 9))
        orta.grid_columnconfigure(0, weight=1)
        tema.bagla(orta, fg_color="yuzey")

        ust_satir = ctk.CTkFrame(orta, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        ust_satir.grid(row=0, column=0, sticky="ew")
        tema.bagla(ust_satir, fg_color="yuzey")

        tur_etiket = "Dönüştürme" if tur == "donusum" else "İndirme"
        self.tur_rozet = Rozet(ust_satir, tur_etiket, "aktif" if tur == "donusum" else "notr")
        self.tur_rozet.pack(side="left", padx=(0, 8))

        self.baslik_lbl = ctk.CTkLabel(
            ust_satir, text="", anchor="w", font=F(13, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"]
        )
        self.baslik_lbl.pack(side="left", fill="x", expand=True)
        tema.bagla(self.baslik_lbl, fg_color="yuzey", text_color="ink")

        # Alt detay: biçim, kalite, boyut, tarih, klasör
        dosya_var = bool(self.dosya and Path(self.dosya).exists())
        boyut = ""
        if dosya_var:
            try:
                boyut = boyut_yaz(Path(self.dosya).stat().st_size)
            except OSError:
                boyut = ""

        durum = kayit.get("durum", "tamam")
        parcalar = [x for x in (kayit.get("format"), kayit.get("kalite"), boyut, kayit.get("tarih")) if x]
        if self.klasor:
            parcalar.append(self.sayfa.uygulama.kisalt_yol(self.klasor, 36))
        if durum == "hata" and kayit.get("hata"):
            detay_metin = f"{' · '.join(parcalar)}  —  {kayit['hata']}"
        elif durum == "tamam" and self.dosya and not dosya_var:
            detay_metin = f"{' · '.join(parcalar)}  (dosya taşınmış veya silinmiş)"
        else:
            detay_metin = " · ".join(parcalar)

        detay_renk_k = "err" if durum == "hata" else "muted"
        self.detay_lbl = ctk.CTkLabel(
            orta, text=detay_metin, anchor="w", font=F(11),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0[detay_renk_k]
        )
        self.detay_lbl.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        tema.bagla(self.detay_lbl, fg_color="yuzey", text_color=detay_renk_k)
        if self.dosya or self.klasor:
            Ipucu(self.detay_lbl, self.dosya or self.klasor)

        # Sağ: durum rozeti + eylemler
        sag = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        sag.grid(row=0, column=2, rowspan=2, padx=(10, 12), pady=9, sticky="e")
        tema.bagla(sag, fg_color="yuzey")

        if durum == "hata":
            Rozet(sag, "Başarısız", "hata").pack(side="left", padx=(0, 8))
        elif self.dosya and not dosya_var:
            Rozet(sag, "Taşınmış", "sirada").pack(side="left", padx=(0, 8))
        else:
            Rozet(sag, "Tamamlandı", "tamam").pack(side="left", padx=(0, 8))

        eylemler = ctk.CTkFrame(sag, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        eylemler.pack(side="left")
        tema.bagla(eylemler, fg_color="yuzey")

        if dosya_var:
            IkonButon(
                eylemler, "dosya_ac",
                komut=lambda: self.sayfa.uygulama.dosya_ac(self.dosya),
                ipucu="Dosyayı aç"
            ).pack(side="left", padx=(0, 4))
        hedef = self.dosya if dosya_var else (self.klasor if self.klasor and Path(self.klasor).is_dir() else "")
        if hedef:
            IkonButon(
                eylemler, "klasor_ac",
                komut=lambda h=hedef: self.sayfa.uygulama.klasor_ac(h),
                ipucu="Klasörde göster"
            ).pack(side="left", padx=(0, 4))
        IkonButon(
            eylemler, "sil", komut=lambda: self.sayfa.kayit_sil(self),
            ipucu="Geçmişten kaldır", tur="tehlike"
        ).pack(side="left")

        self.bind("<Configure>", self._yeniden_boyut, add="+")
        self._baslik_yenile()

    def _yeniden_boyut(self, _e=None):
        self._baslik_yenile()

    def _baslik_yenile(self):
        maks = max(160, (self.winfo_width() or 640) - 360)
        self.baslik_lbl.configure(text=kirp(self.baslik_tam, maks, 13, True))


class GecmisSayfasi(ctk.CTkFrame):
    """İndirme ve dönüştürme geçmişi sayfası."""

    def __init__(self, parent, uygulama):
        p0 = tema.p
        super().__init__(parent, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self, fg_color="bg")
        self.uygulama = uygulama
        self.satir_widgetlar = []
        self._insa_et()
        self.yenile()

    def _insa_et(self):
        p0 = tema.p
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ---- 1. Üst Başlık ----
        ust = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        ust.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))
        ust.grid_columnconfigure(0, weight=1)
        tema.bagla(ust, fg_color="bg")

        sol = ctk.CTkFrame(ust, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        sol.grid(row=0, column=0, sticky="w")
        tema.bagla(sol, fg_color="bg")
        b_lbl = ctk.CTkLabel(
            sol, text="İşlem Geçmişi", font=F(19, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        b_lbl.pack(anchor="w")
        tema.bagla(b_lbl, fg_color="bg", text_color="ink")
        alt_lbl = ctk.CTkLabel(
            sol,
            text="Tamamlanan ve başarısız olan tüm indirme ve dönüştürme kayıtları kalıcı olarak saklanır.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        alt_lbl.pack(anchor="w", pady=(2, 0))
        tema.bagla(alt_lbl, fg_color="bg", text_color="muted")

        sag_aks = ctk.CTkFrame(ust, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        sag_aks.grid(row=0, column=1, sticky="e")
        tema.bagla(sag_aks, fg_color="bg")

        self.sayac_rozet = Rozet(sag_aks, "0 kayıt", "notr")
        self.sayac_rozet.pack(side="left", padx=(0, 10))

        self.temizle_btn = Buton(
            sag_aks, metin="Geçmişi Temizle", ikon="sil",
            komut=self.gecmisi_temizle, tur="tehlike", yukseklik=30, font_boy=11
        )
        self.temizle_btn.pack(side="left")

        # ---- 2. Filtre ve Arama Çubuğu ----
        filtre_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        filtre_bar.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 12))
        filtre_bar.grid_columnconfigure(1, weight=1)
        tema.bagla(filtre_bar, fg_color="bg")

        self.filtre_sb = Segment(
            filtre_bar, list(FILTRELER), komut=lambda _s: self.yenile(),
            aktif=FILTRELER[0], yukseklik=32
        )
        self.filtre_sb.grid(row=0, column=0, sticky="w", padx=(0, 14))

        ara_kutu = ctk.CTkFrame(
            filtre_bar, corner_radius=6, border_width=1, height=32,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"]
        )
        ara_kutu.grid(row=0, column=1, sticky="ew")
        ara_kutu.grid_propagate(False)
        ara_kutu.grid_columnconfigure(1, weight=1)
        tema.bagla(ara_kutu, fg_color="yuzey", border_color="kenar")

        ara_ikon = ctk.CTkLabel(
            ara_kutu, text=GLIF["ara"], font=ikon_fontu(12),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        ara_ikon.grid(row=0, column=0, padx=(10, 6), pady=6)
        tema.bagla(ara_ikon, fg_color="yuzey", text_color="muted")

        self.ara_giris = ctk.CTkEntry(
            ara_kutu, border_width=0, corner_radius=0, height=26,
            placeholder_text="Dosya adı, biçim veya klasör ara…", font=F(12),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"],
            placeholder_text_color=p0["soluk"]
        )
        self.ara_giris.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=2)
        tema.bagla(
            self.ara_giris, fg_color="yuzey", text_color="ink",
            placeholder_text_color="soluk"
        )
        self.ara_giris.bind("<KeyRelease>", lambda _e: self.yenile(), add="+")

        Ayirici(self).grid(row=2, column=0, sticky="ew", padx=28)

        # ---- 3. Liste Alanı ----
        self.liste_alan = kaydirilabilir_alan(self)
        self.liste_alan.grid(row=3, column=0, sticky="nsew", padx=22, pady=(10, 14))
        self.liste_alan.grid_columnconfigure(0, weight=1)

        self.bos_kutu = ctk.CTkFrame(self.liste_alan, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self.bos_kutu, fg_color="bg")
        bos_ik = ctk.CTkLabel(
            self.bos_kutu, text=GLIF["gecmis"], font=ikon_fontu(24),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["soluk"]
        )
        bos_ik.pack(pady=(0, 8))
        tema.bagla(bos_ik, fg_color="bg", text_color="soluk")
        self.bos_baslik = ctk.CTkLabel(
            self.bos_kutu, text="Henüz geçmiş kaydı yok", font=F(13, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        self.bos_baslik.pack()
        tema.bagla(self.bos_baslik, fg_color="bg", text_color="muted")
        self.bos_alt = ctk.CTkLabel(
            self.bos_kutu,
            text="İndirdiğiniz ve dönüştürdüğünüz medya dosyaları burada listelenir.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["soluk"]
        )
        self.bos_alt.pack(pady=(3, 0))
        tema.bagla(self.bos_alt, fg_color="bg", text_color="soluk")

    def _suz(self, kayitlar):
        secim = self.filtre_sb.get()
        if secim == "İndirmeler":
            kayitlar = [k for k in kayitlar if k.get("tur", "indirme") == "indirme"]
        elif secim == "Dönüştürmeler":
            kayitlar = [k for k in kayitlar if k.get("tur") == "donusum"]
        elif secim == "Başarısız":
            kayitlar = [k for k in kayitlar if k.get("durum") == "hata"]

        aranan = (self.ara_giris.get() or "").strip().lower()
        if aranan:
            kayitlar = [
                k for k in kayitlar
                if aranan in (k.get("baslik") or "").lower()
                or aranan in (k.get("dosya") or "").lower()
                or aranan in (k.get("format") or "").lower()
                or aranan in (k.get("kalite") or "").lower()
            ]
        return kayitlar

    def yenile(self):
        for w in self.satir_widgetlar:
            try:
                w.destroy()
            except Exception:
                pass
        self.satir_widgetlar.clear()

        tum = history.liste()
        suzulmus = self._suz(tum)
        self.sayac_rozet.ayarla(f"{len(suzulmus)} kayıt", "notr")

        if not suzulmus:
            self.bos_baslik.configure(
                text="Eşleşen kayıt bulunamadı" if tum else "Henüz geçmiş kaydı yok"
            )
            self.bos_kutu.pack(fill="x", pady=54)
            return

        self.bos_kutu.pack_forget()
        for kayit in suzulmus:
            satir = GecmisSatiri(self.liste_alan, self, kayit)
            satir.pack(fill="x", padx=6, pady=(0, 6))
            self.satir_widgetlar.append(satir)

    def kayit_sil(self, satir):
        if satir.kayit_id:
            history.cikar_id(satir.kayit_id)
        elif satir.dosya:
            history.cikar(satir.dosya)
        self.yenile()

    def gecmisi_temizle(self):
        history.temizle()
        self.yenile()
        self.uygulama.bildirim("İşlem geçmişi temizlendi.", "bilgi")
