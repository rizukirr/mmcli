import os
import sys
from typing import Optional, Dict, Any, List
from functools import reduce
from ..utils.media_format import video_formats, get_format, audio_formats
from ..utils.config import (
    get_output_dir_default,
    get_video_format_default,
    get_audio_format_default,
    get_video_resolution_default,
    get_max_workers_default,
    should_create_playlist_subfolders,
)
from . import media_converter
from . import youtube_downloader


def get_output_dir() -> str:
    """Get default output directory from config."""
    return os.path.join(os.getcwd(), get_output_dir_default())


def ensure_directory_exists(path: str) -> str:
    """Ensure directory exists and return path."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def get_format_or_default(format_arg: Optional[str], format_map: list, default: str) -> str:
    """Get format with fallback to default."""
    if format_arg is None:
        return default
    
    formats = get_format(format_arg, format_map)
    if not formats:
        raise ValueError(f"Unsupported format: {format_arg}")
    return formats[0]["format"]


def get_video_format_or_default(format_arg: Optional[str]) -> str:
    """Get video format with config default."""
    return get_format_or_default(format_arg, video_formats, get_video_format_default())


def get_audio_format_or_default(format_arg: Optional[str]) -> Optional[str]:
    """Get audio format with config default."""
    if format_arg is None:
        return None  # Return None to indicate no conversion needed
    return get_format_or_default(format_arg, audio_formats, get_audio_format_default())


def create_output_path(base_dir: str, media_type: str, subfolder: Optional[str] = None) -> str:
    """Create hierarchical output path."""
    path_components = [base_dir, media_type]
    if subfolder:
        path_components.append(subfolder)
    return os.path.join(*path_components)


def extract_file_extension(filepath: str) -> str:
    """Extract file extension from filepath."""
    return os.path.splitext(filepath)[1][1:].lower()


def should_convert_format(current_ext: str, target_format: str) -> bool:
    """Check if format conversion is needed."""
    if not target_format:
        return False

    return current_ext.lower() != target_format.lower()


async def convert_if_needed(downloaded_file: str, target_format: str, args) -> str:
    """Convert media file if format differs from target."""
    if not downloaded_file or target_format is None:
        return downloaded_file
        
    current_ext = extract_file_extension(downloaded_file)
    
    if should_convert_format(current_ext, target_format):
        print(f"Converting to {target_format} format...")
        
        args.path = downloaded_file 
        args.to = target_format 
        args.output_dir = os.path.dirname(downloaded_file)
        
        results = await media_converter.convert(args)
        
        if results and len(results) > 0 and results[0]["success"]:
            os.remove(downloaded_file)
            return results[0]["output_file"]
        else:
            print(f"Failed to convert {downloaded_file}")
            return downloaded_file
    return downloaded_file


def create_download_config(args, media_type: str) -> Dict[str, Any]:
    """Create download configuration object with config defaults."""
    output_dir = get_output_dir()
    
    if media_type == "video":
        output_format = get_video_format_or_default(args.format)
        output_path = create_output_path(output_dir, "videos")
        # Use config default resolution if not specified
        resolution = getattr(args, 'resolution', None)
        if resolution is None:
            config_resolution = get_video_resolution_default()
            resolution = None if config_resolution == "highest" else config_resolution
    else:  # audio
        output_format = get_audio_format_or_default(args.format)
        output_path = create_output_path(output_dir, "audios")
        resolution = None
    
    return {
        "url": args.url,
        "output_dir": output_dir,
        "output_format": output_format,
        "output_path": ensure_directory_exists(output_path),
        "resolution": resolution,
        "args": args
    }


def create_playlist_config(args, media_type: str) -> Dict[str, Any]:
    """Create playlist download configuration with config options."""
    config = create_download_config(args, media_type)
    
    # Get playlist title for subfolder if enabled in config
    if should_create_playlist_subfolders():
        url_validation = youtube_downloader.validate_youtube_url(args.url)
        if url_validation["is_valid"] and url_validation["is_playlist"]:
            try:
                playlist = youtube_downloader.create_playlist_instance(args.url)
                playlist_title = playlist.title
            except Exception:
                playlist_title = "unknown_playlist"
        else:
            playlist_title = "unknown_playlist"
        
        playlist_base = create_output_path(config["output_dir"], "playlist")
        config["output_path"] = ensure_directory_exists(
            create_output_path(playlist_base, f"{media_type}s", playlist_title)
        )
    else:
        # Use simple playlist directory without title subfolder
        playlist_base = create_output_path(config["output_dir"], "playlist")
        config["output_path"] = ensure_directory_exists(
            create_output_path(playlist_base, f"{media_type}s")
        )
    
    return config


async def process_single_download_result(result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Process single download result with conversion if needed."""
    if not result["success"]:
        return {
            "success": False,
            "title": result["metadata"].get("title", "Unknown"),
            "path": config["output_path"],
            "format": config["output_format"] or "original",
            "converted": False,
            "error": result["metadata"].get("error", "Download failed")
        }
    
    original_file = result["file_path"]
    converted_file = await convert_if_needed(
        result["file_path"], 
        config["output_format"], 
        config["args"]
    )
    was_converted = converted_file != original_file
    
    # If no target format specified, use the original file's extension
    final_format = config["output_format"] or extract_file_extension(converted_file)
    
    return {
        "success": True,
        "title": result["metadata"]["title"],
        "path": config["output_path"],
        "format": final_format,
        "converted": was_converted,
        "file_path": converted_file
    }


def collect_downloaded_files(results: List[Dict[str, Any]]) -> List[str]:
    """Collect successfully downloaded files for batch conversion."""
    return [result["file_path"] for result in results if result["success"] and result["file_path"]]


async def batch_convert_playlist_files(downloaded_files: List[str], target_format: str) -> List[Dict[str, Any]]:
    """Batch convert playlist files using media_converter."""
    if not downloaded_files:
        return []
    
    # Check if conversion is needed
    files_to_convert = []
    for file_path in downloaded_files:
        current_ext = extract_file_extension(file_path)
        if should_convert_format(current_ext, target_format):
            files_to_convert.append(file_path)
    
    if not files_to_convert:
        return []
    
    print(f"Batch converting {len(files_to_convert)} files to {target_format} format...")
    
    # Use media_converter for batch processing with async support
    from pathlib import Path
    input_files = [Path(f) for f in files_to_convert]
    max_workers = get_max_workers_default()
    conversion_results = await media_converter.convert_files_functional(input_files, target_format, max_workers=max_workers)
    
    # Clean up original files that were successfully converted
    for i, result in enumerate(conversion_results):
        if result["success"]:
            try:
                os.remove(files_to_convert[i])
            except:
                pass  # Ignore cleanup errors
    
    return conversion_results


async def process_playlist_results(results: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process playlist download results with batch conversion."""
    # First, collect all downloaded files
    downloaded_files = collect_downloaded_files(results)
    
    # Check if any conversion is needed
    target_format = config["output_format"]
    if target_format is None:
        # No conversion needed, return results as-is
        conversion_map = {}
        needs_conversion = False
    else:
        needs_conversion = any(
            should_convert_format(extract_file_extension(file), target_format)
            for file in downloaded_files
        )
    
    if needs_conversion:
        # Batch convert all files
        conversion_results = await batch_convert_playlist_files(downloaded_files, target_format)
        conversion_map = {result["input_file"]: result for result in conversion_results}
    else:
        conversion_map = {}
    
    # Process results with conversion info
    processed_results = []
    for result in results:
        if not result["success"]:
            processed_results.append({
                "success": False,
                "title": result["metadata"].get("title", "Unknown"),
                "path": config["output_path"],
                "format": config["output_format"] or "original",
                "converted": False,
                "error": result["metadata"].get("error", "Download failed")
            })
        else:
            file_path = result["file_path"]
            conversion_result = conversion_map.get(file_path)
            was_converted = conversion_result is not None and conversion_result["success"]

            final_file_path = conversion_result["output_file"] if was_converted else file_path
            
            # If no target format specified, use the original file's extension
            final_format = config["output_format"] or extract_file_extension(final_file_path)
            
            processed_results.append({
                "success": True,
                "title": result["metadata"]["title"],
                "path": config["output_path"],
                "format": final_format,
                "converted": was_converted,
                "file_path": final_file_path
            })
    
    return processed_results


async def download_single_video(config: Dict[str, Any]) -> Dict[str, Any]:
    """Download single video using async approach."""
    try:
        print(f"Downloading video from: {config['url']}")
        
        result = await youtube_downloader.download_single_video(
            config["url"],
            config["output_path"],
            config["resolution"]
        )
        
        processed_result = await process_single_download_result(result, config)
        
        if processed_result["success"]:
            status_msg = "Video converted and saved to" if processed_result["converted"] else "Video saved to"
            print(f"{status_msg} {config['output_path']}")
        
        return processed_result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": config["output_path"],
            "format": config["output_format"]
        }


async def download_single_audio(config: Dict[str, Any]) -> Dict[str, Any]:
    """Download single audio using async approach."""
    try:
        print(f"Downloading audio from: {config['url']}")
        
        result = await youtube_downloader.download_single_audio(
            config["url"],
            config["output_path"]
        )
        
        processed_result = await process_single_download_result(result, config)
        
        if processed_result["success"]:
            print(f"Audio saved to {config['output_path']}")
        
        return processed_result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": config["output_path"],
            "format": config["output_format"]
        }


async def download_playlist_videos(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Download playlist videos using async approach with concurrency control."""
    try:
        max_workers = get_max_workers_default()
        
        # Always use the async function with concurrency control
        results = await youtube_downloader.download_playlist_videos(
            config["url"],
            config["output_path"],
            config["resolution"],
            max_concurrent=max_workers
        )
        
        return await process_playlist_results(results, config)
        
    except Exception as e:
        return [{
            "success": False,
            "error": str(e),
            "path": config["output_path"],
            "format": config["output_format"]
        }]


async def download_playlist_audios(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Download playlist audios using async approach with concurrency control."""
    try:
        max_workers = get_max_workers_default()
        
        # Always use the async function with concurrency control
        results = await youtube_downloader.download_playlist_audios(
            config["url"],
            config["output_path"],
            max_concurrent=max_workers
        )
        
        return await process_playlist_results(results, config)
        
    except Exception as e:
        return [{
            "success": False,
            "error": str(e),
            "path": config["output_path"],
            "format": config["output_format"]
        }]


async def route_video_download(args) -> Dict[str, Any] | List[Dict[str, Any]]:
    """Route video download based on URL type."""
    url_validation = youtube_downloader.validate_youtube_url(args.url)
    
    if not url_validation["is_valid"]:
        raise ValueError(f"Unsupported URL: {args.url}, currently only YouTube URLs are supported.")
    
    if url_validation["is_playlist"]:
        config = create_playlist_config(args, "video")
        return await download_playlist_videos(config)
    else:
        config = create_download_config(args, "video")
        return await download_single_video(config)


async def route_audio_download(args) -> Dict[str, Any] | List[Dict[str, Any]]:
    """Route audio download based on URL type."""
    url_validation = youtube_downloader.validate_youtube_url(args.url)
    
    if not url_validation["is_valid"]:
        raise ValueError(f"Unsupported URL: {args.url}, currently only YouTube URLs are supported.")
    
    if url_validation["is_playlist"]:
        config = create_playlist_config(args, "audio")
        return await download_playlist_audios(config)
    else:
        config = create_download_config(args, "audio")
        return await download_single_audio(config)


def calculate_success_stats(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate download statistics from results."""
    return reduce(
        lambda acc, result: {
            "total": acc["total"] + 1,
            "success": acc["success"] + (1 if result["success"] else 0),
            "failed": acc["failed"] + (0 if result["success"] else 1)
        },
        results,
        {"total": 0, "success": 0, "failed": 0}
    )


def print_download_summary(results) -> None:
    """Print download summary based on results type."""
    if isinstance(results, list):
        stats = calculate_success_stats(results)
        saved_location = results[0]["path"] if results else "Unknown"
        
        print("Download Summary:")
        print(f"- Total items: {stats['total']}")
        print(f"- Successfully downloaded: {stats['success']}")
        print(f"- Failed to download: {stats['failed']}")
        print(f"- Saved to: {saved_location}")
    else:
        print("Done")


async def download(args):
    """Main download dispatcher function."""
    download_functions = {
        "video": route_video_download,
        "audio": route_audio_download
    }
    
    download_func = download_functions.get(args.type)
    if not download_func:
        raise ValueError(f"Unsupported download type: {args.type}")
    
    try:
        result = await download_func(args)
        print_download_summary(result)
        return result
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
