# YouTube Downloader Redesign Implementation Plan

> **For executing agents:** implement this plan task-by-task. Each step uses checkbox (`- [ ]`) syntax. Do not skip steps. Do not batch commits across tasks.

**Goal:** Narrow `mmcli` into a focused YouTube downloader with a flat positional-URL CLI (`mmcli <url> [--resolution] [--format] [--output-dir]`) and built-in post-download format conversion, removing image conversion, local-file conversion, the `convert` subcommand, and the `config.toml` system.

**Architecture:** In-place refactor (spec Approach A). Keep the existing module split — `youtube_downloader` (pytubefix wrappers), `media_converter` (ffmpeg engine, now internal-only), `media_downloader` (orchestration), `media_format` (format tables), `command_manager` (CLI). Replace the `config.py`/`config.toml` layer with a tiny `constants.py`. `--format` routes audio-vs-video: an audio alias means audio-only download; a video alias or no `--format` means video download.

**Tech stack:** Python 3.12+, `argparse`, `asyncio`, `pytubefix`, `ffmpeg-python`, `pytest` + `pytest-asyncio` (async auto-mode). Run tests with `uv run pytest`.

---

## Premortem

**Hidden assumptions:**
- The plan assumes `pytubefix`'s `get_by_resolution()` expects a `"720p"`-style string, but the spec's CLI passes `--resolution 720`. Mitigation: `media_downloader.normalize_resolution()` appends `"p"` when missing, covered by `test_normalize_resolution`.
- The plan assumes `media_converter.convert_files_functional` returns dicts with keys `input_file`/`output_file`/`success`/`format`. Mitigation: verified by reading the current `media_converter.py`; the conversion engine is kept unchanged and `test_media_converter.py` asserts these keys.
- The plan assumes the targeted-test runs (`uv run pytest tests/<one>.py`) collect only that file, so transient broken imports in not-yet-rewritten test files don't fail a task. Mitigation: pytest only collects the path passed on the CLI; the final task runs the full suite to catch cross-file breakage.

**Irreversible / risky steps:**
- Deletes `app/utils/config.py`, `config.toml`, `tests/test_playlist_downloader.py`, `doc/configuration.md`, and the empty `convert/` dir. Mitigation: each deletion is a separate commit revertible with `git revert`; the values from `config.py` are reproduced in `constants.py` in an earlier commit.

**Spec-misalignment:**
- Spec says playlist files go to `<output-dir>/<playlist-title>/`; the plan uses the live `Playlist.title`, falling back to the literal `"playlist"` when the title can't be fetched. Mitigation: `test_download_playlist` locks the subfolder behavior; the fallback only triggers on network/parse failure and is non-destructive.
- "Audio format ⇒ audio-only download" — the plan interprets *audio format* as any alias in `audio_formats`. Mitigation: `is_audio_format` + `test_is_audio_format` make the classification observable.

**Verify-clause weakness:**
- A "tests pass" clause could pass on a no-op. Mitigation: every test task names specific assertions (e.g. playlist subfolder created, conversion output extension is `mp3`, non-YouTube URL raises `SystemExit`), not just "file passes".

## File structure

New:
- `app/utils/constants.py` — `APP_VERSION`, `PLAYLIST_MAX_CONCURRENT`; replaces `config.py`.

Modified:
- `app/utils/media_format.py` — drop `image_formats`/`subtitle_formats`; add `is_audio_format`/`is_video_format`.
- `app/utils/command_manager.py` — flat positional-URL parser, no subcommands.
- `app/tools/media_converter.py` — remove CLI/glob surface (`convert`, `resolve_file_paths`, `validate_conversion_args`) and the `config` import; keep the ffmpeg engine.
- `app/tools/youtube_downloader.py` — remove the `*_parallel` backward-compat aliases.
- `app/tools/media_downloader.py` — rewritten orchestration (URL validation, audio/video routing, playlist subfolder, post-download conversion).
- `main.py` — single `download(args)` path.
- `app/__init__.py` — export only `download`, `command_manager`, and the remaining format tables.
- `pyproject.toml` — drop `pyyaml` dependency and the `config` optional-extra.
- `requirements.txt` — drop `PyYAML`.
- `tests/test_media_format.py`, `tests/test_command_manager.py`, `tests/test_media_converter.py`, `tests/test_media_downloader.py`, `tests/test_integration.py` — rewritten for the new API.
- `doc/commands.md`, `README.md`, `CLAUDE.md` — rewritten to the new surface.

Deleted:
- `app/utils/config.py`, `config.toml`, `tests/test_playlist_downloader.py`, `doc/configuration.md`, `convert/` (empty dir).

---

### Task 1: Constants module → verify: `python -c "from app.utils.constants import APP_VERSION, PLAYLIST_MAX_CONCURRENT"` exits 0

**Files:**
- Create: `app/utils/constants.py`

- [ ] **Step 1: Create the constants module**

```python
"""Hardcoded defaults for the few values dependencies don't provide."""

APP_VERSION = "0.1.0b1"

# pytubefix/ffmpeg provide quality defaults; only playlist fan-out needs a constant.
PLAYLIST_MAX_CONCURRENT = 3
```

- [ ] **Step 2: Verify it imports**

Run: `uv run python -c "from app.utils.constants import APP_VERSION, PLAYLIST_MAX_CONCURRENT; print(APP_VERSION, PLAYLIST_MAX_CONCURRENT)"`
Expected: prints `0.1.0b1 3`

- [ ] **Step 3: Commit**

```bash
git add app/utils/constants.py
git commit -m "$(cat <<'EOF'
feat: add constants module to replace config layer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Trim format tables + add classifiers → verify: `tests/test_media_format.py` passes; `media_format` has no `image_formats`/`subtitle_formats`

**Files:**
- Modify: `app/utils/media_format.py`
- Modify: `app/__init__.py`
- Test: `tests/test_media_format.py`

- [ ] **Step 1: Rewrite the test file**

Replace the entire contents of `tests/test_media_format.py` with:

```python
from app.utils.media_format import (
    video_formats,
    audio_formats,
    all_formats,
    get_format,
    is_audio_format,
    is_video_format,
)


def test_only_video_and_audio_in_all_formats():
    assert len(all_formats) == len(video_formats) + len(audio_formats)


def test_format_entries_structure():
    for f in all_formats:
        assert {"alias", "format", "desc"} <= set(f.keys())
        assert f["desc"].strip() != ""


def test_common_video_formats_exist():
    aliases = [f["alias"] for f in video_formats]
    for a in ["mp4", "mkv", "webm", "mov", "avi"]:
        assert a in aliases


def test_common_audio_formats_exist():
    aliases = [f["alias"] for f in audio_formats]
    for a in ["mp3", "m4a", "wav", "flac", "aac"]:
        assert a in aliases


def test_no_image_or_subtitle_tables():
    import app.utils.media_format as mf
    assert not hasattr(mf, "image_formats")
    assert not hasattr(mf, "subtitle_formats")


def test_get_format_by_alias():
    result = get_format("mp4")
    assert len(result) == 1
    assert result[0]["alias"] == "mp4"


def test_get_format_nonexistent():
    assert get_format("nope") == []


def test_is_audio_format():
    assert is_audio_format("mp3") is True
    assert is_audio_format("mp4") is False


def test_is_video_format():
    assert is_video_format("mkv") is True
    assert is_video_format("mp3") is False
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_media_format.py`
Expected: collection/import error or failures referencing `is_audio_format` / `is_video_format` not importable (they don't exist yet).

- [ ] **Step 3: Edit `app/utils/media_format.py`**

Delete the `image_formats = [...]` list (currently lines 39–55) and the `subtitle_formats = [...]` list (currently lines 57–65). Then change the `all_formats` line from:

```python
all_formats = video_formats + audio_formats + image_formats + subtitle_formats
```

to:

```python
all_formats = video_formats + audio_formats
```

Leave `video_formats`, `audio_formats`, and `get_format` unchanged. Append these two helpers at the end of the file:

```python
def is_audio_format(alias: str) -> bool:
    """True when alias names an audio output format."""
    return any(f["alias"] == alias for f in audio_formats)


def is_video_format(alias: str) -> bool:
    """True when alias names a video output format."""
    return any(f["alias"] == alias for f in video_formats)
```

- [ ] **Step 4: Update `app/__init__.py` so it stops importing removed names**

Replace the entire contents of `app/__init__.py` with:

```python
from .tools.media_downloader import download
from .utils.command_manager import command_manager
from .utils.media_format import all_formats, audio_formats, video_formats
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `uv run pytest tests/test_media_format.py`
Expected: PASS (all tests in the file).

- [ ] **Step 6: Commit**

```bash
git add app/utils/media_format.py app/__init__.py tests/test_media_format.py
git commit -m "$(cat <<'EOF'
refactor: trim format tables to video+audio, add format classifiers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Flat CLI parser → verify: `tests/test_command_manager.py` passes; `mmcli <url> -f mp3 -r 720 -o out` parses to a namespace

**Files:**
- Modify: `app/utils/command_manager.py`
- Test: `tests/test_command_manager.py`

- [ ] **Step 1: Rewrite the test file**

Replace the entire contents of `tests/test_command_manager.py` with:

```python
import sys
import pytest
from unittest.mock import patch
from app.utils.command_manager import command_manager


def run_with_argv(argv):
    with patch.object(sys, "argv", ["mmcli"] + argv):
        return command_manager()


def test_url_only():
    args = run_with_argv(["https://youtube.com/watch?v=x"])
    assert args.url == "https://youtube.com/watch?v=x"
    assert args.resolution is None
    assert args.format is None
    assert args.output_dir is None


def test_resolution():
    args = run_with_argv(["https://youtu.be/x", "--resolution", "720"])
    assert args.resolution == "720"


def test_format_audio():
    args = run_with_argv(["https://youtu.be/x", "--format", "mp3"])
    assert args.format == "mp3"


def test_output_dir():
    args = run_with_argv(["https://youtu.be/x", "--output-dir", "/tmp/out"])
    assert args.output_dir == "/tmp/out"


def test_short_flags():
    args = run_with_argv(["https://youtu.be/x", "-r", "1080p", "-f", "mkv", "-o", "out/"])
    assert args.resolution == "1080p"
    assert args.format == "mkv"
    assert args.output_dir == "out/"


def test_missing_url_exits():
    with pytest.raises(SystemExit):
        run_with_argv([])


def test_invalid_format_exits():
    with pytest.raises(SystemExit):
        run_with_argv(["https://youtu.be/x", "--format", "exe"])


def test_version_exits_zero():
    with pytest.raises(SystemExit) as exc:
        run_with_argv(["--version"])
    assert exc.value.code == 0
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_command_manager.py`
Expected: failures — the current parser uses `download`/`convert` subcommands, so `args.url` is unset and at least one new test fails with an `AttributeError` or `SystemExit`.

- [ ] **Step 3: Rewrite `app/utils/command_manager.py`**

Replace the entire contents with:

```python
import argparse
from .media_format import all_formats
from .constants import APP_VERSION


def command_manager():
    epilog_text = """
    Examples:
        mmcli "https://youtube.com/watch?v=..."                      # best-quality video
        mmcli "https://youtube.com/watch?v=..." --resolution 720     # video at 720p
        mmcli "https://youtube.com/watch?v=..." --format mp3         # audio only, as mp3
        mmcli "https://youtube.com/watch?v=..." --format mkv         # video as mkv
        mmcli "https://youtube.com/playlist?list=..." --format mp3   # whole playlist as mp3
        mmcli "<url>" --output-dir ~/Downloads                       # choose a directory
    """
    parser = argparse.ArgumentParser(
        prog="mmcli",
        description="YouTube downloader with format conversion",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"mmcli {APP_VERSION}"
    )
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument(
        "--resolution",
        "-r",
        help="Video resolution, e.g. 720 or 720p (ignored for audio formats)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=[f["alias"] for f in all_formats],
        help="Output format. An audio format (mp3, m4a, ...) downloads audio only; "
        "a video format converts the container.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        dest="output_dir",
        help="Output directory (default: current directory)",
    )

    return parser.parse_args()
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `uv run pytest tests/test_command_manager.py`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add app/utils/command_manager.py tests/test_command_manager.py
git commit -m "$(cat <<'EOF'
refactor: flat positional-URL CLI, drop download/convert subcommands

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Simplify entry point → verify: `tests/test_integration.py` passes; `main.main()` awaits `download(args)` once

**Files:**
- Modify: `main.py`
- Test: `tests/test_integration.py`

- [ ] **Step 1: Rewrite the integration test**

Replace the entire contents of `tests/test_integration.py` with:

```python
from unittest.mock import patch, AsyncMock, MagicMock
import main


def test_main_invokes_download():
    mock_args = MagicMock()
    with patch("main.command_manager", return_value=mock_args) as mock_cm, \
         patch("main.download", new=AsyncMock(return_value={"success": True})) as mock_dl:
        main.main()
        mock_cm.assert_called_once()
        mock_dl.assert_awaited_once_with(mock_args)


def test_main_handles_keyboard_interrupt(capsys):
    with patch("main.command_manager", side_effect=KeyboardInterrupt):
        main.main()
    out = capsys.readouterr().out
    assert "cancelled" in out.lower()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_integration.py`
Expected: failure — current `main._async_main` branches on `args.command`, so `download` is not awaited unconditionally and `test_main_invokes_download` fails (`download` not awaited with `mock_args`).

- [ ] **Step 3: Rewrite `main.py`**

Replace the entire contents with:

```python
import asyncio
from app import download, command_manager


async def _async_main():
    """Parse arguments and run the download."""
    args = command_manager()
    await download(args)


def main():
    """CLI entry point: run the async download pipeline."""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `uv run pytest tests/test_integration.py`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_integration.py
git commit -m "$(cat <<'EOF'
refactor: single download path in entry point

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Strip local-file surface from converter → verify: `tests/test_media_converter.py` passes; `media_converter` has no `convert`/`resolve_file_paths`/`validate_conversion_args`

**Files:**
- Modify: `app/tools/media_converter.py`
- Test: `tests/test_media_converter.py`

- [ ] **Step 1: Rewrite the test file**

Replace the entire contents of `tests/test_media_converter.py` with:

```python
from pathlib import Path
import pytest
from app.tools import media_converter as mc


def test_find_ffmpeg_format_known():
    assert mc.find_ffmpeg_format("mp3") == "mp3"
    assert mc.find_ffmpeg_format("mkv") == "matroska"


def test_find_ffmpeg_format_unknown():
    assert mc.find_ffmpeg_format("nope") is None


def test_generate_output_filename_has_extension():
    name = mc.generate_output_filename(Path("clip.mov"), "mp4")
    assert name.startswith("clip_")
    assert name.endswith(".mp4")


def test_create_conversion_config(tmp_path):
    cfg = mc.create_conversion_config(Path("a.mov"), "mp4", tmp_path)
    assert cfg["ffmpeg_format"] == "mp4"
    assert cfg["output_format"] == "mp4"
    assert str(cfg["output_path"]).endswith(".mp4")


def test_calculate_conversion_stats():
    results = [{"success": True}, {"success": True}, {"success": False}]
    assert mc.calculate_conversion_stats(results) == {"total": 3, "success": 2, "failed": 1}


def test_format_conversion_summary_mentions_counts():
    summary = mc.format_conversion_summary({"success": 2, "failed": 1}, "mp4", "/out")
    assert "Successfully converted: 2" in summary
    assert "Failed to convert: 1" in summary


def test_local_file_surface_removed():
    assert not hasattr(mc, "convert")
    assert not hasattr(mc, "resolve_file_paths")
    assert not hasattr(mc, "validate_conversion_args")


@pytest.mark.asyncio
async def test_execute_ffmpeg_conversion_unsupported_format(tmp_path):
    config = {
        "ffmpeg_format": None,
        "output_format": "xyz",
        "input_file": tmp_path / "a.mov",
        "output_path": tmp_path / "a.xyz",
    }
    assert await mc.execute_ffmpeg_conversion(config) is False


@pytest.mark.asyncio
async def test_convert_single_file_functional_success(monkeypatch, tmp_path):
    async def fake_exec(config):
        return True

    monkeypatch.setattr(mc, "execute_ffmpeg_conversion", fake_exec)
    result = await mc.convert_single_file_functional(Path("a.mov"), "mp4", tmp_path)
    assert result["success"] is True
    assert result["output_file"].endswith(".mp4")
    assert result["format"] == "mp4"
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_media_converter.py`
Expected: `test_local_file_surface_removed` fails (the `convert`/`resolve_file_paths`/`validate_conversion_args` attributes still exist).

- [ ] **Step 3: Edit `app/tools/media_converter.py`**

Change the import block at the top from:

```python
import asyncio
import ffmpeg
import os
import textwrap
import sys
from pathlib import Path
from glob import glob
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import reduce
from ..utils.media_format import all_formats
from ..utils.config import get_max_workers_default
```

to:

```python
import asyncio
import ffmpeg
import os
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import reduce
from ..utils.media_format import all_formats
```

Then delete these three functions entirely:
- `resolve_file_paths(input_pattern)` (currently lines 15–27)
- `validate_conversion_args(args)` (currently lines 224–241)
- `convert(args)` (currently lines 244–259, the last function in the file)

Keep everything else unchanged (`ensure_output_directory`, `generate_output_filename`, `create_output_path`, `find_ffmpeg_format`, `create_conversion_config`, `execute_ffmpeg_conversion`, `convert_single_file_functional`, `process_conversion_batch`, `calculate_conversion_stats`, `format_conversion_summary`, `print_conversion_results`, `convert_files_functional`).

- [ ] **Step 4: Run the test to confirm it passes**

Run: `uv run pytest tests/test_media_converter.py`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add app/tools/media_converter.py tests/test_media_converter.py
git commit -m "$(cat <<'EOF'
refactor: make media_converter an internal-only ffmpeg engine

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Remove backward-compat aliases → verify: `python -c "import app.tools.youtube_downloader as y; assert not hasattr(y, 'download_playlist_videos_parallel')"` exits 0

**Files:**
- Modify: `app/tools/youtube_downloader.py`

- [ ] **Step 1: Delete the alias block**

In `app/tools/youtube_downloader.py`, delete everything from the comment line `# Async aliases for backward compatibility` to the end of the file (currently lines 222–243), i.e. remove both `download_playlist_videos_parallel` and `download_playlist_audios_parallel`. The file should now end with the `validate_youtube_url` function.

- [ ] **Step 2: Verify the aliases are gone and the module still imports**

Run: `uv run python -c "import app.tools.youtube_downloader as y; assert not hasattr(y, 'download_playlist_videos_parallel'); assert not hasattr(y, 'download_playlist_audios_parallel'); assert hasattr(y, 'validate_youtube_url'); print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add app/tools/youtube_downloader.py
git commit -m "$(cat <<'EOF'
refactor: drop unused playlist parallel aliases

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Rewrite download orchestration + delete config → verify: `tests/test_media_downloader.py` passes; non-YouTube URL raises `SystemExit`; playlist creates `<out>/<title>/`

**Files:**
- Modify: `app/tools/media_downloader.py`
- Create/replace: `tests/test_media_downloader.py`
- Delete: `tests/test_playlist_downloader.py`, `app/utils/config.py`, `config.toml`

- [ ] **Step 1: Rewrite the test file**

Replace the entire contents of `tests/test_media_downloader.py` with:

```python
from types import SimpleNamespace
import pytest
from app.tools import media_downloader as md


def test_resolve_output_dir_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    args = SimpleNamespace(output_dir=None)
    assert md.resolve_output_dir(args) == str(tmp_path)


def test_resolve_output_dir_explicit(tmp_path):
    args = SimpleNamespace(output_dir=str(tmp_path))
    assert md.resolve_output_dir(args) == str(tmp_path)


def test_extract_file_extension():
    assert md.extract_file_extension("/a/b/video.MP4") == "mp4"
    assert md.extract_file_extension("song.mp3") == "mp3"


def test_should_convert():
    assert md.should_convert("m4a", "mp3") is True
    assert md.should_convert("mp3", "mp3") is False
    assert md.should_convert("mp4", None) is False


def test_normalize_resolution():
    assert md.normalize_resolution("720") == "720p"
    assert md.normalize_resolution("720p") == "720p"
    assert md.normalize_resolution(None) is None


def test_calculate_success_stats():
    results = [{"success": True}, {"success": False}, {"success": True}]
    assert md.calculate_success_stats(results) == {"total": 3, "success": 2, "failed": 1}


@pytest.mark.asyncio
async def test_download_rejects_non_youtube(monkeypatch):
    monkeypatch.setattr(
        md.youtube_downloader,
        "validate_youtube_url",
        lambda u: {"is_valid": False, "is_playlist": False},
    )
    args = SimpleNamespace(
        url="https://example.com/x", resolution=None, format=None, output_dir=None
    )
    with pytest.raises(SystemExit):
        await md.download(args)


@pytest.mark.asyncio
async def test_download_single_video_no_conversion(monkeypatch, tmp_path):
    async def fake_video(url, output_path, resolution=None):
        return {
            "success": True,
            "file_path": str(tmp_path / "v.mp4"),
            "metadata": {"title": "V"},
        }

    monkeypatch.setattr(
        md.youtube_downloader,
        "validate_youtube_url",
        lambda u: {"is_valid": True, "is_playlist": False},
    )
    monkeypatch.setattr(md.youtube_downloader, "download_single_video", fake_video)
    args = SimpleNamespace(
        url="https://youtube.com/watch?v=x",
        resolution=None,
        format=None,
        output_dir=str(tmp_path),
    )
    result = await md.download(args)
    assert result["success"] is True
    assert result["title"] == "V"
    assert result["format"] == "mp4"


@pytest.mark.asyncio
async def test_download_audio_triggers_conversion(monkeypatch, tmp_path):
    async def fake_audio(url, output_path):
        return {
            "success": True,
            "file_path": str(tmp_path / "a.m4a"),
            "metadata": {"title": "A"},
        }

    async def fake_convert(input_files, output_format, output_dir=None, max_workers=1):
        return [
            {
                "input_file": str(input_files[0]),
                "output_file": str(tmp_path / "a.mp3"),
                "success": True,
                "format": output_format,
            }
        ]

    monkeypatch.setattr(
        md.youtube_downloader,
        "validate_youtube_url",
        lambda u: {"is_valid": True, "is_playlist": False},
    )
    monkeypatch.setattr(md.youtube_downloader, "download_single_audio", fake_audio)
    monkeypatch.setattr(md.media_converter, "convert_files_functional", fake_convert)
    monkeypatch.setattr(md.os, "remove", lambda p: None)
    args = SimpleNamespace(
        url="https://youtube.com/watch?v=x",
        resolution=None,
        format="mp3",
        output_dir=str(tmp_path),
    )
    result = await md.download(args)
    assert result["success"] is True
    assert result["file_path"].endswith("a.mp3")
    assert result["format"] == "mp3"


@pytest.mark.asyncio
async def test_download_playlist(monkeypatch, tmp_path):
    class FakePlaylist:
        title = "MyList"

    async def fake_playlist_videos(url, output_path, resolution=None, max_concurrent=3):
        return [
            {"success": True, "file_path": str(tmp_path / "1.mp4"), "metadata": {"title": "one"}},
            {"success": False, "file_path": None, "metadata": {"title": "two", "error": "boom"}},
        ]

    monkeypatch.setattr(
        md.youtube_downloader,
        "validate_youtube_url",
        lambda u: {"is_valid": True, "is_playlist": True},
    )
    monkeypatch.setattr(
        md.youtube_downloader, "create_playlist_instance", lambda u: FakePlaylist()
    )
    monkeypatch.setattr(
        md.youtube_downloader, "download_playlist_videos", fake_playlist_videos
    )
    args = SimpleNamespace(
        url="https://youtube.com/playlist?list=x",
        resolution=None,
        format=None,
        output_dir=str(tmp_path),
    )
    results = await md.download(args)
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["success"] is True and results[0]["title"] == "one"
    assert results[1]["success"] is False
    assert (tmp_path / "MyList").is_dir()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_media_downloader.py`
Expected: failures/errors — the new helpers (`resolve_output_dir`, `normalize_resolution`, etc.) and the rewritten `download` signature don't exist yet.

- [ ] **Step 3: Rewrite `app/tools/media_downloader.py`**

Replace the entire contents with:

```python
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import reduce
from ..utils.media_format import is_audio_format
from ..utils.constants import PLAYLIST_MAX_CONCURRENT
from . import media_converter
from . import youtube_downloader


def resolve_output_dir(args) -> str:
    """Resolve the base output directory, defaulting to the current directory."""
    target = getattr(args, "output_dir", None)
    return os.path.abspath(target) if target else os.getcwd()


def ensure_directory_exists(path: str) -> str:
    """Create the directory if missing and return it."""
    os.makedirs(path, exist_ok=True)
    return path


def normalize_resolution(resolution: Optional[str]) -> Optional[str]:
    """Normalize '720' -> '720p' for pytubefix; pass through None and '720p'."""
    if not resolution:
        return None
    return resolution if resolution.endswith("p") else f"{resolution}p"


def extract_file_extension(filepath: str) -> str:
    """Return the lowercased extension without the leading dot."""
    return os.path.splitext(filepath)[1][1:].lower()


def should_convert(current_ext: str, target_format: Optional[str]) -> bool:
    """True when a non-empty target format differs from the current extension."""
    if not target_format:
        return False
    return current_ext.lower() != target_format.lower()


async def convert_downloaded_file(downloaded_file: str, target_format: str) -> str:
    """Convert one downloaded file in place; remove the original on success."""
    results = await media_converter.convert_files_functional(
        [Path(downloaded_file)],
        target_format,
        output_dir=os.path.dirname(downloaded_file),
    )
    if results and results[0]["success"]:
        try:
            os.remove(downloaded_file)
        except OSError:
            pass
        return results[0]["output_file"]
    print(f"Failed to convert {downloaded_file}")
    return downloaded_file


def resolve_playlist_output(base_dir: str, url: str) -> str:
    """Return <base_dir>/<playlist-title>/, falling back to 'playlist'."""
    try:
        playlist = youtube_downloader.create_playlist_instance(url)
        title = playlist.title
    except Exception:
        title = "playlist"
    return ensure_directory_exists(os.path.join(base_dir, title))


def _finalize_single(result: Dict[str, Any], converted_path: str) -> Dict[str, Any]:
    """Build the user-facing result dict for a single download."""
    return {
        "success": True,
        "title": result["metadata"]["title"],
        "file_path": converted_path,
        "format": extract_file_extension(converted_path),
    }


def _failed(result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a failure result dict from a download result."""
    return {
        "success": False,
        "title": result["metadata"].get("title", "Unknown"),
        "error": result["metadata"].get("error", "Download failed"),
    }


async def _download_single(
    url: str, output_path: str, audio_only: bool, resolution, target_format
) -> Dict[str, Any]:
    if audio_only:
        result = await youtube_downloader.download_single_audio(url, output_path)
    else:
        result = await youtube_downloader.download_single_video(
            url, output_path, resolution
        )

    if not result["success"]:
        return _failed(result)

    file_path = result["file_path"]
    if target_format and should_convert(extract_file_extension(file_path), target_format):
        file_path = await convert_downloaded_file(file_path, target_format)
    return _finalize_single(result, file_path)


async def _download_playlist(
    url: str, output_path: str, audio_only: bool, resolution, target_format
) -> List[Dict[str, Any]]:
    if audio_only:
        results = await youtube_downloader.download_playlist_audios(
            url, output_path, max_concurrent=PLAYLIST_MAX_CONCURRENT
        )
    else:
        results = await youtube_downloader.download_playlist_videos(
            url, output_path, resolution, max_concurrent=PLAYLIST_MAX_CONCURRENT
        )
    return await _finalize_playlist(results, target_format)


async def _finalize_playlist(
    results: List[Dict[str, Any]], target_format: Optional[str]
) -> List[Dict[str, Any]]:
    downloaded = [r["file_path"] for r in results if r["success"] and r["file_path"]]
    conversion_map: Dict[str, Dict[str, Any]] = {}

    if target_format:
        to_convert = [
            f for f in downloaded
            if should_convert(extract_file_extension(f), target_format)
        ]
        if to_convert:
            conv_results = await media_converter.convert_files_functional(
                [Path(f) for f in to_convert],
                target_format,
                output_dir=os.path.dirname(to_convert[0]),
                max_workers=PLAYLIST_MAX_CONCURRENT,
            )
            for i, cr in enumerate(conv_results):
                if cr["success"]:
                    try:
                        os.remove(to_convert[i])
                    except OSError:
                        pass
                conversion_map[cr["input_file"]] = cr

    processed = []
    for r in results:
        if not r["success"]:
            processed.append(_failed(r))
            continue
        file_path = r["file_path"]
        cr = conversion_map.get(file_path)
        final_path = cr["output_file"] if cr and cr["success"] else file_path
        processed.append(_finalize_single(r, final_path))
    return processed


def calculate_success_stats(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Tally total/success/failed across a list of result dicts."""
    return reduce(
        lambda acc, r: {
            "total": acc["total"] + 1,
            "success": acc["success"] + (1 if r["success"] else 0),
            "failed": acc["failed"] + (0 if r["success"] else 1),
        },
        results,
        {"total": 0, "success": 0, "failed": 0},
    )


def print_summary(results) -> None:
    """Print a human-readable summary for single or playlist results."""
    if isinstance(results, list):
        stats = calculate_success_stats(results)
        print("Download Summary:")
        print(f"- Total items: {stats['total']}")
        print(f"- Successfully downloaded: {stats['success']}")
        print(f"- Failed: {stats['failed']}")
    elif results.get("success"):
        print(f"Done: {results.get('title', '')}")
    else:
        print(f"Failed: {results.get('error', 'Download failed')}")


async def download(args):
    """Download a YouTube URL (single or playlist), converting to --format if given."""
    url = args.url
    validation = youtube_downloader.validate_youtube_url(url)
    if not validation["is_valid"]:
        print(f"Error: Unsupported URL: {url}. Only YouTube URLs are supported.")
        sys.exit(1)

    target_format = getattr(args, "format", None)
    audio_only = target_format is not None and is_audio_format(target_format)
    resolution = normalize_resolution(getattr(args, "resolution", None))
    base_dir = resolve_output_dir(args)

    try:
        if validation["is_playlist"]:
            output_path = resolve_playlist_output(base_dir, url)
            results = await _download_playlist(
                url, output_path, audio_only, resolution, target_format
            )
        else:
            output_path = ensure_directory_exists(base_dir)
            results = await _download_single(
                url, output_path, audio_only, resolution, target_format
            )
        print_summary(results)
        return results
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
```

- [ ] **Step 4: Delete the obsolete config + playlist test files**

```bash
git rm app/utils/config.py config.toml tests/test_playlist_downloader.py
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `uv run pytest tests/test_media_downloader.py`
Expected: PASS (all tests, including `test_download_playlist` asserting the `MyList` subfolder exists).

- [ ] **Step 6: Run the full suite to confirm nothing else broke**

Run: `uv run pytest`
Expected: PASS — all collected tests across `tests/` pass (coverage report prints; collection no longer references `config`, `convert`, or image/subtitle formats).

- [ ] **Step 7: Commit**

```bash
git add app/tools/media_downloader.py tests/test_media_downloader.py
git commit -m "$(cat <<'EOF'
refactor: rewrite orchestration for flat URL CLI; remove config layer

Route audio-vs-video on --format, auto-detect playlists into a
title subfolder, convert downloaded media in place, and delete the
config.toml system in favor of constants.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Prune dependencies → verify: `grep -ri pyyaml pyproject.toml requirements.txt` returns nothing; `uv sync` succeeds

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Edit `pyproject.toml`**

In the `[project]` `dependencies` array, delete the `"pyyaml>=6.0",` line. Then delete the entire `config` optional-dependency group so this block:

```toml
[project.optional-dependencies]
test = [
    "pytest>=9.0",
    "pytest-cov>=7.0",
    "pytest-asyncio>=1.0",
]
config = [
    "PyYAML>=6.0",
]
```

becomes:

```toml
[project.optional-dependencies]
test = [
    "pytest>=9.0",
    "pytest-cov>=7.0",
    "pytest-asyncio>=1.0",
]
```

- [ ] **Step 2: Edit `requirements.txt`**

Replace the entire contents with:

```
ffmpeg-python>=0.2.0
pytubefix>=10.10.1
pytest>=9.0
pytest-cov>=7.0
pytest-asyncio>=1.0
```

- [ ] **Step 3: Verify PyYAML is gone and the env still resolves**

Run: `grep -ri pyyaml pyproject.toml requirements.txt; echo "exit=$?"`
Expected: no matching lines; `echo` prints `exit=1` (grep found nothing).

Run: `uv sync`
Expected: completes successfully (lockfile resolves without PyYAML).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml requirements.txt uv.lock
git commit -m "$(cat <<'EOF'
chore: drop PyYAML dependency and config extra

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Update docs and remove stale dirs → verify: full suite passes; `doc/configuration.md` and `convert/` are gone; README shows the flat CLI

**Files:**
- Replace: `doc/commands.md`
- Replace: `README.md`
- Replace: `CLAUDE.md`
- Delete: `doc/configuration.md`, `convert/` (empty dir)

- [ ] **Step 1: Replace `doc/commands.md`**

Replace the entire contents of `doc/commands.md` with:

```markdown
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
```

- [ ] **Step 2: Replace `README.md`**

Replace the entire contents of `README.md` with:

```markdown
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
```

- [ ] **Step 3: Replace `CLAUDE.md`**

Replace the entire contents of `CLAUDE.md` with:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`mmcli` is a Python 3.12+ **YouTube downloader** with built-in format conversion.
It exposes one flat command: a positional YouTube URL plus optional
`--resolution`, `--format`, and `--output-dir` flags. External requirement:
**FFmpeg must be on `PATH`** for conversion.

## Commands

```bash
uv sync                      # install deps (uv.lock is committed)
uv sync --extra test         # install with test extras
uv run mmcli --help          # run installed CLI

python main.py "<url>" --format mp3   # run from source

uv run pytest                                   # full suite with coverage
uv run pytest tests/test_media_downloader.py    # single file
uv run pytest tests/test_x.py::test_name        # single test
uv run pytest -k "playlist"                      # by keyword
uv run pytest tests/test_x.py --no-cov           # skip coverage for a quick run
```

`pytest.ini` forces `--cov=app` and HTML coverage on every default run via
`addopts`. There is no linter/formatter configured.

## Architecture

Async + functional style: functions are mostly pure and pass dict "result
objects" rather than mutating shared state. Blocking I/O (pytubefix downloads,
ffmpeg) runs in `loop.run_in_executor(...)`; playlist concurrency is bounded by
`asyncio.Semaphore` (not thread pools).

**Entry flow:** `main.py` (`asyncio.run`) → `command_manager()` parses argv →
`download(args)`. Public surface is re-exported in `app/__init__.py`.

**Layers:**
- `app/utils/command_manager.py` — flat argparse parser: positional `url`,
  `--resolution`/`-r`, `--format`/`-f` (choices from `media_format.all_formats`),
  `--output-dir`/`-o`, `--version`/`-v`.
- `app/utils/constants.py` — `APP_VERSION`, `PLAYLIST_MAX_CONCURRENT`. There is
  no config file; these are the only hardcoded knobs.
- `app/utils/media_format.py` — `video_formats` + `audio_formats` tables mapping
  a user `alias` (e.g. `mkv`) to the ffmpeg container `format` (e.g. `matroska`).
  `is_audio_format()`/`is_video_format()` classify a `--format` value; adding a
  format = adding a row.
- `app/tools/youtube_downloader.py` — pytubefix wrappers + `validate_youtube_url()`
  (a URL is a playlist when it contains `list=`). No config/conversion knowledge.
- `app/tools/media_downloader.py` — orchestration. Validates the URL, routes
  audio-vs-video on `--format`, resolves output paths (single → output-dir;
  playlist → `<output-dir>/<playlist-title>/`), and converts downloaded files
  in place when `--format` differs from the downloaded extension.
- `app/tools/media_converter.py` — ffmpeg engine, **internal only** (no CLI/glob
  surface). `convert_files_functional()` is the reusable batch entry point.

**Conventions:**
- `--format` routing: audio alias → audio-only download; video alias or none →
  video download. `normalize_resolution()` turns `720` into `720p` for pytubefix.
- Async operations return `{"success": bool, ...}` dicts (or lists of them).
  `asyncio.gather(..., return_exceptions=True)` converts exceptions into
  `success: False` results — check `result["success"]`, don't rely on raising.
- Keep new logic pure/functional; wrap blocking calls in `run_in_executor` and
  bound playlist concurrency with `PLAYLIST_MAX_CONCURRENT`.

## Scope (intentional non-goals)

No local-file conversion, no image/subtitle conversion, no non-YouTube sources,
no persistent config file. This tool is YouTube download + post-download
conversion only.
```

- [ ] **Step 4: Delete stale doc and empty dir**

```bash
git rm doc/configuration.md
rmdir convert 2>/dev/null || true
```

(The `convert/` directory is untracked and empty; `rmdir` removes it if present, and the `|| true` keeps the step from failing if it's already gone.)

- [ ] **Step 5: Run the full suite one last time**

Run: `uv run pytest`
Expected: PASS — entire suite green.

- [ ] **Step 6: Confirm removals**

Run: `test ! -e doc/configuration.md && test ! -e convert && test ! -e config.toml && test ! -e app/utils/config.py && echo "all removed"`
Expected: prints `all removed`

- [ ] **Step 7: Commit**

```bash
git add README.md CLAUDE.md doc/commands.md
git add -A doc/
git commit -m "$(cat <<'EOF'
docs: rewrite README, CLAUDE, and command reference for the YouTube-only CLI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Done criteria

- `uv run pytest` passes with the rewritten suite.
- `mmcli <url>` downloads video; `--format mp3` downloads audio; `--format mkv`
  converts the container; `--resolution 720` selects 720p; `--output-dir`
  controls the destination (default cwd); playlist URLs download into a
  title subfolder.
- `config.toml`, `config.py`, image/subtitle conversion, the `convert`
  subcommand, local-file conversion, and `PyYAML` are gone.
