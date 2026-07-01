# MMCLI — YouTube Downloader

MMCLI is a command-line **YouTube downloader** with built-in format conversion.
Give it a video or playlist URL and it downloads the media, optionally
converting it to the audio or video format you want.

## Features

- Download YouTube **videos** in the best available quality (or a chosen resolution).
- Download **audio only** by requesting an audio format (e.g. `--format mp3`).
- Download entire **playlists** concurrently, organized into a per-playlist folder.
- **Convert** downloaded media to another container/format via FFmpeg.

## Installation

```bash
git clone https://github.com/rizkirakasiwi/mmcli.git
cd mmcli

# Recommended: uv
uv sync
uv run mmcli --help

# Or with pip
pip install -e .
```

Requires **Python 3.12+** and **FFmpeg** on your `PATH` for conversion.

## Usage

```bash
# Best-quality video into the current directory
mmcli "https://youtube.com/watch?v=..."

# Video at 720p
mmcli "https://youtube.com/watch?v=..." --resolution 720

# Audio only, as mp3
mmcli "https://youtube.com/watch?v=..." --format mp3

# Video converted to mkv
mmcli "https://youtube.com/watch?v=..." --format mkv

# Whole playlist as mp3
mmcli "https://youtube.com/playlist?list=..." --format mp3

# Pick an output directory (default is the current directory)
mmcli "https://youtube.com/watch?v=..." --output-dir ~/Downloads
```

See [doc/commands.md](doc/commands.md) for the full reference.

## How it works

- A single positional argument: a YouTube video or playlist URL.
- `--format` decides audio-vs-video: an audio alias downloads the audio stream;
  a video alias (or no `--format`) downloads video and converts the container if
  needed.
- Playlists are detected automatically and downloaded concurrently into
  `<output-dir>/<playlist-title>/`.

## Supported formats

- **Video:** `mp4`, `mkv`, `avi`, `mov`, `webm`, `flv`, `3gp`, and more.
- **Audio:** `mp3`, `m4a`, `wav`, `flac`, `aac`, `ogg`, `opus`, and more.

## Development

```bash
uv sync --extra test
uv run pytest                 # run the test suite (with coverage)
uv run pytest tests/test_media_downloader.py   # a single file
```

All contributors should read [doc/CONTRIBUTOR_GUIDANCE.md](doc/CONTRIBUTOR_GUIDANCE.md).

## License

MIT License. See [LICENSE](LICENSE) for details.
