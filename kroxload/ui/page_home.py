"""Ana Sayfa: Medya İndirme Merkezi.

Mevcut `IndirmeMotoru`, `bilgi_getir`, `formats`, `history` ve `settings` altyapısını
korur; duraklatma (`oge_duraklat`), kaldığı yerden devam ettirme (`.part` dosyası
üzerinden), tekrar deneme ve canlı kuyruk yönetimini sunar.
"""
import io
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from kroxload.core import history
from kroxload.core.engine import IndirmeMotoru, boyut_yaz
from kroxload.core.formats import ETIKET, ETIKET_TERS, KALITELER
from kroxload.core.info import bilgi_getir
from kroxload.core.logs import kayit as log

from .shortcuts import KisayolSeridi
from .theme import F, GLIF, hizli_boya, ikon_fontu, kirp, tema
from .widgets import (
    Anahtar,
    Ayirici,
    Buton,
    IkonButon,
    IlerlemeCubugu,
    Ipucu,
    Rozet,
    Segment,
    kaydirilabilir_alan,
)

SON_DURUMLAR = {"tamam", "hata", "iptal"}


class IndirmeSatiri(ctk.CTkFrame):
    """İndirme kuyruğundaki tek bir medya satırı."""

    def __init__(self, parent, sayfa, is_id, sira, link, fmt, kalite, klasor, liste_mi):
        p0 = tema.p
        super().__init__(
            parent, corner_radius=6, border_width=1,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"]
        )
        self.sayfa = sayfa
        self.is_id = is_id
        self.sira = sira
        self.link = link
        self.fmt = fmt or "MP4"
        self.kalite = kalite or ""
        self.klasor = klasor or ""
        self.liste_mi = bool(liste_mi)
        self.durum_kodu = "sirada"
        self.baslik_tam = ""
        self.dosyalar = []
        self.son_oran = 0.0

        tema.bagla(self, fg_color="yuzey", border_color="kenar")
        self.grid_columnconfigure(1, weight=1)

        # Sol tür ikonu
        ikon_ad = "video" if self.fmt == "MP4" else "muzik"
        ikon_renk_k = "accent_ink" if self.fmt == "MP4" else "muted"
        self.tur_ikon = ctk.CTkLabel(
            self, text=GLIF[ikon_ad], font=ikon_fontu(16), width=28, height=28,
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0[ikon_renk_k]
        )
        self.tur_ikon.grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=10, sticky="n")
        tema.bagla(self.tur_ikon, fg_color="yuzey", text_color=ikon_renk_k)

        # Başlık + meta
        orta = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        orta.grid(row=0, column=1, rowspan=2, sticky="ew", pady=(9, 9))
        orta.grid_columnconfigure(0, weight=1)
        tema.bagla(orta, fg_color="yuzey")

        self.baslik_lbl = ctk.CTkLabel(
            orta, text="", anchor="w", font=F(13, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"]
        )
        self.baslik_lbl.grid(row=0, column=0, sticky="ew")
        tema.bagla(self.baslik_lbl, fg_color="yuzey", text_color="ink")

        self.detay_lbl = ctk.CTkLabel(
            orta, text="", anchor="w", font=F(11),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.detay_lbl.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self._detay_renk_k = "muted"
        tema.bagla(self.detay_lbl, fg_color="yuzey", text_color=lambda p: p[self._detay_renk_k])

        # Sağ: durum rozeti + eylem düğmeleri
        sag = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        sag.grid(row=0, column=2, rowspan=2, padx=(10, 12), pady=9, sticky="e")
        tema.bagla(sag, fg_color="yuzey")

        self.rozet = Rozet(sag, "Sırada", "sirada")
        self.rozet.pack(side="left", padx=(0, 8))

        self.eylem_kutu = ctk.CTkFrame(sag, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        self.eylem_kutu.pack(side="left")
        tema.bagla(self.eylem_kutu, fg_color="yuzey")

        # Alt: ince ilerleme çubuğu
        self.cubuk = IlerlemeCubugu(self, yukseklik=3)
        self.cubuk.grid(row=2, column=0, columnspan=3, sticky="ew", padx=1, pady=(0, 1))

        self.bind("<Configure>", self._yeniden_boyut, add="+")
        self.durum_ata("sirada")

    def _detay_renk_ayarla(self, jeton):
        self._detay_renk_k = jeton
        hizli_boya(self.detay_lbl, fg_color=tema.p["yuzey"], text_color=tema.p[jeton])

    def _yeniden_boyut(self, _e=None):
        if self.baslik_tam:
            maks = max(160, self.winfo_width() - 290)
            self.baslik_lbl.configure(text=kirp(self.baslik_tam, maks, 13, True))

    def baslik_ata(self, metin):
        self.baslik_tam = (metin or "").replace("\n", " ").strip()
        maks = max(200, (self.winfo_width() or 640) - 290)
        self.baslik_lbl.configure(text=kirp(self.baslik_tam, maks, 13, True))

    def _eylemleri_kur(self):
        for w in self.eylem_kutu.winfo_children():
            w.destroy()
        kod = self.durum_kodu
        if kod in ("sirada", "indiriliyor"):
            IkonButon(
                self.eylem_kutu, "duraklat", komut=self._duraklat,
                ipucu="İndirmeyi duraklat"
            ).pack(side="left", padx=(0, 4))
            IkonButon(
                self.eylem_kutu, "kapat", komut=self._iptal,
                ipucu="İndirmeyi iptal et", tur="tehlike"
            ).pack(side="left")
        elif kod == "isleniyor":
            IkonButon(
                self.eylem_kutu, "kapat", komut=self._iptal,
                ipucu="İptal et", tur="tehlike"
            ).pack(side="left")
        elif kod == "duraklatildi":
            IkonButon(
                self.eylem_kutu, "oynat", komut=self._devam_et,
                ipucu="Kaldığı yerden devam et", tur="vurgu"
            ).pack(side="left", padx=(0, 4))
            IkonButon(
                self.eylem_kutu, "kapat", komut=self._kaldir,
                ipucu="Kuyruktan kaldır", tur="tehlike"
            ).pack(side="left")
        elif kod == "tamam":
            if self.dosyalar and Path(self.dosyalar[0]).exists():
                IkonButon(
                    self.eylem_kutu, "dosya_ac",
                    komut=lambda: self.sayfa.uygulama.dosya_ac(self.dosyalar[0]),
                    ipucu="Dosyayı aç"
                ).pack(side="left", padx=(0, 4))
            hedef = self.dosyalar[0] if self.dosyalar else self.klasor
            if hedef:
                IkonButon(
                    self.eylem_kutu, "klasor_ac",
                    komut=lambda: self.sayfa.uygulama.klasor_ac(hedef),
                    ipucu="Klasörde göster"
                ).pack(side="left", padx=(0, 4))
            IkonButon(
                self.eylem_kutu, "kapat", komut=self._kaldir,
                ipucu="Listeden kaldır"
            ).pack(side="left")
        elif kod in ("hata", "iptal"):
            IkonButon(
                self.eylem_kutu, "yenile", komut=self._devam_et,
                ipucu="Tekrar dene"
            ).pack(side="left", padx=(0, 4))
            IkonButon(
                self.eylem_kutu, "kapat", komut=self._kaldir,
                ipucu="Listeden kaldır"
            ).pack(side="left")

    def durum_ata(self, kod):
        self.durum_kodu = kod
        etiketler = {
            "sirada": ("Sırada", "sirada"),
            "indiriliyor": ("İndiriliyor", "aktif"),
            "isleniyor": ("İşleniyor", "aktif"),
            "duraklat_bekliyor": ("Duraklatılıyor", "sirada"),
            "iptal_bekliyor": ("İptal ediliyor", "sirada"),
            "duraklatildi": ("Duraklatıldı", "duraklatildi"),
            "tamam": ("Tamamlandı", "tamam"),
            "hata": ("Hata", "hata"),
            "iptal": ("İptal edildi", "iptal"),
        }
        metin, r_kod = etiketler.get(kod, ("Sırada", "sirada"))
        self.rozet.ayarla(metin, r_kod)
        if kod == "sirada":
            self.detay_lbl.configure(text=f"{self.fmt} · {self.kalite} · sırada bekliyor")
            self._detay_renk_ayarla("muted")
        self._eylemleri_kur()

    def ilerleme_guncelle(self, o):
        if o.get("baslik"):
            self.baslik_ata(o["baslik"])
        asama = o.get("asama")
        if asama in ("donusturuluyor", "hazirlaniyor"):
            if self.durum_kodu != "isleniyor":
                self.durum_ata("isleniyor")
            metin = o.get("asama_metni") or "Dosya hazırlanıyor…"
            self.rozet.ayarla(metin, "aktif")
            self.cubuk.set(1.0)
            self.detay_lbl.configure(text=f"{self.fmt} · {self.kalite} · {metin}")
            return

        if self.durum_kodu not in ("indiriliyor", "duraklat_bekliyor", "iptal_bekliyor"):
            self.durum_ata("indiriliyor")
        oran = float(o.get("oran") or 0.0)
        self.son_oran = oran
        self.cubuk.set(oran)

        parcalar = [f"{self.fmt} {self.kalite}".strip()]
        if o.get("video_sira") and o.get("video_toplam"):
            parcalar.append(f"Liste {o['video_sira']}/{o['video_toplam']}")
        parcalar.append(f"%{oran * 100:.0f}")
        toplam_b = o.get("toplam_byte") or 0
        indirilen_b = o.get("indirilen") or 0
        if toplam_b:
            parcalar.append(f"{boyut_yaz(indirilen_b)} / {boyut_yaz(toplam_b)}")
        elif indirilen_b:
            parcalar.append(boyut_yaz(indirilen_b))
        if o.get("hiz"):
            parcalar.append(o["hiz"])
        if o.get("kalan"):
            parcalar.append(f"kalan {o['kalan']}")
        self.detay_lbl.configure(text=" · ".join(parcalar))

    def bitti_guncelle(self, o):
        if o.get("baslik"):
            self.baslik_ata(o["baslik"])
        self.dosyalar = [d for d in (o.get("dosyalar") or []) if d]

        if o.get("duraklatildi"):
            self.durum_ata("duraklatildi")
            yuzde = f"%{self.son_oran * 100:.0f} tamamlandı · " if self.son_oran > 0 else ""
            self.detay_lbl.configure(text=f"{yuzde}Duraklatıldı — devam ettirmek için oynat düğmesine basın")
            self._detay_renk_ayarla("muted")
            return

        self.cubuk.grid_remove()
        if o.get("basarili"):
            self.durum_ata("tamam")
            alanlar = [x for x in (self.fmt, self.kalite) if x]
            toplam_boyut = 0
            for d in self.dosyalar:
                try:
                    toplam_boyut += Path(d).stat().st_size
                except OSError:
                    pass
            if toplam_boyut:
                alanlar.append(boyut_yaz(toplam_boyut))
            if len(self.dosyalar) > 1:
                alanlar.append(f"{len(self.dosyalar)} dosya")
            self.detay_lbl.configure(text=" · ".join(alanlar) or "Tamamlandı")
            self._detay_renk_ayarla("muted")
        elif o.get("iptal"):
            self.durum_ata("iptal")
            self.detay_lbl.configure(text="Kullanıcı tarafından iptal edildi")
            self._detay_renk_ayarla("muted")
        else:
            self.durum_ata("hata")
            self.detay_lbl.configure(text=o.get("hata") or "Bilinmeyen indirme hatası")
            self._detay_renk_ayarla("err")

    def _duraklat(self):
        self.sayfa.satir_duraklat(self)

    def _devam_et(self):
        self.sayfa.satir_devam_et(self)

    def _iptal(self):
        self.sayfa.satir_iptal(self)

    def _kaldir(self):
        self.sayfa.satir_kaldir(self)


class AnaSayfa(ctk.CTkFrame):
    """Uygulamanın medya indirme merkezi."""

    def __init__(self, parent, uygulama):
        p0 = tema.p
        super().__init__(parent, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self, fg_color="bg")
        self.uygulama = uygulama
        self.isler = {}        # is_id -> {"motor", "satirlar": {sira: IndirmeSatiri}, "fmt", "kalite", "klasor", "liste"}
        self._is_sayac = 0
        self.satirlar = []     # görünür satırlar (en yeni üstte)
        self._onizleme_job = None
        self._onizleme_anahtar = None
        self._kapak_img = None

        self._insa_et()

    def _insa_et(self):
        p0 = tema.p
        ayarlar = self.uygulama.ayarlar
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # ---- 1. Üst başlık çubuğu ----
        ust = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        ust.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 14))
        ust.grid_columnconfigure(0, weight=1)
        tema.bagla(ust, fg_color="bg")

        baslik_kutu = ctk.CTkFrame(ust, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        baslik_kutu.grid(row=0, column=0, sticky="w")
        tema.bagla(baslik_kutu, fg_color="bg")
        b_lbl = ctk.CTkLabel(
            baslik_kutu, text="Medya İndir", font=F(19, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        b_lbl.pack(anchor="w")
        tema.bagla(b_lbl, fg_color="bg", text_color="ink")
        alt_lbl = ctk.CTkLabel(
            baslik_kutu, text="Bağlantıyı yapıştırın, çıktı biçimini seçin ve indirmeyi başlatın.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        alt_lbl.pack(anchor="w", pady=(2, 0))
        tema.bagla(alt_lbl, fg_color="bg", text_color="muted")

        # ---- 2. URL Komut Çubuğu ----
        komut_cerceve = ctk.CTkFrame(
            self, corner_radius=8, border_width=1,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"]
        )
        komut_cerceve.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 10))
        komut_cerceve.grid_columnconfigure(0, weight=1)
        self._komut_cerceve = komut_cerceve
        tema.bagla(komut_cerceve, fg_color="yuzey", border_color="kenar")

        url_satir = ctk.CTkFrame(
            komut_cerceve, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"]
        )
        url_satir.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 10))
        url_satir.grid_columnconfigure(0, weight=1)
        tema.bagla(url_satir, fg_color="yuzey")

        self.url = ctk.CTkTextbox(
            url_satir, height=54, corner_radius=6, border_width=0,
            font=F(13), wrap="none", activate_scrollbars=False,
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"]
        )
        self.url.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        tema.bagla(self.url, fg_color="yuzey", text_color="ink")

        self.yer_tutucu_lbl = ctk.CTkLabel(
            self.url,
            text="https://youtube.com/watch?v=...  (Çoklu indirme için her satıra bir bağlantı)",
            font=F(12), anchor="w",
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["soluk"]
        )
        self.yer_tutucu_lbl.place(x=8, y=7)
        tema.bagla(self.yer_tutucu_lbl, fg_color="yuzey", text_color="soluk")
        self.yer_tutucu_lbl.bind("<Button-1>", lambda _e: self._url_odakla())

        self.url.bind("<FocusIn>", self._url_odak_gir, add="+")
        self.url.bind("<FocusOut>", self._url_odak_cik, add="+")
        self.url.bind("<KeyRelease>", self._url_degisti, add="+")
        self.url.bind("<Control-Return>", lambda _e: self.baslat(), add="+")

        aksiyonlar = ctk.CTkFrame(
            url_satir, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"]
        )
        aksiyonlar.grid(row=0, column=1, sticky="ne", pady=(2, 0))
        tema.bagla(aksiyonlar, fg_color="yuzey")

        self.yapistir_btn = Buton(
            aksiyonlar, metin="Yapıştır", ikon="yapistir",
            komut=self.yapistir, tur="ikincil", yukseklik=36
        )
        self.yapistir_btn.pack(side="left", padx=(0, 6))

        self.temizle_btn = IkonButon(
            aksiyonlar, "kapat", komut=self.temizle_linkler,
            ipucu="Bağlantı alanını temizle", boy=36, tur="ikincil"
        )
        self.temizle_btn.pack(side="left", padx=(0, 8))

        self.indir_btn = Buton(
            aksiyonlar, metin="İndir", ikon="indir",
            komut=self.baslat, tur="birincil", yukseklik=36, genislik=112, font_boy=13
        )
        self.indir_btn.pack(side="left")

        # ---- Canlı Medya Önizleme Şeridi (URL girilince görünür) ----
        self.onizleme = ctk.CTkFrame(
            komut_cerceve, corner_radius=6, border_width=1,
            fg_color=p0["bg"], border_color=p0["kenar"], bg_color=p0["yuzey"]
        )
        self.onizleme.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.onizleme.grid_columnconfigure(1, weight=1)
        tema.bagla(self.onizleme, fg_color="bg", border_color="kenar")

        self.bos_kapak = ctk.CTkImage(Image.new("RGB", (96, 54), "#22222C"), size=(96, 54))
        self.onizleme_resim = ctk.CTkLabel(
            self.onizleme, text="", image=self.bos_kapak, width=96, height=54,
            fg_color=p0["bg"], bg_color=p0["bg"]
        )
        self.onizleme_resim.grid(row=0, column=0, rowspan=2, padx=8, pady=8)
        tema.bagla(self.onizleme_resim, fg_color="bg")

        self.onizleme_baslik = ctk.CTkLabel(
            self.onizleme, text="", anchor="w", justify="left", font=F(12, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        self.onizleme_baslik.grid(row=0, column=1, sticky="sw", padx=(2, 12), pady=(8, 0))
        tema.bagla(self.onizleme_baslik, fg_color="bg", text_color="ink")

        self.onizleme_alt = ctk.CTkLabel(
            self.onizleme, text="", anchor="w", justify="left", font=F(11),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        self.onizleme_alt.grid(row=1, column=1, sticky="nw", padx=(2, 12), pady=(2, 8))
        tema.bagla(self.onizleme_alt, fg_color="bg", text_color="muted")
        self.onizleme.grid_remove()

        # ---- 3. Kompakt Parametre Bölümü ----
        param = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        param.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 10))
        param.grid_columnconfigure(2, weight=1)
        tema.bagla(param, fg_color="bg")

        # Üst parametre satırı: Biçim + Kalite/Bitrate + Oynatma Listesi
        f_kutu = ctk.CTkFrame(param, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        f_kutu.grid(row=0, column=0, sticky="w", padx=(0, 18))
        tema.bagla(f_kutu, fg_color="bg")
        f_lbl = ctk.CTkLabel(
            f_kutu, text="Çıktı Biçimi", font=F(11, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        f_lbl.pack(anchor="w", pady=(0, 4))
        tema.bagla(f_lbl, fg_color="bg", text_color="muted")
        fmt = ayarlar.get("format", "MP4")
        if fmt not in KALITELER:
            fmt = "MP4"
        self.format_sb = Segment(
            f_kutu, [ETIKET[k] for k in KALITELER],
            komut=self.format_degisti, aktif=ETIKET[fmt], yukseklik=30
        )
        self.format_sb.pack(anchor="w")

        k_kutu = ctk.CTkFrame(param, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        k_kutu.grid(row=0, column=1, sticky="w", padx=(0, 18))
        tema.bagla(k_kutu, fg_color="bg")
        k_lbl = ctk.CTkLabel(
            k_kutu, text="Kalite / Bit Hızı", font=F(11, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        k_lbl.pack(anchor="w", pady=(0, 4))
        tema.bagla(k_lbl, fg_color="bg", text_color="muted")
        degerler = list(KALITELER[fmt])
        kal = ayarlar.get("kalite")
        self.kalite_sb = Segment(
            k_kutu, degerler, komut=lambda _s: self.ayar_kaydet(),
            aktif=kal if kal in degerler else degerler[0], yukseklik=30
        )
        self.kalite_sb.pack(anchor="w")

        l_kutu = ctk.CTkFrame(param, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        l_kutu.grid(row=0, column=2, sticky="e")
        tema.bagla(l_kutu, fg_color="bg")
        l_lbl = ctk.CTkLabel(
            l_kutu, text="Oynatma Listesi", font=F(11, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        l_lbl.pack(anchor="e", pady=(0, 4))
        tema.bagla(l_lbl, fg_color="bg", text_color="muted")
        l_ic = ctk.CTkFrame(
            l_kutu, corner_radius=0, height=30, fg_color=p0["bg"], bg_color=p0["bg"]
        )
        l_ic.pack(anchor="e", pady=(4, 0))
        tema.bagla(l_ic, fg_color="bg")
        self.liste_sw = Anahtar(l_ic, deger=bool(ayarlar.get("liste")), komut=self.liste_degisti)
        self.liste_sw.pack(side="left", padx=(0, 8))
        l_yazi = ctk.CTkLabel(
            l_ic, text="Tüm listeyi indir", font=F(12),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        l_yazi.pack(side="left")
        tema.bagla(l_yazi, fg_color="bg", text_color="ink")

        # Alt parametre satırı: Kayıt Klasörü (tam genişlik)
        kl_satir = ctk.CTkFrame(param, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        kl_satir.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        kl_satir.grid_columnconfigure(1, weight=1)
        tema.bagla(kl_satir, fg_color="bg")

        kl_lbl = ctk.CTkLabel(
            kl_satir, text="Kayıt Klasörü:", font=F(11, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        kl_lbl.grid(row=0, column=0, sticky="w", padx=(0, 10))
        tema.bagla(kl_lbl, fg_color="bg", text_color="muted")

        self.klasor_kutu = ctk.CTkFrame(
            kl_satir, corner_radius=6, border_width=1, height=30,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"], cursor="hand2"
        )
        self.klasor_kutu.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.klasor_kutu.grid_propagate(False)
        tema.bagla(self.klasor_kutu, fg_color="yuzey", border_color="kenar")
        self.klasor_lbl = ctk.CTkLabel(
            self.klasor_kutu, text=self.uygulama.kisalt_yol(self.uygulama.klasor, 68),
            font=F(11), anchor="w",
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"], cursor="hand2"
        )
        self.klasor_lbl.pack(fill="both", expand=True, padx=10)
        tema.bagla(self.klasor_lbl, fg_color="yuzey", text_color="ink")
        self.klasor_ipucu = Ipucu(self.klasor_lbl, self.uygulama.klasor)
        for w in (self.klasor_kutu, self.klasor_lbl):
            w.bind("<ButtonRelease-1>", lambda _e: self.klasor_sec(), add="+")

        self.klasor_degistir_btn = Buton(
            kl_satir, metin="Klasör Değiştir", ikon="klasor", komut=self.klasor_sec,
            tur="ikincil", yukseklik=30, font_boy=11
        )
        self.klasor_degistir_btn.grid(row=0, column=2, padx=(0, 6))
        IkonButon(
            kl_satir, "klasor_ac",
            komut=lambda: self.uygulama.klasor_ac(self.uygulama.klasor),
            ipucu="Kayıt klasörünü aç", boy=30, tur="ikincil"
        ).grid(row=0, column=3)

        # Alt satır: platform kısayolları
        self.kisayol_seridi = KisayolSeridi(param)
        self.kisayol_seridi.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))

        Ayirici(self).grid(row=3, column=0, sticky="ew", padx=28)

        # ---- 4. Kuyruk başlığı ----
        kbas = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        kbas.grid(row=4, column=0, sticky="ew", padx=28, pady=(12, 6))
        kbas.grid_columnconfigure(1, weight=1)
        tema.bagla(kbas, fg_color="bg")

        kb_lbl = ctk.CTkLabel(
            kbas, text="İndirme Kuyruğu", font=F(13, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        kb_lbl.grid(row=0, column=0, sticky="w")
        tema.bagla(kb_lbl, fg_color="bg", text_color="ink")

        self.sayac_rozet = Rozet(kbas, "0 öge", "notr")
        self.sayac_rozet.grid(row=0, column=1, sticky="w", padx=(8, 0))

        k_aksiyon = ctk.CTkFrame(kbas, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        k_aksiyon.grid(row=0, column=2, sticky="e")
        tema.bagla(k_aksiyon, fg_color="bg")

        self.bitenleri_temizle_btn = Buton(
            k_aksiyon, metin="Tamamlananları Temizle",
            komut=self.bitenleri_temizle, tur="hayalet", yukseklik=26, font_boy=11
        )
        self.bitenleri_temizle_btn.pack(side="left", padx=(0, 6))

        self.tumunu_iptal_btn = Buton(
            k_aksiyon, metin="Tümünü İptal Et",
            komut=self.tumunu_iptal_et, tur="tehlike", yukseklik=26, font_boy=11
        )
        self.tumunu_iptal_btn.pack(side="left")
        self.tumunu_iptal_btn.pack_forget()

        # ---- 5. Kuyruk listesi ----
        self.liste_alan = kaydirilabilir_alan(self)
        self.liste_alan.grid(row=5, column=0, sticky="nsew", padx=22, pady=(0, 14))
        self.liste_alan.grid_columnconfigure(0, weight=1)

        self.bos_kutu = ctk.CTkFrame(self.liste_alan, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self.bos_kutu, fg_color="bg")
        self.bos_kutu.pack(fill="x", pady=48)
        bos_ikon = ctk.CTkLabel(
            self.bos_kutu, text=GLIF["indir"], font=ikon_fontu(24),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["soluk"]
        )
        bos_ikon.pack(pady=(0, 8))
        tema.bagla(bos_ikon, fg_color="bg", text_color="soluk")
        bos_b = ctk.CTkLabel(
            self.bos_kutu, text="İndirme kuyruğu boş", font=F(13, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        bos_b.pack()
        tema.bagla(bos_b, fg_color="bg", text_color="muted")
        bos_a = ctk.CTkLabel(
            self.bos_kutu,
            text="Yukarıdaki alana bir bağlantı yapıştırıp İndir düğmesine basın veya Ctrl+Enter kullanın.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["soluk"]
        )
        bos_a.pack(pady=(3, 0))
        tema.bagla(bos_a, fg_color="bg", text_color="soluk")

    # ------------------------------------------------------------------ URL ve parametreler
    def _url_odakla(self):
        self.url.focus_set()

    def _url_odak_gir(self, _e=None):
        self.yer_tutucu_lbl.place_forget()
        hizli_boya(self._komut_cerceve, border_color=tema.p["accent"])

    def _url_odak_cik(self, _e=None):
        hizli_boya(self._komut_cerceve, border_color=tema.p["kenar"])
        self._yer_tutucu_kontrol()
        self.onizleme_iste()

    def _url_degisti(self, _e=None):
        self._yer_tutucu_kontrol()
        self.onizleme_iste()

    def _yer_tutucu_kontrol(self):
        if self.linkler():
            self.yer_tutucu_lbl.place_forget()
        elif self.focus_get() != getattr(self.url, "_textbox", None):
            self.yer_tutucu_lbl.place(x=8, y=7)

    def linkler(self):
        satirlar = (s.strip() for s in self.url.get("1.0", "end").splitlines())
        return [s for s in satirlar if s]

    def aktif_format(self):
        return ETIKET_TERS.get(self.format_sb.get(), "MP4")

    def format_degisti(self, secim):
        fmt = ETIKET_TERS.get(secim, "MP4")
        degerler = list(KALITELER[fmt])
        self.kalite_sb.secenekleri_guncelle(degerler, degerler[0])
        self.ayar_kaydet()

    def liste_degisti(self, _deger=None):
        self.ayar_kaydet()
        self._onizleme_anahtar = None
        self.onizleme_iste()

    def klasor_sec(self):
        yol = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=self.uygulama.klasor,
            title="İndirme Kayıt Klasörünü Seçin",
        )
        if yol:
            self.uygulama.klasor_guncelle(yol)

    def klasor_etiketi_guncelle(self, yol):
        self.klasor_lbl.configure(text=self.uygulama.kisalt_yol(yol, 68))
        self.klasor_ipucu.guncelle(yol)

    def ayar_kaydet(self):
        self.uygulama.ayar_guncelle(
            format=self.aktif_format(),
            kalite=self.kalite_sb.get(),
            liste=bool(self.liste_sw.get()),
        )

    def yapistir(self):
        try:
            metin = self.winfo_toplevel().clipboard_get().strip()
        except Exception:
            self.uygulama.bildirim("Panoda yapıştırılacak bir bağlantı bulunamadı.", "hata")
            return
        if not metin:
            return
        mevcut = self.url.get("1.0", "end").strip()
        if mevcut:
            son_kar = self.url.get("end-2c", "end-1c")
            self.url.insert("end", ("" if son_kar == "\n" else "\n") + metin)
        else:
            self.url.insert("1.0", metin)
        self._yer_tutucu_kontrol()
        self.onizleme_iste()

    def pano_otomatik_kontrol(self):
        if self.linkler():
            return
        try:
            metin = self.winfo_toplevel().clipboard_get().strip()
        except Exception:
            return
        if metin.lower().startswith(("http://", "https://")):
            self.url.insert("1.0", metin)
            self._yer_tutucu_kontrol()
            self.onizleme_iste()

    def temizle_linkler(self):
        self.url.delete("1.0", "end")
        self._yer_tutucu_kontrol()
        self.onizleme.grid_remove()
        self._onizleme_anahtar = None

    # ------------------------------------------------------------------ önizleme
    def onizleme_iste(self):
        if self._onizleme_job:
            try:
                self.after_cancel(self._onizleme_job)
            except Exception:
                pass
        self._onizleme_job = self.after(600, self._onizleme_baslat)

    def _onizleme_baslat(self):
        self._onizleme_job = None
        linkler = self.linkler()
        if not linkler or not linkler[0].lower().startswith(("http://", "https://")):
            self.onizleme.grid_remove()
            self._onizleme_anahtar = None
            return
        liste_mi = bool(self.liste_sw.get())
        anahtar = (linkler[0], liste_mi, len(linkler))
        if anahtar == self._onizleme_anahtar:
            return
        self._onizleme_anahtar = anahtar
        self.onizleme_resim.configure(image=self.bos_kapak)
        self.onizleme_baslik.configure(text="Medya bilgisi alınıyor…")
        self.onizleme_alt.configure(text=linkler[0])
        self.onizleme.grid()
        threading.Thread(
            target=self._onizleme_getir,
            args=(linkler[0], liste_mi, anahtar, len(linkler)),
            daemon=True,
        ).start()

    def _onizleme_getir(self, link, liste_mi, anahtar, adet):
        try:
            bilgi = bilgi_getir(link, liste_mi)
            if adet > 1:
                ek = f"Toplam {adet} bağlantı"
                bilgi["alt"] = f"{bilgi['alt']} · {ek}" if bilgi.get("alt") else ek
            self.uygulama.ui_cagir(self._onizleme_goster, anahtar, bilgi)
        except Exception:
            self.uygulama.ui_cagir(self._onizleme_goster, anahtar, {
                "baslik": "Önizleme bilgisi alınamadı",
                "alt": "Bağlantıyı doğrudan indirmeyi deneyebilirsiniz.",
                "kapak": None,
            })

    def _onizleme_goster(self, anahtar, bilgi):
        if anahtar != self._onizleme_anahtar or not self.winfo_exists():
            return
        self.onizleme_baslik.configure(text=kirp(bilgi.get("baslik") or "", 520, 12, True))
        self.onizleme_alt.configure(text=bilgi.get("alt") or "")
        resim = None
        if bilgi.get("kapak"):
            try:
                resim = Image.open(io.BytesIO(bilgi["kapak"])).convert("RGB")
            except Exception:
                resim = None
        if resim is not None:
            self._kapak_img = ctk.CTkImage(light_image=resim, dark_image=resim, size=(96, 54))
            self.onizleme_resim.configure(image=self._kapak_img)
        else:
            self.onizleme_resim.configure(image=self.bos_kapak)

    # ------------------------------------------------------------------ kuyruk yönetimi
    def _kuyruk_durum_guncelle(self):
        toplam = len(self.satirlar)
        aktif = sum(
            1 for s in self.satirlar
            if s.durum_kodu in ("sirada", "indiriliyor", "isleniyor", "duraklat_bekliyor")
        )
        if aktif > 0:
            self.sayac_rozet.ayarla(f"{aktif} aktif / {toplam} öge", "aktif")
            self.tumunu_iptal_btn.pack(side="left")
        else:
            self.sayac_rozet.ayarla(f"{toplam} öge", "notr")
            self.tumunu_iptal_btn.pack_forget()
        if self.satirlar:
            self.bos_kutu.pack_forget()
        else:
            self.bos_kutu.pack(fill="x", pady=48)
        self.uygulama.alt_durum_guncelle()

    def aktif_is_sayisi(self):
        return sum(1 for is_ in self.isler.values() if is_["motor"] and is_["motor"].calisiyor)

    def _satir_ekle(self, is_id, sira, link, fmt, kalite, klasor, liste_mi, baslik):
        satir = IndirmeSatiri(
            self.liste_alan, self, is_id, sira, link, fmt, kalite, klasor, liste_mi
        )
        satir.baslik_ata(baslik)
        onceki = self.satirlar[0] if self.satirlar else None
        if onceki is not None and onceki.winfo_exists():
            satir.pack(fill="x", padx=6, pady=(0, 6), before=onceki)
        else:
            satir.pack(fill="x", padx=6, pady=(0, 6))
        self.satirlar.insert(0, satir)
        self._kuyruk_durum_guncelle()
        return satir

    def satir_kaldir(self, satir):
        if satir in self.satirlar:
            self.satirlar.remove(satir)
        try:
            satir.destroy()
        except Exception:
            pass
        self._kuyruk_durum_guncelle()

    def satir_duraklat(self, satir):
        is_ = self.isler.get(satir.is_id)
        motor = is_["motor"] if is_ else None
        if motor and motor.calisiyor:
            satir.durum_ata("duraklat_bekliyor")
            motor.oge_duraklat(satir.sira)
        else:
            satir.bitti_guncelle({"duraklatildi": True})
        self._kuyruk_durum_guncelle()

    def satir_iptal(self, satir):
        is_ = self.isler.get(satir.is_id)
        motor = is_["motor"] if is_ else None
        if motor and motor.calisiyor:
            satir.durum_ata("iptal_bekliyor")
            motor.oge_iptal_et(satir.sira)
        else:
            satir.bitti_guncelle({"iptal": True})
        self._kuyruk_durum_guncelle()

    def satir_devam_et(self, satir):
        """Duraklatılmış veya hata vermiş bir satırı kaldığı yerden yeniden başlatır."""
        self._is_sayac += 1
        yeni_is_id = self._is_sayac
        satir.is_id = yeni_is_id
        satir.sira = 1
        satir.cubuk.grid(row=2, column=0, columnspan=3, sticky="ew", padx=1, pady=(0, 1))
        satir.durum_ata("indiriliyor")

        is_ = {
            "motor": None,
            "satirlar": {1: satir},
            "fmt": satir.fmt,
            "kalite": satir.kalite,
            "klasor": satir.klasor,
            "liste": satir.liste_mi,
        }
        self.isler[yeni_is_id] = is_
        motor = IndirmeMotoru(
            on_olay=lambda olay, iid=yeni_is_id: self.uygulama.ui_cagir(self.olay_isle, iid, olay)
        )
        is_["motor"] = motor
        self._kuyruk_durum_guncelle()
        threading.Thread(
            target=motor.indir,
            args=([satir.link], satir.fmt, satir.kalite, satir.klasor, satir.liste_mi),
            daemon=True,
        ).start()

    def bitenleri_temizle(self):
        for s in list(self.satirlar):
            if s.durum_kodu in SON_DURUMLAR:
                self.satir_kaldir(s)

    def tumunu_iptal_et(self):
        for is_ in self.isler.values():
            if is_["motor"] and is_["motor"].calisiyor:
                is_["motor"].iptal_et()

    # ------------------------------------------------------------------ indirme başlatma
    def baslat(self):
        linkler = self.linkler()
        if not linkler:
            self.uygulama.bildirim("Önce bir medya bağlantısı yapıştırın.", "hata")
            self.url.focus_set()
            return
        gecersiz = [
            str(i) for i, l in enumerate(linkler, 1)
            if not l.lower().startswith(("http://", "https://"))
        ]
        if gecersiz:
            self.uygulama.bildirim(
                f"Geçersiz bağlantı (satır {', '.join(gecersiz)}): bağlantılar http:// veya https:// ile başlamalıdır.",
                "hata",
            )
            return

        fmt = self.aktif_format()
        kalite = self.kalite_sb.get()
        klasor = self.uygulama.klasor
        liste_mi = bool(self.liste_sw.get())
        self.ayar_kaydet()

        self._is_sayac += 1
        is_id = self._is_sayac
        is_ = {
            "motor": None,
            "satirlar": {},
            "fmt": fmt,
            "kalite": kalite,
            "klasor": klasor,
            "liste": liste_mi,
        }
        self.isler[is_id] = is_

        for sira, link in enumerate(linkler, 1):
            baslik = link
            is_["satirlar"][sira] = self._satir_ekle(
                is_id, sira, link, fmt, kalite, klasor, liste_mi, baslik
            )
        log.info("İndirme başladı: %d link, %s %s -> %s", len(linkler), fmt, kalite, klasor)

        motor = IndirmeMotoru(
            on_olay=lambda olay, iid=is_id: self.uygulama.ui_cagir(self.olay_isle, iid, olay)
        )
        is_["motor"] = motor
        self._kuyruk_durum_guncelle()
        threading.Thread(
            target=motor.indir,
            args=(linkler, fmt, kalite, klasor, liste_mi),
            daemon=True,
        ).start()

    def olay_isle(self, is_id, olay):
        if not self.winfo_exists():
            return
        is_ = self.isler.get(is_id)
        if not is_:
            return
        tip = olay.get("tip")
        satir = is_["satirlar"].get(olay.get("sira"))

        if tip == "basladi" and satir:
            satir.durum_ata("indiriliyor")
        elif tip == "ilerleme" and satir:
            satir.ilerleme_guncelle(olay)
        elif tip == "oge_bitti" and satir:
            satir.bitti_guncelle(olay)
            if not olay.get("iptal") and not olay.get("duraklatildi"):
                dosyalar = olay.get("dosyalar") or []
                ilk_dosya = dosyalar[0] if dosyalar else ""
                try:
                    history.ekle(
                        baslik=olay.get("baslik") or satir.link,
                        dosya=ilk_dosya,
                        klasor=str(Path(ilk_dosya).parent) if ilk_dosya else is_["klasor"],
                        fmt=is_["fmt"],
                        kalite=is_["kalite"],
                        tur="indirme",
                        durum="tamam" if olay.get("basarili") else "hata",
                        hata=olay.get("hata"),
                    )
                    self.uygulama.gecmis_yenile()
                except Exception:
                    log.exception("Geçmişe kayıt eklenemedi")
        elif tip == "bitti":
            for s in is_["satirlar"].values():
                if s.durum_kodu not in SON_DURUMLAR and s.durum_kodu != "duraklatildi":
                    s.bitti_guncelle({"iptal": olay.get("iptal", True)})
            if olay.get("iptal"):
                self.uygulama.bildirim("İndirme kuyruğu iptal edildi.", "bilgi")
            elif olay["basarili"] > 0 and olay["basarili"] == olay["toplam"]:
                mesaj = (
                    "İndirme tamamlandı."
                    if olay["toplam"] == 1
                    else f"{olay['toplam']} bağlantının tamamı indirildi."
                )
                self.uygulama.bildirim(mesaj, "tamam")
                if self.uygulama.ayarlar.get("bitince_klasor_ac"):
                    self.uygulama.klasor_ac(is_["klasor"])
            elif olay.get("hatalar"):
                self.uygulama.bildirim(f"İndirme hatası: {olay['hatalar'][-1]}", "hata")
        self._kuyruk_durum_guncelle()
