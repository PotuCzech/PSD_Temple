"""
PSD Optimization utilities for faster rendering and memory efficiency.

This module provides various optimization techniques for working with PSD files,
including cached composites, progressive loading, and layer-based optimizations.
"""

import logging
from typing import Optional, List, Tuple
from PIL import Image
from psd_tools import PSDImage
import threading

logger = logging.getLogger(__name__)

class PSDOptimizer:
    """Optimization utilities for PSD files."""
    
    def __init__(self, cache: bool = True):
        """Initialize the PSD optimizer.
        
        Args:
            cache: Whether to enable caching of composites
        """
        self.cache = cache
        self._cache = {}
        
    def get_cached_composite(self, psd: PSDImage, scale: float = 1.0) -> Optional[Image.Image]:
        """Get a cached composite or generate a new one.
        
        Args:
            psd: The PSDImage instance
            scale: Scale factor for the composite
            
        Returns:
            The composite image or None if failed
        """
        cache_key = f"{id(psd)}_{scale}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            composite = self._get_optimized_composite(psd, scale)
            if self.cache:
                self._cache[cache_key] = composite
            return composite
        except Exception as e:
            logger.error(f"Error generating composite: {e}")
            return None
            
    def _get_optimized_composite(self, psd: PSDImage, scale: float = 1.0) -> Image.Image:
        """Generate an optimized composite image.
        
        Args:
            psd: The PSDImage instance or a dictionary with composite method
            scale: Scale factor for the composite
            
        Returns:
            The composite image
        """
        try:
            # Check if psd has a compose method (direct PSDImage)
            if hasattr(psd, 'compose'):
                # Check if psd has layers and they have 'visible' attribute
                if hasattr(psd, 'layers') and all(hasattr(layer, 'visible') for layer in psd.layers):
                    visible_layers = [layer for layer in psd.layers if layer.visible]
                    if visible_layers:
                        return psd.compose(layers=visible_layers, scale=scale)
                return psd.compose(scale=scale)
            
            # Fallback to direct composite if available
            if hasattr(psd, 'get_composite_image'):
                return psd.get_composite_image()
                
            # If we get here, we don't know how to handle this PSD
            raise ValueError("Unsupported PSD document type")
            
        except Exception as e:
            logger.exception(f"Error generating composite: {str(e)}")
            # Try one last fallback to basic composite
            if hasattr(psd, 'compose'):
                return psd.compose(scale=scale)
            raise
        
    def get_progressive_preview(self, psd: PSDImage) -> Tuple[Image.Image, threading.Thread]:
        """Get a progressive preview with low-res and full-res loading.
        
        Args:
            psd: The PSDImage instance
            
        Returns:
            Tuple of (low_res_preview, loading_thread)
        """
        # Generate low-res preview immediately
        low_res = psd.compose(scale=0.25)
        
        # Start full-res loading in background
        def load_full_res():
            try:
                full_res = psd.compose()
                # Store in cache if enabled
                if self.cache:
                    self._cache[id(psd)] = full_res
            except Exception as e:
                logger.error(f"Error loading full res: {e}")
                
        thread = threading.Thread(target=load_full_res, daemon=True)
        thread.start()
        
        return low_res, thread
        
    def get_layer_group_composites(self, psd: PSDImage) -> List[Image.Image]:
        """Get composites for each layer group separately.
        
        Args:
            psd: The PSDImage instance
            
        Returns:
            List of composite images for each layer group
        """
        composites = []
        for group in psd.layer_groups:
            try:
                composite = group.compose()
                composites.append(composite)
            except Exception as e:
                logger.error(f"Error composing group {group.name}: {e}")
        return composites
        
    def clear_cache(self):
        """Clear all cached composites."""
        self._cache.clear()
        
    def __del__(self):
        """Cleanup resources."""
        self.clear_cache()

# Singleton instance
psd_optimizer = PSDOptimizer(cache=True)
