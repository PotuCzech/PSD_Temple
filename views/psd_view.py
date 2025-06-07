"""
PSD View component for displaying PSD files with layer information.

This module provides the PSDView class which is responsible for the graphical
representation of PSD files, including layer management, zooming, and navigation.
"""
from __future__ import annotations

import os
import logging
import threading
from typing import Optional, Dict, Any, Tuple, List, Union, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
from psd_tools import PSDImage
from psd_tools.api.layers import (
    Group,
    Layer,
    TypeLayer,
    ShapeLayer,
    PixelLayer,
    SmartObjectLayer
)

from psd_editor.views.base_view import BaseView
from psd_editor.views.psd_info_view import PSDInfoView
from psd_editor.models.psd_document import PSDDocument
from psd_editor.utils.psd_optimizer import PSDOptimizer
from psd_editor.rendering import PSDFullRenderer

# Initialize the PSD optimizer as a class attribute
psd_optimizer = PSDOptimizer(cache=True)

# Set up logging
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of status messages."""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'

    @classmethod
    def from_string(cls, value: str) -> 'MessageType':
        """Convert a string to MessageType enum."""
        return cls(value.lower())

    def __str__(self) -> str:
        return self.value

# Zoom functionality has been removed

if TYPE_CHECKING:
    from typing_extensions import Self
    from psd_editor.models.psd_document import PSDDocument as PSDDocumentType

# Remove duplicate logging setup since it's already configured at module level
logger = logging.getLogger(__name__)

@dataclass
class LayerInfo:
    """Container for layer information.
    
    Attributes:
        name: The name of the layer.
        visible: Whether the layer is visible.
        opacity: The opacity of the layer (0.0 to 1.0).
        size: The (width, height) of the layer in pixels.
        position: The (x, y) position of the layer.
        kind: The type of layer (e.g., 'pixel', 'text', 'group').
        selected: Whether the layer is currently selected.
    """
    name: str
    visible: bool
    opacity: float
    size: Tuple[int, int]
    position: Tuple[int, int]
    kind: str
    selected: bool = False


class PSDView(BaseView):
    """View for displaying and interacting with PSD files.
    
    This class handles the graphical representation of PSD files, including:
    - Displaying the composite image with smooth zooming and panning
    - Layer management with selection and visibility toggling
    - Memory-efficient rendering of large PSD files
    - Status updates and error handling
    """
    
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        """Initialize the PSD view with enhanced memory management.
        
        Args:
            parent: The parent widget.
            **kwargs: Additional keyword arguments passed to the parent class.
        """
        # Initialize instance variables with type hints
        self.psd_doc: Optional[PSDDocument] = None
        self.current_scale: float = 1.0  # Fixed scale at 100%
        
        # Image and canvas references
        self._photo_image: Optional[ImageTk.PhotoImage] = None
        self._current_image: Optional[Image.Image] = None
        self.image_on_canvas: Optional[int] = None
        
        # Layer management
        self.layer_widgets: Dict[str, Any] = {}
        self.show_hidden_layers: bool = False
        
        # Status bar
        self._status_timer: Optional[str] = None
        self._status_message_id: Optional[int] = None
        
        # UI components
        self.main_paned: Optional[ttk.PanedWindow] = None
        self.info_view: Optional[PSDInfoView] = None
        self.preview_frame: Optional[ttk.Frame] = None
        self.canvas: Optional[tk.Canvas] = None
        self.h_scrollbar: Optional[ttk.Scrollbar] = None
        self.v_scrollbar: Optional[ttk.Scrollbar] = None
        self.status_var: Optional[tk.StringVar] = None
        self.status_bar: Optional[ttk.Label] = None
        self.context_menu: Optional[tk.Menu] = None
        
        # Track mouse state for panning
        self._pan_start_x: int = 0
        self._pan_start_y: int = 0
        self._is_panning: bool = False
        
        # Initialize the PSD optimizer
        self.psd_optimizer = PSDOptimizer(cache=True)
        
        # Initialize the base class
        super().__init__(parent, **kwargs)
        
        # Setup the UI
        try:
            self._setup_ui()
        except Exception as e:
            logger.exception("Error initializing PSDView")
            raise RuntimeError(f"Failed to initialize PSD view: {str(e)}") from e
    
    def register_callback(self, event_name: str, callback: Callable[..., Any]) -> None:
        """Register a callback function for a specific event.
        
        Args:
            event_name: Name of the event to register the callback for.
            callback: The callback function to be called when the event occurs.
            
        Raises:
            ValueError: If the event_name is not supported.
        """
        if not hasattr(self, '_callbacks'):
            self._callbacks = {}
            
        if event_name not in ['zoom_in', 'zoom_out', 'zoom_fit', 'zoom_100', 'fit_to_window']:
            raise ValueError(f"Unsupported event: {event_name}")
            
        self._callbacks[event_name] = callback
        
        # Bind the callback to the appropriate method if it exists
        if hasattr(self, event_name) and callable(getattr(self, event_name)):
            # The method already exists, no need to do anything
            pass
    
    def cleanup(self) -> None:
        """Clean up resources to prevent memory leaks.
        
        This method should be called when the PSDView is no longer needed
        to properly clean up resources like images, timers, and references.
        It handles all necessary cleanup operations in a safe manner.
        
        Note:
            This method is designed to be safe to call multiple times and
            will not raise exceptions if resources have already been cleaned up.
        """
        try:
            # Clean up image resources
            if hasattr(self, '_photo_image') and self._photo_image:
                self._photo_image = None
            if hasattr(self, '_current_image') and self._current_image:
                self._current_image = None
            
            # Clean up canvas items
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.delete(tk.ALL)
                
            # Clean up scrollbars
            if hasattr(self, 'h_scrollbar') and self.h_scrollbar:
                self.h_scrollbar.destroy()
            if hasattr(self, 'v_scrollbar') and self.v_scrollbar:
                self.v_scrollbar.destroy()
                
            # Clean up status bar
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set('')
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.destroy()
                
            # Clean up context menu
            if hasattr(self, 'context_menu') and self.context_menu:
                self.context_menu.destroy()
                
            # Clean up layer widgets
            if hasattr(self, 'layer_widgets') and self.layer_widgets:
                for widget in self.layer_widgets.values():
                    if isinstance(widget, tk.Widget):
                        widget.destroy()
                self.layer_widgets.clear()
                
            # Clean up PSD document
            if hasattr(self, 'psd_doc') and self.psd_doc:
                # Clear references to prevent memory leaks
                self.psd_doc = None
                
            # Clear PSD optimizer cache
            if hasattr(self, 'psd_optimizer'):
                self.psd_optimizer.clear_cache()
                
                
            # Clear any remaining references
            self.image_on_canvas = None
            self.layer_widgets = {}
            self.main_paned = None
            self.info_view = None
            self.preview_frame = None
            self.canvas = None
            self.h_scrollbar = None
            self.v_scrollbar = None
            self.status_var = None
            self.status_bar = None
            self.context_menu = None
            
        except Exception as e:
            logger.exception("Error cleaning up resources")
            raise RuntimeError(f"Failed to clean up resources: {str(e)}") from e

    def _cleanup_photo_image(self) -> None:
        """Cleanup the PhotoImage reference to prevent memory leaks."""
        if hasattr(self, '_photo_image') and self._photo_image:
            self._photo_image = None

    def _bind_events(self):
        """Bind necessary events for the PSD view.
        
        This method sets up event bindings for panning and basic interaction.
        """
        if not self.canvas:
            return
            
        # Panning with middle mouse button
        self.canvas.bind("<ButtonPress-2>", self._on_mouse_press)
        self.canvas.bind("<B2-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_mouse_release)
        
        # Right-click context menu
        self.canvas.bind("<Button-3>", self._show_context_menu)
        
        # Canvas click events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # Make sure the canvas has focus to receive keyboard events
        self.canvas.focus_set()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Handle canvas resize event.
        
        This method updates the canvas size and adjusts the scroll region accordingly.
        """
        try:
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                self._update_scroll_region()
        except Exception as e:
            logger.exception("Error handling canvas configure event")
            raise RuntimeError(f"Failed to handle canvas configure event: {str(e)}") from e
    
    def _on_mouse_press(self, event: tk.Event) -> None:
        """Handle mouse button press event for panning."""
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._is_panning = True
        self.canvas.config(cursor="fleur")
    
    def _on_mouse_drag(self, event: tk.Event) -> None:
        """Handle mouse drag event for panning."""
        if not self._is_panning or not self.canvas:
            return
            
        try:
            dx = event.x - self._pan_start_x
            dy = event.y - self._pan_start_y
            
            # Convert pixels to units (1 unit = 1 pixel in Tkinter)
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            
            self._pan_start_x = event.x
            self._pan_start_y = event.y
        except Exception as e:
            logger.error(f"Error during canvas panning: {str(e)}")
            self._show_status_message(f"Error: {str(e)}", MessageType.ERROR)
    
    def _on_mouse_release(self, event: tk.Event) -> None:
        """Handle mouse button release event."""
        self._is_panning = False
        self.canvas.config(cursor="")
    
    def _setup_ui(self) -> None:
        """Set up the PSD view UI components.
        
        This method initializes all the UI elements of the PSD view,
        including the main paned window, canvas, scrollbars, and status bar.
        """
        try:
            # Create the main paned window
            self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
            self.main_paned.pack(fill=tk.BOTH, expand=True)
            
            # Create the preview frame with a minimum size
            self.preview_frame = ttk.Frame(self.main_paned)
            self.main_paned.add(self.preview_frame, weight=1)
            
            # Create the canvas with scrollbars
            self._setup_canvas_area()
            
            # Create the info view with a minimum width
            self.info_view = PSDInfoView(self.main_paned)
            self.main_paned.add(self.info_view, weight=0)
            
            # Configure the paned window
            # The weight is already set in the add() method
            # No additional configuration needed here
            
            # Set up the status bar
            self._setup_status_bar()
            
            # Bind events
            self._bind_events()
            
        except Exception as e:
            logger.exception("Error setting up PSD view UI")
            raise

    def _setup_status_bar(self) -> None:
        """Set up the status bar at the bottom of the view.
        
        This method creates a status bar that can display messages to the user.
        The status bar includes a label for displaying status messages.
        """
        try:
            # Create a frame for the status bar
            status_frame = ttk.Frame(self, padding="2 2 2 2")
            status_frame.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Create a label for status messages
            self.status_var = tk.StringVar()
            self.status_bar = ttk.Label(
                status_frame,
                textvariable=self.status_var,
                relief=tk.SUNKEN,
                anchor=tk.W,
                padding=(5, 2, 5, 2)
            )
            self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Initialize with a default message
            self.show_status("Ready", MessageType.INFO)
            
        except Exception as e:
            logger.exception("Error setting up status bar")
            raise RuntimeError(f"Failed to set up status bar: {str(e)}") from e
    
    def _setup_canvas_area(self) -> None:
        """Set up the canvas area with scrollbars and tools.
        
        This method initializes the canvas and scrollbars for the PSD preview.
        It handles:
        - Creating and configuring the canvas and scrollbars
        - Setting up the grid layout

        Args:
            None
        
        Returns:
            None
        
        Raises:
            Exception: If there is an error setting up the canvas area.
        
        Note:
            The canvas is configured with a checkerboard background for better visibility.
            Scrollbars are added for horizontal and vertical scrolling.
        """
        try:
            # Create a frame to hold the canvas and scrollbars
            canvas_frame = ttk.Frame(self.preview_frame)
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create horizontal and vertical scrollbars
            self.h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
            self.v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
            
            # Create the canvas with a checkerboard background
            self.canvas = tk.Canvas(
                canvas_frame,
                bg='#2d2d2d',
                xscrollcommand=self.h_scrollbar.set,
                yscrollcommand=self.v_scrollbar.set,
                highlightthickness=0,
                cursor='crosshair'  # Better cursor for precision work
            )
            
            # Configure scrollbars
            self.h_scrollbar.config(command=self._on_xscroll)
            self.v_scrollbar.config(command=self._on_yscroll)
            
            # Grid layout
            self.canvas.grid(row=0, column=0, sticky='nsew')
            self.v_scrollbar.grid(row=0, column=1, sticky='ns')
            self.h_scrollbar.grid(row=1, column=0, sticky='ew')
            
            # Configure grid weights
            canvas_frame.grid_rowconfigure(0, weight=1)
            canvas_frame.grid_columnconfigure(0, weight=1)
            
        except Exception as e:
            logger.exception("Error setting up canvas")
            raise RuntimeError("Failed to initialize canvas") from e
    
    def _on_xscroll(self, *args) -> None:
        """Handle horizontal scrolling."""
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.xview(*args)
    
    def _on_yscroll(self, *args) -> None:
        """Handle vertical scrolling."""
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.yview(*args)
    
    def _setup_context_menu(self) -> None:
        """Set up the right-click context menu for the canvas."""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        self.context_menu = tk.Menu(self.canvas, tearoff=0)
        self.context_menu.add_command(label="Reset View", command=self.reset_zoom)
        self.context_menu.add_command(label="Fit to Window", command=self.fit_to_window)
        
        # Bind right-click to show context menu
        self.canvas.bind("<Button-3>", self._show_context_menu)
    
    def _show_context_menu(self, event: tk.Event) -> None:
        """Show the context menu on right-click.
        
        This method creates and displays a context menu with zoom and view options
        when the user right-clicks on the canvas.
        
        Args:
            event: The mouse event that triggered the context menu.
        """
        if not hasattr(self, 'context_menu'):
            try:
                # Create the context menu
                self.context_menu = tk.Menu(self, tearoff=0)
                
                # Add menu items with keyboard shortcuts
                self.context_menu.add_command(
                    label="Fit to Window",
                    command=self.fit_to_window,
                    accelerator="Ctrl+1"
                )
                
                # Disable menu items if no document is loaded
                if not hasattr(self, 'psd_doc') or not self.psd_doc:
                    for i in range(self.context_menu.index('end') + 1):
                        self.context_menu.entryconfigure(i, state='disabled')
            except Exception as e:
                logger.exception("Error creating context menu")
                return
        
        try:
            # Update menu item states based on current state
            has_doc = hasattr(self, 'psd_doc') and self.psd_doc is not None
            state = 'normal' if has_doc else 'disabled'
            
            for i in range(self.context_menu.index('end') + 1):
                self.context_menu.entryconfigure(i, state=state)
            
            # Show the menu at the click position
            self.context_menu.tk_popup(event.x_root, event.y_root)
            
        except Exception as e:
            logger.exception("Error showing context menu")
            try:
                self.context_menu.grab_release()
            except:
                pass
    
    def _on_canvas_click(self, event: tk.Event) -> None:
        """Handle canvas click events.
        
        This method handles mouse clicks on the canvas, with different behaviors
        for left and right clicks. Right clicks show the context menu, while
        left clicks hide it if visible.
        
        Args:
            event: The mouse click event containing button and position info.
        """
        try:
            # Handle left click (button 1)
            if event.num == 1 or event.num == 1:  # Standard left click
                # Hide context menu if visible
                if hasattr(self, 'context_menu') and self.context_menu:
                    try:
                        self.context_menu.unpost()
                    except Exception as e:
                        logger.debug("Error hiding context menu: %s", str(e))
                
                # Additional left-click handling can be added here
                # For example, layer selection or other interactive elements
                
            # Handle right click (button 3) is already handled by _show_context_menu
            
        except Exception as e:
            logger.exception("Error in canvas click handler")
            self.show_status(f"Error handling click: {str(e)}", "error")
    
    def _on_composite_ready(self, composite: Optional[Image.Image]) -> None:
        """Handle the composite image when it's ready.
        
        Args:
            composite: The composite image, or None if there was an error.
        """
        if composite is None:
            self.show_status("Failed to generate composite image", "error")
            return
            
        try:
            # Update the image display
            self._current_image = composite
            self._photo_image = ImageTk.PhotoImage(composite)
            
            # Update the canvas
            self._update_canvas()
            self._center_image()
            
            # Update info view if available
            if hasattr(self, 'info_view') and self.info_view and hasattr(self, 'psd_doc'):
                self.info_view.update_info(self.psd_doc)
                
            self.show_status("Image rendering complete", "success")
            
        except Exception as e:
            logger.error(f"Error updating display with composite: {str(e)}")
            self.show_status(f"Error updating display: {str(e)}", "error")
    
    def load_psd(self, filepath: str, render_mode: str = 'full') -> bool:
        """Load a PSD file into the view with caching support.
        
        Args:
            filepath: Path to the PSD file to load.
            render_mode: Rendering mode ('full' or 'light').
            
        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        try:
            # Show loading state
            self.show_status(f"Loading {os.path.basename(filepath)}...", "info", duration=5000)
            self._show_loading_indicator("Loading PSD file...")
            
            # Reset view state
            self.current_scale = 1.0
            
            # Clean up existing PSD document
            if hasattr(self, 'psd_doc') and self.psd_doc:
                if hasattr(self.psd_doc, 'cleanup') and callable(self.psd_doc.cleanup):
                    self.psd_doc.cleanup()
                self.psd_doc = None
            
            # Try to load from cache first if in light mode
            if render_mode == 'light':
                from utils.cache_manager import psd_cache
                
                # Try to get cached preview
                cached_preview = psd_cache.get_cached_image(filepath, "_preview")
                if cached_preview:
                    try:
                        self._current_image = cached_preview
                        self._photo_image = ImageTk.PhotoImage(cached_preview)
                        self._update_canvas()
                        self._center_image()
                        
                        # Load PSD in background for metadata
                        def load_psd_in_background():
                            try:
                                self.psd_doc = PSDDocument.from_file(filepath, render_mode=render_mode)
                                if hasattr(self, 'info_view') and self.info_view:
                                    self.info_view.update_info(self.psd_doc)
                            except Exception as e:
                                logger.error(f"Error loading PSD in background: {e}")
                        
                        import threading
                        threading.Thread(target=load_psd_in_background, daemon=True).start()
                        
                        self.show_status(f"Loaded from cache: {os.path.basename(filepath)}", "success")
                        return True
                        
                    except Exception as e:
                        logger.error(f"Error loading cached preview: {str(e)}")
            
            # Load the PSD file
            self.psd_doc = PSDDocument.from_file(filepath, render_mode=render_mode)
            
            # For light mode, try to load or generate preview
            if render_mode == 'light':
                from utils.cache_manager import psd_cache
                
                # Try to get the composite from cache
                cached_composite = psd_cache.get_cached_image(filepath, "_full")
                if cached_composite:
                    self._current_image = cached_composite
                    self._photo_image = ImageTk.PhotoImage(cached_composite)
                    self._update_canvas()
                    self._center_image()
                    
                    if hasattr(self, 'info_view') and self.info_view:
                        self.info_view.update_info(self.psd_doc)
                    
                    self.show_status(f"Successfully loaded: {os.path.basename(filepath)}", "success")
                    return True
            
            # If we get here, we need to generate the composite
            self.show_status("Generating composite...", "info")
            
            # Use the optimized renderer with callback
            try:
                # Get the underlying PSD object from the document
                psd_obj = getattr(self.psd_doc, '_psd', None)
                if psd_obj is None:
                    raise ValueError("Could not access PSD data")
                
                logger.debug(f"Creating renderer for PSD: {filepath}")
                renderer = PSDFullRenderer(psd_obj, filepath)
                
                logger.debug("Requesting composite image...")
                composite = renderer.get_composite_image(callback=self._on_composite_ready)
                
                if composite is not None:
                    # Got composite synchronously
                    logger.debug("Got synchronous composite")
                    self._on_composite_ready(composite)
                else:
                    # Composite will be loaded asynchronously
                    logger.debug("Composite will be loaded asynchronously")
                    self._show_loading_indicator("Generating composite in background...")
                    
            except Exception as e:
                logger.exception("Error in composite generation")
                self.show_status(f"Error generating composite: {str(e)}", "error")
                self._show_error_indicator(f"Error: {str(e)}")
                return False
            
            return True
            
            # If we reach here, loading failed
            error_msg = "Failed to load PSD: No valid image found"
            logger.error(error_msg)
            self.show_status(error_msg, "error", duration=5000)
            self._show_error_indicator(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Error loading PSD: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error", duration=5000)
            self._show_error_indicator(str(e))
            # Safely clean up PSD document if it exists
            if hasattr(self, 'psd_doc') and self.psd_doc:
                if hasattr(self.psd_doc, 'cleanup') and callable(self.psd_doc.cleanup):
                    try:
                        self.psd_doc.cleanup()
                    except Exception as cleanup_error:
                        logger.warning(f"Error during PSD cleanup: {str(cleanup_error)}")
                self.psd_doc = None
            raise ValueError(f"Failed to load PSD: {str(e)}") from e

    def _show_loading_indicator(self, message: str) -> None:
        """Display a loading indicator on the canvas.
        
        Args:
            message: The message to display in the loading indicator.
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            text=message,
            font=('Arial', 12),
            fill='gray',
            tags=("loading_text",)
        )
        self.canvas.update()

    def _show_error_indicator(self, error_msg: str) -> None:
        """Display an error message on the canvas.
        
        Args:
            error_msg: The error message to display.
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            text=f"Error: {error_msg}",
            font=('Arial', 12),
            fill='red',
            tags=("error_text",),
            width=self.canvas.winfo_width() - 40
        )

    def _update_canvas(self) -> None:
        """Update the canvas with the current PSD image.
        
        This method renders the current state of the PSD document to the canvas,
        handling scaling and display updates. It shows a loading indicator while
        processing and updates the scroll region to match the image dimensions.
        
        Raises:
            RuntimeError: If the canvas is not properly initialized.
        """
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                error_msg = "Canvas not initialized"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            if not self.psd_doc or not hasattr(self.psd_doc, 'get_composite_image'):
                self._show_error_indicator("No PSD document loaded")
                return
                
            # Show loading indicator
            self._show_loading_indicator("Rendering PSD...")
            
            # Get the composite image
            img = self.psd_doc.get_composite_image()
            if not img:
                self._show_error_indicator("Failed to generate composite image")
                return
            
            # Convert to PhotoImage
            try:
                self.photo_image = ImageTk.PhotoImage(image=img)
            except Exception as photo_error:
                error_msg = f"Error creating image preview: {photo_error}"
                logger.exception(error_msg)
                self._show_error_indicator(error_msg)
                return
            
            # Clear canvas and display the image
            self.canvas.delete("all")
            try:
                self.image_on_canvas = self.canvas.create_image(
                    0, 0, 
                    anchor=tk.NW, 
                    image=self.photo_image,
                    tags=("psd_image",)
                )
                
                # Update scroll region and center the image
                self._update_scroll_region()
                self._center_image()
                
            except Exception as canvas_error:
                error_msg = f"Error updating canvas: {canvas_error}"
                logger.exception(error_msg)
                self._show_error_indicator(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error updating canvas: {str(e)}"
            logger.exception(error_msg)
            self._show_error_indicator(error_msg)
            self.show_status(error_msg, "error")

    def _update_scroll_region(self) -> None:
        """Update the scroll region to include the entire image with padding.
        
        This ensures that the entire image is scrollable, with some extra
        padding around the edges for better user experience.
        
        Raises:
            RuntimeError: If required attributes are not initialized.
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            error_msg = "Canvas not initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        if not hasattr(self, 'image_on_canvas') or not self._photo_image:
            logger.debug("No image to update scroll region for")
            return
            
        try:
            # Get image dimensions
            img_width = self._photo_image.width()
            img_height = self._photo_image.height()
            
            # Add padding around the image
            padding = 20
            
            # Update scroll region to include the full image with padding
            self.canvas.config(
                scrollregion=(
                    -padding,
                    -padding,
                    img_width + padding * 2,  # Double padding for width
                    img_height + padding * 2   # Double padding for height
                )
            )
            
            # Reset the view to show the top-left corner
            self.canvas.xview_moveto(0.0)
            self.canvas.yview_moveto(0.0)
            
        except Exception as e:
            error_msg = f"Error updating scroll region: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")

    def _center_image(self) -> None:
        """Center the image in the scrollable area.
        
        This method positions the image in the center of the visible canvas area
        and updates the scroll region to ensure the entire image is accessible.
        
        Raises:
            RuntimeError: If required attributes are not initialized.
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            error_msg = "Canvas not initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        if not hasattr(self, 'image_on_canvas') or not self._photo_image:
            logger.debug("No image to center")
            return
            
        try:
            # Get current canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Get image dimensions
            img_width = self._photo_image.width()
            img_height = self._photo_image.height()
            
            # Calculate center position with bounds checking
            x = max(0, (canvas_width - img_width) // 2)
            y = max(0, (canvas_height - img_height) // 2)
            
            # Position the image
            self.canvas.coords(self.image_on_canvas, x, y)
            
            # Update scroll region to ensure all of the image is accessible
            self._update_scroll_region()
            
        except Exception as e:
            error_msg = f"Error centering image: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")

    def show_status(self, message: str, msg_type: Union[str, MessageType] = "info", duration: int = 5000) -> None:
        """Show a status message in the status bar.
        
        This method displays a message in the status bar with appropriate
        styling based on the message type. The message can be automatically
        cleared after a specified duration.
        
        Args:
            message: The message text to display.
            msg_type: The type of message, which determines the color:
                     - 'info': Default black text
                     - 'success': Green text
                     - 'warning': Orange text
                     - 'error': Red text
            duration: How long to show the message in milliseconds.
                     Set to 0 to show the message until explicitly cleared.
                     
        Note:
            If the status bar is not initialized, this method will do nothing.
        """
        if not hasattr(self, 'status_var') or not hasattr(self, 'status_bar'):
            logger.warning("Status bar not initialized, cannot show message")
            return
            
        try:
            # Set the message text
            self.status_var.set(str(message))
            
            # Set the foreground color based on message type
            colors = {
                MessageType.INFO: 'black',
                MessageType.SUCCESS: '#006400',     # Dark green
                MessageType.WARNING: '#8B4513',     # Saddle brown
                MessageType.ERROR: '#8B0000'        # Dark red
            }
            
            # Apply styling
            fg_color = colors.get(msg_type, 'black')
            self.status_bar.config(foreground=fg_color)
            
            # Set font weight based on message type
            font = ('TkDefaultFont', 9)
            if msg_type in (MessageType.WARNING, MessageType.ERROR):
                font = ('TkDefaultFont', 9, 'bold')
                
            self.status_bar.config(font=font)
            
            # Clear any existing timer
            if hasattr(self, '_status_timer') and self._status_timer is not None:
                try:
                    self.after_cancel(self._status_timer)
                except (ValueError, tk.TclError):
                    # Timer ID was invalid or already canceled
                    pass
            
            # Set a timer to clear the message if duration is positive
            if duration > 0:
                try:
                    self._status_timer = self.after(
                        duration,
                        self.clear_status
                    )
                except tk.TclError as e:
                    logger.error(f"Failed to set status timer: {e}")
                    
            # Log the status message
            log_levels = {
                'info': logging.INFO,
                'success': logging.INFO,
                'warning': logging.WARNING,
                'error': logging.ERROR
            }
            # Convert string to MessageType if needed
            if isinstance(msg_type, str):
                msg_type = MessageType.from_string(msg_type)
            log_level = log_levels.get(msg_type.value, logging.INFO)
            logger.log(log_level, f"Status: {message}")
            
        except Exception as e:
            logger.exception(f"Error showing status message: {e}")

    def clear_status(self) -> None:
        """Clear the status bar."""
        if hasattr(self, 'status_var'):
            self.status_var.set('')

    def fit_to_window(self):
        """Center the PSD in the current window."""
        if not self.psd_doc or not self.canvas:
            return
            
        # Just center the image at 100% scale
        self.current_scale = 1.0
        self._update_canvas()
        self._center_image()
        self.show_status("Image centered at 100%", MessageType.INFO)
