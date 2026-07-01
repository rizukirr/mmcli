import asyncio
from typing import Optional, Dict, Any, Callable, List
from functools import partial
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress


def create_youtube_instance(url: str, progress_callback: Callable = on_progress) -> YouTube:
    """Create YouTube instance with progress callback."""
    return YouTube(url, on_progress_callback=progress_callback)


def create_playlist_instance(url: str) -> Playlist:
    """Create YouTube playlist instance."""
    return Playlist(url)


def select_video_stream(yt: YouTube, resolution: Optional[str]):
    """Select video stream based on resolution preference."""
    if resolution is not None:
        return yt.streams.get_by_resolution(resolution)
    return yt.streams.get_highest_resolution()


def select_audio_stream(yt: YouTube):
    """Select best available audio stream."""
    return yt.streams.get_audio_only()


def download_stream(stream, output_path: str) -> Optional[str]:
    """Download stream to specified output path."""
    return stream.download(output_path=output_path)


def get_video_metadata(yt: YouTube) -> Dict[str, Any]:
    """Extract video metadata."""
    return {
        "title": yt.title,
        "length": yt.length,
        "views": yt.views,
        "author": yt.author
    }


def get_playlist_metadata(playlist: Playlist) -> Dict[str, Any]:
    """Extract playlist metadata."""
    return {
        "title": playlist.title,
        "video_count": len(list(playlist.videos)),
        "owner": playlist.owner
    }


async def download_single_video(
    url: str, 
    output_path: str, 
    resolution: Optional[str] = None,
    progress_callback: Callable = on_progress
) -> Dict[str, Any]:
    """Download single YouTube video asynchronously."""
    loop = asyncio.get_event_loop()
    
    def _download():
        yt = create_youtube_instance(url, progress_callback)
        stream = select_video_stream(yt, resolution)
        downloaded_file = download_stream(stream, output_path)
        metadata = get_video_metadata(yt)
        return {
            "success": downloaded_file is not None,
            "file_path": downloaded_file,
            "metadata": metadata
        }
    
    return await loop.run_in_executor(None, _download)


async def download_single_audio(
    url: str, 
    output_path: str,
    progress_callback: Callable = on_progress
) -> Dict[str, Any]:
    """Download single YouTube audio asynchronously."""
    loop = asyncio.get_event_loop()
    
    def _download():
        yt = create_youtube_instance(url, progress_callback)
        stream = select_audio_stream(yt)
        downloaded_file = download_stream(stream, output_path)
        metadata = get_video_metadata(yt)
        return {
            "success": downloaded_file is not None,
            "file_path": downloaded_file,
            "metadata": metadata
        }
    
    return await loop.run_in_executor(None, _download)


async def download_playlist_videos(
    url: str,
    output_path: str,
    resolution: Optional[str] = None,
    progress_callback: Callable = on_progress,
    max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    """Download all videos from YouTube playlist asynchronously."""
    playlist = create_playlist_instance(url)
    playlist_meta = get_playlist_metadata(playlist)
    
    async def download_with_info(index: int, yt) -> Dict[str, Any]:
        print(f"[{index+1}/{playlist_meta['video_count']}] Downloading: {yt.title}")
        try:
            result = await download_single_video(yt.watch_url, output_path, resolution, progress_callback)
            if result["success"]:
                print(f"[OK] Successfully downloaded {yt.title}")
            else:
                print(f"[FAIL] Failed to download {yt.title}")
            return result
        except Exception as e:
            print(f"[FAIL] Error downloading {yt.title}: {e}")
            return {
                "success": False,
                "file_path": None,
                "metadata": {"title": yt.title, "error": str(e)}
            }
    
    # Use semaphore to limit concurrent downloads
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def download_with_semaphore(index: int, yt):
        async with semaphore:
            return await download_with_info(index, yt)
    
    tasks = [download_with_semaphore(index, yt) for index, yt in enumerate(playlist.videos)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions in results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "file_path": None,
                "metadata": {"title": f"video_{i}", "error": str(result)}
            })
        else:
            processed_results.append(result)
    
    return processed_results


async def download_playlist_audios(
    url: str,
    output_path: str,
    progress_callback: Callable = on_progress,
    max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    """Download all audios from YouTube playlist asynchronously."""
    playlist = create_playlist_instance(url)
    playlist_meta = get_playlist_metadata(playlist)
    
    async def download_with_info(index: int, yt) -> Dict[str, Any]:
        print(f"[{index+1}/{playlist_meta['video_count']}] Downloading: {yt.title}")
        try:
            result = await download_single_audio(yt.watch_url, output_path, progress_callback)
            if result["success"]:
                print(f"[OK] Successfully downloaded {yt.title}")
            else:
                print(f"[FAIL] Failed to download {yt.title}")
            return result
        except Exception as e:
            print(f"[FAIL] Error downloading {yt.title}: {e}")
            return {
                "success": False,
                "file_path": None,
                "metadata": {"title": yt.title, "error": str(e)}
            }
    
    # Use semaphore to limit concurrent downloads
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def download_with_semaphore(index: int, yt):
        async with semaphore:
            return await download_with_info(index, yt)
    
    tasks = [download_with_semaphore(index, yt) for index, yt in enumerate(playlist.videos)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions in results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "file_path": None,
                "metadata": {"title": f"audio_{i}", "error": str(result)}
            })
        else:
            processed_results.append(result)
    
    return processed_results


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube URL."""
    return "youtube.com" in url or "youtu.be" in url


def is_playlist_url(url: str) -> bool:
    """Check if URL is a playlist URL."""
    return "list=" in url


def validate_youtube_url(url: str) -> Dict[str, bool]:
    """Validate YouTube URL and determine type."""
    return {
        "is_valid": is_youtube_url(url),
        "is_playlist": is_playlist_url(url)
    }
