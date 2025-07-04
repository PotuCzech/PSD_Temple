"""
PSD View component for displaying PSD files with layer information.

This module provides the PSDView class which is responsible for the graphical
representation of PSD files, including layer management, zooming, and navigation.
"""
from __future__ import annotations

import os
import logging
import math
import threading
from typing import Optional, Dict, Any, Tuple, List, Union, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, auto

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps
from psd_tools import PSDImage
from psd_tools.api.layers import (
    Group,
    Layer,
    TypeLayer,
    ShapeLayer,
    PixelLayer,
    SmartObjectLayer
)

from views.base_view import BaseView
from views.psd_info_view import PSDInfoView
from models.psd_document import PSDDocument

# Set up logging
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of status messages."""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()

@dataclass
class ZoomSettings:
    """Zoom-related settings."""
    min_scale: float = 0.1  # 10%
    max_scale: float = 10.0  # 1000%
    zoom_step: float = 1.2  # 20% zoom per step
    default_scale: float = 1.0  # 100%

if TYPE_CHECKING:
    from typing_extensions import Self
    from models.psd_document import PSDDocument as PSDDocumentType

# Set up logging
logging.basicConfig(level=logging.INFO)
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
        self._zoom_settings = ZoomSettings()
        self.current_scale: float = self._zoom_settings.default_scale
        
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
        
        # Initialize the base class
        super().__init__(parent, **kwargs)
        
        # Setup the UI
        try:
            self._setup_ui()
        except Exception as e:
            logger.exception("Error initializing PSDView")
            raise RuntimeError(f"Failed to initialize PSD view: {str(e)}") from e
    
    def cleanup(self) -> None:
        """Clean up resources to prevent memory leaks.
        
        This method should be called when the PSDView is no longer needed
        to ensure proper cleanup of resources like images, timers, and references.
        """
        try:
            # Clean up the PSD document
            if hasattr(self, 'psd_doc') and self.psd_doc is not None:
                if hasattr(self.psd_doc, 'close'):
                    self.psd_doc.close()
                self.psd_doc = None
            
            # Clean up the photo image
            if hasattr(self, '_photo_image') and self._photo_image is not None:
                self._photo_image = None
            
            # Clean up the current image
            if hasattr(self, '_current_image') and self._current_image is not None:
                self._current_image.close()
                self._current_image = None
            
            # Clean up any pending timers
            if hasattr(self, '_status_timer') and self._status_timer is not None:
                if hasattr(self, 'after_cancel') and callable(self.after_cancel):
                    self.after_cancel(self._status_timer)
                self._status_timer = None
            
            # Clean up the context menu
            if hasattr(self, 'context_menu') and self.context_menu is not None:
                if hasattr(self.context_menu, 'destroy'):
                    self.context_menu.destroy()
                self.context_menu = None
            
            logger.debug("PSDView cleanup completed")
            
        except Exception as e:
            logger.exception("Error during PSDView cleanup")
    
    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        self.cleanup()
    
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
            self._setup_canvas()
            
            # Create the info view with a minimum width
            self.info_view = PSDInfoView(self.main_paned)
            self.main_paned.add(self.info_view, weight=0)
            
            # Configure the paned window
            self.main_paned.paneconfigure(self.preview_frame, width=800)
            self.main_paned.paneconfigure(self.info_view, width=300, minsize=250)
            
            # Set up the status bar
            self._setup_status_bar()
            
            # Bind events
            self._bind_events()
            
        except Exception as e:
            logger.exception("Error setting up PSD view UI")
            raise
            
        except Exception as e:
            error_msg = f"Failed to initialize UI: {str(e)}"
            logger.exception(error_msg)
            messagebox.showerror("Initialization Error", error_msg)
            raise
    
    def _setup_canvas_area(self) -> None:
        """Set up the canvas area with scrollbars and tools.
        
        This method initializes the canvas and scrollbars for the PSD preview.
        It handles:
        - Creating and configuring the canvas and scrollbars
        - Setting up the grid layout
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
            
            # Initialize zoom state
            self._last_zoom_center = (0, 0)
            self._last_canvas_width = 0
            self._last_canvas_height = 0
            
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
    
    def zoom(self, factor: float, center: Optional[Tuple[int, int]] = None) -> None:
        """Zoom the canvas by the given factor around the specified center point.
        
        Args:
            factor: Zoom factor (e.g., 1.2 for 20% zoom in, 0.8 for 20% zoom out)
            center: Optional (x, y) tuple for the zoom center (in canvas coordinates)
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        try:
            # Get current canvas dimensions and scroll positions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # If no center point is provided, use the center of the visible area
            if center is None:
                center_x = canvas_width // 2
                center_y = canvas_height // 2
            else:
                center_x, center_y = center
            
            # Calculate the current scroll position in canvas coordinates
            x1 = self.canvas.canvasx(0)
            y1 = self.canvas.canvasy(0)
            x2 = self.canvas.canvasx(canvas_width)
            y2 = self.canvas.canvasy(canvas_height)
            
            # Calculate the current center in canvas coordinates
            current_center_x = (x1 + x2) / 2
            current_center_y = (y1 + y2) / 2
            
            # Calculate the offset from the center to the zoom point
            offset_x = (center_x - current_center_x) / self.current_scale
            offset_y = (center_y - current_center_y) / self.current_scale
            
            # Update the scale
            new_scale = self.current_scale * factor
            
            # Apply zoom constraints
            new_scale = max(self._zoom_settings.min_scale, 
                          min(new_scale, self._zoom_settings.max_scale))
            
            # Skip if no change
            if abs(new_scale - self.current_scale) < 0.01:
                return
                
            self.current_scale = new_scale
            
            # Calculate the new center point after zoom
            new_center_x = center_x - offset_x * (new_scale - self.current_scale)
            new_center_y = center_y - offset_y * (new_scale - self.current_scale)
            
            # Update the display
            self._update_canvas()
            
            # Calculate the new scroll position to keep the center point fixed
            new_x = (new_center_x - canvas_width / 2) / new_scale
            new_y = (new_center_y - canvas_height / 2) / new_scale
            
            # Update the scroll position
            self.canvas.xview_moveto(max(0, min(1, new_x / self.psd_doc.width)))
            self.canvas.yview_moveto(max(0, min(1, new_y / self.psd_doc.height)))
            
            # Update status bar
            self.show_status(f"Zoom: {int(self.current_scale * 100)}%")
            
        except Exception as e:
            logger.exception("Error during zoom operation")
            self.show_status(f"Zoom error: {str(e)}", MessageType.ERROR)
    
    def zoom_in(self, event=None) -> None:
        """Zoom in at the current mouse position or view center."""
        center = None
        if event and hasattr(event, 'x') and hasattr(event, 'y'):
            center = (event.x, event.y)
        self.zoom(self._zoom_settings.zoom_step, center)
    
    def zoom_out(self, event=None) -> None:
        """Zoom out at the current mouse position or view center."""
        center = None
        if event and hasattr(event, 'x') and hasattr(event, 'y'):
            center = (event.x, event.y)
        self.zoom(1.0 / self._zoom_settings.zoom_step, center)
    
    def zoom_fit(self) -> None:
        """Zoom to fit the entire PSD in the view."""
        if not hasattr(self, 'canvas') or not self.canvas or not self.psd_doc:
            return
            
        try:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 0 or canvas_height <= 0 or not self.psd_doc.width or not self.psd_doc.height:
                return
                
            # Calculate scale to fit width and height
            width_scale = canvas_width / self.psd_doc.width
            height_scale = canvas_height / self.psd_doc.height
            
            # Use the smaller scale to fit the entire image
            new_scale = min(width_scale, height_scale) * 0.95  # 5% padding
            
            # Apply zoom constraints
            new_scale = max(self._zoom_settings.min_scale, 
                          min(new_scale, self._zoom_settings.max_scale))
            
            # Update scale and redraw
            self.current_scale = new_scale
            self._update_canvas()
            
            # Center the image
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
            
            self.show_status(f"Zoom to fit: {int(self.current_scale * 100)}%")
            
        except Exception as e:
            logger.exception("Error fitting to view")
            self.show_status(f"Fit to view error: {str(e)}", MessageType.ERROR)
    
    def zoom_100(self) -> None:
        """Zoom to 100%."""
        if not hasattr(self, 'canvas') or not self.canvas or not self.psd_doc:
            return
            
        try:
            # Get current view center
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 0 or canvas_height <= 0 or not self.psd_doc.width or not self.psd_doc.height:
                return
                
            # Center point in canvas coordinates
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            
            # Zoom to 100% at the center
            self.current_scale = 1.0
            self._update_canvas()
            
            # Center the view
            self.canvas.xview_moveto(0.5 - (canvas_width / 2) / (self.psd_doc.width * self.current_scale))
            self.canvas.yview_moveto(0.5 - (canvas_height / 2) / (self.psd_doc.height * self.current_scale))
            
            self.show_status("Zoom: 100%")
            
        except Exception as e:
            logger.exception("Error setting zoom to 100%")
            self.show_status(f"Zoom error: {str(e)}", MessageType.ERROR)
            
            # Bind mouse wheel for zooming and scrolling
            self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
            self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_mouse_wheel)
            
            # Linux-specific bindings for mouse wheel
            self.canvas.bind("<Button-4>", self._on_linux_zoom_in)
            self.canvas.bind("<Button-5>", self._on_linux_zoom_out)
            
            # Handle canvas resize events
            self.canvas.bind("<Configure>", self._on_canvas_configure)
            
            # Add right-click context menu
            self._setup_context_menu()
            
        except Exception as e:
            error_msg = f"Failed to initialize canvas area: {str(e)}"
            logger.exception(error_msg)
            messagebox.showerror("Initialization Error", error_msg)
            raise
    
    def _setup_context_menu(self) -> None:
        """Set up the right-click context menu for the canvas."""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        self.context_menu = tk.Menu(self.canvas, tearoff=0)
        self.context_menu.add_command(label="Reset View", command=self.reset_zoom)
        self.context_menu.add_command(label="Fit to Window", command=self.fit_to_window)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Zoom In", command=self.zoom_in)
        self.context_menu.add_command(label="Zoom Out", command=self.zoom_out)
        
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
                    label="Zoom In (Ctrl++)",
                    command=self.zoom_in,
                    accelerator="Ctrl++"
                )
                self.context_menu.add_command(
                    label="Zoom Out (Ctrl+-)",
                    command=self.zoom_out,
                    accelerator="Ctrl+-"
                )
                self.context_menu.add_separator()
                self.context_menu.add_command(
                    label="Reset Zoom (Ctrl+0)",
                    command=self.reset_zoom,
                    accelerator="Ctrl+0"
                )
                self.context_menu.add_command(
                    label="Fit to Window (Ctrl+1)",
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
    
    def cleanup(self) -> None:
        """Clean up resources to prevent memory leaks and ensure proper shutdown.
        
        This method should be called when the PSDView is no longer needed
        to properly clean up resources like images, timers, and references.
        It handles all necessary cleanup operations in a safe manner.
        
        Note:
            This method is designed to be safe to call multiple times and
            will not raise exceptions if resources have already been cleaned up.
        """
        cleanup_operations = [
            self._cleanup_photo_image,
            self._cleanup_psd_doc,
            self._cleanup_timers,
            self._cleanup_context_menu,
            self._cleanup_canvas,
            self._cleanup_bindings,
            self._cleanup_status_bar
        ]
        
        for operation in cleanup_operations:
            try:
                operation()
            except Exception as e:
                logger.warning("Error during cleanup operation %s: %s", 
                             operation.__name__, str(e))
        
        logger.debug("PSDView cleanup completed")
    
    def _cleanup_photo_image(self) -> None:
        """Clean up the photo image reference."""
        if hasattr(self, 'photo_image') and self.photo_image is not None:
            try:
                # Explicitly delete the photo image to free resources
                self.photo_image.__del__()
            except Exception as e:
                logger.debug("Error deleting photo image: %s", str(e))
            finally:
                self.photo_image = None
    
    def _cleanup_psd_doc(self) -> None:
        """Clean up the PSD document reference."""
        if hasattr(self, 'psd_doc') and self.psd_doc is not None:
            try:
                # If PSDDocument has a close/cleanup method, call it
                if hasattr(self.psd_doc, 'close') and callable(self.psd_doc.close):
                    self.psd_doc.close()
            except Exception as e:
                logger.debug("Error closing PSD document: %s", str(e))
            finally:
                self.psd_doc = None
    
    def _cleanup_timers(self) -> None:
        """Clean up any pending timers."""
        if hasattr(self, '_status_timer') and self._status_timer is not None:
            try:
                self.after_cancel(self._status_timer)
            except (ValueError, tk.TclError):
                pass  # Timer already expired or was canceled
            finally:
                self._status_timer = None
    
    def _cleanup_context_menu(self) -> None:
        """Clean up the context menu."""
        if hasattr(self, 'context_menu') and self.context_menu is not None:
            try:
                if self.context_menu.winfo_exists():
                    self.context_menu.destroy()
            except (tk.TclError, AttributeError):
                pass  # Menu already destroyed or invalid
            finally:
                if hasattr(self, 'context_menu'):
                    del self.context_menu
    
    def _cleanup_canvas(self) -> None:
        """Clean up the canvas."""
        if hasattr(self, 'canvas') and self.canvas is not None:
            try:
                # Clear all canvas items
                self.canvas.delete('all')
                
                # Unbind all events to prevent memory leaks
                for tag in self.canvas.bindtags():
                    for sequence in self.canvas.bind_class(tag):
                        if sequence != 'all':
                            self.canvas.unbind_class(tag, sequence)
            except Exception as e:
                logger.debug("Error cleaning up canvas: %s", str(e))
    
    def _cleanup_bindings(self) -> None:
        """Clean up event bindings."""
        if hasattr(self, 'bindings') and isinstance(self.bindings, dict):
            for widget, bindings in self.bindings.items():
                if widget and widget.winfo_exists():
                    for sequence, callback in bindings.items():
                        try:
                            widget.unbind(sequence)
                        except tk.TclError:
                            pass
    
    def _cleanup_status_bar(self) -> None:
        """Clean up the status bar."""
        if hasattr(self, 'status_var') and self.status_var is not None:
            try:
                self.status_var.set('')
            except tk.TclError:
                pass
    
    def load_psd(self, filepath: str) -> bool:
        """Load a PSD file into the view.
        
        This method handles the complete process of loading a PSD file,
        including showing loading indicators, handling errors, and updating
        the UI components.
        
        Args:
            filepath: Path to the PSD file to load.
            
        Returns:
            bool: True if the PSD was loaded successfully, False otherwise.
            
        Raises:
            FileNotFoundError: If the specified file does not exist.
            PermissionError: If there are permission issues reading the file.
            ValueError: If the file is not a valid PSD.
        """
        if not os.path.exists(filepath):
            error_msg = f"File not found: {filepath}"
            logger.error(error_msg)
            self.show_status(error_msg, "error")
            raise FileNotFoundError(error_msg)
            
        if not os.access(filepath, os.R_OK):
            error_msg = f"Permission denied when reading file: {filepath}"
            logger.error(error_msg)
            self.show_status(error_msg, "error")
            raise PermissionError(error_msg)
            
        try:
            # Show loading state
            self.show_status(f"Loading {os.path.basename(filepath)}...", "info")
            self._show_loading_indicator("Loading PSD file...")
            
            # Reset view state
            self.current_scale = 1.0
            
            # Load the PSD file
            self.psd_doc = PSDDocument.from_file(filepath)
            
            # Update the display
            self._update_canvas()
            self._center_image()
            
            # Update info view if available
            if hasattr(self, 'info_view') and self.info_view:
                self.info_view.update_info(self.psd_doc)
            
            # Show success message
            success_msg = f"Successfully loaded: {os.path.basename(filepath)}"
            logger.info(success_msg)
            self.show_status(success_msg, "success")
            
            return True
            
        except Exception as e:
            error_msg = f"Error loading PSD: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")
            
            # Show error on canvas
            self._show_error_indicator(str(e))
            
            # Re-raise the exception for the controller to handle
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
        if not hasattr(self, 'canvas') or not self.canvas:
            error_msg = "Canvas not initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        if not self.psd_doc or not hasattr(self.psd_doc, 'get_composite_image'):
            self._show_error_indicator("No PSD document loaded")
            return
            
        try:
            # Show loading indicator
            self._show_loading_indicator("Rendering PSD...")
            
            # Get the composite image
            img = self.psd_doc.get_composite_image()
            if not img:
                self._show_error_indicator("Failed to generate composite image")
                return
            
            # Apply scaling if needed
            if abs(self.current_scale - 1.0) > 0.01:  # Only resize if scale is not ~1.0
                try:
                    new_width = max(1, int(img.width * self.current_scale))
                    new_height = max(1, int(img.height * self.current_scale))
                    img = img.resize(
                        (new_width, new_height),
                        Image.Resampling.LANCZOS
                    )
                except Exception as resize_error:
                    error_msg = f"Error scaling image: {resize_error}"
                    logger.exception(error_msg)
                    self._show_error_indicator(error_msg)
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
            
        if not hasattr(self, 'image_on_canvas') or not self.photo_image:
            logger.debug("No image to update scroll region for")
            return
            
        try:
            # Get image dimensions
            img_width = self.photo_image.width()
            img_height = self.photo_image.height()
            
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
            
        if not hasattr(self, 'image_on_canvas') or not self.photo_image:
            logger.debug("No image to center")
            return
            
        try:
            # Get current canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Get image dimensions
            img_width = self.photo_image.width()
            img_height = self.photo_image.height()
            
            # Calculate center position with bounds checking
            x = max(0, (canvas_width - img_width) // 2)
            y = max(0, (canvas_height - img_height) // 2)
            
            # Position the image
            self.canvas.coords(self.image_on_canvas, x, y)
            
            # Update scroll region to ensure all of the image is accessible
            self._update_scroll_region()
            
            # Ensure the image is visible in the viewport
            self.canvas.update_idletasks()
            
            # If the image is larger than the canvas, adjust the view
            if img_width > canvas_width or img_height > canvas_height:
                # Center the view on the image
                self.canvas.xview_moveto(max(0, (x - (canvas_width - img_width) / 2) / img_width))
                self.canvas.yview_moveto(max(0, (y - (canvas_height - img_height) / 2) / img_height))
            
        except Exception as e:
            error_msg = f"Error centering image: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")
    
    def show_status(self, message: str, msg_type: str = "info", duration: int = 5000) -> None:
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
                'info': 'black',
                'success': '#006400',     # Dark green
                'warning': '#8B4513',     # Saddle brown
                'error': '#8B0000'        # Dark red
            }
            
            # Apply styling
            fg_color = colors.get(msg_type.lower(), 'black')
            self.status_bar.config(foreground=fg_color)
            
            # Set font weight based on message type
            font = ('TkDefaultFont', 9)
            if msg_type.lower() in ('warning', 'error'):
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
            log_level = log_levels.get(msg_type.lower(), logging.INFO)
            logger.log(log_level, f"Status: {message}")
            
        except Exception as e:
            logger.exception(f"Error showing status message: {e}")
    
    def clear_status(self) -> None:
        """Clear the status bar."""
        if hasattr(self, 'status_var'):
            self.status_var.set('')
    
    def _on_mouse_wheel(self, event: tk.Event) -> str:
        """Handle mouse wheel for vertical scrolling.
        
        This method handles vertical scrolling when the user uses the mouse wheel.
        It supports multiple platforms and input methods, including:
        - Windows/Mac: Uses event.delta with positive/negative values
        - Linux: Uses event.num (4 for up, 5 for down)
        
        Args:
            event: The mouse wheel event containing delta or button information.
            
        Returns:
            str: "break" to prevent default behavior on all platforms.
            
        Note:
            The method includes platform-specific handling to ensure consistent
            behavior across different operating systems and input devices.
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            return "break"
            
        try:
            # Handle different event types across platforms
            delta = 0
            if hasattr(event, 'delta'):
                # Windows/Mac - delta is positive when scrolling up
                delta = event.delta
                # On some systems, delta might be 120 units per click
                if abs(delta) == 120:
                    delta = 1 if delta > 0 else -1
            elif event.num == 4:  # Linux - scroll up
                delta = 1
            elif event.num == 5:  # Linux - scroll down
                delta = -1
            
            # Apply smooth scrolling with acceleration
            if delta != 0:
                # Calculate scroll amount with acceleration
                scroll_amount = max(1, abs(delta)) * (1 if delta > 0 else -1)
                self.canvas.yview_scroll(-scroll_amount, "units")
                
        except Exception as e:
            logger.exception("Error handling mouse wheel event")
            self.show_status(f"Scroll error: {str(e)}", "error")
            
        return "break"  # Prevent default behavior on all platforms
    
    def _on_ctrl_mouse_wheel(self, event: tk.Event) -> str:
        """Handle Ctrl+MouseWheel for smooth zooming.
        
        This method provides smooth zooming when the user holds Ctrl and scrolls
        the mouse wheel. It includes acceleration for better user experience and
        prevents the default scrolling behavior.
        
        Args:
            event: The mouse wheel event containing delta information.
            
        Returns:
            str: "break" to prevent default behavior on all platforms.
            
        Note:
            The zoom is centered around the mouse cursor position for a more
            intuitive zooming experience.
        """
        if not hasattr(self, 'canvas') or not self.canvas:
            return "break"
            
        try:
            # Get the current mouse position in canvas coordinates
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Handle different event types across platforms
            delta = 0
            if hasattr(event, 'delta'):
                # Windows/Mac - delta is positive when scrolling up
                delta = event.delta
                # Normalize delta to -1 or 1 for consistent behavior
                delta = 1 if delta > 0 else -1
            elif event.num == 4:  # Linux - scroll up
                delta = 1
            elif event.num == 5:  # Linux - scroll down
                delta = -1
            
            # Apply zoom based on scroll direction with mouse position as center
            if delta > 0:
                self.zoom_in(center=(canvas_x, canvas_y))
            elif delta < 0:
                self.zoom_out(center=(canvas_x, canvas_y))
                
        except Exception as e:
            logger.exception("Error handling zoom event")
            self.show_status(f"Zoom error: {str(e)}", "error")
            
        return "break"  # Prevent default behavior on all platforms
    
    def _on_linux_zoom_in(self, event: tk.Event) -> None:
        """Handle zoom in on Linux (Button-4).
        
        This method is specifically for handling zoom in on Linux systems
        where mouse wheel events are reported as button presses.
        
        Args:
            event: The mouse button event.
        """
        if event.num == 4:  # Only handle button 4 (scroll up)
            self.zoom_in()
        return "break"  # Prevent default behavior
    
    def _on_linux_zoom_out(self, event: tk.Event) -> None:
        """Handle zoom out on Linux (Button-5).
        
        This method is specifically for handling zoom out on Linux systems
        where mouse wheel events are reported as button presses.
        
        Args:
            event: The mouse button event.
        """
        if event.num == 5:  # Only handle button 5 (scroll down)
            self.zoom_out()
        return "break"  # Prevent default behavior
    
    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Handle canvas resize events."""
        self._center_image()
    
    def zoom_in(self, event: Optional[tk.Event] = None) -> None:
        """Zoom in the PSD view by 10%.
        
        This method increases the zoom level of the PSD document by 10%,
        up to a maximum of 500% zoom.
        
        Args:
            event: Optional event object (for binding to events).
        """
        if not self.psd_doc or not hasattr(self, 'canvas') or not self.canvas:
            return
            
        try:
            # Calculate new scale with bounds checking
            new_scale = min(5.0, self.current_scale * 1.1)  # Max 500%
            
            # Only update if scale changed significantly
            if abs(new_scale - self.current_scale) > 0.01:
                self.current_scale = new_scale
                self._update_canvas()
                self.show_status(f"Zoom: {int(self.current_scale * 100)}%")
                
        except Exception as e:
            error_msg = f"Error zooming in: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")
    
    def zoom_out(self, event: Optional[tk.Event] = None) -> None:
        """Zoom out the PSD view by 10%.
        
        This method decreases the zoom level of the PSD document by 10%,
        down to a minimum of 10% zoom.
        
        Args:
            event: Optional event object (for binding to events).
        """
        if not self.psd_doc or not hasattr(self, 'canvas') or not self.canvas:
            return
            
        try:
            # Calculate new scale with bounds checking
            new_scale = max(0.1, self.current_scale / 1.1)  # Min 10%
            
            # Only update if scale changed significantly
            if abs(new_scale - self.current_scale) > 0.01:
                self.current_scale = new_scale
                self._update_canvas()
                self.show_status(f"Zoom: {int(self.current_scale * 100)}%")
                
        except Exception as e:
            error_msg = f"Error zooming out: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")
    
    def reset_zoom(self) -> None:
        """Reset zoom to 100% and center the image.
        
        This method resets the zoom level to 100% and centers the image
        in the viewport.
        """
        if not self.psd_doc or not hasattr(self, 'canvas') or not self.canvas:
            return
            
        try:
            if abs(self.current_scale - 1.0) > 0.01:  # Only update if not already at 100%
                self.current_scale = 1.0
                self._update_canvas()
                self.show_status("Zoom: 100%")
            self._center_image()
            
        except Exception as e:
            error_msg = f"Error resetting zoom: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")
    
    def fit_to_window(self) -> None:
        """Fit the PSD to the current window size.
        
        This method calculates the maximum zoom level that allows the entire
        PSD to be visible in the current window, then applies that zoom level
        and centers the image.
        """
        if not self.psd_doc or not hasattr(self, 'canvas') or not self.canvas:
            return
            
        try:
            # Get canvas size with padding
            canvas_width = max(1, self.canvas.winfo_width() - 40)
            canvas_height = max(1, self.canvas.winfo_height() - 40)
            
            # Get image size
            img = self.psd_doc.get_composite_image()
            if not img:
                self.show_status("No image to display", "warning")
                return
                
            # Calculate scale to fit window
            width_scale = canvas_width / img.width
            height_scale = canvas_height / img.height
            
            # Use the smaller scale to ensure entire image is visible
            new_scale = min(width_scale, height_scale)
            
            # Don't scale up beyond 100% unless image is larger than window
            if img.width <= canvas_width and img.height <= canvas_height:
                new_scale = min(1.0, new_scale)
            
            # Only update if scale changed significantly
            if abs(new_scale - self.current_scale) > 0.01:
                self.current_scale = new_scale
                self._update_canvas()
                self.show_status(f"Fit to window: {int(self.current_scale * 100)}%")
            
            # Always center the image after fitting
            self._center_image()
            
        except Exception as e:
            error_msg = f"Error fitting to window: {str(e)}"
            logger.exception(error_msg)
            self.show_status(error_msg, "error")
