"""
Drawing models for the PSD Editor.
"""
from typing import List, Dict, Any, Optional, Tuple
import tkinter as tk
from dataclasses import dataclass, field
from enum import Enum, auto

class ShapeType(Enum):
    RECTANGLE = auto()
    ELLIPSE = auto()
    LINE = auto()
    FREEHAND = auto()

@dataclass
class Shape:
    """Represents a drawable shape on a layer."""
    shape_type: ShapeType
    coords: List[float]
    outline: str = "#000000"
    fill: str = ""
    width: int = 1
    
    def draw(self, canvas: tk.Canvas, offset: Tuple[int, int] = (0, 0)) -> None:
        """Draw the shape on the given canvas."""
        coords = [c + offset[i % 2] for i, c in enumerate(self.coords)]
        
        if self.shape_type == ShapeType.RECTANGLE:
            return canvas.create_rectangle(*coords, outline=self.outline, 
                                       fill=self.fill, width=self.width)
        elif self.shape_type == ShapeType.ELLIPSE:
            return canvas.create_oval(*coords, outline=self.outline, 
                                   fill=self.fill, width=self.width)
        elif self.shape_type == ShapeType.LINE:
            return canvas.create_line(*coords, fill=self.outline, 
                                   width=self.width)
        elif self.shape_type == ShapeType.FREEHAND:
            return canvas.create_line(*coords, fill=self.outline, 
                                   width=self.width, smooth=True)

class DrawingLayer:
    """Represents a layer containing drawable shapes."""
    
    def __init__(self, id: int, name: str, color: str, visible: bool = True):
        self.id = id
        self.name = name
        self.color = color
        self.visible = visible
        self.fill_enabled = False
        self.fill_color = color + '80'  # Add transparency
        self.line_width = 2
        self.shapes: List[Shape] = []
    
    def __repr__(self) -> str:
        return f"<DrawingLayer id={self.id} name='{self.name}' visible={self.visible} shapes={len(self.shapes)}>"
    
    def add_shape(self, shape_type: ShapeType, coords: List[float], **kwargs) -> Shape:
        """Add a shape to this layer."""
        shape = Shape(
            shape_type=shape_type,
            coords=coords,
            outline=kwargs.get('outline', self.color),
            fill=kwargs.get('fill', self.fill_color if self.fill_enabled else ''),
            width=kwargs.get('width', self.line_width)
        )
        self.shapes.append(shape)
        return shape
    
    def draw(self, canvas: tk.Canvas, offset: Tuple[int, int] = (0, 0)) -> None:
        """Draw all shapes in this layer on the canvas."""
        if not self.visible:
            return
            
        for shape in self.shapes:
            shape.draw(canvas, offset)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert layer to a dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'visible': self.visible,
            'fill_enabled': self.fill_enabled,
            'fill_color': self.fill_color,
            'line_width': self.line_width,
            'shapes': [
                {
                    'type': shape.shape_type.name,
                    'coords': shape.coords,
                    'outline': shape.outline,
                    'fill': shape.fill,
                    'width': shape.width
                }
                for shape in self.shapes
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawingLayer':
        """Create a layer from a dictionary."""
        layer = cls(
            id=data.get('id', 0),
            name=data.get('name', 'Layer'),
            color=data.get('color', '#000000'),
            visible=data.get('visible', True)
        )
        layer.fill_enabled = data.get('fill_enabled', False)
        layer.fill_color = data.get('fill_color', layer.color + '80')
        layer.line_width = data.get('line_width', 2)
        
        # Convert shape dictionaries back to Shape objects
        for shape_data in data.get('shapes', []):
            shape_type = ShapeType[shape_data['type']]
            layer.add_shape(
                shape_type=shape_type,
                coords=shape_data['coords'],
                outline=shape_data.get('outline', layer.color),
                fill=shape_data.get('fill', ''),
                width=shape_data.get('width', layer.line_width)
            )
            
        return layer
