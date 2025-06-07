"""
PSD document model for the PSD Editor.

This module provides the PSDDocument class which serves as a data model
for PSD files, handling loading, manipulation, and rendering of PSD content.
"""
from __future__ import annotations
import os
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path
import logging

import numpy as np
from PIL import Image, ImageTk
from psd_tools import PSDImage
from psd_editor.rendering import create_renderer, Renderer

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class PSDDocument:
    """Represents a PSD document with layer management."""
    
    filepath: Optional[str] = None
    psd: Optional[PSDImage] = None
    current_scale: float = 1.0
    layer_images: List[ImageTk.PhotoImage] = field(default_factory=list)
    _renderer: Optional[Renderer] = None
    _render_mode: str = 'light'
    
    @classmethod
    def from_file(cls, filepath: str, render_mode: str = 'light') -> 'PSDDocument':
        """Create a PSDDocument from a file.
        
        Args:
            filepath: Path to the PSD file to load.
            render_mode: Rendering mode ('full' or 'light')
            
        Returns:
            PSDDocument: A new PSDDocument instance.
            
        Raises:
            FileNotFoundError: If the specified file does not exist.
            PermissionError: If there are permission issues reading the file.
            ValueError: If the file is not a valid PSD.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"PSD file not found: {filepath}")
            
        try:
            psd = PSDImage.open(filepath)
            doc = cls(filepath=filepath, psd=psd)
            doc._render_mode = render_mode
            
            # Create preview path
            preview_path = os.path.splitext(filepath)[0] + '_preview.png'
            
            # Create renderer with preview path
            doc._renderer = create_renderer(psd, render_mode=render_mode, preview_path=preview_path)
            return doc
        except Exception as e:
            logger.error(f"Failed to load PSD from {filepath}: {e}")
            raise ValueError(f"Invalid PSD file: {filepath}") from e
    
    @property
    def filename(self) -> str:
        """Get the filename from the filepath.
        
        Returns:
            str: The base filename or 'Untitled' if no filepath is set.
        """
        if not self.filepath:
            return "Untitled"
        return Path(self.filepath).name
    
    def is_loaded(self) -> bool:
        """Check if a PSD is loaded.
        
        Returns:
            bool: True if a PSD is loaded, False otherwise.
        """
        return self.psd is not None
    
    def cleanup(self) -> None:
        """Clean up resources used by the PSDDocument.
        
        This method should be called when the document is no longer needed
        to ensure proper cleanup of resources.
        """
        try:
            if self._renderer:
                if hasattr(self._renderer, 'cleanup'):
                    self._renderer.cleanup()
                self._renderer = None
            
            if self.psd:
                self.psd.close()
                self.psd = None
            
            # Clean up layer images
            for img in self.layer_images:
                img = None
            self.layer_images.clear()
            
            logger.debug("PSDDocument cleanup completed")
            
        except Exception as e:
            logger.exception("Error during PSDDocument cleanup")
    
    def get_composite_image(self) -> Optional[Image.Image]:
        """Get the composite image of the PSD using the configured renderer.
        
        Returns:
            Optional[Image.Image]: The composite image as a PIL Image, 
            or None if no PSD is loaded.
        """
        if not self._renderer:
            return None
            
        try:
            return self._renderer.get_composite_image()
        except Exception as e:
            logger.error(f"Error generating composite image: {e}")
            return None
    
    def get_scaled_image(self, scale: Optional[float] = None) -> Optional[Image.Image]:
        """Get a scaled version of the composite image.
        
        Args:
            scale: Optional scale factor. If None, uses current_scale.
            
        Returns:
            Optional[Image.Image]: The scaled image, or None if no image is available.
        """
        if not self.psd:
            return None
            
        img = self.get_composite_image()
        if not img:
            return None
            
        scale = scale or self.current_scale
        if scale != 1.0:
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        return img
    
    def get_photo_image(self, scale: Optional[float] = None) -> Optional[ImageTk.PhotoImage]:
        """Get a PhotoImage of the PSD at the specified scale."""
        img = self.get_scaled_image(scale)
        if not img:
            return None
            
        # Convert to PhotoImage and keep a reference to prevent garbage collection
        photo = ImageTk.PhotoImage(img)
        self.layer_images.append(photo)  # Keep reference
        
        # Clean up old images to prevent memory leaks
        if len(self.layer_images) > 5:  # Keep last 5 images
            self.layer_images = self.layer_images[-5:]
            
        return photo
    
    def get_layer_tree(self) -> List[Dict[str, Any]]:
        """Get the layer hierarchy as a tree structure."""
        if not self.psd:
            return []
            
        def process_layer(layer, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
            layer_id = f"{id(layer)}"
            node = {
                'id': layer_id,
                'parent_id': parent_id,
                'name': layer.name,
                'visible': layer.visible,
                'is_group': layer.is_group(),
                'opacity': layer.opacity,
                'children': []
            }
            
            if layer.is_group():
                for child in layer:
                    node['children'].extend(process_layer(child, layer_id))
                    
            return [node]
        
        root_nodes = []
        for layer in self.psd:
            root_nodes.extend(process_layer(layer))
            
        return root_nodes
    
    def set_layer_visibility(self, layer_name: str, visible: bool) -> bool:
        """Set the visibility of a layer by name."""
        if not self.psd:
            return False
            
        def set_visibility(layer, name: str, is_visible: bool) -> bool:
            if layer.name == name:
                layer.visible = is_visible
                return True
            elif layer.is_group():
                for child in layer:
                    if set_visibility(child, name, is_visible):
                        return True
            return False
            
        for layer in self.psd:
            if set_visibility(layer, layer_name, visible):
                return True
                
        return False
    
    def save(self, filepath: Optional[str] = None) -> bool:
        """Save the PSD to a file."""
        if not self.psd:
            return False
            
        try:
            save_path = filepath or self.filepath
            if not save_path:
                return False
                
            self.psd.save(save_path)
            self.filepath = save_path
            return True
        except Exception:
            return False
