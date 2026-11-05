# Kroxload

[🇬🇧 English](README.md) | [🇹🇷 Türkçe](README.tr.md)

A modern, fast, and professional desktop media downloader and converter developed by **KXR YAZILIM**.

Download videos and audio from YouTube and hundreds of platforms supported by `yt-dlp`. Convert local audio and video files with the built-in **FFmpeg & FFprobe** engine.

## Key Features (v1.1.0)

- **Home (Media Downloader):**
  - Multiple URL queue, automatic clipboard detection, and live media previews (thumbnail, channel, duration).
  - Format and quality selection (`MP3`, `WAV`, `MP4`, `M4A`) with playlist support.
  - Live download speed, file size, and estimated time remaining (ETA) for each download.
  - **Pause / Resume**, **Cancel**, **Retry**, **Open File**, and **Show in Folder** actions.

- **Converter (Local FFmpeg & FFprobe):**
  - **Audio → Audio:** `MP3`, `WAV`, `FLAC`, `AAC`, `OGG`, `M4A`
  - **Video → Video:** `MP4`, `MKV`, `AVI`, `MOV`, `WEBM`
  - **Video → Audio:** `MP3`, `WAV`, `FLAC`, `AAC`, `OGG`, `M4A`
  - **Audio → Video:** Create videos by combining audio files with cover images (`PNG`/`JPG`/`WEBP`). Supported output formats: `MP4`, `MKV`, `WEBM`, `MOV`, `AVI`.
  - Drag-and-drop support (`tkinterdnd2`), multiple file queue, FFprobe stream analysis, dynamic codec/bitrate/resolution/sample rate selection, and live progress tracking.

- **History:**
  - Persistent download and conversion history (`%APPDATA%\Kroxload\gecmis.json`).
  - Category filters (`All`, `Downloads`, `Conversions`, `Failed`) and instant search.

- **Settings & Themes:**
  - **Dark Mode** and **Light Mode** with smooth color transition animations.
  - One-click `yt-dlp` engine updates.
  - FFmpeg/FFprobe status verification.
  - Notification and animation preferences.

## Building

**Requirements:**

- Python 3.10+
- `customtkinter`
- `yt-dlp`
- `pillow`
- `tkinterdnd2`
- `pyinstaller`
- Inno Setup 6
- `deps/ffmpeg/` (LGPL shared FFmpeg)

Install the required Python packages:

```bash
pip install customtkinter yt-dlp pillow tkinterdnd2 pyinstaller
```

Build the project:

```bash
build.bat
```

**Build outputs:**

- `release/Kroxload_Setup.exe`
- `release/Kroxload_Portable.zip`

FFmpeg and FFprobe are bundled with the application (`_internal/ffmpeg`), so users do not need to install Python or FFmpeg separately.

## Tests

Run the tests using:

```bash
python tests/test_engine.py
python tests/test_converter.py
python tests/test_ui.py
```

## Project Structure

```text
main.py                      Entry point (the executable is built from this file)
kroxload/
  core/                      Core layer independent of the UI
    engine.py                Event-driven download engine (pause/cancel/queue)
    converter.py             FFmpeg & FFprobe media conversion engine
    info.py                  Media preview and metadata retrieval
    history.py               Persistent download and conversion history
    settings.py              Persistent user settings
    errors.py                Turkish user-friendly error translator
    logs.py                  Rotating log system and crash handler
    updater.py               yt-dlp engine updater
    formats.py               Download format and quality definitions
    paths.py                 Data directories, resource paths, and bundled FFmpeg resolution
    ytdlp.py                 Dynamic yt-dlp loader
  ui/                        Modern desktop interface layer
    theme.py                 Dark/light color palettes, typography, and theme animator
    widgets.py               Custom components (segments, switches, buttons, notifications, etc.)
    desktop.py               Main window, sidebar navigation, and page transition manager
    page_home.py             Home page (download center)
    page_converter.py        Converter page (drag-and-drop & FFmpeg queue)
    page_history.py          History page
    page_settings.py         Settings and About page
assets/                      Kroxload logos and icon files (PNG + ICO)
installer/Kroxload.iss       Inno Setup 6 installer script
tools/make_icon.py           Logo and icon generator
tools/make_portable.py       Portable ZIP packager
tests/                       Automated engine, converter, and UI tests
```

---

Developed by **KXR YAZILIM**.
