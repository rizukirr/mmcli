import asyncio
import ffmpeg
import os
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import reduce
from ..utils.media_format import all_formats


def ensure_output_directory(output_dir: Optional[str]) -> Path:
    """Create output directory if needed and return Path object."""
    path = Path(output_dir) if output_dir else Path(os.getcwd()) / "convert"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_output_filename(input_file: Path, output_format: str) -> str:
    """Generate unique output filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{input_file.stem}_{timestamp}.{output_format}"


def create_output_path(input_file: Path, output_format: str, output_dir: Path) -> Path:
    """Create full output file path."""
    output_filename = generate_output_filename(input_file, output_format)
    return output_dir / output_filename


def find_ffmpeg_format(output_format: str) -> Optional[str]:
    """Find matching ffmpeg format from format alias."""
    format_matches = list(filter(lambda fmt: fmt["alias"] == output_format, all_formats))
    return format_matches[0]["format"] if format_matches else None


def create_conversion_config(input_file: Path, output_format: str, output_dir: Path) -> Dict[str, Any]:
    """Create conversion configuration object."""
    ffmpeg_format = find_ffmpeg_format(output_format)
    output_path = create_output_path(input_file, output_format, output_dir)
    
    return {
        "input_file": input_file,
        "output_path": output_path,
        "ffmpeg_format": ffmpeg_format,
        "output_format": output_format
    }


async def execute_ffmpeg_conversion(config: Dict[str, Any]) -> bool:
    """Execute ffmpeg conversion with given configuration asynchronously."""
    if not config["ffmpeg_format"]:
        print(f"Unsupported format: {config['output_format']}")
        return False

    def _convert():
        try:
            ffmpeg.input(str(config["input_file"])).output(
                str(config["output_path"]), 
                format=config["ffmpeg_format"]
            ).run(quiet=True, overwrite_output=True)
            return True
        except Exception as e:
            print(f"Error converting {config['input_file']}: {e}")
            return False
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _convert)


async def convert_single_file_functional(
    input_file: Path, 
    output_format: str, 
    output_dir: Path
) -> Dict[str, Any]:
    """Convert single file using functional approach with detailed result."""
    config = create_conversion_config(input_file, output_format, output_dir)
    success = await execute_ffmpeg_conversion(config)
    
    return {
        "input_file": str(input_file),
        "output_file": str(config["output_path"]) if success else None,
        "success": success,
        "format": output_format
    }


async def process_conversion_batch(
    input_files: List[Path], 
    output_format: str, 
    output_dir: Path,
    max_concurrent: int = 1
) -> List[Dict[str, Any]]:
    """Process batch conversion using async concurrency control."""
    
    async def convert_with_feedback(input_file: Path) -> Dict[str, Any]:
        try:
            result = await convert_single_file_functional(input_file, output_format, output_dir)
            if result["success"]:
                print(f"[OK] Converted {input_file.name}")
            else:
                print(f"[FAIL] Failed to convert {input_file.name}")
            return result
        except Exception as e:
            print(f"[ERROR] Error converting {input_file.name}: {e}")
            return {
                "input_file": str(input_file),
                "output_file": None,
                "success": False,
                "format": output_format,
                "error": str(e)
            }
    
    if len(input_files) == 1 or max_concurrent <= 1:
        # Sequential conversion for single files or when max_concurrent is 1
        print(f"Converting {len(input_files)} file(s) to {output_format}...")
        results = []
        for input_file in input_files:
            result = await convert_with_feedback(input_file)
            results.append(result)
        return results
    else:
        # Concurrent conversion for multiple files
        print(f"Converting {len(input_files)} file(s) to {output_format} using max {max_concurrent} concurrent conversions...")
        
        # Use semaphore to limit concurrent conversions
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def convert_with_semaphore(input_file: Path):
            async with semaphore:
                return await convert_with_feedback(input_file)
        
        tasks = [convert_with_semaphore(input_file) for input_file in input_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "input_file": str(input_files[i]),
                    "output_file": None,
                    "success": False,
                    "format": output_format,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results


def calculate_conversion_stats(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate conversion statistics from results."""
    return reduce(
        lambda acc, result: {
            "total": acc["total"] + 1,
            "success": acc["success"] + (1 if result["success"] else 0),
            "failed": acc["failed"] + (0 if result["success"] else 1)
        },
        results,
        {"total": 0, "success": 0, "failed": 0}
    )


def format_conversion_summary(stats: Dict[str, int], output_format: str, output_dir: str) -> str:
    """Format conversion summary message."""
    return textwrap.dedent(f"""
        Summary:
        Successfully converted: {stats['success']}
        Failed to convert: {stats['failed']}
        Format: {output_format}
        Output directory: {output_dir}
    """).strip()


def print_conversion_results(results: List[Dict[str, Any]], output_format: str, output_dir: str) -> None:
    """Print detailed conversion results and summary."""
    stats = calculate_conversion_stats(results)
    
    print("Conversion complete.")
    print(format_conversion_summary(stats, output_format, output_dir))
    
    if stats["failed"] > 0:
        print("\nFailed conversions:")
        failed_files = [r["input_file"] for r in results if not r["success"]]
        for file_path in failed_files:
            print(f"  - {file_path}")


async def convert_files_functional(
    input_files: List[Path], 
    output_format: str, 
    output_dir: Optional[str] = None,
    max_workers: int = 1
) -> List[Dict[str, Any]]:
    """Convert batch of files using async concurrency."""
    resolved_output_dir = ensure_output_directory(output_dir)
    
    results = await process_conversion_batch(input_files, output_format, resolved_output_dir, max_workers)
    print_conversion_results(results, output_format, str(resolved_output_dir))
    
    return results
