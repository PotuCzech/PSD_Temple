"""
Cache manager for storing and retrieving PSD previews and composites.
"""
import os
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class PSDFileCache:
    """Cache manager for PSD files and their previews."""
    
    def __init__(self, cache_dir: str = "psd_cache"):
        """Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()
        self.max_cache_size = 1024 * 1024 * 1024  # 1GB max cache size
    
    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self.metadata = {}
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def _get_file_hash(self, filepath: str) -> str:
        """Generate a hash for the file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            str: Hex digest of the file hash
        """
        filepath = str(filepath)
        hasher = hashlib.md5()
        hasher.update(filepath.encode('utf-8'))
        file_stat = os.stat(filepath)
        hasher.update(str(file_stat.st_size).encode('utf-8'))
        hasher.update(str(file_stat.st_mtime).encode('utf-8'))
        return hasher.hexdigest()
    
    def get_cache_path(self, filepath: str, suffix: str = "") -> Path:
        """Get the cache path for a file.
        
        Args:
            filepath: Path to the source file
            suffix: Optional suffix for the cache file
            
        Returns:
            Path: Path to the cache file
        """
        file_hash = self._get_file_hash(filepath)
        filename = f"{file_hash}{suffix}.png"
        return self.cache_dir / filename
    
    def get_cached_image(self, filepath: str, suffix: str = "") -> Optional[Image.Image]:
        """Get a cached image if it exists and is valid.
        
        Args:
            filepath: Path to the source file
            suffix: Optional suffix for the cache file
            
        Returns:
            Optional[Image.Image]: Cached image or None if not found/invalid
        """
        cache_path = self.get_cache_path(filepath, suffix)
        if not cache_path.exists():
            return None
            
        # Check if cache is still valid
        source_mtime = os.path.getmtime(filepath)
        cache_mtime = os.path.getmtime(cache_path)
        
        if cache_mtime < source_mtime:
            # Source file has been modified since cache was created
            try:
                os.remove(cache_path)
            except Exception as e:
                logger.warning(f"Failed to remove stale cache {cache_path}: {e}")
            return None
            
        try:
            return Image.open(cache_path)
        except Exception as e:
            logger.warning(f"Failed to load cached image {cache_path}: {e}")
            return None
    
    def save_image_to_cache(self, image: Image.Image, filepath: str, suffix: str = "") -> None:
        """Save an image to the cache.
        
        Args:
            image: PIL Image to save
            filepath: Path to the source file
            suffix: Optional suffix for the cache file
        """
        try:
            cache_path = self.get_cache_path(filepath, suffix)
            # Create parent directories if they don't exist
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with optimization
            image.save(cache_path, "PNG", optimize=True)
            
            # Update metadata
            file_key = f"{self._get_file_hash(filepath)}{suffix}"
            self.metadata[file_key] = {
                "source_path": filepath,
                "cache_path": str(cache_path),
                "size": os.path.getsize(cache_path),
                "created_at": time.time(),
                "last_accessed": time.time()
            }
            self._save_metadata()
            
            # Clean up old cache if needed
            self._cleanup_cache()
            
        except Exception as e:
            logger.error(f"Failed to save image to cache: {e}")
    
    def _cleanup_cache(self) -> None:
        """Clean up old cache files if cache size exceeds limit."""
        try:
            # Get total cache size
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("**/*") if f.is_file())
            
            if total_size <= self.max_cache_size:
                return
                
            # Sort files by last accessed time (oldest first)
            files = []
            for f in self.cache_dir.glob("**/*"):
                if f.is_file() and f.suffix in ('.png', '.jpg', '.jpeg'):
                    files.append((f, os.path.getatime(f)))
            
            files.sort(key=lambda x: x[1])
            
            # Delete oldest files until under limit
            for f, _ in files:
                if total_size <= self.max_cache_size:
                    break
                try:
                    file_size = f.stat().st_size
                    os.remove(f)
                    total_size -= file_size
                except Exception as e:
                    logger.warning(f"Failed to clean up cache file {f}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")

# Global cache instance
psd_cache = PSDFileCache()
