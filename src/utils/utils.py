"""
Utility functions for the AI Video Generation System
"""

import os
import logging
import time
import yaml
from pathlib import Path
from typing import Any, Dict
import hashlib
import json


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """Set up logging configuration"""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/video_generator.log')
    
    # Create logs directory if it doesn't exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('VideoGenerator')


def ensure_directories(config: Dict[str, Any]):
    """Ensure all required directories exist"""
    paths = config.get('paths', {})
    
    directories = [
        paths.get('cache_dir', 'cache'),
        paths.get('cache_audio', 'cache/audio'),
        paths.get('cache_images', 'cache/images'),
        paths.get('output_dir', 'output'),
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Retry a function with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    raise Exception(f"Failed after {max_retries} attempts")


def generate_cache_key(*args) -> str:
    """
    Generate a cache key from arguments
    
    Args:
        *args: Arguments to hash
        
    Returns:
        MD5 hash of the arguments
    """
    content = json.dumps(args, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_file(cache_dir: str, cache_key: str, extension: str) -> str:
    """
    Get cached file path
    
    Args:
        cache_dir: Cache directory
        cache_key: Cache key
        extension: File extension (with dot)
        
    Returns:
        Path to cached file
    """
    return os.path.join(cache_dir, f"{cache_key}{extension}")


def file_exists_and_valid(filepath: str, min_size: int = 100) -> bool:
    """
    Check if file exists and has minimum size
    
    Args:
        filepath: Path to file
        min_size: Minimum file size in bytes
        
    Returns:
        True if file exists and is valid
    """
    if not os.path.exists(filepath):
        return False
    
    return os.path.getsize(filepath) >= min_size


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename to remove invalid characters
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    return filename


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1:23")
    """
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


def cleanup_temp_files(directory: str, pattern: str = "temp_*"):
    """
    Clean up temporary files in a directory
    
    Args:
        directory: Directory to clean
        pattern: File pattern to match
    """
    import glob
    
    temp_files = glob.glob(os.path.join(directory, pattern))
    for file in temp_files:
        try:
            os.remove(file)
            logging.debug(f"Removed temp file: {file}")
        except Exception as e:
            logging.warning(f"Failed to remove temp file {file}: {e}")


_LOG_ESCAPES = {
    "\\": "\\\\",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def scrub_for_log(value, max_length: int = 256) -> str:
    """
    Make an untrusted value safe to put in a log line

    A value carrying a newline stops being a value and becomes a second
    record, which the reader cannot tell from one the application wrote.
    Backslash is escaped first so a value that literally contained the two
    characters backslash and 'n' stays distinguishable from a real newline.

    This duplicates backend/core/logsafe.scrub. It is not imported from
    there on purpose: backend/ imports src/ (see backend/services/video.py),
    so src/ importing backend/ would close the cycle. Change both together.

    Args:
        value: Value to place in a log record
        max_length: Cap on the escaped result

    Returns:
        A single-line string safe to log
    """
    text = value if isinstance(value, str) else str(value)

    out = []
    for char in text:
        escape = _LOG_ESCAPES.get(char)
        if escape is not None:
            out.append(escape)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append("\\x{:02x}".format(ord(char)))
        else:
            out.append(char)

    scrubbed = "".join(out)

    if len(scrubbed) > max_length:
        scrubbed = scrubbed[:max_length] + "...[truncated]"

    return scrubbed
