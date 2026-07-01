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
