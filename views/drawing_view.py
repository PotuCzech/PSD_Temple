"""
Drawing View component for the PSD Editor.
"""
import tkinter as tk
from tkinter import ttk, colorchooser
from typing import Optional, Dict, Any, List, Tuple, Callable

from models.drawing import ShapeType, DrawingLayer
from views.base import BaseView

class DrawingView(BaseView):
    """View for the drawing canvas and tools."""
    
    def __init__(self, parent: tk.Widget, **kwargs):
        """Initialize the drawing view.
        
        Args:
            parent: The parent widget.
            **kwargs: Additional keyword arguments for the frame.
        """
        self.drawing_layers: List[DrawingLayer] = []
        self.active_layer_id: Optional[int] = None
        self.current_tool: str = "select"
        self.draw_color: str = "#000000"
        self.fill_color: str = "#00000080"
        self.line_width: int = 2
        self.fill_enabled: bool = False
        self.grid_visible: bool = True
        self.grid_type: str = "none"
        self.drawing: bool = False
        self.start_x: float = 0
        self.start_y: float = 0
        self.current_item: Optional[Dict[str, Any]] = None
        self.temp_drawing: Optional[int] = None
        
        super().__init__(parent, **kwargs)
    
    def _setup_ui(self) -> None:
        """Set up the drawing view UI components."""
        # Create main container
        self.main_frame = ttk.Frame(self.frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tools frame
        self.tools_frame = ttk.LabelFrame(self.main_frame, text="Tools")
        self.tools_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create canvas frame
        self.canvas_frame = ttk.Frame(self.main_frame)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbars
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        
        # Create canvas
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg='white',
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set
        )
        
        # Configure scrollbars
        self.h_scrollbar.config(command=self.canvas.xview)
        self.v_scrollbar.config(command=self.canvas.yview)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Add tools
        self._setup_tools()
        
        # Bind events
        self._bind_events()
    
    def _setup_tools(self) -> None:
        """Set up the drawing tools."""
        # Tool selection
        self.tool_var = tk.StringVar(value="select")
        
        tools = [
            ("Select", "select"),
            ("Rectangle", "rectangle"),
            ("Ellipse", "ellipse"),
            ("Line", "line"),
            ("Freehand", "freehand")
        ]
        
        for text, value in tools:
            btn = ttk.Radiobutton(
                self.tools_frame,
                text=text,
                variable=self.tool_var,
                value=value,
                command=self._on_tool_selected
            )
            btn.pack(anchor=tk.W, padx=5, pady=2)
        
        # Color selection
        ttk.Label(self.tools_frame, text="Colors:").pack(anchor=tk.W, padx=5, pady=(10, 2))
        
        self.color_frame = ttk.Frame(self.tools_frame)
        self.color_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.outline_btn = ttk.Button(
            self.color_frame, text="Outline", width=8,
            command=lambda: self._choose_color('outline')
        )
        self.outline_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.fill_btn = ttk.Button(
            self.color_frame, text="Fill", width=8,
            command=lambda: self._choose_color('fill')
        )
        self.fill_btn.pack(side=tk.LEFT)
        
        # Line width
        ttk.Label(self.tools_frame, text="Line Width:").pack(anchor=tk.W, padx=5, pady=(10, 2))
        self.width_var = tk.IntVar(value=self.line_width)
        width_spin = ttk.Spinbox(
            self.tools_frame,
            from_=1, to=20,
            textvariable=self.width_var,
            width=5,
            command=self._on_width_changed
        )
        width_spin.pack(anchor=tk.W, padx=5, pady=2)
        
        # Fill toggle
        self.fill_var = tk.BooleanVar(value=self.fill_enabled)
        fill_check = ttk.Checkbutton(
            self.tools_frame,
            text="Fill",
            variable=self.fill_var,
            command=self._on_fill_toggled
        )
        fill_check.pack(anchor=tk.W, padx=5, pady=2)
        
        # Grid options
        ttk.Separator(self.tools_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(self.tools_frame, text="Grid:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.grid_var = tk.StringVar(value=self.grid_type)
        grid_types = ["None", "Lines", "Dots", "Cross"]
        for gtype in grid_types:
            btn = ttk.Radiobutton(
                self.tools_frame,
                text=gtype,
                variable=self.grid_var,
                value=gtype.lower(),
                command=self._on_grid_changed
            )
            btn.pack(anchor=tk.W, padx=5, pady=1)
        
        # Grid visibility toggle
        self.grid_visible_var = tk.BooleanVar(value=self.grid_visible)
        grid_visible_check = ttk.Checkbutton(
            self.tools_frame,
            text="Show Grid",
            variable=self.grid_visible_var,
            command=self._on_grid_visibility_changed
        )
        grid_visible_check.pack(anchor=tk.W, padx=5, pady=2)
    
    def _bind_events(self) -> None:
        """Bind canvas events."""
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
    
    def _on_tool_selected(self) -> None:
        """Handle tool selection."""
        self.current_tool = self.tool_var.get()
    
    def _choose_color(self, color_type: str) -> None:
        """Choose a color for outline or fill."""
        current_color = self.draw_color if color_type == 'outline' else self.fill_color
        color = colorchooser.askcolor(
            initialcolor=current_color,
            title=f"Choose {color_type.capitalize()} Color"
        )
        
        if color[1]:  # User didn't cancel
            if color_type == 'outline':
                self.draw_color = color[1]
                self.outline_btn.config(style=f"Color.TButton")
            else:
                self.fill_color = color[1] + '80'  # Add transparency
                self.fill_btn.config(style=f"Color.TButton")
    
    def _on_width_changed(self) -> None:
        """Handle line width change."""
        try:
            self.line_width = int(self.width_var.get())
        except ValueError:
            pass
    
    def _on_fill_toggled(self) -> None:
        """Handle fill toggle."""
        self.fill_enabled = self.fill_var.get()
    
    def _on_grid_changed(self) -> None:
        """Handle grid type change."""
        self.grid_type = self.grid_var.get()
        self._draw_grid()
    
    def _on_grid_visibility_changed(self) -> None:
        """Handle grid visibility change."""
        self.grid_visible = self.grid_visible_var.get()
        self._draw_grid()
    
    def _on_mouse_down(self, event: tk.Event) -> None:
        """Handle mouse button press."""
        if not self.active_layer_id:
            return
            
        self.drawing = True
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        if self.current_tool == 'freehand':
            self._start_freehand()
    
    def _on_mouse_drag(self, event: tk.Event) -> None:
        """Handle mouse drag."""
        if not self.drawing or not self.active_layer_id:
            return
            
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if self.current_tool == 'freehand':
            self._continue_freehand(x, y)
        else:
            self._update_shape_preview(x, y)
    
    def _on_mouse_up(self, event: tk.Event) -> None:
        """Handle mouse button release."""
        if not self.drawing or not self.active_layer_id:
            return
            
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if self.current_tool == 'freehand':
            self._end_freehand()
        else:
            self._complete_shape(x, y)
        
        self.drawing = False
        self.current_item = None
    
    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Handle canvas resize."""
        self._draw_grid()
    
    def _start_freehand(self) -> None:
        """Start a freehand drawing."""
        layer = self._get_active_layer()
        if not layer:
            return
            
        self.current_item = {
            'type': 'freehand',
            'coords': [self.start_x, self.start_y],
            'outline': self.draw_color,
            'width': self.line_width
        }
        
        # Add the initial point to the layer
        layer.add_shape(
            ShapeType.FREEHAND,
            [self.start_x, self.start_y],
            outline=self.draw_color,
            width=self.line_width
        )
        
        # Redraw to show the new shape
        self.redraw_canvas()
    
    def _continue_freehand(self, x: float, y: float) -> None:
        """Continue a freehand drawing."""
        if not self.current_item or self.current_item['type'] != 'freehand':
            return
            
        # Add the current point to the coordinates
        self.current_item['coords'].extend([x, y])
        
        # Update the last shape in the active layer
        layer = self._get_active_layer()
        if layer and layer.shapes:
            layer.shapes[-1] = self.current_item
            self.redraw_canvas()
    
    def _end_freehand(self) -> None:
        """End a freehand drawing."""
        self.current_item = None
    
    def _update_shape_preview(self, x: float, y: float) -> None:
        """Update the preview of the current shape."""
        if self.temp_drawing:
            self.canvas.delete(self.temp_drawing)
        
        if self.current_tool == 'rectangle':
            self.temp_drawing = self.canvas.create_rectangle(
                self.start_x, self.start_y, x, y,
                outline=self.draw_color,
                fill=self.fill_color if self.fill_enabled else '',
                width=self.line_width
            )
        elif self.current_tool == 'ellipse':
            self.temp_drawing = self.canvas.create_oval(
                self.start_x, self.start_y, x, y,
                outline=self.draw_color,
                fill=self.fill_color if self.fill_enabled else '',
                width=self.line_width
            )
        elif self.current_tool == 'line':
            self.temp_drawing = self.canvas.create_line(
                self.start_x, self.start_y, x, y,
                fill=self.draw_color,
                width=self.line_width
            )
    
    def _complete_shape(self, x: float, y: float) -> None:
        """Complete the current shape and add it to the active layer."""
        layer = self._get_active_layer()
        if not layer:
            return
            
        if self.temp_drawing:
            self.canvas.delete(self.temp_drawing)
            self.temp_drawing = None
        
        if self.current_tool == 'rectangle':
            layer.add_shape(
                ShapeType.RECTANGLE,
                [self.start_x, self.start_y, x, y],
                outline=self.draw_color,
                fill=self.fill_color if self.fill_enabled else '',
                width=self.line_width
            )
        elif self.current_tool == 'ellipse':
            layer.add_shape(
                ShapeType.ELLIPSE,
                [self.start_x, self.start_y, x, y],
                outline=self.draw_color,
                fill=self.fill_color if self.fill_enabled else '',
                width=self.line_width
            )
        elif self.current_tool == 'line':
            layer.add_shape(
                ShapeType.LINE,
                [self.start_x, self.start_y, x, y],
                outline=self.draw_color,
                width=self.line_width
            )
        
        # Redraw to show the new shape
        self.redraw_canvas()
    
    def _draw_grid(self) -> None:
        """Draw the grid on the canvas."""
        if not self.grid_visible or self.grid_type == 'none':
            self.canvas.delete('grid')
            return
            
        self.canvas.delete('grid')
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width <= 1 or height <= 1:  # Canvas not yet visible
            return
            
        spacing = 20  # Grid spacing in pixels
        
        # Draw vertical lines
        for x in range(0, width, spacing):
            self.canvas.create_line(
                x, 0, x, height,
                fill='#e0e0e0',
                tags='grid',
                dash=(2, 2) if self.grid_type == 'dots' else None
            )
        
        # Draw horizontal lines
        for y in range(0, height, spacing):
            self.canvas.create_line(
                0, y, width, y,
                fill='#e0e0e0',
                tags='grid',
                dash=(2, 2) if self.grid_type == 'dots' else None
            )
        
        # Bring grid to back
        self.canvas.tag_lower('grid')
    
    def _get_active_layer(self) -> Optional[DrawingLayer]:
        """Get the currently active layer."""
        if not self.active_layer_id:
            return None
            
        for layer in self.drawing_layers:
            if layer.id == self.active_layer_id:
                return layer
        return None
    
    def redraw_canvas(self) -> None:
        """Redraw all layers on the canvas."""
        self.canvas.delete('all')
        self._draw_grid()
        
        # Draw all layers from bottom to top
        for layer in self.drawing_layers:
            if layer.visible:
                layer.draw(self.canvas)
    
    def add_layer(self, name: str = None) -> Optional[DrawingLayer]:
        """Add a new drawing layer.
        
        Args:
            name: Optional name for the layer.
            
        Returns:
            The created DrawingLayer, or None if failed.
        """
        if not name:
            name = f"Layer {len(self.drawing_layers) + 1}"
            
        # Generate a unique ID
        layer_id = max((layer.id for layer in self.drawing_layers), default=0) + 1
        
        # Create the layer
        layer = DrawingLayer(
            id=layer_id,
            name=name,
            color=self.draw_color,
            visible=True
        )
        
        self.drawing_layers.append(layer)
        self.active_layer_id = layer_id
        
        # Redraw to show the new layer
        self.redraw_canvas()
        
        return layer
    
    def set_active_layer(self, layer_id: int) -> None:
        """Set the active layer by ID.
        
        Args:
            layer_id: ID of the layer to activate.
        """
        self.active_layer_id = layer_id
    
    def get_active_layer(self) -> Optional[DrawingLayer]:
        """Get the currently active layer.
        
        Returns:
            The active DrawingLayer, or None if no layer is active.
        """
        return self._get_active_layer()
    
    def get_layers(self) -> List[DrawingLayer]:
        """Get all drawing layers.
        
        Returns:
            List of all DrawingLayer objects.
        """
        return self.drawing_layers
    
    def clear(self) -> None:
        """Clear the drawing canvas."""
        self.drawing_layers = []
        self.active_layer_id = None
        self.redraw_canvas()
