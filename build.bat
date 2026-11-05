@echo off
rem Kroxload 1.1.0 - tam derleme hatti: ikon -> PyInstaller (onedir) -> Setup.exe -> Portable.zip
rem Gereksinimler: python + pip install customtkinter yt-dlp pillow pyinstaller ; Inno Setup 6 (ISCC.exe)
cd /d "%~dp0"

if not exist deps\ffmpeg\ffmpeg.exe (
  echo deps\ffmpeg\ffmpeg.exe bulunamadi. FFmpeg LGPL shared build dosyalarini deps\ffmpeg\ altina koyun.
  goto :hata
)

echo [1/4] Ikon uretiliyor...
python tools\make_icon.py || goto :hata

echo [2/4] PyInstaller calisiyor...
python -m PyInstaller --noconfirm --clean Kroxload.spec || goto :hata

echo [3/4] Kurulum paketi (Inno Setup)...
set ISCC=
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if defined INNO_ISCC set "ISCC=%INNO_ISCC%"
if not defined ISCC (
  echo ISCC.exe bulunamadi. Inno Setup 6 kurun veya INNO_ISCC ortam degiskenini ayarlayin.
  goto :hata
)
"%ISCC%" installer\Kroxload.iss || goto :hata

echo [4/4] Portable zip...
python tools\make_portable.py || goto :hata

echo.
echo Hazir: release\Kroxload_Setup.exe ve release\Kroxload_Portable.zip
pause
exit /b 0

:hata
echo.
echo Derleme basarisiz!
pause
exit /b 1
