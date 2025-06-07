import os
import sys
import random
import json
import io
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union

import numpy as np
from PIL import Image, ImageTk, ImageEnhance, ImageDraw, ImageGrab
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from psd_tools import PSDImage

# Constants
DEFAULT_DRAW_COLOR = "#ff0000"
DEFAULT_FILL_COLOR = "#ff000080"  # Semi-transparent red
DEFAULT_GRID_COLOR = "#E0E0E0"

# Drawing tools and UI constants
DRAW_TOOLS = ["Select", "Rectangle", "Ellipse", "Line", "Freehand"]
GRID_TYPES = ["None", "Square", "Golden Ratio", "Rule of Thirds", "Dots", "Lines"]

# Color palette for auto-assigning colors to layers
COLOR_PALETTE = [
    "#FF5252", "#FF4081", "#E040FB", "#7C4DFF", "#536DFE",
    "#448AFF", "#40C4FF", "#18FFFF", "#64FFDA", "#69F0AE",
    "#B2FF59", "#EEFF41", "#FFFF00", "#FFD740", "#FFAB40"
]

class DrawingLayer:
    def __init__(self, id: int, name: str, color: str, visible: bool = True):
        self.id = id
        self.name = name
        self.color = color
        self.visible = visible
        self.fill_enabled = False
        self.fill_color = color + '80'  # Add transparency
        self.line_width = 2
        self.shapes = []  # List to store shapes in this layer
        
    def __repr__(self):
        return f"<DrawingLayer id={self.id} name='{self.name}' visible={self.visible} shapes={len(self.shapes)}>"
    
    def add_shape(self, shape_type: str, coords: List[float], **kwargs):
        """Add a shape to this layer"""
        shape = {
            'type': shape_type,
            'coords': coords,
            'outline': kwargs.get('outline', self.color),
            'fill': kwargs.get('fill', self.fill_color if self.fill_enabled else ''),
            'width': kwargs.get('width', self.line_width)
        }
        self.shapes.append(shape)
        return shape
    
    def draw(self, canvas: tk.Canvas, offset: Tuple[int, int] = (0, 0)):
        """Draw all shapes in this layer on the canvas"""
        if not self.visible:
            return
            
        for shape in self.shapes:
            coords = [c + offset[i % 2] for i, c in enumerate(shape['coords'])]
            
            if shape['type'] == 'rectangle':
                canvas.create_rectangle(
                    *coords,
                    outline=shape['outline'],
                    fill=shape['fill'],
                    width=shape['width']
                )
            elif shape['type'] == 'ellipse':
                canvas.create_oval(
                    *coords,
                    outline=shape['outline'],
                    fill=shape['fill'],
                    width=shape['width']
                )
            elif shape['type'] == 'line':
                canvas.create_line(
                    *coords,
                    fill=shape['outline'],
                    width=shape['width']
                )
            elif shape['type'] == 'freehand':
                canvas.create_line(
                    *coords,
                    fill=shape['outline'],
                    width=shape['width'],
                    smooth=True
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert layer to a dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'visible': self.visible,
            'fill_enabled': self.fill_enabled,
            'fill_color': self.fill_color,
            'line_width': self.line_width,
            'shapes': self.shapes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawingLayer':
        """Create a layer from a dictionary"""
        layer = cls(
            id=data.get('id', 0),
            name=data.get('name', 'Layer'),
            color=data.get('color', '#000000'),
            visible=data.get('visible', True)
        )
        layer.fill_enabled = data.get('fill_enabled', False)
        layer.fill_color = data.get('fill_color', layer.color + '80')
        layer.line_width = data.get('line_width', 2)
        layer.shapes = data.get('shapes', [])
        return layer

class PSDEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PSD Layer Editor & Template Creator")
        self.root.geometry("1400x900")
        
        self.psd: Optional[PSDImage] = None
        self.current_psd_path: Optional[str] = None
        self.layer_images = []  # To prevent garbage collection
        self.current_scale = 1.0
        
        # Drawing state
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        self.current_item = None
        self.current_tool = "Select"
        self.draw_color = DEFAULT_DRAW_COLOR
        self.line_width = 2
        self.fill_enabled = False
        self.grid_type = "None"
        self.grid_color = DEFAULT_GRID_COLOR
        self.grid_visible = True
        self.temp_drawing = None
        self.drawn_items = []  # Initialize drawn items list
        self.drawing_canvas = None  # Initialize drawing canvas reference
        
        # Layer management
        self.drawing_layers: List[DrawingLayer] = []
        self.current_layer_id = 0
        self.active_layer_id = 0
        
        # Template state
        self.template_mode = False
        self.template_layers = {}
        
        self.setup_ui()
        self.create_new_layer("Background")
        
    def create_new_layer(self, name: str = None) -> DrawingLayer:
        """Create a new drawing layer"""
        if name is None:
            name = f"Layer {len(self.drawing_layers) + 1}"
        
        # Get a random color from the palette
        color = random.choice(COLOR_PALETTE)
        
        # Create and add the new layer
        layer = DrawingLayer(
            id=len(self.drawing_layers),
            name=name,
            color=color
        )
        
        self.drawing_layers.append(layer)
        self.active_layer_id = layer.id
        self.update_layer_list()
        return layer
        
    def update_layer_list(self):
        """Update the layer list in the UI"""
        if not hasattr(self, 'layer_listbox'):
            return
            
        self.layer_listbox.delete(0, tk.END)
        for layer in reversed(self.drawing_layers):
            visibility = "●" if layer.visible else "○"
            self.layer_listbox.insert(tk.END, f"{visibility} {layer.name}")
            
        # Select the active layer
        if self.drawing_layers:
            idx = len(self.drawing_layers) - 1 - next(
                i for i, l in enumerate(reversed(self.drawing_layers)) 
                if l.id == self.active_layer_id
            )
            self.layer_listbox.selection_clear(0, tk.END)
            self.layer_listbox.selection_set(idx)
            self.layer_listbox.see(idx)
    
    def get_active_layer(self) -> Optional[DrawingLayer]:
        """Get the currently active layer"""
        for layer in self.drawing_layers:
            if layer.id == self.active_layer_id:
                return layer
        return None
        
    def setup_ui(self):
        # Configure root window
        self.root.title("PSD Editor & Template Creator")
        self.root.geometry("1400x900")
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Layer management
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Configure grid weights for left panel
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)
        
        # PSD Layers
        psd_layer_frame = ttk.LabelFrame(left_panel, text="PSD Layers", padding=5)
        psd_layer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # PSD Layer treeview
        self.layer_tree = ttk.Treeview(psd_layer_frame, selectmode='browse', show='tree', height=10)
        self.layer_tree.heading('#0', text='PSD Layers', anchor='w')
        
        # Add scrollbar to layer tree
        tree_scroll = ttk.Scrollbar(psd_layer_frame, orient=tk.VERTICAL, command=self.layer_tree.yview)
        self.layer_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Pack the tree and scrollbar
        self.layer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Drawing Layers
        drawing_layer_frame = ttk.LabelFrame(left_panel, text="Drawing Layers", padding=5)
        drawing_layer_frame.pack(fill=tk.BOTH, expand=True)
        
        # Layer listbox with scrollbar
        layer_list_frame = ttk.Frame(drawing_layer_frame)
        layer_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(layer_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.layer_listbox = tk.Listbox(
            layer_list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            exportselection=0
        )
        self.layer_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.layer_listbox.yview)
        
        # Layer controls
        btn_frame = ttk.Frame(drawing_layer_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(btn_frame, text="+", width=3, command=self.create_new_layer).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="-", width=3, command=self.delete_layer).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="↑", width=3, command=self.move_layer_up).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="↓", width=3, command=self.move_layer_down).pack(side=tk.LEFT, padx=1)
        
        # Right panel - Notebook for PSD and Drawing tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # PSD View Tab
        psd_frame = ttk.Frame(self.notebook)
        self.notebook.add(psd_frame, text="PSD View")
        
        # Drawing Tab
        self.drawing_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.drawing_frame, text="Drawing")
        
        # Bind events
        self.layer_listbox.bind('<<ListboxSelect>>', self.on_layer_select)
        
        # Toolbar for PSD view
        toolbar = ttk.Frame(psd_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Buttons
        ttk.Button(toolbar, text="Open PSD", command=self.open_psd).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save PSD", command=self.save_psd).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Export Image", command=self.export_image).pack(side=tk.LEFT, padx=2)
        
        # Canvas with scrollbars for PSD view
        self.psd_canvas_container = ttk.Frame(psd_frame)
        self.psd_canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with initial size
        self.canvas = tk.Canvas(self.psd_canvas_container, bg='#2e2e2e', cursor='cross')
        
        # Add scrollbars
        h_scroll = ttk.Scrollbar(self.psd_canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(self.psd_canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        # Grid layout with weights
        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        self.psd_canvas_container.grid_rowconfigure(0, weight=1)
        self.psd_canvas_container.grid_columnconfigure(0, weight=1)
        
        # Bind resize event
        self.psd_canvas_container.bind('<Configure>', self.on_psd_canvas_configure)
        
        # Setup drawing canvas
        self.setup_drawing_canvas()
        
        # Layer properties
        props_frame = ttk.LabelFrame(psd_frame, text="Layer Properties", padding=5)
        props_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Layer opacity control
        ttk.Label(props_frame, text="Opacity:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.opacity_var = tk.DoubleVar(value=100)
        opacity_scale = ttk.Scale(
            props_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.opacity_var, command=self.update_layer_opacity
        )
        opacity_scale.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        
        # Bind events
        self.layer_tree.bind('<<TreeviewSelect>>', self.on_layer_select)
        self.canvas.bind('<MouseWheel>', self.zoom_with_wheel)  # Windows
        self.canvas.bind('<Button-4>', self.zoom_in)  # Linux
        self.canvas.bind('<Button-5>', self.zoom_out)  # Linux
        
        # Menu
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open PSD", command=self.open_psd)
        file_menu.add_command(label="Save PSD", command=self.save_psd)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Toggle Layer Visibility", command=self.toggle_layer_visibility)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        self.root.config(menu=menubar)
    
    def open_psd(self):
        file_path = filedialog.askopenfilename(
            title="Open PSD File",
            filetypes=(("PSD Files", "*.psd"), ("All Files", "*.*"))
        )
        
        if not file_path:
            return
            
        try:
            self.psd = PSDImage.open(file_path)
            self.current_psd_path = file_path
            self.update_layer_tree()
            self.render_canvas()
            self.root.title(f"PSD Layer Editor - {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PSD file: {str(e)}")
    
    def update_layer_tree(self):
        self.layer_tree.delete(*self.layer_tree.get_children())
        
        def add_layers(parent, layer):
            if layer.is_group():
                node = self.layer_tree.insert(parent, 'end', text=f"📁 {layer.name}", open=True)
                for child in reversed(layer):
                    add_layers(node, child)
            else:
                visible = "●" if layer.visible else "○"
                self.layer_tree.insert(parent, 'end', text=f"{visible} {layer.name}", values=(layer.visible,))
        
        if self.psd:
            for layer in reversed(self.psd):
                add_layers('', layer)
    
    def render_canvas(self):
        if not self.psd:
            return
            
        # Clear canvas
        self.canvas.delete("all")
        self.layer_images.clear()
        
        # Create a composite image
        img = self.psd.composite()
        
        # Scale the image if needed
        if hasattr(self, 'current_scale') and self.current_scale != 1.0:
            new_width = int(img.width * self.current_scale)
            new_height = int(img.height * self.current_scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(img)
        
        # Update canvas size
        self.canvas.config(width=img.width, height=img.height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Update scroll region
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Center the image in the scrollable area
        self.center_image()
    
    def center_image(self):
        """Center the image in the scrollable area"""
        if not hasattr(self, 'photo'):
            return
            
        # Get the canvas size and image size
        canvas_width = self.psd_canvas_container.winfo_width()
        canvas_height = self.psd_canvas_container.winfo_height()
        
        # Calculate the position to center the image
        x = max(0, (canvas_width - self.photo.width()) // 2)
        y = max(0, (canvas_height - self.photo.height()) // 2)
        
        # Update the canvas scroll region and position
        self.canvas.config(scrollregion=(-x, -y, 
                                      max(canvas_width, self.photo.width() - x), 
                                      max(canvas_height, self.photo.height() - y)))
    
    def toggle_psd_layer_visibility(self, layer_name, visible):
        """Toggle visibility of a PSD layer by name"""
        if not self.psd:
            return
            
        def set_visibility(layer, name, is_visible):
            if layer.name == name:
                layer.visible = is_visible
                return True
            elif hasattr(layer, 'layers'):
                for child in layer.layers:
                    if set_visibility(child, name, is_visible):
                        return True
            return False
            
        set_visibility(self.psd, layer_name, visible)
        self.render_canvas()
    
    def on_layer_select(self, event):
        selection = self.layer_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        layer_name = self.layer_tree.item(item, 'text').lstrip("●○📁 ")
        
        # Find the layer in the PSD
        def find_layer(layer, name):
            if layer.name == name:
                return layer
            if layer.is_group():
                for child in layer:
                    found = find_layer(child, name)
                    if found:
                        return found
            return None
            
        for layer in self.psd:
            found = find_layer(layer, layer_name)
            if found:
                self.current_layer = found
                self.opacity_var.set(round(found.opacity * 100))
                break
    
    def update_layer_opacity(self, value):
        if hasattr(self, 'current_layer'):
            self.current_layer.opacity = float(value) / 100
            self.render_canvas()
    
    def toggle_layer_visibility(self):
        if hasattr(self, 'current_layer'):
            self.current_layer.visible = not self.current_layer.visible
            self.update_layer_tree()
            self.render_canvas()
    
    def zoom_with_wheel(self, event):
        if event.delta > 0:
            self.zoom_in(event)
        else:
            self.zoom_out(event)
    
    def zoom_in(self, event=None):
        self.current_scale *= 1.1
        self._update_zoom()
    
    def zoom_out(self, event=None):
        self.current_scale = max(0.1, self.current_scale / 1.1)
        self._update_zoom()
    
    def _update_zoom(self):
        if hasattr(self, 'photo'):
            # Get current scroll position
            x = self.canvas.canvasx(0)
            y = self.canvas.canvasy(0)
            
            # Apply zoom
            self.canvas.scale("all", 0, 0, self.current_scale, self.current_scale)
            
            # Update scroll region and position
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.canvas.xview_moveto(x / self.psd.width)
            self.canvas.yview_moveto(y / self.psd.height)
    
    def save_psd(self):
        if not self.psd:
            messagebox.showwarning("No PSD", "No PSD file is currently open.")
            return
            
        if not self.current_psd_path:
            self.current_psd_path = filedialog.asksaveasfilename(
                defaultextension=".psd",
                filetypes=(("PSD Files", "*.psd"), ("All Files", "*.*")),
                initialfile="modified.psd"
            )
            if not self.current_psd_path:
                return
        
        try:
            self.psd.save(self.current_psd_path)
            messagebox.showinfo("Success", f"PSD saved successfully to {self.current_psd_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PSD: {str(e)}")
    
    def export_image(self):
        if not self.psd:
            messagebox.showwarning("No PSD", "No PSD file is currently open.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=(
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg;*.jpeg"),
                ("All Files", "*.*")
            ),
            initialfile="exported.png"
        )
        
        if not file_path:
            return
            
        try:
            img = self.psd.composite()
            img.save(file_path)
            messagebox.showinfo("Success", f"Image exported successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export image: {str(e)}")

    def on_psd_canvas_configure(self, event):
        """Handle PSD canvas resize events"""
        if hasattr(self, 'photo'):
            # Get the available size
            container_width = self.psd_canvas_container.winfo_width() - 20  # Account for scrollbar
            container_height = self.psd_canvas_container.winfo_height() - 20  # Account for scrollbar
            
            # Calculate scale to fit
            scale_x = container_width / self.psd.width if self.psd.width > 0 else 1
            scale_y = container_height / self.psd.height if self.psd.height > 0 else 1
            self.current_scale = min(scale_x, scale_y, 1.0)  # Don't scale up beyond 100%
            
            # Apply the scale
            self.render_canvas()
    
    def setup_drawing_canvas(self):
        # Main container for drawing tools and canvas
        main_container = ttk.Frame(self.drawing_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Tools
        left_panel = ttk.Frame(main_container, width=200)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Toolbox frame
        toolbox_frame = ttk.LabelFrame(left_panel, text="Tools", padding=5)
        toolbox_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Add drawing tools as radio buttons
        tool_var = tk.StringVar(value=self.current_tool)
        for tool in DRAW_TOOLS:
            btn = ttk.Radiobutton(
                toolbox_frame,
                text=tool,
                value=tool,
                variable=tool_var,
                command=lambda t=tool: self.set_tool(t)
            )
            btn.pack(anchor='w', padx=2, pady=1)
        
        # Color settings
        color_frame = ttk.LabelFrame(left_panel, text="Colors", padding=5)
        color_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Outline color
        ttk.Label(color_frame, text="Outline:").pack(anchor='w')
        self.outline_btn = tk.Button(
            color_frame,
            bg=self.draw_color,
            width=10,
            command=lambda: self.choose_color('outline')
        )
        self.outline_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Fill color
        self.fill_var = tk.BooleanVar(value=self.fill_enabled)
        ttk.Checkbutton(
            color_frame,
            text="Fill Shape",
            variable=self.fill_var,
            command=self.toggle_fill
        ).pack(anchor='w', pady=(0, 5))
        
        # Line width
        ttk.Label(color_frame, text="Line Width:").pack(anchor='w')
        self.line_width_var = tk.IntVar(value=self.line_width)
        line_scale = ttk.Scale(
            color_frame,
            from_=1,
            to=20,
            orient=tk.HORIZONTAL,
            variable=self.line_width_var,
            command=lambda v: setattr(self, 'line_width', int(float(v)))
        )
        line_scale.pack(fill=tk.X, pady=(0, 10))
        
        # Template controls
        template_frame = ttk.LabelFrame(left_panel, text="Template", padding=5)
        template_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(template_frame, text="Create Template", command=self.create_template).pack(fill=tk.X, pady=2)
        ttk.Button(template_frame, text="Load Template", command=self.load_template).pack(fill=tk.X, pady=2)
        ttk.Button(template_frame, text="Export Template", command=self.export_template).pack(fill=tk.X, pady=2)
        
        # Layer visibility toggle
        ttk.Separator(left_panel).pack(fill=tk.X, pady=5)
        ttk.Button(
            left_panel, 
            text="Toggle Layer Visibility", 
            command=self.toggle_layer_visibility
        ).pack(fill=tk.X, pady=2)
        
        # Canvas container
        canvas_container = ttk.Frame(main_container)
        canvas_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Add scrollbars
        h_scroll = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        v_scroll = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        
        # Create canvas with initial size
        self.drawing_canvas = tk.Canvas(
            canvas_container,
            bg='white',
            width=800,
            height=600,
            scrollregion=(0, 0, 800, 600),
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set
        )
        
        h_scroll.config(command=self.drawing_canvas.xview)
        v_scroll.config(command=self.drawing_canvas.yview)
        
        # Grid layout with weights
        self.drawing_canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self.drawing_canvas.bind("<ButtonPress-1>", self.start_draw)
        self.drawing_canvas.bind("<B1-Motion>", self.draw)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.stop_draw)
        
        # Draw initial grid
        self.draw_grid()
        
        # Update the layer list
        self.update_layer_list()
    
    def set_tool(self, tool):
        self.current_tool = tool
        self.drawing_canvas.config(cursor="cross" if tool != "Select" else "arrow")
        self.update_layer_list()
    
    def choose_color(self, color_type='outline'):
        color = colorchooser.askcolor(
            title=f"Choose {color_type} color",
            initialcolor=self.draw_color if color_type == 'outline' else self.fill_color
        )
        if color[1]:  # If a color was selected
            if color_type == 'outline':
                self.draw_color = color[1]
                self.outline_btn.config(bg=self.draw_color)
            else:
                self.fill_color = color[1]
                self.fill_btn.config(bg=self.fill_color)
            
            # Update the active layer's color
            layer = self.get_active_layer()
            if layer:
                layer.color = self.draw_color
                self.redraw_canvas()
    
    def on_drawing_canvas_configure(self, event):
        """Handle drawing canvas resize events"""
        self.draw_grid()
    
    def set_grid_type(self, grid_type):
        self.grid_type = grid_type
        self.draw_grid()
    
    def toggle_grid_visibility(self):
        self.grid_visible = not self.grid_visible
        self.draw_grid()
    
    def draw_grid(self):
        # Clear existing grid
        self.drawing_canvas.delete("grid")
        
        if not self.grid_visible or self.grid_type == "None":
            return
        
        width = int(self.drawing_canvas.cget("width"))
        height = int(self.drawing_canvas.cget("height"))
        
        if self.grid_type == "Square":
            # Draw square grid
            spacing = 20
            for x in range(0, width, spacing):
                self.drawing_canvas.create_line(x, 0, x, height, fill=self.grid_color, tags="grid")
            for y in range(0, height, spacing):
                self.drawing_canvas.create_line(0, y, width, y, fill=self.grid_color, tags="grid")
        
        elif self.grid_type == "Rule of Thirds":
            # Rule of thirds grid
            for i in (1/3, 2/3):
                x = width * i
                y = height * i
                self.drawing_canvas.create_line(x, 0, x, height, fill=self.grid_color, dash=(4, 2), tags="grid")
                self.drawing_canvas.create_line(0, y, width, y, fill=self.grid_color, dash=(4, 2), tags="grid")
        
        elif self.grid_type == "Golden Ratio":
            # Golden ratio grid
            phi = 1.618033988749895
            for i in (1/phi, 1 - 1/phi):
                x = width * i
                y = height * i
                self.drawing_canvas.create_line(x, 0, x, height, fill=self.grid_color, dash=(4, 2), tags="grid")
                self.drawing_canvas.create_line(0, y, width, y, fill=self.grid_color, dash=(4, 2), tags="grid")
    
    def toggle_fill(self):
        self.fill_enabled = self.fill_var.get()
        layer = self.get_active_layer()
        if layer:
            layer.fill_enabled = self.fill_enabled
            self.redraw_canvas()
    
    def toggle_layer_visibility(self):
        """Toggle visibility of the currently selected layer"""
        layer = self.get_active_layer()
        if layer:
            layer.visible = not layer.visible
            self.update_layer_list()
            self.redraw_canvas()
    
    def create_template(self):
        """Create a template from the current drawing"""
        if not self.drawing_layers:
            messagebox.showinfo("Info", "No layers to save as template")
            return
            
        # Create a copy of the current drawing state
        template = {
            'layers': [layer.to_dict() for layer in self.drawing_layers],
            'created_at': datetime.datetime.now().isoformat(),
            'version': '1.0'
        }
        
        # Prompt for template name
        template_name = simpledialog.askstring("Save Template", "Enter template name:")
        if not template_name:
            return
            
        # Save template to templates directory
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        os.makedirs(templates_dir, exist_ok=True)
        
        template_path = os.path.join(templates_dir, f"{template_name}.json")
        with open(template_path, 'w') as f:
            json.dump(template, f, indent=2)
            
        messagebox.showinfo("Success", f"Template saved as {template_name}")
    
    def load_template(self):
        """Load a template from file"""
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        os.makedirs(templates_dir, exist_ok=True)
        
        # Get list of available templates
        try:
            templates = [f for f in os.listdir(templates_dir) if f.endswith('.json')]
            if not templates:
                messagebox.showinfo("Info", "No templates found")
                return
                
            # Show template selection dialog
            template_name = simpledialog.askstring("Load Template", "Enter template name:")
            if not template_name:
                return
                
            template_path = os.path.join(templates_dir, f"{template_name}.json")
            if not os.path.exists(template_path):
                messagebox.showerror("Error", f"Template '{template_name}' not found")
                return
                
            # Load template
            with open(template_path, 'r') as f:
                template = json.load(f)
                
            # Clear current drawing
            self.drawing_layers = []
            
            # Create layers from template
            for layer_data in template.get('layers', []):
                layer = DrawingLayer.from_dict(layer_data)
                self.drawing_layers.append(layer)
                
            # Set active layer to the top one
            if self.drawing_layers:
                self.active_layer_id = self.drawing_layers[-1].id
                
            self.redraw_canvas()
            self.update_layer_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load template: {str(e)}")
    
    def export_template(self):
        """Export the current drawing as an image"""
        if not self.drawing_layers:
            messagebox.showinfo("Info", "No layers to export")
            return
            
        # Get export path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # Create a temporary surface to draw on
            bbox = self.drawing_canvas.bbox("all")
            if not bbox:
                messagebox.showinfo("Info", "Nothing to export")
                return
                
            # Add some padding
            padding = 20
            bbox = (bbox[0]-padding, bbox[1]-padding, bbox[2]+padding, bbox[3]+padding)
            
            # Create a temporary canvas for export
            temp_canvas = tk.Canvas(self.drawing_frame, width=bbox[2]-bbox[0], height=bbox[3]-bbox[1])
            temp_canvas.pack()
            
            # Draw background
            temp_canvas.create_rectangle(0, 0, bbox[2]-bbox[0], bbox[3]-bbox[1], fill='white')
            
            # Draw all layers
            for layer in self.drawing_layers:
                if layer.visible:
                    layer.draw(temp_canvas, offset=(-bbox[0], -bbox[1]))
            
            # Export to image
            ps = temp_canvas.postscript(colormode='color')
            img = Image.open(io.BytesIO(ps.encode('utf-8')))
            img.save(file_path)
            
            temp_canvas.destroy()
            messagebox.showinfo("Success", f"Drawing exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def delete_layer(self):
        """Delete the currently selected layer"""
        if not self.drawing_layers:
            return
            
        if len(self.drawing_layers) <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last layer")
            return
            
        # Find the layer to delete
        layer_idx = next((i for i, l in enumerate(self.drawing_layers) 
                         if l.id == self.active_layer_id), -1)
        
        if layer_idx >= 0:
            # Remove the layer
            del self.drawing_layers[layer_idx]
            
            # Update active layer
            if layer_idx >= len(self.drawing_layers):
                layer_idx = len(self.drawing_layers) - 1
            self.active_layer_id = self.drawing_layers[layer_idx].id if self.drawing_layers else None
            
            self.redraw_canvas()
            self.update_layer_list()
    
    def move_layer_up(self):
        """Move the current layer up in the stack"""
        idx = next((i for i, l in enumerate(self.drawing_layers) 
                   if l.id == self.active_layer_id), -1)
        
        if idx > 0:
            # Swap with the layer above
            self.drawing_layers[idx], self.drawing_layers[idx-1] = \
                self.drawing_layers[idx-1], self.drawing_layers[idx]
            
            self.redraw_canvas()
            self.update_layer_list()
    
    def move_layer_down(self):
        """Move the current layer down in the stack"""
        idx = next((i for i, l in enumerate(self.drawing_layers) 
                   if l.id == self.active_layer_id), -1)
        
        if 0 <= idx < len(self.drawing_layers) - 1:
            # Swap with the layer below
            self.drawing_layers[idx], self.drawing_layers[idx+1] = \
                self.drawing_layers[idx+1], self.drawing_layers[idx]
            
            self.redraw_canvas()
            self.update_layer_list()
    
    def redraw_canvas(self):
        """Redraw all layers on the canvas"""
        self.drawing_canvas.delete("all")
        self.draw_grid()
        
        # Draw all layers from bottom to top
        for layer in self.drawing_layers:
            layer.draw(self.drawing_canvas)
    
    def start_draw(self, event):
        if not self.get_active_layer():
            return
            
        self.drawing = True
        self.start_x = self.drawing_canvas.canvasx(event.x)
        self.start_y = self.drawing_canvas.canvasy(event.y)
        
        if self.current_tool == "Freehand":
            # For freehand drawing, we'll store the coordinates in the current item
            self.current_item = {
                'type': 'freehand',
                'coords': [self.start_x, self.start_y],
                'outline': self.draw_color,
                'width': self.line_width
            }
            
            # Add the initial point to the current item
            layer = self.get_active_layer()
            if layer:
                layer.add_shape(
                    'freehand',
                    [self.start_x, self.start_y],
                    outline=self.draw_color,
                    width=self.line_width
                )
                self.redraw_canvas()
    
    def draw(self, event):
        if not self.drawing or not self.get_active_layer():
            return
            
        x = self.drawing_canvas.canvasx(event.x)
        y = self.drawing_canvas.canvasy(event.y)
        
        # For freehand drawing, add the current point to the current item
        if self.current_tool == "Freehand" and isinstance(self.current_item, dict):
            self.current_item['coords'].extend([x, y])
            
            # Update the last shape in the active layer
            layer = self.get_active_layer()
            if layer and layer.shapes:
                layer.shapes[-1] = self.current_item
                self.redraw_canvas()
            return
        
        # For other shapes, update the preview
        if self.current_item:
            self.drawing_canvas.delete(self.current_item)
        
        fill_color = self.draw_color + '80' if self.fill_enabled else ''
        
        if self.current_tool == "Rectangle":
            self.current_item = self.drawing_canvas.create_rectangle(
                self.start_x, self.start_y, x, y,
                outline=self.draw_color,
                fill=fill_color,
                width=self.line_width
            )
        elif self.current_tool == "Ellipse":
            self.current_item = self.drawing_canvas.create_oval(
                self.start_x, self.start_y, x, y,
                outline=self.draw_color,
                fill=fill_color,
                width=self.line_width
            )
        elif self.current_tool == "Line":
            self.current_item = self.drawing_canvas.create_line(
                self.start_x, self.start_y, x, y,
                fill=self.draw_color,
                width=self.line_width
            )
    
    def stop_draw(self, event):
        if not self.drawing or not self.get_active_layer():
            return
            
        x = self.drawing_canvas.canvasx(event.x)
        y = self.drawing_canvas.canvasy(event.y)
        
        layer = self.get_active_layer()
        if not layer:
            return
        
        # For freehand drawing, we've already added the shape
        if self.current_tool == "Freehand":
            self.current_item = None
            self.drawing = False
            return
            
        # For other shapes, add the final shape to the active layer
        fill_color = self.draw_color + '80' if self.fill_enabled else ''
        
        if self.current_tool == "Rectangle":
            layer.add_shape(
                'rectangle',
                [self.start_x, self.start_y, x, y],
                outline=self.draw_color,
                fill=fill_color,
                width=self.line_width
            )
        elif self.current_tool == "Ellipse":
            layer.add_shape(
                'ellipse',
                [self.start_x, self.start_y, x, y],
                outline=self.draw_color,
                fill=fill_color,
                width=self.line_width
            )
        elif self.current_tool == "Line":
            layer.add_shape(
                'line',
                [self.start_x, self.start_y, x, y],
                outline=self.draw_color,
                width=self.line_width
            )
        
        # Redraw the canvas to show the new shape
        self.redraw_canvas()
        
        self.drawing = False
        self.current_item = None
    
    def clear_drawing(self):
        if not hasattr(self, 'drawing_canvas') or not self.drawing_canvas:
            return
            
        if messagebox.askyesno("Clear Drawing", "Are you sure you want to clear the drawing?"):
            self.drawing_canvas.delete("all")
            self.drawn_items = []
            self.draw_grid()
    
    def undo_drawing(self):
        if not hasattr(self, 'drawn_items') or not hasattr(self, 'drawing_canvas') or not self.drawing_canvas:
            return
            
        if self.drawn_items:
            item = self.drawn_items.pop()
            self.drawing_canvas.delete(item)

def main():
    root = tk.Tk()
    app = PSDEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
