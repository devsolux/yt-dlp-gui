# YT-DLP GUI - YouTube, TikTok and hundreds of sites video and audio downloader

![Windows](https://img.shields.io/badge/Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

## Description

A simple desktop app for downloading videos and audio
from [hundreds of sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) using yt-dlp.

**What it does:**

- Downloads videos in MP4 (144p to 4K)
- Extracts audio as MP3

## Tech Stack

- **Python 3.12+** - Core language
- **CustomTkinter** - Modern GUI framework
- **yt-dlp** - Video downloading engine
- **Pillow** - Image processing
- **PyInstaller** - Executable builds

## Installation

### From source

```bash
git clone https://github.com/devsolux/yt-dlp-gui.git
cd yt-dlp-gui

pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
pip install -e .

python main.py
```

### Build executable

```bash
pip install pyinstaller

rm -rf build/ dist/
rm -rf *.spec
python build.py
```

## Usage

1. Launch the application
2. Paste video URL in the input field
3. Wait for video preview to load
4. Select desired quality and format
5. Click "Start" to begin download

