"""Dönüştürücü Sayfası: FFmpeg + FFprobe tabanlı yerel medya dönüştürücü.

Desteklenen modlar:
- Ses → Ses:   MP3, WAV, FLAC, AAC, OGG, M4A
- Video → Video: MP4, MKV, AVI, MOV, WEBM
- Video → Ses: MP3, WAV, FLAC, AAC, OGG, M4A
- Ses → Video: MP4, MKV, WEBM, MOV, AVI (isteğe bağlı kapak görseliyle)

Yalnızca paketlenmiş FFmpeg'in gerçekten içerdiği kodlayıcılar (`converter.mevcut`)
gösterilir. Eklenen her dosya arka planda `converter.sonda` (FFprobe) ile incelenir.
"""
import os
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from kroxload.core import converter as conv
from kroxload.core import history
from kroxload.core.logs import kayit as log

from .theme import F, GLIF, hizli_boya, ikon_fontu, kirp, tema
from .widgets import (
    Ayirici,
    Buton,
    IkonButon,
    IlerlemeCubugu,
    Ipucu,
    Rozet,
    Segment,
    kaydirilabilir_alan,
)

MODLAR = ("Ses → Ses", "Video → Video", "Video → Ses", "Ses → Video")
CODEC_TERS = {v: k for k, v in conv.CODEC_ADI.items()}
ORNEKLEMELER = {"Orijinal": None, "48 kHz": 48000, "44.1 kHz": 44100}
KANALLAR = {"Orijinal": None, "Stereo": 2, "Mono": 1}


class DonusumSatiri(ctk.CTkFrame):
    """Dönüştürme kuyruğundaki tek bir dosya satırı."""

    def __init__(self, parent, sayfa, yol):
        p0 = tema.p
        super().__init__(
            parent, corner_radius=6, border_width=1,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"]
        )
        self.sayfa = sayfa
        self.yol = str(yol)
        self.ad = os.path.basename(self.yol)
        self.bilgi = None          # ffprobe sonucu
        self.inceleme_hatasi = None
        self.durum_kodu = "hazir"  # hazir | sirada | isleniyor | tamam | hata | iptal
        self.sira = 0
        self.cikti_dosya = None
        self.hedef_etiket = ""

        tema.bagla(self, fg_color="yuzey", border_color="kenar")
        self.grid_columnconfigure(1, weight=1)

        uzanti = Path(self.yol).suffix.lower()
        ikon_ad = "video" if uzanti in conv.VIDEO_UZANTILARI else "muzik"
        self._ikon_renk_k = "accent_ink" if ikon_ad == "video" else "muted"
        self.tur_ikon = ctk.CTkLabel(
            self, text=GLIF[ikon_ad], font=ikon_fontu(16), width=28, height=28,
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0[self._ikon_renk_k]
        )
        self.tur_ikon.grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=10, sticky="n")
        tema.bagla(self.tur_ikon, fg_color="yuzey", text_color=lambda p: p[self._ikon_renk_k])

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
            orta, text="FFprobe ile dosya inceleniyor…", anchor="w", font=F(11),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.detay_lbl.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self._detay_renk_k = "muted"
        tema.bagla(self.detay_lbl, fg_color="yuzey", text_color=lambda p: p[self._detay_renk_k])

        sag = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        sag.grid(row=0, column=2, rowspan=2, padx=(10, 12), pady=9, sticky="e")
        tema.bagla(sag, fg_color="yuzey")

        self.rozet = Rozet(sag, "İnceleniyor", "sirada")
        self.rozet.pack(side="left", padx=(0, 8))

        self.eylem_kutu = ctk.CTkFrame(sag, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        self.eylem_kutu.pack(side="left")
        tema.bagla(self.eylem_kutu, fg_color="yuzey")

        self.cubuk = IlerlemeCubugu(self, yukseklik=3)
        self.cubuk.grid(row=2, column=0, columnspan=3, sticky="ew", padx=1, pady=(0, 1))
        self.cubuk.grid_remove()

        self.bind("<Configure>", self._yeniden_boyut, add="+")
        self._baslik_yenile()
        self._eylemleri_kur()

    def _detay_renk_ayarla(self, jeton):
        self._detay_renk_k = jeton
        hizli_boya(self.detay_lbl, fg_color=tema.p["yuzey"], text_color=tema.p[jeton])

    def _yeniden_boyut(self, _e=None):
        self._baslik_yenile()

    def _baslik_yenile(self):
        maks = max(180, (self.winfo_width() or 640) - 290)
        self.baslik_lbl.configure(text=kirp(self.ad, maks, 13, True))

    def kaynak_ozeti(self):
        if self.inceleme_hatasi:
            return self.inceleme_hatasi
        if not self.bilgi:
            return "İnceleniyor…"
        b = self.bilgi
        parcalar = []
        if b.get("sure"):
            parcalar.append(conv.sure_yaz(b["sure"]))
        if b.get("boyut"):
            parcalar.append(conv.boyut_yaz(b["boyut"]))
        v = b.get("video")
        if v:
            coz = f"{v.get('genislik')}×{v.get('yukseklik')}" if v.get("genislik") else ""
            fps = f" {v['fps']:g}fps" if v.get("fps") else ""
            parcalar.append(f"Video: {coz}{fps} ({v.get('codec') or '?'})".strip())
        s = b.get("ses")
        if s:
            sp = [s.get("codec") or "ses"]
            if s.get("bitrate"):
                sp.append(f"{s['bitrate']} kbps")
            if s.get("hz"):
                sp.append(f"{s['hz'] / 1000:g} kHz")
            parcalar.append("Ses: " + " ".join(sp))
        return " · ".join(parcalar)

    def sonda_ata(self, bilgi=None, hata=None):
        if not self.winfo_exists():
            return
        self.bilgi = bilgi
        self.inceleme_hatasi = hata
        if hata:
            self.durum_kodu = "hata"
            self.rozet.ayarla("Geçersiz dosya", "hata")
            self.detay_lbl.configure(text=hata)
            self._detay_renk_ayarla("err")
        else:
            self.durum_kodu = "hazir"
            tur = "Video" if bilgi.get("video") else "Ses"
            self.tur_ikon.configure(text=GLIF["video" if bilgi.get("video") else "muzik"])
            self._ikon_renk_k = "accent_ink" if bilgi.get("video") else "muted"
            hizli_boya(self.tur_ikon, fg_color=tema.p["yuzey"], text_color=tema.p[self._ikon_renk_k])
            self.rozet.ayarla(f"{tur} · Hazır", "notr")
            self.detay_lbl.configure(text=self.kaynak_ozeti())
            self._detay_renk_ayarla("muted")
        self._eylemleri_kur()

    def _eylemleri_kur(self):
        for w in self.eylem_kutu.winfo_children():
            w.destroy()
        kod = self.durum_kodu
        if kod in ("sirada", "isleniyor"):
            IkonButon(
                self.eylem_kutu, "kapat", komut=lambda: self.sayfa.satir_iptal(self),
                ipucu="Dönüştürmeyi iptal et", tur="tehlike"
            ).pack(side="left")
        elif kod == "tamam":
            if self.cikti_dosya and Path(self.cikti_dosya).exists():
                IkonButon(
                    self.eylem_kutu, "dosya_ac",
                    komut=lambda: self.sayfa.uygulama.dosya_ac(self.cikti_dosya),
                    ipucu="Dönüştürülen dosyayı aç"
                ).pack(side="left", padx=(0, 4))
                IkonButon(
                    self.eylem_kutu, "klasor_ac",
                    komut=lambda: self.sayfa.uygulama.klasor_ac(self.cikti_dosya),
                    ipucu="Klasörde göster"
                ).pack(side="left", padx=(0, 4))
            IkonButon(
                self.eylem_kutu, "kapat", komut=lambda: self.sayfa.satir_kaldir(self),
                ipucu="Listeden kaldır"
            ).pack(side="left")
        else:
            IkonButon(
                self.eylem_kutu, "kapat", komut=lambda: self.sayfa.satir_kaldir(self),
                ipucu="Listeden kaldır"
            ).pack(side="left")

    def siraya_al(self, sira, hedef_etiket):
        self.sira = sira
        self.hedef_etiket = hedef_etiket
        self.durum_kodu = "sirada"
        self.cikti_dosya = None
        self.cubuk.set(0, animasyonlu=False)
        self.cubuk.grid(row=2, column=0, columnspan=3, sticky="ew", padx=1, pady=(0, 1))
        self.rozet.ayarla("Sırada", "sirada")
        self.detay_lbl.configure(text=f"{self.kaynak_ozeti()}  →  {hedef_etiket}")
        self._detay_renk_ayarla("muted")
        self._eylemleri_kur()

    def basladi(self):
        self.durum_kodu = "isleniyor"
        self.rozet.ayarla("Dönüştürülüyor", "aktif")
        self._eylemleri_kur()

    def ilerleme(self, olay):
        self.durum_kodu = "isleniyor"
        oran = float(olay.get("oran") or 0.0)
        self.cubuk.set(oran)
        parcalar = [self.hedef_etiket, f"%{oran * 100:.0f}"]
        if olay.get("boyut"):
            parcalar.append(conv.boyut_yaz(olay["boyut"]))
        if olay.get("hiz"):
            parcalar.append(olay["hiz"])
        if olay.get("kalan"):
            parcalar.append(f"kalan {olay['kalan']}")
        self.rozet.ayarla(f"%{oran * 100:.0f}", "aktif")
        self.detay_lbl.configure(text=" · ".join(p for p in parcalar if p))

    def bitti(self, olay):
        self.cubuk.grid_remove()
        if olay.get("basarili"):
            self.durum_kodu = "tamam"
            self.cikti_dosya = olay.get("dosya")
            cikti_ad = Path(self.cikti_dosya).name if self.cikti_dosya else ""
            boyut = conv.boyut_yaz(olay.get("boyut") or 0)
            self.rozet.ayarla("Tamamlandı", "tamam")
            self.detay_lbl.configure(
                text=" · ".join(x for x in (cikti_ad, self.hedef_etiket, boyut) if x)
            )
            self._detay_renk_ayarla("muted")
        elif olay.get("iptal"):
            self.durum_kodu = "iptal"
            self.rozet.ayarla("İptal edildi", "iptal")
            self.detay_lbl.configure(text="Kullanıcı tarafından iptal edildi")
            self._detay_renk_ayarla("muted")
        else:
            self.durum_kodu = "hata"
            self.rozet.ayarla("Hata", "hata")
            self.detay_lbl.configure(text=olay.get("hata") or "Dönüştürme başarısız oldu")
            self._detay_renk_ayarla("err")
        self._eylemleri_kur()


class DonusturucuSayfasi(ctk.CTkFrame):
    """FFmpeg ve FFprobe entegrasyonlu medya dönüştürücü sayfası."""

    def __init__(self, parent, uygulama):
        p0 = tema.p
        super().__init__(parent, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self, fg_color="bg")
        self.uygulama = uygulama
        self.satirlar = []
        self.motor = None
        self.aktif_harita = {}     # sira -> DonusumSatiri
        self.kapak_yolu = None
        self._surukleme_aktif = False

        self.ses_fmt_listesi = conv.ses_formatlari() or ["MP3", "WAV", "FLAC", "AAC", "OGG", "M4A"]
        self.video_fmt_listesi = conv.video_formatlari() or ["MP4", "MKV", "AVI", "MOV", "WEBM"]

        self._insa_et()
        self._mod_uygula(MODLAR[0], ilk=True)
        self._surukle_birak_bagla()

    def _insa_et(self):
        p0 = tema.p
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        # ---- 1. Üst başlık + İşlem Türü Seçici ----
        ust = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        ust.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))
        ust.grid_columnconfigure(0, weight=1)
        tema.bagla(ust, fg_color="bg")

        sol = ctk.CTkFrame(ust, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        sol.grid(row=0, column=0, sticky="w")
        tema.bagla(sol, fg_color="bg")
        b_lbl = ctk.CTkLabel(
            sol, text="Medya Dönüştürücü", font=F(19, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        b_lbl.pack(anchor="w")
        tema.bagla(b_lbl, fg_color="bg", text_color="ink")
        alt_lbl = ctk.CTkLabel(
            sol,
            text="Bilgisayarınızdaki ses ve video dosyalarını FFmpeg ile yüksek kalitede dönüştürün.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        alt_lbl.pack(anchor="w", pady=(2, 0))
        tema.bagla(alt_lbl, fg_color="bg", text_color="muted")

        self.mod_sb = Segment(
            ust, list(MODLAR), komut=self._mod_uygula, aktif=MODLAR[0], yukseklik=32
        )
        self.mod_sb.grid(row=0, column=1, sticky="e")

        # ---- 2. Sürükle-Bırak ve Dosya Seçim Alanı ----
        self.birak_cerceve = ctk.CTkFrame(
            self, corner_radius=8, border_width=1, height=74,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"], cursor="hand2"
        )
        self.birak_cerceve.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 10))
        self.birak_cerceve.grid_propagate(False)
        self.birak_cerceve.grid_columnconfigure(1, weight=1)

        self._b_ikon = ctk.CTkLabel(
            self.birak_cerceve, text=GLIF["yukle"], font=ikon_fontu(20),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["accent_ink"], cursor="hand2"
        )
        self._b_ikon.grid(row=0, column=0, rowspan=2, padx=(18, 12), pady=14)

        self.birak_baslik = ctk.CTkLabel(
            self.birak_cerceve,
            text="Dosyaları buraya sürükleyip bırakın veya bilgisayarınızdan seçin",
            anchor="w", font=F(13, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["ink"], cursor="hand2"
        )
        self.birak_baslik.grid(row=0, column=1, sticky="sw", pady=(14, 0))

        self.birak_alt = ctk.CTkLabel(
            self.birak_cerceve,
            text="Desteklenen kaynaklar: MP3, WAV, FLAC, AAC, OGG, M4A, MP4, MKV, AVI, MOV, WEBM",
            anchor="w", font=F(11),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"], cursor="hand2"
        )
        self.birak_alt.grid(row=1, column=1, sticky="nw", pady=(2, 12))

        self._b_aksiyon = ctk.CTkFrame(
            self.birak_cerceve, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"]
        )
        self._b_aksiyon.grid(row=0, column=2, rowspan=2, padx=14)

        tema.bagla_fn(self.birak_cerceve, self._birak_boya)

        self.dosya_ekle_btn = Buton(
            self._b_aksiyon, metin="Dosya Seç", ikon="ekle",
            komut=self.dosya_sec, tur="ikincil", yukseklik=34
        )
        self.dosya_ekle_btn.pack(side="left")

        for w in (self.birak_cerceve, self._b_ikon, self.birak_baslik, self.birak_alt):
            w.bind("<ButtonRelease-1>", lambda _e: self.dosya_sec(), add="+")

        # ---- 3. Hedef Biçim, Codec, Bitrate ve Çözünürlük Şeridi ----
        ayar_kutu = ctk.CTkFrame(
            self, corner_radius=8, border_width=1,
            fg_color=p0["yuzey"], border_color=p0["kenar"], bg_color=p0["bg"]
        )
        ayar_kutu.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 10))
        ayar_kutu.grid_columnconfigure(0, weight=1)
        tema.bagla(ayar_kutu, fg_color="yuzey", border_color="kenar")

        # Satır A: Hedef Biçim + Codec
        satir_a = ctk.CTkFrame(ayar_kutu, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        satir_a.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        satir_a.grid_columnconfigure(3, weight=1)
        tema.bagla(satir_a, fg_color="yuzey")

        fmt_k = ctk.CTkFrame(satir_a, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        fmt_k.grid(row=0, column=0, sticky="w", padx=(0, 16))
        tema.bagla(fmt_k, fg_color="yuzey")
        self.fmt_baslik = ctk.CTkLabel(
            fmt_k, text="Hedef Biçim", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.fmt_baslik.pack(anchor="w", pady=(0, 4))
        tema.bagla(self.fmt_baslik, fg_color="yuzey", text_color="muted")
        self.hedef_fmt_sb = Segment(
            fmt_k, self.ses_fmt_listesi, komut=self._format_degisti, yukseklik=28, font_boy=11
        )
        self.hedef_fmt_sb.pack(anchor="w")

        codec_k = ctk.CTkFrame(satir_a, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        codec_k.grid(row=0, column=1, sticky="w", padx=(0, 16))
        tema.bagla(codec_k, fg_color="yuzey")
        self.codec_baslik = ctk.CTkLabel(
            codec_k, text="Kodlayıcı (Codec)", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.codec_baslik.pack(anchor="w", pady=(0, 4))
        tema.bagla(self.codec_baslik, fg_color="yuzey", text_color="muted")
        self.codec_sb = Segment(codec_k, ["MP3 (LAME)"], yukseklik=28, font_boy=11)
        self.codec_sb.pack(anchor="w")

        # Kapak görseli (Ses → Video modunda sağda belirir)
        self.kapak_kutu = ctk.CTkFrame(satir_a, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        self.kapak_kutu.grid(row=0, column=3, sticky="e")
        tema.bagla(self.kapak_kutu, fg_color="yuzey")
        kp_lbl = ctk.CTkLabel(
            self.kapak_kutu, text="Kapak Görseli (Ses → Video)", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        kp_lbl.pack(anchor="w", pady=(0, 4))
        tema.bagla(kp_lbl, fg_color="yuzey", text_color="muted")
        kp_ic = ctk.CTkFrame(self.kapak_kutu, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        kp_ic.pack(anchor="e")
        tema.bagla(kp_ic, fg_color="yuzey")
        self.kapak_etiket = ctk.CTkLabel(
            kp_ic, text="Görsel yok (koyu arka plan)", font=F(11), anchor="w",
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.kapak_etiket.pack(side="left", padx=(0, 8))
        tema.bagla(self.kapak_etiket, fg_color="yuzey", text_color="muted")
        self.gorsel_sec_btn = Buton(
            kp_ic, metin="Görsel Seç", ikon="resim", komut=self.gorsel_sec,
            tur="ikincil", yukseklik=28, font_boy=11
        )
        self.gorsel_sec_btn.pack(side="left", padx=(0, 4))
        self.kapak_sil_btn = IkonButon(
            kp_ic, "kapat", komut=self.gorsel_temizle,
            ipucu="Görseli kaldır", boy=28, tur="ikincil"
        )
        self.kapak_sil_btn.pack(side="left")

        # Satır B: Bit Hızı / Kalite + Çözünürlük / Örnekleme + Kanal
        satir_b = ctk.CTkFrame(ayar_kutu, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        satir_b.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 10))
        tema.bagla(satir_b, fg_color="yuzey")

        bit_k = ctk.CTkFrame(satir_b, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        bit_k.grid(row=0, column=0, sticky="w", padx=(0, 18))
        tema.bagla(bit_k, fg_color="yuzey")
        self.bit_baslik = ctk.CTkLabel(
            bit_k, text="Ses Bit Hızı (kbps)", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.bit_baslik.pack(anchor="w", pady=(0, 4))
        tema.bagla(self.bit_baslik, fg_color="yuzey", text_color="muted")
        self.bit_sb = Segment(bit_k, conv.SES_BITRATELER, aktif="192", yukseklik=28, font_boy=11)
        self.bit_sb.pack(anchor="w")

        coz_k = ctk.CTkFrame(satir_b, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        coz_k.grid(row=0, column=1, sticky="w", padx=(0, 18))
        tema.bagla(coz_k, fg_color="yuzey")
        self.coz_baslik = ctk.CTkLabel(
            coz_k, text="Örnekleme Hızı", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.coz_baslik.pack(anchor="w", pady=(0, 4))
        tema.bagla(self.coz_baslik, fg_color="yuzey", text_color="muted")
        self.coz_sb = Segment(
            coz_k, list(ORNEKLEMELER), aktif="Orijinal", yukseklik=28, font_boy=11
        )
        self.coz_sb.pack(anchor="w")

        self.kanal_k = ctk.CTkFrame(satir_b, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        self.kanal_k.grid(row=0, column=2, sticky="w")
        tema.bagla(self.kanal_k, fg_color="yuzey")
        self.kanal_baslik = ctk.CTkLabel(
            self.kanal_k, text="Kanal", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        self.kanal_baslik.pack(anchor="w", pady=(0, 4))
        tema.bagla(self.kanal_baslik, fg_color="yuzey", text_color="muted")
        self.kanal_sb = Segment(
            self.kanal_k, list(KANALLAR), aktif="Orijinal", yukseklik=28, font_boy=11
        )
        self.kanal_sb.pack(anchor="w")

        # Satır C: Ayırıcı + Çıktı Konumu ve Dönüştür CTA çubuğu
        Ayirici(ayar_kutu).grid(row=2, column=0, sticky="ew", padx=14)

        satir_c = ctk.CTkFrame(ayar_kutu, corner_radius=0, fg_color=p0["yuzey"], bg_color=p0["yuzey"])
        satir_c.grid(row=3, column=0, sticky="ew", padx=14, pady=(8, 10))
        satir_c.grid_columnconfigure(1, weight=1)
        tema.bagla(satir_c, fg_color="yuzey")

        sk_lbl = ctk.CTkLabel(
            satir_c, text="Çıktı Klasörü:", font=F(11, True),
            fg_color=p0["yuzey"], bg_color=p0["yuzey"], text_color=p0["muted"]
        )
        sk_lbl.grid(row=0, column=0, sticky="w", padx=(0, 8))
        tema.bagla(sk_lbl, fg_color="yuzey", text_color="muted")

        self.cikti_kutu = ctk.CTkFrame(
            satir_c, corner_radius=6, border_width=1, height=32,
            fg_color=p0["bg"], border_color=p0["kenar"], bg_color=p0["yuzey"], cursor="hand2"
        )
        self.cikti_kutu.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.cikti_kutu.grid_propagate(False)
        tema.bagla(self.cikti_kutu, fg_color="bg", border_color="kenar")
        self.cikti_lbl = ctk.CTkLabel(
            self.cikti_kutu, text="", font=F(11), anchor="w",
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"], cursor="hand2"
        )
        self.cikti_lbl.pack(fill="both", expand=True, padx=10)
        tema.bagla(self.cikti_lbl, fg_color="bg", text_color="ink")
        self.cikti_ipucu = Ipucu(self.cikti_lbl, "")
        self.cikti_etiketi_guncelle()
        for w in (self.cikti_kutu, self.cikti_lbl):
            w.bind("<ButtonRelease-1>", lambda _e: self.cikti_klasor_sec(), add="+")

        self.cikti_klasor_btn = Buton(
            satir_c, metin="Klasör Seç", ikon="klasor", komut=self.cikti_klasor_sec,
            tur="ikincil", yukseklik=32, font_boy=11
        )
        self.cikti_klasor_btn.grid(row=0, column=2, padx=(0, 10))

        self.donustur_btn = Buton(
            satir_c, metin="Dönüştür", ikon="donustur",
            komut=self.baslat, tur="birincil", yukseklik=34, genislik=136, font_boy=13
        )
        self.donustur_btn.grid(row=0, column=3, sticky="e")

        Ayirici(self).grid(row=4, column=0, sticky="ew", padx=28)

        # ---- 4. Kuyruk Başlığı ----
        kbas = ctk.CTkFrame(self, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        kbas.grid(row=5, column=0, sticky="ew", padx=28, pady=(10, 6))
        kbas.grid_columnconfigure(1, weight=1)
        tema.bagla(kbas, fg_color="bg")

        kb_lbl = ctk.CTkLabel(
            kbas, text="Dönüştürme Listesi", font=F(13, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["ink"]
        )
        kb_lbl.grid(row=0, column=0, sticky="w")
        tema.bagla(kb_lbl, fg_color="bg", text_color="ink")

        self.sayac_rozet = Rozet(kbas, "0 dosya", "notr")
        self.sayac_rozet.grid(row=0, column=1, sticky="w", padx=(8, 0))

        k_aks = ctk.CTkFrame(kbas, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        k_aks.grid(row=0, column=2, sticky="e")
        tema.bagla(k_aks, fg_color="bg")

        Buton(
            k_aks, metin="Tamamlananları Temizle",
            komut=self.tamamlananlari_temizle, tur="hayalet", yukseklik=26, font_boy=11
        ).pack(side="left", padx=(0, 6))
        Buton(
            k_aks, metin="Listeyi Boşalt",
            komut=self.listeyi_bosalt, tur="hayalet", yukseklik=26, font_boy=11
        ).pack(side="left", padx=(0, 6))
        self.iptal_btn = Buton(
            k_aks, metin="Tümünü İptal Et",
            komut=self.tumunu_iptal_et, tur="tehlike", yukseklik=26, font_boy=11
        )
        self.iptal_btn.pack(side="left")
        self.iptal_btn.pack_forget()

        # ---- 5. Kaydırılabilir Kuyruk Listesi ----
        self.liste_alan = kaydirilabilir_alan(self)
        self.liste_alan.grid(row=6, column=0, sticky="nsew", padx=22, pady=(0, 14))
        self.liste_alan.grid_columnconfigure(0, weight=1)

        self.bos_kutu = ctk.CTkFrame(self.liste_alan, corner_radius=0, fg_color=p0["bg"], bg_color=p0["bg"])
        tema.bagla(self.bos_kutu, fg_color="bg")
        self.bos_kutu.pack(fill="x", pady=42)
        b_ik = ctk.CTkLabel(
            self.bos_kutu, text=GLIF["donustur"], font=ikon_fontu(24),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["soluk"]
        )
        b_ik.pack(pady=(0, 8))
        tema.bagla(b_ik, fg_color="bg", text_color="soluk")
        b_b = ctk.CTkLabel(
            self.bos_kutu, text="Henüz dönüştürülecek dosya eklenmedi", font=F(13, True),
            fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["muted"]
        )
        b_b.pack()
        tema.bagla(b_b, fg_color="bg", text_color="muted")
        b_a = ctk.CTkLabel(
            self.bos_kutu,
            text="Dosya Seç düğmesini kullanın veya ses/video dosyalarını pencereye sürükleyin.",
            font=F(12), fg_color=p0["bg"], bg_color=p0["bg"], text_color=p0["soluk"]
        )
        b_a.pack(pady=(3, 0))
        tema.bagla(b_a, fg_color="bg", text_color="soluk")

    # ------------------------------------------------------------------ sürükle & bırak
    def _birak_boya(self, p=None):
        if not self.birak_cerceve.winfo_exists():
            return
        p = p or tema.p
        if self._surukleme_aktif:
            zemin, kenar = p["accent_bg"], p["accent"]
        else:
            zemin, kenar = p["yuzey"], p["kenar"]
        hizli_boya(self.birak_cerceve, fg_color=zemin, border_color=kenar, bg_color=p["bg"])
        hizli_boya(self._b_ikon, fg_color=zemin, bg_color=zemin, text_color=p["accent_ink"])
        hizli_boya(self.birak_baslik, fg_color=zemin, bg_color=zemin, text_color=p["ink"])
        hizli_boya(self.birak_alt, fg_color=zemin, bg_color=zemin, text_color=p["muted"])
        hizli_boya(self._b_aksiyon, fg_color=zemin, bg_color=zemin)
        if hasattr(self, "dosya_ekle_btn"):
            self.dosya_ekle_btn._boya(p)

    def _surukle_birak_bagla(self):
        kok = self.winfo_toplevel()
        for hedef in (self.birak_cerceve, self):
            try:
                hedef.drop_target_register("DND_Files")
                hedef.dnd_bind("<<DragEnter>>", self._surukle_gir)
                hedef.dnd_bind("<<DragLeave>>", self._surukle_cik)
                hedef.dnd_bind("<<Drop>>", self._birakildi)
            except Exception:
                pass
        try:
            kok.drop_target_register("DND_Files")
        except Exception:
            pass

    def _surukle_gir(self, _e=None):
        self._surukleme_aktif = True
        self._birak_boya()

    def _surukle_cik(self, _e=None):
        self._surukleme_aktif = False
        self._birak_boya()

    def _birakildi(self, e):
        self._surukleme_aktif = False
        self._birak_boya()
        veri = getattr(e, "data", "") or ""
        if not veri:
            return
        try:
            yollar = list(self.tk.splitlist(veri))
        except Exception:
            yollar = [veri.strip("{}")]
        self.dosyalari_ekle(yollar)

    # ------------------------------------------------------------------ mod ve format
    def hedef_tur(self):
        mod = self.mod_sb.get()
        return "ses" if mod in ("Ses → Ses", "Video → Ses") else "video"

    def _mod_uygula(self, mod, ilk=False):
        hedef_ses = mod in ("Ses → Ses", "Video → Ses")
        if mod == "Ses → Video":
            self.kapak_kutu.grid()
        else:
            self.kapak_kutu.grid_remove()

        if hedef_ses:
            varsayilan = self.uygulama.ayarlar.get("donusum_ses_format", "MP3")
            secim = varsayilan if varsayilan in self.ses_fmt_listesi else self.ses_fmt_listesi[0]
            self.hedef_fmt_sb.secenekleri_guncelle(self.ses_fmt_listesi, secim)
            self.coz_baslik.configure(text="Örnekleme Hızı")
            self.coz_sb.secenekleri_guncelle(list(ORNEKLEMELER), "Orijinal")
            self.kanal_baslik.configure(text="Ses Kanalı")
            self.kanal_sb.secenekleri_guncelle(list(KANALLAR), "Orijinal")
        else:
            varsayilan = self.uygulama.ayarlar.get("donusum_video_format", "MP4")
            secim = varsayilan if varsayilan in self.video_fmt_listesi else self.video_fmt_listesi[0]
            self.hedef_fmt_sb.secenekleri_guncelle(self.video_fmt_listesi, secim)
            self.bit_baslik.configure(text="Video Kalitesi")
            self.bit_sb.secenekleri_guncelle(list(conv.KALITELER), "Dengeli")
            self.coz_baslik.configure(text="Çözünürlük")
            self.coz_sb.secenekleri_guncelle(list(conv.COZUNURLUKLER), "Orijinal")
            self.kanal_baslik.configure(text="Ses Bit Hızı")
            self.kanal_sb.secenekleri_guncelle(["320", "192", "128"], "192")

        self._format_degisti(self.hedef_fmt_sb.get(), kaydet=not ilk)

    def _format_degisti(self, fmt, kaydet=True):
        if self.hedef_tur() == "ses":
            d = conv.SES_HEDEFLERI.get(fmt, conv.SES_HEDEFLERI["MP3"])
            codecler = [conv.CODEC_ADI.get(c, c) for c in conv.mevcut(d["codec"])]
            self.codec_sb.secenekleri_guncelle(codecler or ["Varsayılan"], (codecler or ["Varsayılan"])[0])
            if d["bitrate"]:
                self.bit_baslik.configure(text="Ses Bit Hızı (kbps)")
                mevcut_b = self.bit_sb.get()
                self.bit_sb.secenekleri_guncelle(
                    conv.SES_BITRATELER,
                    mevcut_b if mevcut_b in conv.SES_BITRATELER else "192",
                )
            else:
                self.bit_baslik.configure(text="Ses Kalitesi")
                self.bit_sb.secenekleri_guncelle(["Kayıpsız"], "Kayıpsız")
            if kaydet:
                self.uygulama.ayar_guncelle(donusum_ses_format=fmt)
        else:
            d = conv.VIDEO_HEDEFLERI.get(fmt, conv.VIDEO_HEDEFLERI["MP4"])
            codecler = [conv.CODEC_ADI.get(c, c) for c in conv.mevcut(d["video"])]
            self.codec_sb.secenekleri_guncelle(codecler or ["H.264"], (codecler or ["H.264"])[0])
            if kaydet:
                self.uygulama.ayar_guncelle(donusum_video_format=fmt)

    # ------------------------------------------------------------------ görsel ve klasör
    def gorsel_sec(self):
        yol = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Kapak Görseli Seçin",
            filetypes=[("Görsel Dosyaları", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if not yol:
            return
        try:
            Image.open(yol).verify()
        except Exception:
            self.uygulama.bildirim("Seçilen görsel dosyası geçerli bir resim değil.", "hata")
            return
        self.kapak_yolu = yol
        self.kapak_etiket.configure(text=kirp(Path(yol).name, 150, 11))

    def gorsel_temizle(self):
        self.kapak_yolu = None
        self.kapak_etiket.configure(text="Görsel yok (koyu arka plan)")

    def cikti_klasor_sec(self):
        baslangic = self.uygulama.ayarlar.get("donusum_klasor") or self.uygulama.klasor
        yol = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=baslangic,
            title="Dönüştürme Çıktı Klasörünü Seçin",
        )
        if yol:
            self.uygulama.ayar_guncelle(donusum_klasor=yol)
            self.cikti_etiketi_guncelle()
            if "ayarlar" in self.uygulama.sayfalar:
                self.uygulama.sayfalar["ayarlar"]._don_klasor_goster()

    def cikti_etiketi_guncelle(self):
        ozel = self.uygulama.ayarlar.get("donusum_klasor") or ""
        if ozel and Path(ozel).is_dir():
            self.cikti_lbl.configure(text=self.uygulama.kisalt_yol(ozel, 62))
            self.cikti_ipucu.guncelle(f"Çıktı klasörü: {ozel}")
        else:
            self.cikti_lbl.configure(text="Kaynak dosya ile aynı klasör")
            self.cikti_ipucu.guncelle("Dönüştürülen dosyalar kaynak dosyanın yanına kaydedilir.")

    # ------------------------------------------------------------------ dosya ekleme
    def dosya_sec(self):
        mod = self.mod_sb.get()
        ses_uz = " ".join(f"*{u}" for u in conv.SES_UZANTILARI)
        vid_uz = " ".join(f"*{u}" for u in conv.VIDEO_UZANTILARI)
        if mod.startswith("Ses"):
            tipler = [("Ses Dosyaları", ses_uz), ("Tüm Medya Dosyaları", f"{ses_uz} {vid_uz}")]
        else:
            tipler = [("Video Dosyaları", vid_uz), ("Tüm Medya Dosyaları", f"{vid_uz} {ses_uz}")]
        yollar = filedialog.askopenfilenames(
            parent=self.winfo_toplevel(),
            title="Dönüştürülecek Dosyaları Seçin",
            filetypes=tipler,
        )
        if yollar:
            self.dosyalari_ekle(yollar)

    def dosyalari_ekle(self, yollar):
        mevcut_yollar = {s.yol for s in self.satirlar if s.durum_kodu in ("hazir", "sirada", "isleniyor")}
        eklenen = []
        for ham in yollar:
            p = Path(str(ham).strip().strip('"'))
            if p.is_dir():
                for alt in sorted(p.iterdir()):
                    if alt.suffix.lower() in conv.SES_UZANTILARI + conv.VIDEO_UZANTILARI:
                        if str(alt) not in mevcut_yollar:
                            eklenen.append(str(alt))
                            mevcut_yollar.add(str(alt))
            elif p.is_file():
                if str(p) not in mevcut_yollar:
                    eklenen.append(str(p))
                    mevcut_yollar.add(str(p))

        if not eklenen:
            return

        # İlk eklenen dosyanın uzantısına göre akıllı mod uyumu
        ilk_uz = Path(eklenen[0]).suffix.lower()
        mod = self.mod_sb.get()
        if ilk_uz in conv.VIDEO_UZANTILARI and mod == "Ses → Ses":
            self.mod_sb.set("Video → Ses")
            self._mod_uygula("Video → Ses")
        elif ilk_uz in conv.SES_UZANTILARI and mod in ("Video → Video", "Video → Ses"):
            yeni_mod = "Ses → Video" if mod == "Video → Video" else "Ses → Ses"
            self.mod_sb.set(yeni_mod)
            self._mod_uygula(yeni_mod)

        for yol in eklenen:
            satir = DonusumSatiri(self.liste_alan, self, yol)
            satir.pack(fill="x", padx=6, pady=(0, 6))
            self.satirlar.append(satir)
            threading.Thread(target=self._dosya_incele, args=(satir,), daemon=True).start()

        self._kuyruk_durum_guncelle()

    def _dosya_incele(self, satir):
        try:
            bilgi = conv.sonda(satir.yol)
            self.uygulama.ui_cagir(satir.sonda_ata, bilgi, None)
        except ValueError as e:
            self.uygulama.ui_cagir(satir.sonda_ata, None, str(e))
        except Exception:
            self.uygulama.ui_cagir(satir.sonda_ata, None, "Dosya incelenemedi.")

    # ------------------------------------------------------------------ kuyruk yönetimi
    def aktif_is_sayisi(self):
        return 1 if (self.motor and self.motor.calisiyor) else 0

    def _kuyruk_durum_guncelle(self):
        toplam = len(self.satirlar)
        calisiyor = bool(self.motor and self.motor.calisiyor)
        if calisiyor:
            aktif = sum(1 for s in self.satirlar if s.durum_kodu in ("sirada", "isleniyor"))
            self.sayac_rozet.ayarla(f"{aktif} işleniyor / {toplam} dosya", "aktif")
            self.iptal_btn.pack(side="left")
            self.donustur_btn.durum_ayarla(False, "Dönüştürülüyor…")
        else:
            self.sayac_rozet.ayarla(f"{toplam} dosya", "notr")
            self.iptal_btn.pack_forget()
            self.donustur_btn.durum_ayarla(True, "Dönüştür")
        if self.satirlar:
            self.bos_kutu.pack_forget()
        else:
            self.bos_kutu.pack(fill="x", pady=42)
        self.uygulama.alt_durum_guncelle()

    def satir_kaldir(self, satir):
        if satir.durum_kodu in ("sirada", "isleniyor") and self.motor and self.motor.calisiyor:
            self.motor.oge_iptal_et(satir.sira)
            return
        if satir in self.satirlar:
            self.satirlar.remove(satir)
        try:
            satir.destroy()
        except Exception:
            pass
        self._kuyruk_durum_guncelle()

    def satir_iptal(self, satir):
        if self.motor and self.motor.calisiyor:
            self.motor.oge_iptal_et(satir.sira)
        else:
            satir.bitti({"iptal": True})
        self._kuyruk_durum_guncelle()

    def tamamlananlari_temizle(self):
        for s in list(self.satirlar):
            if s.durum_kodu in ("tamam", "iptal", "hata"):
                self.satir_kaldir(s)

    def listeyi_bosalt(self):
        if self.motor and self.motor.calisiyor:
            self.uygulama.bildirim("Önce devam eden dönüştürmeyi iptal edin.", "bilgi")
            return
        for s in list(self.satirlar):
            self.satir_kaldir(s)

    def tumunu_iptal_et(self):
        if self.motor and self.motor.calisiyor:
            self.motor.iptal_et()

    # ------------------------------------------------------------------ dönüştürme başlatma
    def _is_ayari_uret(self, kaynak_yol):
        tur = self.hedef_tur()
        fmt = self.hedef_fmt_sb.get()
        secili_codec_ad = self.codec_sb.get()
        codec_id = CODEC_TERS.get(secili_codec_ad, secili_codec_ad)
        ozel_klasor = self.uygulama.ayarlar.get("donusum_klasor") or ""
        klasor = ozel_klasor if (ozel_klasor and Path(ozel_klasor).is_dir()) else str(Path(kaynak_yol).parent)

        if tur == "ses":
            d = conv.SES_HEDEFLERI[fmt]
            bit = self.bit_sb.get() if d["bitrate"] else None
            orn = ORNEKLEMELER.get(self.coz_sb.get())
            kan = KANALLAR.get(self.kanal_sb.get())
            etiket = f"{fmt} · {secili_codec_ad}" + (f" · {bit} kbps" if bit else "")
            return {
                "kaynak": kaynak_yol,
                "hedef_tur": "ses",
                "format": fmt,
                "ses_codec": codec_id,
                "ses_bitrate": bit,
                "ornekleme": orn,
                "kanal": kan,
                "klasor": klasor,
            }, etiket

        d = conv.VIDEO_HEDEFLERI[fmt]
        ses_codec = conv.mevcut(d["ses"])[0]
        kalite = self.bit_sb.get()
        coz_ad = self.coz_sb.get()
        coz = conv.COZUNURLUKLER.get(coz_ad)
        ses_bit = self.kanal_sb.get()
        etiket = f"{fmt} · {secili_codec_ad} · {coz_ad} · {kalite}"
        return {
            "kaynak": kaynak_yol,
            "hedef_tur": "video",
            "format": fmt,
            "video_codec": codec_id,
            "ses_codec": ses_codec,
            "ses_bitrate": ses_bit,
            "kalite": kalite,
            "cozunurluk": coz,
            "gorsel": self.kapak_yolu if self.mod_sb.get() == "Ses → Video" else None,
            "klasor": klasor,
        }, etiket

    def baslat(self):
        if self.motor and self.motor.calisiyor:
            return
        adaylar = [
            s for s in self.satirlar
            if not s.inceleme_hatasi and s.durum_kodu in ("hazir", "hata", "iptal", "tamam")
        ]
        if not adaylar:
            self.uygulama.bildirim("Dönüştürmek için önce geçerli bir medya dosyası ekleyin.", "hata")
            return

        isler = []
        self.aktif_harita.clear()
        for idx, satir in enumerate(adaylar, 1):
            ayar, etiket = self._is_ayari_uret(satir.yol)
            satir.siraya_al(idx, etiket)
            self.aktif_harita[idx] = satir
            isler.append(ayar)

        self.motor = conv.DonusumMotoru(
            on_olay=lambda olay: self.uygulama.ui_cagir(self.olay_isle, olay)
        )
        self._kuyruk_durum_guncelle()
        threading.Thread(target=self.motor.donustur, args=(isler,), daemon=True).start()

    def olay_isle(self, olay):
        if not self.winfo_exists():
            return
        tip = olay.get("tip")
        satir = self.aktif_harita.get(olay.get("sira"))

        if tip == "basladi" and satir:
            satir.basladi()
        elif tip == "ilerleme" and satir:
            satir.ilerleme(olay)
        elif tip == "oge_bitti" and satir:
            satir.bitti(olay)
            if not olay.get("iptal"):
                dosya = olay.get("dosya") or ""
                try:
                    history.ekle(
                        baslik=Path(dosya).name if dosya else satir.ad,
                        dosya=dosya,
                        klasor=str(Path(dosya).parent) if dosya else str(Path(satir.yol).parent),
                        fmt=self.hedef_fmt_sb.get(),
                        kalite=satir.hedef_etiket,
                        tur="donusum",
                        durum="tamam" if olay.get("basarili") else "hata",
                        hata=olay.get("hata"),
                    )
                    self.uygulama.gecmis_yenile()
                except Exception:
                    log.exception("Dönüştürme geçmişe kaydedilemedi")
        elif tip == "bitti":
            for s in self.aktif_harita.values():
                if s.durum_kodu in ("sirada", "isleniyor"):
                    s.bitti({"iptal": True})
            if olay.get("iptal"):
                self.uygulama.bildirim("Dönüştürme işlemi iptal edildi.", "bilgi")
            elif olay["basarili"] > 0 and olay["basarili"] == olay["toplam"]:
                mesaj = (
                    "Dönüştürme tamamlandı."
                    if olay["toplam"] == 1
                    else f"{olay['toplam']} dosyanın tamamı dönüştürüldü."
                )
                self.uygulama.bildirim(mesaj, "tamam")
                if self.uygulama.ayarlar.get("bitince_klasor_ac"):
                    son_satir = next((s for s in self.aktif_harita.values() if s.cikti_dosya), None)
                    if son_satir and son_satir.cikti_dosya:
                        self.uygulama.klasor_ac(son_satir.cikti_dosya)
            elif olay.get("hatalar"):
                self.uygulama.bildirim(f"Dönüştürme hatası: {olay['hatalar'][-1]}", "hata")
        self._kuyruk_durum_guncelle()
