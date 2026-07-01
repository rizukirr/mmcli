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
