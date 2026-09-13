# mmcli

[![PyPI version](https://img.shields.io/pypi/v/mmcli-dl)](https://pypi.org/project/mmcli-dl/)
[![Python versions](https://img.shields.io/pypi/pyversions/mmcli-dl)](https://pypi.org/project/mmcli-dl/)
[![License: MIT](https://img.shields.io/pypi/l/mmcli-dl)](LICENSE)

mmcli is a command-line YouTube downloader with built-in format conversion. Give
it a video or playlist URL and it downloads the media, optionally converting it
to the audio or video format you choose. Playlists are detected automatically and
saved into a per-playlist folder. Requires Python 3.12+ and FFmpeg on your `PATH`.

## Install

Install from PyPI with [pipx](https://pipx.pypa.io) or [uv](https://docs.astral.sh/uv/) (requires Python 3.12+). Both put the `mmcli` command on your `PATH` in its own isolated environment:

```
pipx install mmcli-dl        # or: uv tool install mmcli-dl
```

If `mmcli` is not found afterwards, run `pipx ensurepath` (or `uv tool update-shell`) and open a new terminal. Upgrade later with `pipx upgrade mmcli-dl` (or `uv tool upgrade mmcli-dl`).

Plain `pip install mmcli-dl` works inside a virtual environment. Many Linux distributions and Homebrew Python block global pip installs with an `externally-managed-environment` error, so use pipx or uv there.

Or download a standalone binary (no Python required) for your platform from the [latest release](https://github.com/rizukirr/mmcli/releases/latest), available for Linux, Windows and macOS (x86_64 and arm64). On Linux and macOS, rename it to `mmcli`, make it executable and move it onto your `PATH`:

```
chmod +x mmcli-v0.1.1-linux-x86_64
mv mmcli-v0.1.1-linux-x86_64 ~/.local/bin/mmcli
```

FFmpeg must be on your `PATH` for format conversion.

### Windows

pipx and uv install `mmcli.exe` into `%USERPROFILE%\.local\bin`. Run `pipx ensurepath` (or `uv tool update-shell`) once to add that folder to your user `PATH`, then open a new terminal. Plain `pip install mmcli-dl` is not blocked on Windows, but pip may place `mmcli.exe` in a `Scripts` folder that is not on `PATH`, and it prints a warning when that happens.

For the standalone binary, rename `mmcli-v0.1.1-windows-x86_64.exe` (or the arm64 build) to `mmcli.exe` and move it into a folder on your `PATH`. In PowerShell:

```powershell
$bin = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force $bin | Out-Null
Move-Item .\mmcli-v0.1.1-windows-x86_64.exe "$bin\mmcli.exe"
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$bin", "User")
```

Skip the last line if that folder is already on your `PATH`, for example after `pipx ensurepath`. The binary is not code signed, so SmartScreen may warn on first run. Choose More info, then Run anyway.

FFmpeg is not preinstalled on Windows. Install it with `winget install Gyan.FFmpeg`, which also puts it on `PATH`, then open a new terminal.

## Command

```
mmcli <url> [--resolution RES] [--format FMT] [--output-dir DIR]
```

| Argument | Short | Description |
|----------|-------|-------------|
| `url` | | YouTube video or playlist URL (required). |
| `--resolution` | `-r` | Video resolution, e.g. `720` or `720p`. Ignored for audio formats. Default: highest available. |
| `--format` | `-f` | Output format. An audio format (`mp3`, `m4a`, `wav`, ...) downloads audio only; a video format (`mp4`, `mkv`, `webm`, ...) converts the container. Default: keep the downloaded video as-is. |
| `--output-dir` | `-o` | Directory to save into. Default: current directory. |
| `--version` | `-v` | Print the version and exit. |

Examples:

```
mmcli "https://youtube.com/watch?v=..."                       # best-quality video
mmcli "https://youtube.com/watch?v=..." --resolution 720      # video at 720p
mmcli "https://youtube.com/watch?v=..." --format mp3          # audio only, as mp3
mmcli "https://youtube.com/watch?v=..." --format mkv          # video, converted to mkv
mmcli "https://youtube.com/playlist?list=..." --format mp3    # whole playlist as mp3
mmcli "https://youtube.com/watch?v=..." --output-dir ~/Videos # choose the output directory
```

## Supported `--format` values

An **audio** format downloads audio only; a **video** format downloads video and
converts the container.

- **Audio:** `mp3`, `wav`, `flac`, `aac`, `m4a`, `ogg`, `oga`, `opus`, `wma`, `alac`, `amr`, `ac3`, `dts`, `eac3`
- **Video:** `mp4`, `mkv`, `avi`, `mov`, `flv`, `webm`, `mpeg`, `mpg`, `ts`, `m2ts`, `ogv`, `3gp`, `3g2`, `vob`, `f4v`, `wmv`, `rm`, `rmvb`
