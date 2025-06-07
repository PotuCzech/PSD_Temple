"""
PSD Document Model.

This module provides the PSDDocument class which represents a PSD file
with its layers, metadata, and rendering capabilities.
"""
from __future__ import annotations
import os
import logging
from dataclasses import dataclass, field
import json
from typing import List, Dict, Any, Optional, Tuple, Union, cast
from PIL import Image, ImageTk
from psd_tools import PSDImage
from psd_tools.api.layers import Layer, PixelLayer, Group, TypeLayer, ShapeLayer, SmartObjectLayer
from psd_editor.rendering import create_renderer, PSDFullRenderer, PSDLightRenderer

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class PSDDocument:
    """Represents a PSD document with its layers and metadata.
    
    Attributes:
        filepath: Path to the PSD file.
        width: Width of the document.
        height: Height of the document.
        layers: List of layer information dictionaries.
        active_layer: ID of the currently active layer.
        _psd: Internal PSD document reference.
        _renderer: Rendering engine for the PSD.
        _render_mode: Rendering mode ('full' or 'light').
    """
    
    filepath: str
    width: int = 0
    height: int = 0
    layers: List[Dict[str, Any]] = field(default_factory=list)
    active_layer: Optional[int] = None
    _psd: Optional[PSDImage] = None
    _renderer: Optional[Union[PSDFullRenderer, PSDLightRenderer]] = None
    _render_mode: str = 'full'
    
    @classmethod
    def from_file(cls, filepath: str, render_mode: str = 'full') -> 'PSDDocument':
        """Create a PSDDocument from a file.
        
        Args:
            filepath: Path to the PSD file.
            render_mode: Rendering mode ('full' or 'light').
            
        Returns:
            PSDDocument: A new PSDDocument instance.
            
        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file is not a valid PSD.
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")
            
        try:
            psd = PSDImage.open(filepath)
            doc = cls(filepath=filepath, width=psd.width, height=psd.height, _psd=psd)
            doc._render_mode = render_mode
            doc._renderer = create_renderer(render_mode)
            doc._renderer.psd = psd
            doc._parse_layers()
            return doc
        except Exception as e:
            logger.exception(f"Error loading PSD file: {filepath}")
            raise ValueError(f"Invalid PSD file: {str(e)}") from e
    
    def _parse_layers(self) -> None:
        """Parse the PSD layers and store them in a more accessible format."""
        if not self._psd:
            return
            
        self.layers = []
        
        def process_layer(layer: Layer, parent_id: Optional[str] = None) -> None:
            """Recursively process a layer and its children."""
            try:
                layer_data = {
                    'id': str(id(layer)),
                    'name': layer.name,
                    'visible': layer.is_visible(),
                    'opacity': layer.opacity / 255.0,
                    'bounds': layer.bbox,
                    'type': self._get_layer_type(layer),
                    'parent_id': parent_id,
                    'children': []
                }
                
                # Process nested layers if this is a group
                if hasattr(layer, 'layers') and layer.layers:
                    for child in layer.layers:
                        child_id = process_layer(child, layer_data['id'])
                        layer_data['children'].append(child_id)
                
                self.layers.append(layer_data)
                return layer_data['id']
                
            except Exception as e:
                logger.exception(f"Error processing layer: {layer.name}")
                return None
        
        # Start processing from the top-level layers
        for layer in self._psd._layers:
            process_layer(layer)
    
    @staticmethod
    def _get_layer_type(layer: Layer) -> str:
        """Get the type of a layer as a string."""
        if isinstance(layer, PixelLayer):
            return 'pixel'
        elif isinstance(layer, TypeLayer):
            return 'text'
        elif isinstance(layer, ShapeLayer):
            return 'shape'
        elif isinstance(layer, SmartObjectLayer):
            return 'smart_object'
        elif isinstance(layer, Group):
            return 'group'
        return 'unknown'

    def get_composite_image(self) -> Image.Image:
        """Get the composite image of the PSD document.
        
        Returns:
            PIL.Image.Image: The composite image of the PSD.
            
        Raises:
            ValueError: If the PSD document is not loaded.
        """
        if not self._renderer:
            raise ValueError("Renderer not initialized")
            
        return self._renderer.get_composite_image()

    def get_thumbnail(self, size: Tuple[int, int]) -> Image.Image:
        """Get a thumbnail of the PSD.
        
        Args:
            size: The maximum size of the thumbnail as (width, height).
            
        Returns:
            PIL.Image: The thumbnail image.
        """
        if not self._psd:
            return Image.new('RGBA', size, (255, 255, 255, 0))
            
        try:
            # Create a composite image of visible layers
            composite = self._psd.composite()
            
            # Convert to RGBA if needed
            if composite.mode != 'RGBA':
                composite = composite.convert('RGBA')
                
            # Create a transparent background
            bg = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 0))
            
            # Paste the composite on top
            bg.alpha_composite(composite)
            
            # Create thumbnail
            bg.thumbnail(size, Image.LANCZOS)
            return bg
            
        except Exception as e:
            logger.exception("Error creating thumbnail")
            return Image.new('RGBA', size, (255, 255, 255, 0))
    
    def get_layer_image(self, layer_id: str) -> Optional[Image.Image]:
        """Get the image data for a specific layer.
        
        Args:
            layer_id: The ID of the layer to get.
            
        Returns:
            Optional[Image.Image]: The layer image, or None if not found.
        """
        if not self._psd:
            return None
            
        try:
            # Find the layer in the PSD
            def find_layer(layers, target_id):
                for layer in layers:
                    if str(id(layer)) == target_id:
                        return layer
                    if hasattr(layer, 'layers'):
                        found = find_layer(layer.layers, target_id)
                        if found:
                            return found
                return None
                
            layer = find_layer(self._psd.layers, layer_id)
            if not layer:
                return None
                
            # Get the layer image
            image = layer.composite()
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            return image
            
        except Exception as e:
            logger.exception(f"Error getting layer image: {layer_id}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the PSD document to a dictionary.
        
        Returns:
            Dict containing the PSD document structure.
        """
        if not self._psd:
            return {
                'error': 'No PSD loaded',
                'filepath': self.filepath
            }
            
        def layer_to_dict(layer: Layer) -> Dict[str, Any]:
            """Convert a layer to a dictionary."""
            layer_dict = {
                'id': id(layer),
                'name': layer.name,
                'visible': layer.is_visible(),
                'opacity': layer.opacity,
                'blend_mode': layer.blend_mode,
                'type': layer.kind,
                'bbox': layer.bbox if hasattr(layer, 'bbox') else None,
                'left': layer.offset[0],
                'top': layer.offset[1],
                'width': layer.width,
                'height': layer.height,
                'locked': layer.locked,
            }
            
            if isinstance(layer, Group):
                layer_dict['layers'] = [layer_to_dict(child) for child in layer.layers]
                
            return layer_dict
        
        return {
            'filepath': self.filepath,
            'width': self.width,
            'height': self.height,
            'color_mode': str(self._psd.color_mode),
            'channels': self._psd.channels,
            'dpi': self._psd.dpi,
            'layers': [layer_to_dict(layer) for layer in self._psd.descendants()],
            'has_thumbnail': self._psd.has_thumbnail(),
            'has_preview': self._psd.has_preview(),
            'version': self._psd.version,
            'is_visible': self._psd.is_visible(),
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert the PSD document to a JSON string.
        
        Args:
            indent: Number of spaces for indentation. Use None for compact output.
            
        Returns:
            JSON string representation of the PSD document.
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def close(self) -> None:
        """Close the PSD document and release resources."""
        if self._psd:
            try:
                self._psd.close()
                self._psd = None
                self._renderer = None
            except Exception as e:
                logger.error(f"Error closing PSD: {e}")
