"""
Controller for drawing operations and layer management.
"""
import json
import os
from typing import List, Optional, Dict, Any, Callable, Tuple

from tkinter import filedialog, messagebox, colorchooser

from models.drawing import DrawingLayer, ShapeType
from views.drawing_view import DrawingView
from views.layers import LayerManagerView

class DrawingController:
    """Controller for drawing operations and layer management."""
    
    def __init__(self, drawing_view: DrawingView, layer_view: LayerManagerView):
        """Initialize the drawing controller.
        
        Args:
            drawing_view: The drawing view to control.
            layer_view: The layer manager view to control.
        """
        self.drawing_view = drawing_view
        self.layer_view = layer_view
        self.layers: List[DrawingLayer] = []
        self.active_layer_id: Optional[int] = None
        
        # Register callbacks
        self._register_drawing_callbacks()
        self._register_layer_callbacks()
        
        # Add initial layer
        self.add_layer("Layer 1")
    
    def _register_drawing_callbacks(self) -> None:
        """Register callbacks for the drawing view."""
        self.drawing_view.register_callback('add_layer', self.add_layer)
        self.drawing_view.register_callback('delete_layer', self.delete_layer)
        self.drawing_view.register_callback('move_layer', self.move_layer)
        self.drawing_view.register_callback('layer_selected', self.select_layer)
        self.drawing_view.register_callback('visibility_changed', self.toggle_layer_visibility)
    
    def _register_layer_callbacks(self) -> None:
        """Register callbacks for the layer view."""
        self.layer_view.register_callback('add_layer', self.add_layer)
        self.layer_view.register_callback('delete_layer', self.delete_layer)
        self.layer_view.register_callback('move_layer', self.move_layer)
        self.layer_view.register_callback('layer_selected', self.select_layer)
        self.layer_view.register_callback('visibility_changed', self.toggle_layer_visibility)
        
    def update_view(self) -> None:
        """Update the drawing view when switching to this tab."""
        self.drawing_view.redraw_canvas()
        if hasattr(self.layer_view, 'refresh_layers'):
            self.layer_view.refresh_layers()
    
    def add_layer(self, name: Optional[str] = None) -> Optional[DrawingLayer]:
        """Add a new drawing layer.
        
        Args:
            name: Optional name for the layer.
            
        Returns:
            The created DrawingLayer, or None if failed.
        """
        layer = self.drawing_view.add_layer(name)
        if layer:
            self.layers = self.drawing_view.get_layers()
            self.active_layer_id = layer.id
            self._update_layer_view()
            return layer
        return None
    
    def delete_layer(self, layer_id: int) -> None:
        """Delete a layer.
        
        Args:
            layer_id: ID of the layer to delete.
        """
        if len(self.layers) <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last layer")
            return
            
        # Find the layer index
        layer_idx = next((i for i, l in enumerate(self.layers) 
                         if l.id == layer_id), -1)
        
        if layer_idx >= 0:
            # Remove the layer
            del self.layers[layer_idx]
            
            # Update active layer
            if layer_idx >= len(self.layers):
                layer_idx = len(self.layers) - 1
            
            self.active_layer_id = self.layers[layer_idx].id if self.layers else None
            
            # Update views
            self.drawing_view.set_layers(self.layers, self.active_layer_id)
            self._update_layer_view()
    
    def move_layer(self, layer_id: int, direction: str) -> None:
        """Move a layer up or down in the stack.
        
        Args:
            layer_id: ID of the layer to move.
            direction: 'up' or 'down'.
        """
        idx = next((i for i, l in enumerate(self.layers) 
                   if l.id == layer_id), -1)
        
        if direction == 'up' and idx > 0:
            # Swap with the layer above
            self.layers[idx], self.layers[idx-1] = self.layers[idx-1], self.layers[idx]
        elif direction == 'down' and 0 <= idx < len(self.layers) - 1:
            # Swap with the layer below
            self.layers[idx], self.layers[idx+1] = self.layers[idx+1], self.layers[idx]
        else:
            return
        
        # Update views
        self.drawing_view.set_layers(self.layers, self.active_layer_id)
        self._update_layer_view()
    
    def select_layer(self, layer_id: int) -> None:
        """Select a layer.
        
        Args:
            layer_id: ID of the layer to select.
        """
        self.active_layer_id = layer_id
        self.drawing_view.set_active_layer(layer_id)
        self._update_layer_view()
    
    def toggle_layer_visibility(self, layer_id: int, visible: bool) -> None:
        """Toggle the visibility of a layer.
        
        Args:
            layer_id: The ID of the layer to toggle.
            visible: Whether the layer should be visible.
        """
        for layer in self.layers:
            if layer.id == layer_id:
                layer.visible = visible
                self.drawing_view.update_layer_visibility(layer_id, visible)
                self.layer_view.update_layer_visibility(layer_id, visible)
                break
                
    def cleanup(self) -> None:
        """Clean up resources used by the controller.
        
        This method should be called when the controller is no longer needed
        to prevent memory leaks.
        """
        try:
            # Clear all layers
            self.layers.clear()
            self.active_layer_id = None
            
            # Clear view references
            if hasattr(self, 'drawing_view') and self.drawing_view:
                if hasattr(self.drawing_view, 'cleanup'):
                    self.drawing_view.cleanup()
                self.drawing_view = None
                
            if hasattr(self, 'layer_view') and self.layer_view:
                if hasattr(self.layer_view, 'cleanup'):
                    self.layer_view.cleanup()
                self.layer_view = None
                
        except Exception as e:
            import logging
            logging.exception("Error cleaning up DrawingController")
    
    def _update_layer_view(self) -> None:
        """Update the layer view with current layers and active layer."""
        self.layer_view.set_layers(self.layers, self.active_layer_id)
    
    def clear_drawing(self) -> None:
        """Clear all drawing layers."""
        if messagebox.askyesno("Clear Drawing", "Are you sure you want to clear all layers?"):
            self.layers = []
            self.active_layer_id = None
            self.drawing_view.clear()
            self._update_layer_view()
            # Add a default layer
            self.add_layer("Layer 1")
    
    def save_template(self) -> None:
        """Save the current drawing as a template."""
        if not self.layers:
            messagebox.showinfo("Info", "No layers to save")
            return
        
        # Create template data
        template = {
            'version': '1.0',
            'layers': [layer.to_dict() for layer in self.layers]
        }
        
        # Prompt for template name
        template_name = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Template As"
        )
        
        if not template_name:
            return
        
        try:
            with open(template_name, 'w') as f:
                json.dump(template, f, indent=2)
            messagebox.showinfo("Success", f"Template saved to {template_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template: {e}")
    
    def load_template(self) -> None:
        """Load a template from a file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Open Template"
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r') as f:
                template = json.load(f)
            
            # Clear current drawing
            self.layers = []
            self.active_layer_id = None
            
            # Create layers from template
            for layer_data in template.get('layers', []):
                layer = DrawingLayer.from_dict(layer_data)
                self.layers.append(layer)
            
            # Set active layer to the top one
            if self.layers:
                self.active_layer_id = self.layers[-1].id
            
            # Update views
            self.drawing_view.set_layers(self.layers, self.active_layer_id)
            self._update_layer_view()
            
            messagebox.showinfo("Success", f"Template loaded from {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load template: {e}")
    
    def export_image(self) -> None:
        """Export the current drawing as an image."""
        if not self.layers:
            messagebox.showinfo("Info", "No layers to export")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg;*.jpeg"),
                ("All files", "*.*")
            ],
            title="Export As"
        )
        
        if not filepath:
            return
        
        try:
            # Use the drawing view's export functionality
            self.drawing_view.export_image(filepath)
            messagebox.showinfo("Success", f"Drawing exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export drawing: {e}")
