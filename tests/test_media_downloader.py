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


@pytest.mark.asyncio
async def test_download_playlist_audio_conversion(monkeypatch, tmp_path):
    """--format mp3 on a playlist downloads audio for every item and converts each to mp3."""
    class FakePlaylist:
        title = "MyList"

    calls = {}

    async def fake_playlist_audios(url, output_path, max_concurrent=3):
        calls["audio"] = True
        return [
            {"success": True, "file_path": str(tmp_path / "1.m4a"), "metadata": {"title": "one"}},
            {"success": True, "file_path": str(tmp_path / "2.m4a"), "metadata": {"title": "two"}},
        ]

    async def fake_playlist_videos(url, output_path, resolution=None, max_concurrent=3):
        calls["video"] = True
        return []

    async def fake_convert(input_files, output_format, output_dir=None, max_workers=1):
        return [
            {
                "input_file": str(f),
                "output_file": str(tmp_path / f"{f.stem}.mp3"),
                "success": True,
                "format": output_format,
            }
            for f in input_files
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
        md.youtube_downloader, "download_playlist_audios", fake_playlist_audios
    )
    monkeypatch.setattr(
        md.youtube_downloader, "download_playlist_videos", fake_playlist_videos
    )
    monkeypatch.setattr(md.media_converter, "convert_files_functional", fake_convert)
    monkeypatch.setattr(md.os, "remove", lambda p: None)
    args = SimpleNamespace(
        url="https://youtube.com/playlist?list=x",
        resolution=None,
        format="mp3",
        output_dir=str(tmp_path),
    )
    results = await md.download(args)
    # routed to the audio path, not the video path
    assert calls.get("audio") is True
    assert "video" not in calls
    # every item came back converted to mp3
    assert len(results) == 2
    assert all(r["success"] and r["format"] == "mp3" for r in results)
    assert all(r["file_path"].endswith(".mp3") for r in results)
