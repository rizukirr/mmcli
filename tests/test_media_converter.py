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
    assert mc.calculate_conversion_stats(results) == {
        "total": 3,
        "success": 2,
        "failed": 1,
    }


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


@pytest.mark.asyncio
async def test_convert_files_functional_missing_ffmpeg(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("shutil.which", lambda name: None)
    results = await mc.convert_files_functional([Path("a.mov")], "mp3", str(tmp_path))
    assert results == [
        {
            "input_file": "a.mov",
            "output_file": None,
            "success": False,
            "format": "mp3",
            "error": "ffmpeg not found",
        }
    ]
    out = capsys.readouterr().out
    assert "FFmpeg not found on PATH" in out
    assert "https://ffmpeg.org/download.html" in out


@pytest.mark.asyncio
async def test_convert_files_functional_ffmpeg_present_no_short_circuit(
    monkeypatch, tmp_path
):
    # ffmpeg present: guard is a no-op. Empty batch => empty results, and the
    # guard's "ffmpeg not found" error must NOT appear.
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/ffmpeg")
    results = await mc.convert_files_functional([], "mp3", str(tmp_path))
    assert results == []
