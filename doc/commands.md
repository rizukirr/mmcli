# MMCLI Command Reference

`mmcli` is a YouTube downloader with built-in format conversion. It takes a
single YouTube URL (video or playlist) and optional flags.

## Usage

```bash
mmcli <url> [--resolution RES] [--format FMT] [--output-dir DIR]
mmcli --version
mmcli --help
```

## Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `url` (positional) | | YouTube video or playlist URL (required). |
| `--resolution` | `-r` | Video resolution, e.g. `720` or `720p`. Ignored for audio formats. Default: highest available. |
| `--format` | `-f` | Output format. An **audio** format (`mp3`, `m4a`, `wav`, `flac`, ...) downloads audio only; a **video** format (`mp4`, `mkv`, `webm`, ...) converts the container. Default: download video in its native format. |
| `--output-dir` | `-o` | Directory to save into. Default: current directory. |
| `--version` | `-v` | Print version and exit. |

## Examples

```bash
# Best-quality video into the current directory
mmcli "https://youtube.com/watch?v=..."

# Video at 720p
mmcli "https://youtube.com/watch?v=..." --resolution 720

# Audio only, converted to mp3
mmcli "https://youtube.com/watch?v=..." --format mp3

# Video converted to mkv
mmcli "https://youtube.com/watch?v=..." --format mkv

# Whole playlist as mp3 (saved under <output-dir>/<playlist-title>/)
mmcli "https://youtube.com/playlist?list=..." --format mp3

# Choose an output directory
mmcli "https://youtube.com/watch?v=..." --output-dir ~/Downloads
```

## Behavior notes

- **Playlists** are auto-detected from the URL (`list=`) and downloaded
  concurrently into a subfolder named after the playlist title.
- **Conversion** runs after download and only when the requested format differs
  from the downloaded file's format. FFmpeg must be installed and on `PATH`.
