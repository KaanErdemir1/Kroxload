"""Ayarlar Sayfası: Görünüm, İndirme, Dönüştürme, Sistem ve Hakkında.

Linear tarzı yatay ayar satırları kullanılır; gereksiz iç içe kart kalabalığı yoktur.
Tüm tercihler `%APPDATA%\\Kroxload\\ayarlar.json` dosyasına kalıcı olarak kaydedilir.
"""
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from kroxload import APP_ADI, SURUM, YAPIMCI
from kroxload.core import converter as conv
from kroxload.core.paths import LOG_KLASORU, VERI_KLASORU, ffmpeg_klasoru
from kroxload.core.updater import guncelle
from kroxload.core.ytdlp import YTDLP_SURUM

from .theme import F, tema
from .widgets import Anahtar, Ayirici, Buton, Ipucu, Rozet, Segment, kaydirilabilir_alan


class AyarlarSayfasi(ctk.CTkFrame):
    """Uygulama tercihleri, motor güncelleme ve hakkında sayfası."""

    def __init__(self, parent, uygulama):
        p0 = tema.p
        super().__init__(parent, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self, fg_color="bg")
        self.uygulama = uygulama
        self._insa_et()

    def _bolum_basligi(self, parent, baslik, aciklama=None):
        p0 = tema.p
        kutu = ctk.CTkFrame(parent, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(kutu, fg_color="bg")
        kutu.pack(fill="x", padx=6, pady=(20, 6))
        lbl = ctk.CTkLabel(
            kutu, text=baslik, font=F(13, True), anchor="w",
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["accent_ink"]
        )
        lbl.pack(anchor="w")
        tema.bagla(lbl, fg_color="bg", text_color="accent_ink")
        if aciklama:
            alt = ctk.CTkLabel(
                kutu, text=aciklama, font=F(11), anchor="w",
                fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
            )
            alt.pack(anchor="w", pady=(1, 0))
            tema.bagla(alt, fg_color="bg", text_color="muted")
        Ayirici(parent).pack(fill="x", padx=6, pady=(2, 4))

    def _satir(self, parent, baslik, aciklama):
        p0 = tema.p
        satir = ctk.CTkFrame(parent, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(satir, fg_color="bg")
        satir.pack(fill="x", padx=6, pady=8)
        satir.grid_columnconfigure(0, weight=1)

        b_lbl = ctk.CTkLabel(
            satir, text=baslik, font=F(13, True), anchor="w",
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        b_lbl.grid(row=0, column=0, sticky="w", padx=(0, 16))
        tema.bagla(b_lbl, fg_color="bg", text_color="ink")

        a_lbl = ctk.CTkLabel(
            satir, text=aciklama, font=F(11), anchor="w", justify="left",
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        a_lbl.grid(row=1, column=0, sticky="w", padx=(0, 16), pady=(2, 0))
        tema.bagla(a_lbl, fg_color="bg", text_color="muted")

        sag = ctk.CTkFrame(satir, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(sag, fg_color="bg")
        sag.grid(row=0, column=1, rowspan=2, sticky="e")

        Ayirici(parent).pack(fill="x", padx=6)
        return sag

    def _insa_et(self):
        p0 = tema.p
        ayarlar = self.uygulama.ayarlar
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---- Üst Başlık ----
        ust = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        ust.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 8))
        tema.bagla(ust, fg_color="bg")
        b_lbl = ctk.CTkLabel(
            ust, text="Ayarlar", font=F(19, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        b_lbl.pack(anchor="w")
        tema.bagla(b_lbl, fg_color="bg", text_color="ink")
        alt_lbl = ctk.CTkLabel(
            ust,
            text="Görünüm, varsayılan klasörler, dönüştürme tercihleri ve sistem bileşenlerini yönetin.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        alt_lbl.pack(anchor="w", pady=(2, 0))
        tema.bagla(alt_lbl, fg_color="bg", text_color="muted")

        # ---- Kaydırılabilir İçerik ----
        alan = kaydirilabilir_alan(self)
        alan.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 14))

        # 1. GÖRÜNÜM VE TEMA
        self._bolum_basligi(alan, "Görünüm ve Etkileşim")

        sag = self._satir(
            alan,
            "Uygulama Teması",
            "Koyu antrasit görünüm ile aydınlık görünüm arasında yumuşak geçiş yapın.",
        )
        aktif_tema_etiket = "Koyu Tema" if ayarlar.get("tema", "koyu") == "koyu" else "Açık Tema"
        self.tema_sb = Segment(
            sag, ["Koyu Tema", "Açık Tema"],
            komut=self._tema_secildi, aktif=aktif_tema_etiket, yukseklik=30
        )
        self.tema_sb.pack()

        sag = self._satir(
            alan,
            "Arayüz Animasyonları",
            "Sayfa geçişleri, tema renk geçişleri ve ilerleme çubuğu yumuşatmasını etkinleştirir.",
        )
        self.anim_sw = Anahtar(
            sag, deger=bool(ayarlar.get("animasyonlar", True)),
            komut=self._animasyon_degisti
        )
        self.anim_sw.pack()

        sag = self._satir(
            alan,
            "İşlem Bildirimleri",
            "İndirme veya dönüştürme tamamlandığında sağ alt köşede durum bildirimi gösterir.",
        )
        self.bildirim_sw = Anahtar(
            sag, deger=bool(ayarlar.get("bildirimler", True)),
            komut=lambda d: self.uygulama.ayar_guncelle(bildirimler=bool(d))
        )
        self.bildirim_sw.pack()

        # 2. İNDİRME AYARLARI
        self._bolum_basligi(alan, "İndirme Tercihleri")

        sag = self._satir(
            alan,
            "Varsayılan İndirme Klasörü",
            "İndirilen video ve ses dosyalarının kaydedileceği ana klasör.",
        )
        self.indir_kl_kutu = ctk.CTkFrame(
            sag, corner_radius=6, border_width=1, height=30, width=220,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"], cursor="hand2"
        )
        self.indir_kl_kutu.pack(side="left", padx=(0, 6))
        self.indir_kl_kutu.pack_propagate(False)
        tema.bagla(self.indir_kl_kutu, fg_color="yuzey", border_color="kenar")
        self.indir_kl_lbl = ctk.CTkLabel(
            self.indir_kl_kutu,
            text=self.uygulama.kisalt_yol(self.uygulama.klasor, 30),
            font=F(11), anchor="w",
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"], cursor="hand2"
        )
        self.indir_kl_lbl.pack(fill="both", expand=True, padx=8)
        tema.bagla(self.indir_kl_lbl, fg_color="yuzey", text_color="ink")
        self.indir_kl_ipucu = Ipucu(self.indir_kl_lbl, self.uygulama.klasor)
        for w in (self.indir_kl_kutu, self.indir_kl_lbl):
            w.bind("<ButtonRelease-1>", lambda _e: self._indir_klasor_sec(), add="+")

        self.indir_kl_degistir_btn = Buton(
            sag, metin="Değiştir", komut=self._indir_klasor_sec,
            tur="ikincil", yukseklik=30, font_boy=11
        )
        self.indir_kl_degistir_btn.pack(side="left", padx=(0, 4))
        Buton(
            sag, metin="Aç", komut=lambda: self.uygulama.klasor_ac(self.uygulama.klasor),
            tur="ikincil", yukseklik=30, font_boy=11
        ).pack(side="left")

        sag = self._satir(
            alan,
            "Panodaki Bağlantıyı Otomatik Algıla",
            "Pencereye geçtiğinizde panoda bir medya bağlantısı varsa bağlantı alanına otomatik yerleştirir.",
        )
        self.pano_sw = Anahtar(
            sag, deger=bool(ayarlar.get("pano_otomatik", True)),
            komut=lambda d: self.uygulama.ayar_guncelle(pano_otomatik=bool(d))
        )
        self.pano_sw.pack()

        sag = self._satir(
            alan,
            "Tamamlandığında Klasörü Otomatik Aç",
            "İndirme veya dönüştürme kuyruğu bittiğinde çıktı klasörünü Windows Gezgini'nde açar.",
        )
        self.oto_ac_sw = Anahtar(
            sag, deger=bool(ayarlar.get("bitince_klasor_ac", False)),
            komut=lambda d: self.uygulama.ayar_guncelle(bitince_klasor_ac=bool(d))
        )
        self.oto_ac_sw.pack()

        # 3. DÖNÜŞTÜRME AYARLARI
        self._bolum_basligi(alan, "Dönüştürme Tercihleri")

        sag = self._satir(
            alan,
            "Varsayılan Dönüştürme Çıktı Klasörü",
            "Boş bırakıldığında dönüştürülen dosyalar kaynak dosyanın bulunduğu klasöre kaydedilir.",
        )
        self.don_kl_kutu = ctk.CTkFrame(
            sag, corner_radius=6, border_width=1, height=30, width=220,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"], cursor="hand2"
        )
        self.don_kl_kutu.pack(side="left", padx=(0, 6))
        self.don_kl_kutu.pack_propagate(False)
        tema.bagla(self.don_kl_kutu, fg_color="yuzey", border_color="kenar")
        self.don_kl_lbl = ctk.CTkLabel(
            self.don_kl_kutu, text="", font=F(11), anchor="w",
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"], cursor="hand2"
        )
        self.don_kl_lbl.pack(fill="both", expand=True, padx=8)
        tema.bagla(self.don_kl_lbl, fg_color="yuzey", text_color="ink")
        self.don_kl_ipucu = Ipucu(self.don_kl_lbl, "")
        self._don_klasor_goster()
        for w in (self.don_kl_kutu, self.don_kl_lbl):
            w.bind("<ButtonRelease-1>", lambda _e: self._don_klasor_sec(), add="+")

        self.don_kl_sec_btn = Buton(
            sag, metin="Seç", komut=self._don_klasor_sec,
            tur="ikincil", yukseklik=30, font_boy=11
        )
        self.don_kl_sec_btn.pack(side="left", padx=(0, 4))
        Buton(
            sag, metin="Sıfırla", komut=self._don_klasor_sifirla,
            tur="hayalet", yukseklik=30, font_boy=11
        ).pack(side="left")

        ses_fmtler = conv.ses_formatlari() or ["MP3", "WAV", "FLAC", "AAC", "OGG", "M4A"]
        sag = self._satir(
            alan,
            "Varsayılan Ses Dönüştürme Biçimi",
            "Dönüştürücüde ses hedefleri seçildiğinde başlangıç olarak kullanılacak biçim.",
        )
        self.don_ses_sb = Segment(
            sag, ses_fmtler,
            komut=lambda s: self.uygulama.ayar_guncelle(donusum_ses_format=s),
            aktif=ayarlar.get("donusum_ses_format", "MP3"), yukseklik=28, font_boy=11,
        )
        self.don_ses_sb.pack()

        vid_fmtler = conv.video_formatlari() or ["MP4", "MKV", "AVI", "MOV", "WEBM"]
        sag = self._satir(
            alan,
            "Varsayılan Video Dönüştürme Biçimi",
            "Dönüştürücüde video hedefleri seçildiğinde başlangıç olarak kullanılacak biçim.",
        )
        self.don_vid_sb = Segment(
            sag, vid_fmtler,
            komut=lambda s: self.uygulama.ayar_guncelle(donusum_video_format=s),
            aktif=ayarlar.get("donusum_video_format", "MP4"), yukseklik=28, font_boy=11,
        )
        self.don_vid_sb.pack()

        # 4. SİSTEM VE MOTOR
        self._bolum_basligi(alan, "Sistem ve Altyapı")

        sag = self._satir(
            alan,
            "İndirme Motoru (yt-dlp)",
            f"Etkin sürüm: {YTDLP_SURUM}. Platform değişikliklerinde indirme sorunlarını gidermek için güncelleyin.",
        )
        self.yenile_btn = Buton(
            sag, metin="Motoru Güncelle", ikon="yenile",
            komut=self.motor_guncelle, tur="ikincil", yukseklik=30, font_boy=11
        )
        self.yenile_btn.pack(side="left")

        ff_yol = ffmpeg_klasoru()
        kod_sayisi = len(conv.kodlayicilar()) if ff_yol else 0
        ff_aciklama = (
            f"Paketlenmiş FFmpeg & FFprobe hazır ({kod_sayisi} kodlayıcı etkin)."
            if ff_yol
            else "FFmpeg bulunamadı — dönüştürme işlemleri için kurulumu doğrulayın."
        )
        sag = self._satir(alan, "Medya İşleme Motoru (FFmpeg & FFprobe)", ff_aciklama)
        Rozet(
            sag, "Hazır" if ff_yol else "Eksik", "tamam" if ff_yol else "hata"
        ).pack(side="left", padx=(0, 8))
        Buton(
            sag, metin="Günlükleri Aç", ikon="belge",
            komut=self.uygulama.gunluk_ac, tur="ikincil", yukseklik=30, font_boy=11
        ).pack(side="left", padx=(0, 4))
        Buton(
            sag, metin="Veri Klasörü", ikon="klasor",
            komut=lambda: self.uygulama.klasor_ac(str(VERI_KLASORU)),
            tur="ikincil", yukseklik=30, font_boy=11,
        ).pack(side="left")

        # 5. HAKKINDA
        self._bolum_basligi(alan, "Hakkında")
        sag = self._satir(
            alan,
            f"{APP_ADI} v{SURUM}  —  {YAPIMCI}",
            "Modern medya indirme ve yerel ses/video dönüştürme masaüstü yazılımı. "
            "FFmpeg (LGPLv3) ve yt-dlp altyapısını kullanır.",
        )
        Rozet(sag, f"Sürüm {SURUM}", "aktif").pack(side="left")

    # ------------------------------------------------------------------ olaylar
    def _tema_secildi(self, secim):
        hedef = "koyu" if secim == "Koyu Tema" else "acik"
        self.uygulama.tema_ayarla(hedef)

    def tema_etiketi_senkronla(self, tema_kodu):
        self.tema_sb.set("Koyu Tema" if tema_kodu == "koyu" else "Açık Tema")

    def _animasyon_degisti(self, deger):
        tema.animasyon = bool(deger)
        self.uygulama.ayar_guncelle(animasyonlar=bool(deger))

    def _indir_klasor_sec(self):
        yol = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=self.uygulama.klasor,
            title="Varsayılan İndirme Klasörünü Seçin",
        )
        if yol:
            self.uygulama.klasor_guncelle(yol)

    def klasor_etiketi_guncelle(self, yol):
        self.indir_kl_lbl.configure(text=self.uygulama.kisalt_yol(yol, 30))
        self.indir_kl_ipucu.guncelle(yol)

    def _don_klasor_goster(self):
        ozel = self.uygulama.ayarlar.get("donusum_klasor") or ""
        if ozel and Path(ozel).is_dir():
            self.don_kl_lbl.configure(text=self.uygulama.kisalt_yol(ozel, 30))
            self.don_kl_ipucu.guncelle(ozel)
        else:
            self.don_kl_lbl.configure(text="Kaynak dosya ile aynı klasör")
            self.don_kl_ipucu.guncelle("Dönüştürülen dosyalar kaynak dosyanın bulunduğu klasöre yazılır.")

    def _don_klasor_sec(self):
        bas = self.uygulama.ayarlar.get("donusum_klasor") or self.uygulama.klasor
        yol = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=bas,
            title="Varsayılan Dönüştürme Çıktı Klasörünü Seçin",
        )
        if yol:
            self.uygulama.ayar_guncelle(donusum_klasor=yol)
            self._don_klasor_goster()
            self.uygulama.sayfalar["donusturucu"].cikti_etiketi_guncelle()

    def _don_klasor_sifirla(self):
        self.uygulama.ayar_guncelle(donusum_klasor="")
        self._don_klasor_goster()
        self.uygulama.sayfalar["donusturucu"].cikti_etiketi_guncelle()

    def motor_guncelle(self):
        if self.uygulama.aktif_gorev_var_mi():
            self.uygulama.bildirim("Güncelleme öncesi devam eden işlemleri tamamlayın.", "bilgi")
            return
        self.yenile_btn.durum_ayarla(False, "Kontrol ediliyor…")
        threading.Thread(target=self._motor_guncelle_is, daemon=True).start()

    def _motor_guncelle_is(self):
        mesaj, tamam = guncelle(
            lambda m: self.uygulama.ui_cagir(self.yenile_btn.metin_ayarla, m)
        )
        self.uygulama.ui_cagir(self._motor_guncelle_bitti, mesaj, tamam)

    def _motor_guncelle_bitti(self, mesaj, tamam):
        if not self.winfo_exists():
            return
        self.yenile_btn.durum_ayarla(True, "Motoru Güncelle")
        self.uygulama.bildirim(mesaj, "tamam" if tamam else "hata")
        LOG_KLASORU.mkdir(parents=True, exist_ok=True)
