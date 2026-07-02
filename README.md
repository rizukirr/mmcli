# mmcli

mmcli is a command-line YouTube downloader with built-in format conversion. Give
it a video or playlist URL and it downloads the media, optionally converting it
to the audio or video format you choose. Playlists are detected automatically and
saved into a per-playlist folder. Requires Python 3.12+ and FFmpeg on your `PATH`.

## Install

```
pip install mmcli-dl      # or: pipx install mmcli-dl / uv tool install mmcli-dl
```

The installed command is `mmcli`. FFmpeg must be on your `PATH` for format conversion.

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
