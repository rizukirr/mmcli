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


def sanitize_subfolder(name: str) -> str:
    """Reduce a playlist title to a safe single path segment."""
    # Drop path separators and surrounding whitespace so a title can never
    # escape base_dir or create nested folders; fall back to 'playlist' when
    # nothing meaningful survives (empty, or only separators/dots).
    cleaned = name.replace("/", "_").replace("\\", "_").strip().strip(".")
    if not cleaned or set(cleaned) <= {"_"}:
        return "playlist"
    return cleaned


def resolve_playlist_output(base_dir: str, url: str) -> str:
    """Return <base_dir>/<playlist-title>/, falling back to 'playlist'."""
    try:
        playlist = youtube_downloader.create_playlist_instance(url)
        title = playlist.title
    except Exception:
        title = "playlist"
    return ensure_directory_exists(os.path.join(base_dir, sanitize_subfolder(title)))


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
    if target_format and should_convert(
        extract_file_extension(file_path), target_format
    ):
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
            f
            for f in downloaded
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
                # Key on the original download path, not cr["input_file"], so the
                # lookup below matches regardless of Path round-trip normalization.
                conversion_map[to_convert[i]] = cr

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
