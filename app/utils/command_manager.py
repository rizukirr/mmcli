import argparse
from .media_format import all_formats, video_formats, audio_formats
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
    video_aliases = ", ".join(f["alias"] for f in video_formats)
    audio_aliases = ", ".join(f["alias"] for f in audio_formats)
    parser.add_argument(
        "--format",
        "-f",
        choices=[f["alias"] for f in all_formats],
        metavar="FORMAT",
        help=(
            "Output format. Audio formats download audio only "
            f"({audio_aliases}); video formats convert the container "
            f"({video_aliases})."
        ),
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        dest="output_dir",
        help="Output directory (default: current directory)",
    )

    return parser.parse_args()
