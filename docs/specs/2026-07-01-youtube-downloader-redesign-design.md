---
title: youtube-downloader-redesign
date: 2026-07-01
status: draft
---

# YouTube Downloader Redesign — Design

## Problem

`mmcli` today is a general multimedia tool with two subcommands (`download
video|audio`, `convert`) plus image/subtitle conversion of arbitrary local
files, and a `config.toml` system. The surface is larger than what's actually
wanted. The goal is to narrow `mmcli` into a focused **YouTube downloader** with
a flat, positional-URL CLI and built-in format conversion of the downloaded
media, and to remove everything outside that scope.

## Goals

- Flat CLI driven by a single positional YouTube URL:
  - `mmcli <url>` → download best-quality video.
  - `mmcli <url> --resolution 720` → download video at that resolution.
  - `mmcli <url> --format mp3` → download audio only, converted to mp3.
  - `mmcli <url> --format mp4` → download video, converted to that container if needed.
  - `mmcli <url> --output-dir <path>` → save location (default: current working directory).
- Auto-detect playlists from the URL (`list=`) and download every item
  concurrently; no extra flag.
- `--format` decides video-vs-audio: an audio format (mp3, m4a, wav, flac, …)
  means audio-only download; a video format (mp4, mkv, webm, …) or no `--format`
  means video download.
- Remove `config.toml` and replace its values with a small `constants.py`.
- Remove image conversion, subtitle handling, and standalone local-file
  conversion. Keep ffmpeg conversion only as an internal post-download step.

## Non-goals

- No local-file conversion (`mmcli <path>` is out of scope).
- No image or subtitle conversion.
- No "rich extraction" beyond audio (no thumbnail/metadata/subtitle extraction).
- No persistent user config file.
- No non-YouTube sources.
- No new flags beyond `--resolution`, `--format`, `--output-dir` (and `--version`/`--help`).

## Constraints

- Python 3.12+. FFmpeg must be on `PATH` for conversion.
- Keep the existing async + functional style and the separation between
  downloading (`youtube_downloader`) and transcoding (`media_converter`).
- pytubefix provides best-video (`get_highest_resolution()`) and best-audio
  (`get_audio_only()`) defaults; rely on those rather than reimplementing.
- Approach A (in-place refactor): smallest safe diff, preserve tested internals.

## Approach

In-place refactor of the existing module layout, with dead code removed.

### CLI (`app/utils/command_manager.py`)

Rewrite to a single flat `argparse` parser — no subparsers:

- positional `url` (required)
- `--resolution` / `-r` (optional; ignored for audio formats)
- `--format` / `-f` (optional; choices = audio+video aliases from `media_format`)
- `--output-dir` / `-o` (optional; default = cwd)
- `--version` / `-v`, `--help`

Returns the parsed `args` namespace (`url`, `resolution`, `format`, `output_dir`).

### Constants (`app/utils/constants.py`, new — replaces `config.py`)

Holds the few values not provided by libraries:

- `PLAYLIST_MAX_CONCURRENT = 3`
- `APP_VERSION = "0.1.0b1"` (sourced for `--version`)
- default output dir = cwd (resolved at runtime, not a constant path)

`app/utils/config.py` and the root `config.toml` are deleted.

### Format tables (`app/utils/media_format.py`)

Keep `video_formats` and `audio_formats` only. Delete `image_formats`,
`subtitle_formats`. `all_formats = video_formats + audio_formats`. A helper
distinguishes audio vs video aliases so the downloader can route on `--format`.

### Download orchestration (`app/tools/media_downloader.py`)

Rewrite `download(args)` to:

1. Validate the URL is YouTube (`youtube_downloader.validate_youtube_url`);
   error out otherwise.
2. Classify `--format`: audio format → audio path; video format or `None` →
   video path. (Resolution applies only to the video path.)
3. Resolve output dir: `args.output_dir or cwd`. For a playlist, append the
   playlist title as a subfolder: `<output-dir>/<playlist-title>/`. For a single
   video, files go directly into `<output-dir>`.
4. Dispatch to single vs playlist download (playlist auto-detected via `list=`),
   using `PLAYLIST_MAX_CONCURRENT` for playlist concurrency.
5. After download, if `--format` is set and differs from the downloaded file's
   extension, convert via `media_converter` (single or batch), deleting the
   original on success. Audio formats always trigger conversion from the native
   audio stream unless the native extension already matches.
6. Print a summary (reuse existing summary/stats helpers).

### Conversion engine (`app/tools/media_converter.py`)

Keep the ffmpeg execution and batch helpers
(`convert_single_file_functional`, `convert_files_functional`,
`process_conversion_batch`, stats/summary). Delete the CLI/local-file surface:
`convert(args)`, `resolve_file_paths()` (glob), `validate_conversion_args()`.
Conversion now only operates on freshly downloaded local files.

### YouTube wrappers (`app/tools/youtube_downloader.py`)

Keep the core single/playlist video/audio download functions and URL
validation. Delete the backward-compat `*_parallel` aliases.

### Entry + exports

- `main.py`: `asyncio.run` a single `download(args)` path; drop the
  download/convert dispatch.
- `app/__init__.py`: export only `download`, `command_manager`, and the
  remaining format tables. Drop `convert`, image format exports.

### Removals summary

- Files deleted: `app/utils/config.py`, `config.toml`, empty `convert/` dir.
- Dependency removed: `PyYAML` and the `config` optional-extra in
  `pyproject.toml`; `PyYAML` removed from `requirements.txt`.
- Docs: delete `doc/configuration.md`; update `doc/commands.md`, `README.md`,
  `CLAUDE.md` to the new surface.
- Tests: remove convert/image/config tests; update command-manager, downloader,
  playlist, and integration tests to the flat CLI.

## Alternatives considered

- **B — Refactor + consolidate** (fold `media_converter` into
  `media_downloader`): fewer files but merges downloading and transcoding, two
  cleanly separable concerns, and makes conversion harder to test in isolation.
  Rejected to preserve unit boundaries.
- **C — Clean rewrite** from scratch: most churn, discards working/tested
  download and conversion internals for an already-small codebase. Rejected as
  wasteful and higher-risk.

## Testing

- `command_manager`: positional URL parsing; `--resolution`, `--format`,
  `--output-dir` defaults and values; invalid `--format` choice rejected;
  missing URL rejected.
- Format routing: audio alias → audio download path; video alias / no format →
  video path; resolution ignored for audio.
- Output paths: single video → output-dir; playlist → output-dir/<title>/;
  default output-dir = cwd.
- URL validation: non-YouTube URL errors; playlist URL (`list=`) routes to
  playlist download.
- Conversion: skipped when downloaded extension already matches `--format`;
  invoked and original removed when it differs (mocked ffmpeg).
- Integration: `main()` dispatches to `download` for a URL (pytubefix/ffmpeg
  mocked).
- All tests run under existing pytest async-auto config; ffmpeg/pytubefix are
  mocked so no network or binary is needed.

## Open questions

None.
