"""Kroxload masaüstü arayüzü (KXR YAZILIM).

Sol navigasyon paneli sıralaması:
  1. Ana Sayfa
  2. Geçmiş
  3. Ayarlar
  4. Dönüştürücü

Tasarım ilkeleri:
- Spotify Desktop, Linear ve Raycast'in tipografi ve hiyerarşi disiplininden ilham alır.
- Gradyan, neon parlama, cam efekti veya jenerik istatistik kartları kullanılmaz.
- Logo rengiyle (#4E5AE6) uyumlu mor vurgu yalnızca birincil eylemlerde ve aktif
  göstergelerde kullanılır.
"""
import ctypes
import os
import queue
import subprocess
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from kroxload import APP_ADI, SURUM, YAPIMCI
from kroxload.core.logs import kayit as log
from kroxload.core.paths import LOG_KLASORU, ffmpeg_klasoru, kaynak_yolu
from kroxload.core.settings import ayar_oku, ayar_yaz

from .page_converter import DonusturucuSayfasi
from .page_history import GecmisSayfasi
from .page_home import AnaSayfa
from .page_settings import AyarlarSayfasi
from .theme import F, GLIF, ease_out, hizli_boya, ikon_fontu, karistir, tema
from .widgets import Ayirici, BildirimYoneticisi, IkonButon, _fare_icinde_mi

MENU_SIRASI = (
    ("ana", "Ana Sayfa", "ev"),
    ("gecmis", "Geçmiş", "gecmis"),
    ("ayarlar", "Ayarlar", "ayar"),
    ("donusturucu", "Dönüştürücü", "donustur"),
)


class NavOgesi(ctk.CTkFrame):
    """Sol navigasyon menüsündeki tek bir sayfa öğesi."""

    def __init__(self, parent, anahtar, baslik, ikon, komut):
        p0 = tema.p
        super().__init__(
            parent, height=38, corner_radius=6,
            fg_color=p0["yan"], bg_color=p0["yan"], cursor="hand2"
        )
        self.pack_propagate(False)
        self.anahtar = anahtar
        self.komut = komut
        self.aktif = False
        self._hover_t = 0.0
        self._anim_id = f"nav_{anahtar}"

        self.ikon_lbl = ctk.CTkLabel(
            self, text=GLIF[ikon], font=ikon_fontu(15), width=22,
            fg_color=p0["yan"], bg_color=p0["yan"], text_color=p0["muted"], cursor="hand2"
        )
        self.ikon_lbl.pack(side="left", padx=(14, 10))

        self.metin_lbl = ctk.CTkLabel(
            self, text=baslik, font=F(13, True), anchor="w",
            fg_color=p0["yan"], bg_color=p0["yan"], text_color=p0["muted"], cursor="hand2"
        )
        self.metin_lbl.pack(side="left", fill="x", expand=True)

        for w in (self, self.ikon_lbl, self.metin_lbl):
            w.bind("<Enter>", self._gir, add="+")
            w.bind("<Leave>", self._cik, add="+")
            w.bind("<ButtonRelease-1>", self._tikla, add="+")

        tema.bagla_fn(self, self._boya)

    def _tikla(self, _e=None):
        if _fare_icinde_mi(self):
            self.komut(self.anahtar)

    def aktif_ayarla(self, aktif):
        self.aktif = bool(aktif)
        self._boya()

    def _gir(self, _e=None):
        if self._hover_t >= 0.99:
            return
        bas = self._hover_t
        tema.anim(self._anim_id, 110, lambda k: self._adim(bas + (1.0 - bas) * k))

    def _cik(self, _e=None):
        if _fare_icinde_mi(self):
            return
        bas = self._hover_t
        tema.anim(self._anim_id, 130, lambda k: self._adim(bas * (1.0 - k)))

    def _adim(self, deger):
        self._hover_t = max(0.0, min(1.0, deger))
        self._boya()

    def _boya(self, p=None):
        if not self.winfo_exists():
            return
        p = p or tema.p
        yan = p["yan"]
        if self.aktif:
            zemin = karistir(yan, p["accent_bg"], 0.85)
            ikon_renk = p["accent_ink"]
            yazi_renk = p["ink"]
        elif self._hover_t > 0.02:
            zemin = karistir(yan, p["yuzey2"], self._hover_t * 0.75)
            ikon_renk = karistir(p["muted"], p["ink"], self._hover_t)
            yazi_renk = karistir(p["muted"], p["ink"], self._hover_t)
        else:
            zemin = yan
            ikon_renk = p["muted"]
            yazi_renk = p["muted"]
        hizli_boya(self, fg_color=zemin, bg_color=yan)
        hizli_boya(self.ikon_lbl, fg_color=zemin, bg_color=zemin, text_color=ikon_renk)
        hizli_boya(self.metin_lbl, fg_color=zemin, bg_color=zemin, text_color=yazi_renk)


class App(ctk.CTk):
    """Kroxload ana uygulama penceresi."""

    def __init__(self):
        super().__init__()
        self._dnd_hazirla()
        self._ui_kuyruk = queue.SimpleQueue()

        self.ayarlar = ayar_oku()
        baslangic_tema = self.ayarlar.get("tema", "koyu")
        if baslangic_tema not in ("koyu", "acik"):
            baslangic_tema = "koyu"

        ctk.set_appearance_mode("dark")
        tema.baslat(
            self,
            ad=baslangic_tema,
            animasyon=bool(self.ayarlar.get("animasyonlar", True)),
        )

        self.title(f"{APP_ADI}")
        self.geometry("1060x720")
        self.minsize(920, 620)
        self.protocol("WM_DELETE_WINDOW", self.kapat)
        tema.bagla(self, fg_color="bg")
        self._baslik_cubugu_temasi(baslangic_tema == "koyu")

        try:
            self.iconbitmap(str(kaynak_yolu("assets/kroxload.ico")))
        except Exception:
            pass

        klasor = self.ayarlar.get("klasor")
        self.klasor = (
            klasor if klasor and Path(klasor).is_dir() else str(Path.home() / "Downloads")
        )
        self.ffmpeg_sorunu = not ffmpeg_klasoru()

        self.nav_ogeleri = {}
        self.sayfalar = {}
        self.aktif_sayfa = None
        self._vurgucu_y = 0.0

        self._arayuz_kur()
        self.bildirim_yoneticisi = BildirimYoneticisi(self)

        # Klavye kısayolları ve odak kontrolü
        self.bind("<FocusIn>", self._pencere_odaklandi, add="+")
        self.bind("<Control-Key-1>", lambda _e: self.sayfa_sec("ana"), add="+")
        self.bind("<Control-Key-2>", lambda _e: self.sayfa_sec("gecmis"), add="+")
        self.bind("<Control-Key-3>", lambda _e: self.sayfa_sec("ayarlar"), add="+")
        self.bind("<Control-Key-4>", lambda _e: self.sayfa_sec("donusturucu"), add="+")

        self.sayfa_sec("ana", animasyonlu=False)
        self._ui_kuyruk_pompala()

        if self.ffmpeg_sorunu:
            self.after(
                300,
                lambda: self.bildirim(
                    "FFmpeg bulunamadı — ses/video dönüştürme için kurulumu doğrulayın.",
                    "hata",
                ),
            )
            log.error("FFmpeg bulunamadı")

    def _dnd_hazirla(self):
        """tkinterdnd2 kütüphanesini mevcut CTk kök penceresine yükler."""
        try:
            from tkinterdnd2 import TkinterDnD

            TkinterDnD._require(self)
        except Exception:
            pass

    def _baslik_cubugu_temasi(self, koyu_mu):
        """Windows 10/11 pencere başlık çubuğunu koyu/açık temayla uyumlu yapar."""
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            deger = ctypes.c_int(1 if koyu_mu else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(deger), ctypes.sizeof(deger)
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ ana yerleşim
    def _arayuz_kur(self):
        p0 = tema.p
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Sol Navigasyon Paneli ----
        self.yan_panel = ctk.CTkFrame(
            self, width=216, corner_radius=0, fg_color=p0["yan"], bg_color=p0["yan"]
        )
        self.yan_panel.grid(row=0, column=0, sticky="nsew")
        self.yan_panel.grid_propagate(False)
        self.yan_panel.grid_columnconfigure(0, weight=1)
        self.yan_panel.grid_rowconfigure(2, weight=1)
        tema.bagla(self.yan_panel, fg_color="yan")

        # Marka üst bilgisi
        marka = ctk.CTkFrame(self.yan_panel, corner_radius=0, fg_color=p0["yan"], bg_color=p0["yan"])
        marka.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 16))
        tema.bagla(marka, fg_color="yan")
        try:
            img = Image.open(kaynak_yolu("assets/kroxload.png"))
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(30, 30))
            logo_lbl = ctk.CTkLabel(
                marka, text="", image=self.logo_img, fg_color=p0["yan"], bg_color=p0["yan"]
            )
            logo_lbl.pack(side="left", padx=(0, 10))
            tema.bagla(logo_lbl, fg_color="yan")
        except Exception:
            pass

        m_yazi = ctk.CTkFrame(marka, corner_radius=0, fg_color=p0["yan"], bg_color=p0["yan"])
        m_yazi.pack(side="left")
        tema.bagla(m_yazi, fg_color="yan")
        m_ad = ctk.CTkLabel(
            m_yazi, text=APP_ADI, font=F(17, True), anchor="w",
            fg_color=p0["yan"], bg_color=p0["yan"], text_color=p0["ink"]
        )
        m_ad.pack(anchor="w")
        tema.bagla(m_ad, fg_color="yan", text_color="ink")
        m_alt = ctk.CTkLabel(
            m_yazi, text=YAPIMCI, font=F(10, True), anchor="w",
            fg_color=p0["yan"], bg_color=p0["yan"], text_color=p0["muted"]
        )
        m_alt.pack(anchor="w")
        tema.bagla(m_alt, fg_color="yan", text_color="muted")

        # Menü listesi (1. Ana Sayfa, 2. Geçmiş, 3. Ayarlar, 4. Dönüştürücü)
        self.menu_kapsayici = ctk.CTkFrame(
            self.yan_panel, corner_radius=0, fg_color=p0["yan"], bg_color=p0["yan"]
        )
        self.menu_kapsayici.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 0))
        tema.bagla(self.menu_kapsayici, fg_color="yan")

        for anahtar, baslik, ikon in MENU_SIRASI:
            oge = NavOgesi(self.menu_kapsayici, anahtar, baslik, ikon, self.sayfa_sec)
            oge.pack(fill="x", pady=2)
            self.nav_ogeleri[anahtar] = oge

        # Aktif sayfa sol mor vurgu çubuğu (menü kapsayıcısı üzerinde kayar)
        self.nav_vurgu = ctk.CTkFrame(
            self.menu_kapsayici, width=3, height=20, corner_radius=2,
            fg_color=p0["accent"], bg_color=p0["yan"]
        )
        tema.bagla(self.nav_vurgu, fg_color="accent")

        # Yan panel alt bilgi + hızlı tema anahtarı
        yan_alt = ctk.CTkFrame(self.yan_panel, corner_radius=0, fg_color=p0["yan"], bg_color=p0["yan"])
        yan_alt.grid(row=3, column=0, sticky="ew", padx=14, pady=(8, 14))
        yan_alt.grid_columnconfigure(0, weight=1)
        tema.bagla(yan_alt, fg_color="yan")

        Ayirici(yan_alt).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.alt_durum_lbl = ctk.CTkLabel(
            yan_alt, text="Hazır", font=F(11), anchor="w",
            fg_color=p0["yan"], bg_color=p0["yan"], text_color=p0["muted"]
        )
        self.alt_durum_lbl.grid(row=1, column=0, sticky="w")
        tema.bagla(self.alt_durum_lbl, fg_color="yan", text_color="muted")

        tema_ikon = "gunes" if tema.ad == "koyu" else "ay"
        self.hizli_tema_btn = IkonButon(
            yan_alt, tema_ikon, komut=self.tema_degistir_hizli,
            ipucu="Temayı değiştir (Koyu / Açık)", boy=28, tur="ikincil"
        )
        self.hizli_tema_btn.grid(row=1, column=1, rowspan=2, sticky="e")

        surum_lbl = ctk.CTkLabel(
            yan_alt, text=f"v{SURUM} · {YAPIMCI}", font=F(10), anchor="w",
            fg_color=p0["yan"], bg_color=p0["yan"], text_color=p0["soluk"]
        )
        surum_lbl.grid(row=2, column=0, sticky="w", pady=(1, 0))
        tema.bagla(surum_lbl, fg_color="yan", text_color="soluk")

        # Dikey ayırıcı çizgi
        Ayirici(self, dikey=True).grid(row=0, column=1, sticky="ns")

        # ---- Sağ Ana Çalışma Alanı ----
        self.icerik_kapsayici = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        self.icerik_kapsayici.grid(row=0, column=2, sticky="nsew")
        tema.bagla(self.icerik_kapsayici, fg_color="bg")

        self.sayfalar["ana"] = AnaSayfa(self.icerik_kapsayici, self)
        self.sayfalar["gecmis"] = GecmisSayfasi(self.icerik_kapsayici, self)
        self.sayfalar["ayarlar"] = AyarlarSayfasi(self.icerik_kapsayici, self)
        self.sayfalar["donusturucu"] = DonusturucuSayfasi(self.icerik_kapsayici, self)

        self.alt_durum_guncelle()

    # ------------------------------------------------------------------ navigasyon ve animasyon
    def sayfa_sec(self, anahtar, animasyonlu=True):
        if anahtar not in self.sayfalar or anahtar == self.aktif_sayfa:
            return
        eski = self.sayfalar.get(self.aktif_sayfa)
        yeni = self.sayfalar[anahtar]
        self.aktif_sayfa = anahtar

        for k, oge in self.nav_ogeleri.items():
            oge.aktif_ayarla(k == anahtar)

        # Sol vurgu çubuğu animasyonu
        sira_indeks = [k for k, _, _ in MENU_SIRASI].index(anahtar)
        hedef_y = sira_indeks * 42 + 11
        if not animasyonlu or not tema.animasyon:
            self._vurgucu_y = float(hedef_y)
            self.nav_vurgu.place(x=2, y=hedef_y)
            self.nav_vurgu.lift()
        else:
            bas_y = self._vurgucu_y
            fark_y = hedef_y - bas_y

            def vurgu_adim(t):
                self._vurgucu_y = bas_y + fark_y * t
                self.nav_vurgu.place(x=2, y=int(round(self._vurgucu_y)))
                self.nav_vurgu.lift()

            tema.anim("nav_vurgu", 150, vurgu_adim, ease=ease_out)

        if anahtar == "gecmis":
            self.sayfalar["gecmis"].yenile()

        # Sayfa gizliyken tema değişmişse renklerini senkronla
        tema.sayfa_guncelle(anahtar)

        # Önce yeni sayfayı yerleştirip üste çıkar, ardından eskiyi gizle (siyah parlama olmaz)
        yeni.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        yeni.lift()
        if eski is not None:
            eski.place_forget()

    # ------------------------------------------------------------------ tema ve ayarlar
    def tema_degistir_hizli(self):
        hedef = "acik" if tema.ad == "koyu" else "koyu"
        self.tema_ayarla(hedef)

    def tema_ayarla(self, hedef):
        if hedef not in ("koyu", "acik") or hedef == tema.ad:
            return
        self.hizli_tema_btn.ikon_ayarla("gunes" if hedef == "koyu" else "ay")
        if "ayarlar" in self.sayfalar:
            self.sayfalar["ayarlar"].tema_etiketi_senkronla(hedef)

        def _gecis_bitti():
            self.ayar_guncelle(tema=hedef)
            self._baslik_cubugu_temasi(hedef == "koyu")

        tema.gecis(hedef, bitti=_gecis_bitti)

    def ui_cagir(self, fn, *args, **kwargs):
        """Arka plan iş parçacıklarından arayüz işlevini güvenli şekilde kuyruğa ekler."""
        self._ui_kuyruk.put((fn, args, kwargs))

    def _ui_kuyruk_bosalt(self):
        while not self._ui_kuyruk.empty():
            try:
                fn, args, kwargs = self._ui_kuyruk.get_nowait()
                fn(*args, **kwargs)
            except queue.Empty:
                break
            except Exception:
                log.exception("UI kuyruk görevi hatası")

    def _ui_kuyruk_pompala(self):
        if not self.winfo_exists():
            return
        self._ui_kuyruk_bosalt()
        self.after(15, self._ui_kuyruk_pompala)

    def update(self):
        self._ui_kuyruk_bosalt()
        super().update()

    def ayar_guncelle(self, **degisiklikler):
        self.ayarlar.update(degisiklikler)
        ayar_yaz(self.ayarlar)

    def klasor_guncelle(self, yeni_yol):
        self.klasor = str(yeni_yol)
        self.ayar_guncelle(klasor=self.klasor)
        if "ana" in self.sayfalar:
            self.sayfalar["ana"].klasor_etiketi_guncelle(self.klasor)
        if "ayarlar" in self.sayfalar:
            self.sayfalar["ayarlar"].klasor_etiketi_guncelle(self.klasor)

    def gecmis_yenile(self):
        if "gecmis" in self.sayfalar:
            self.sayfalar["gecmis"].yenile()

    def aktif_gorev_var_mi(self):
        ind_aktif = self.sayfalar["ana"].aktif_is_sayisi() if "ana" in self.sayfalar else 0
        don_aktif = self.sayfalar["donusturucu"].aktif_is_sayisi() if "donusturucu" in self.sayfalar else 0
        return (ind_aktif + don_aktif) > 0

    def alt_durum_guncelle(self):
        ind_aktif = self.sayfalar["ana"].aktif_is_sayisi() if "ana" in self.sayfalar else 0
        don_aktif = self.sayfalar["donusturucu"].aktif_is_sayisi() if "donusturucu" in self.sayfalar else 0
        if ind_aktif > 0 and don_aktif > 0:
            self.alt_durum_lbl.configure(text="İndirme ve dönüştürme sürüyor…")
        elif ind_aktif > 0:
            self.alt_durum_lbl.configure(text="İndirme devam ediyor…")
        elif don_aktif > 0:
            self.alt_durum_lbl.configure(text="Dönüştürme devam ediyor…")
        elif self.ffmpeg_sorunu:
            self.alt_durum_lbl.configure(text="FFmpeg eksik")
        else:
            self.alt_durum_lbl.configure(text="Hazır · FFmpeg etkin")

    # ------------------------------------------------------------------ yardımcılar
    @staticmethod
    def kisalt_yol(yol, maks_karakter=36):
        yol = str(yol or "")
        return yol if len(yol) <= maks_karakter else "…" + yol[-(maks_karakter - 1):]

    def bildirim(self, metin, tur="bilgi"):
        if tur != "hata" and not self.ayarlar.get("bildirimler", True):
            return
        self.bildirim_yoneticisi.goster(metin, tur=tur)

    def dosya_ac(self, yol):
        try:
            os.startfile(yol)
        except Exception:
            log.exception("Dosya açılamadı: %s", yol)
            self.bildirim("Dosya açılamadı.", "hata")

    def klasor_ac(self, yol):
        try:
            p = Path(yol)
            if p.is_dir():
                os.startfile(str(p))
            elif p.exists():
                subprocess.Popen(["explorer", "/select,", str(p)])
            elif p.parent.is_dir():
                os.startfile(str(p.parent))
        except Exception:
            log.exception("Klasör açılamadı: %s", yol)
            self.bildirim("Klasör açılamadı.", "hata")

    def gunluk_ac(self):
        try:
            LOG_KLASORU.mkdir(parents=True, exist_ok=True)
            os.startfile(str(LOG_KLASORU))
        except Exception:
            log.exception("Günlük klasörü açılamadı")

    def _pencere_odaklandi(self, _e=None):
        if self.aktif_sayfa == "ana" and self.ayarlar.get("pano_otomatik", True):
            self.sayfalar["ana"].pano_otomatik_kontrol()

    def kapat(self):
        ayar_yaz(self.ayarlar)
        if "ana" in self.sayfalar:
            self.sayfalar["ana"].tumunu_iptal_et()
        if "donusturucu" in self.sayfalar:
            self.sayfalar["donusturucu"].tumunu_iptal_et()
        self.destroy()


def calistir():
    app = App()
    app.mainloop()
