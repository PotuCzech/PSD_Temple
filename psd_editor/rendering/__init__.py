"""
Rendering module for PSD files.

This module provides two rendering modes:
1. Full rendering: Complete PSD layer management and rendering
2. Light rendering: Simple PNG conversion and display
"""
from __future__ import annotations

import os
import logging
from typing import Optional, Union
from PIL import Image
from psd_tools import PSDImage

# Set up logging
logger = logging.getLogger(__name__)

class PSDFullRenderer:
    """Full PSD renderer with layer management."""
    
    def __init__(self, psd_doc: PSDImage):
        """Initialize the full renderer.
        
        Args:
            psd_doc: The PSD document to render.
        """
        self.psd_doc = psd_doc
        
    def get_composite_image(self) -> Image.Image:
        """Get the composite image of all visible layers.
        
        Returns:
            PIL.Image.Image: The composite image.
        """
        return self.psd_doc.composite()
    
    def get_layer_image(self, layer_id: str) -> Optional[Image.Image]:
        """Get image for a specific layer.
        
        Args:
            layer_id: The ID of the layer to render.
            
        Returns:
            PIL.Image.Image: The layer image, or None if not found.
        """
        try:
            layer = self._find_layer_by_id(layer_id)
            if layer:
                return layer.composite()
        except Exception as e:
            logger.exception(f"Error getting layer image: {str(e)}")
        return None
    
    def _find_layer_by_id(self, layer_id: str) -> Optional[Layer]:
        """Find a layer by its ID.
        
        Args:
            layer_id: The ID of the layer to find.
            
        Returns:
            Layer: The found layer, or None if not found.
        """
        for layer in self._iterate_layers(self.psd_doc):
            if str(id(layer)) == layer_id:
                return layer
        return None
    
    def _iterate_layers(self, parent: Union[PSDImage, Layer]) -> list[Layer]:
        """Recursively iterate through all layers.
        
        Args:
            parent: The parent layer or PSD document to iterate through.
            
        Returns:
            list[Layer]: List of all layers.
        """
        layers = []
        for layer in getattr(parent, 'layers', []):
            layers.append(layer)
            if hasattr(layer, 'layers'):
                layers.extend(self._iterate_layers(layer))
        return layers

class PSDLightRenderer:
    """Lightweight PSD renderer that converts to PNG."""
    
    def __init__(self, psd_path: str):
        """Initialize the light renderer.
        
        Args:
            psd_path: Path to the PSD file.
        """
        self.psd_path = psd_path
        self.png_path = None
        
    def convert_to_png(self) -> str:
        """Convert PSD to PNG and return the path.
        
        Returns:
            str: Path to the generated PNG file.
        """
        try:
            # Create a temporary PNG file
            png_path = self._get_temp_png_path()
            
            # Load and convert PSD
            psd = PSDImage.open(self.psd_path)
            image = psd.composite()
            image.save(png_path)
            
            self.png_path = png_path
            return png_path
            
        except Exception as e:
            logger.exception(f"Error converting PSD to PNG: {str(e)}")
            raise RuntimeError(f"Failed to convert PSD to PNG: {str(e)}") from e
    
    def _get_temp_png_path(self) -> str:
        """Get a temporary PNG path based on the PSD file.
        
        Returns:
            str: Path to the temporary PNG file.
        """
        base_name = os.path.splitext(os.path.basename(self.psd_path))[0]
        temp_dir = os.path.dirname(self.psd_path)
        return os.path.join(temp_dir, f"{base_name}.png")
    
    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.png_path and os.path.exists(self.png_path):
            try:
                os.remove(self.png_path)
                self.png_path = None
            except Exception as e:
                logger.exception(f"Error cleaning up PNG file: {str(e)}")

def create_renderer(mode: str = 'full') -> Union[PSDFullRenderer, PSDLightRenderer]:
    """Create a renderer based on the specified mode.
    
    Args:
        mode: Rendering mode ('full' or 'light').
        
    Returns:
        Union[PSDFullRenderer, PSDLightRenderer]: The appropriate renderer.
    """
    if mode == 'light':
        return PSDLightRenderer
    return PSDFullRenderer
