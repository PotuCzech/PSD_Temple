"""
Layer management view for the PSD Editor.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Dict, Any, Callable

from models.drawing import DrawingLayer
from views.base import BaseView

class LayerManagerView(BaseView):
    """View for managing drawing layers."""
    
    def __init__(self, parent: tk.Widget, **kwargs):
        """Initialize the layer manager view.
        
        Args:
            parent: The parent widget.
            **kwargs: Additional keyword arguments for the frame.
        """
        self.layers: List[DrawingLayer] = []
        self.active_layer_id: Optional[int] = None
        self._layer_buttons: Dict[int, ttk.Button] = {}
        self._visibility_vars: Dict[int, tk.BooleanVar] = {}
        
        super().__init__(parent, **kwargs)
    
    def _setup_ui(self) -> None:
        """Set up the layer manager UI components."""
        # Create main container
        self.main_frame = ttk.Frame(self.frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        self.toolbar = ttk.Frame(self.main_frame)
        self.toolbar.pack(fill=tk.X, padx=2, pady=2)
        
        # Add layer button
        self.add_btn = ttk.Button(
            self.toolbar, text="+", width=3,
            command=self._on_add_layer
        )
        self.add_btn.pack(side=tk.LEFT, padx=2)
        
        # Delete layer button
        self.del_btn = ttk.Button(
            self.toolbar, text="-", width=3,
            command=self._on_delete_layer
        )
        self.del_btn.pack(side=tk.LEFT, padx=2)
        
        # Move up button
        self.up_btn = ttk.Button(
            self.toolbar, text="↑", width=3,
            command=self._on_move_up
        )
        self.up_btn.pack(side=tk.LEFT, padx=2)
        
        # Move down button
        self.down_btn = ttk.Button(
            self.toolbar, text="↓", width=3,
            command=self._on_move_down
        )
        self.down_btn.pack(side=tk.LEFT, padx=2)
        
        # Create layers container with scrollbar
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(
            self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        
        self.layers_frame = ttk.Frame(self.canvas)
        self.layers_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.layers_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mouse wheel for scrolling
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.layers_frame.bind("<MouseWheel>", self._on_mouse_wheel)
    
    def set_layers(self, layers: List[DrawingLayer], active_layer_id: Optional[int] = None) -> None:
        """Set the layers to display in the manager.
        
        Args:
            layers: List of DrawingLayer objects.
            active_layer_id: ID of the currently active layer.
        """
        self.layers = layers
        self.active_layer_id = active_layer_id
        self._update_layers_display()
    
    def set_active_layer(self, layer_id: int) -> None:
        """Set the active layer.
        
        Args:
            layer_id: ID of the layer to activate.
        """
        self.active_layer_id = layer_id
        self._update_layers_display()
    
    def _update_layers_display(self) -> None:
        """Update the display of layers."""
        # Clear existing layer buttons
        for widget in self.layers_frame.winfo_children():
            widget.destroy()
        
        self._layer_buttons = {}
        self._visibility_vars = {}
        
        # Add layers in reverse order (top to bottom)
        for layer in reversed(self.layers):
            self._add_layer_button(layer)
    
    def _add_layer_button(self, layer: DrawingLayer) -> None:
        """Add a button for a layer.
        
        Args:
            layer: The DrawingLayer to create a button for.
        """
        frame = ttk.Frame(self.layers_frame)
        frame.pack(fill=tk.X, pady=1)
        
        # Visibility checkbox
        var = tk.BooleanVar(value=layer.visible)
        self._visibility_vars[layer.id] = var
        
        def on_visibility_changed():
            layer.visible = var.get()
            self.trigger_callback('visibility_changed', layer.id, var.get())
        
        check = ttk.Checkbutton(
            frame, variable=var, command=on_visibility_changed
        )
        check.pack(side=tk.LEFT, padx=2)
        
        # Layer name button
        style = 'Active.TButton' if layer.id == self.active_layer_id else 'TButton'
        btn = ttk.Button(
            frame,
            text=layer.name,
            style=style,
            command=lambda l=layer: self._on_layer_selected(l.id)
        )
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Store reference to the button
        self._layer_buttons[layer.id] = btn
    
    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """Handle mouse wheel for scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_add_layer(self) -> None:
        """Handle add layer button click."""
        self.trigger_callback('add_layer')
    
    def _on_delete_layer(self) -> None:
        """Handle delete layer button click."""
        if self.active_layer_id is not None:
            self.trigger_callback('delete_layer', self.active_layer_id)
    
    def _on_move_up(self) -> None:
        """Handle move up button click."""
        if self.active_layer_id is not None:
            self.trigger_callback('move_layer', self.active_layer_id, 'up')
    
    def _on_move_down(self) -> None:
        """Handle move down button click."""
        if self.active_layer_id is not None:
            self.trigger_callback('move_layer', self.active_layer_id, 'down')
    
    def _on_layer_selected(self, layer_id: int) -> None:
        """Handle layer button click.
        
        Args:
            layer_id: ID of the selected layer.
        """
        self.active_layer_id = layer_id
        self._update_layers_display()
        self.trigger_callback('layer_selected', layer_id)
