# -*- mode: python ; coding: utf-8 -*-
# Kroxload 1.1.0 — onedir derleme: dist/Kroxload/Kroxload.exe
# FFmpeg/FFprobe ve DLL'leri deps/ffmpeg'den alınıp _internal/ffmpeg altına
# OLDUĞU GİBİ kopyalanır (datas); kullanıcı FFmpeg kurmak zorunda kalmaz.
from PyInstaller.utils.hooks import collect_all

datas = [("assets", "assets"), ("deps/ffmpeg", "ffmpeg")]
binaries = []
hiddenimports = []

for paket in ("customtkinter", "yt_dlp", "tkinterdnd2"):
    tmp = collect_all(paket)
    datas += tmp[0]
    binaries += tmp[1]
    hiddenimports += tmp[2]


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Kroxload",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX bazı antivirüslerde yanlış uyarı tetiklediği için kapalı
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/kroxload.ico",
    version="version.txt",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Kroxload",
)
