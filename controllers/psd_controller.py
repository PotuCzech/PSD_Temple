"""
Controller for PSD-related operations.

This module handles the business logic for PSD file operations,
including loading, saving, and manipulating PSD documents.
"""
import os
import logging
from typing import Optional, Dict, Any, Callable, List, TYPE_CHECKING
import tkinter as tk
from tkinter import ttk

from psd_editor.models.psd import PSDDocument

if TYPE_CHECKING:
    from psd_editor.views.psd_view import PSDView

# Set up logging
logger = logging.getLogger(__name__)

class PSDController:
    """Controller for PSD-related operations."""
    
    def __init__(self, view: 'PSDView'):
        """Initialize the PSD controller.
        
        Args:
            view: The PSD view to control.
        """
        self.view = view
        self.psd_doc: Optional[PSDDocument] = None
        self.root = view.winfo_toplevel()  # Store reference to root window
        
        # Register callbacks
        self.view.register_callback('zoom_in', self.zoom_in)
        self.view.register_callback('zoom_out', self.zoom_out)
        self.view.register_callback('fit_to_window', self.fit_to_window)
    
    def load_psd(self, filepath: str, render_mode: Optional[str] = None) -> None:
        """Load a PSD file into the view with rendering mode selection.
        
        Args:
            filepath: Path to the PSD file to load.
            render_mode: Optional rendering mode ('full' or 'light').
                         If None, shows a dialog to select rendering mode.
            
        Raises:
            ValueError: If the file is not a valid PSD.
        """
        if not os.path.exists(filepath):
            error_msg = f"File not found: {filepath}"
            logger.error(error_msg)
            self.view.show_status(error_msg, "error", duration=5000)
            raise FileNotFoundError(error_msg)
            
        if not os.access(filepath, os.R_OK):
            error_msg = f"Permission denied when reading file: {filepath}"
            logger.error(error_msg)
            self.view.show_status(error_msg, "error", duration=5000)
            raise PermissionError(error_msg)
            
        # Show rendering mode selection dialog if not specified
        if render_mode is None:
            render_mode = self._show_rendering_mode_dialog()
            
        if render_mode not in ['light', 'full']:
            raise ValueError(f"Invalid render mode: {render_mode}")
            
        try:
            self.psd_doc = PSDDocument.from_file(filepath, render_mode=render_mode)
            success = self.view.load_psd(filepath, render_mode=render_mode)
            if success:
                logger.info(f"Successfully loaded PSD: {filepath} in {render_mode} mode")
                self.view.show_status(f"Loaded: {os.path.basename(filepath)} in {render_mode} mode", "success")
                # Automatically fit the PSD to the window
                self.view.fit_to_window()
            return success
            
        except Exception as e:
            error_msg = f"Error loading PSD: {str(e)}"
            logger.exception(error_msg)
            self.view.show_status(f"Error loading PSD: {str(e)}", "error", duration=5000)
            raise ValueError(f"Invalid PSD file: {filepath}") from e
    
    def save_psd(self, filepath: Optional[str] = None) -> bool:
        """Save the current PSD.
        
        Args:
            filepath: Optional path to save the PSD. Uses current path if None.
            
        Returns:
            bool: True if saved successfully, False otherwise.
        """
        if not self.psd_doc:
            return False
            
        try:
            return self.psd_doc.save(filepath)
        except Exception as e:
            print(f"Error saving PSD: {e}")
            return False
    
    def update_view(self) -> None:
        """Update the view when switching to the PSD tab.
        
        This method is called when the user switches to the PSD view tab.
        It updates the view with the current PSD document state.
        """
        try:
            if self.psd_doc:
                # Update the view with the current PSD document
                self.view.load_psd(self.psd_doc.filepath, render_mode=self.psd_doc._render_mode)
                self.view.fit_to_window()
        except Exception as e:
            logger.exception("Error updating view")
            self.view.show_status(f"Error updating view: {str(e)}", "error", duration=5000)

    def cleanup(self) -> None:
        """Clean up resources used by the PSD controller.
        
        This method should be called when the controller is no longer needed
        to ensure proper cleanup of resources.
        """
        try:
            # Clean up the PSD document
            if hasattr(self, 'psd_doc') and self.psd_doc is not None:
                self.psd_doc = None
                
            # Clean up any view resources
            if hasattr(self, 'view') and self.view is not None:
                self.view.cleanup()
                self.view = None
                
            logger.debug("PSDController cleanup completed")
            
        except Exception as e:
            logger.exception("Error during PSDController cleanup")

    def get_layer_tree(self) -> List[Dict[str, Any]]:
        """Get the layer hierarchy as a tree structure.
        
        Returns:
            List of dictionaries representing the layer tree.
        """
        if not self.psd_doc:
            return []
        return self.psd_doc.get_layer_tree()
    
    def set_layer_visibility(self, layer_name: str, visible: bool) -> bool:
        """Set the visibility of a layer.
        
        Args:
            layer_name: Name of the layer.
            visible: Whether the layer should be visible.
            
        Returns:
            bool: True if the layer was found and updated, False otherwise.
        """
        if not self.psd_doc:
            return False
            
        return self.psd_doc.set_layer_visibility(layer_name, visible)
    
    def zoom_in(self, event=None) -> None:
        """Zoom in the PSD view."""
        self.view.zoom_in()
    
    def zoom_out(self, event=None) -> None:
        """Zoom out the PSD view."""
        self.view.zoom_out()
    
    def fit_to_window(self) -> None:
        """Fit the PSD to the current window size."""
        self.view.fit_to_window()
    
    def get_photo_image(self) -> Any:
        """Get the current PSD as a PhotoImage.
        
        Returns:
            A Tkinter PhotoImage of the PSD, or None if no PSD is loaded.
        """
        if not self.psd_doc:
            return None
        return self.psd_doc.get_photo_image()
    
    def _show_rendering_mode_dialog(self) -> str:
        """Show dialog to select rendering mode.
        
        Returns:
            str: The selected rendering mode ('light' or 'full')
        """
        # Create modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Rendering Mode")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame for dialog content
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add description
        ttk.Label(frame, text="Select rendering mode:").pack(pady=(0, 10))
        
        # Add radio buttons
        mode_var = tk.StringVar(value="light")
        
        # Create light mode radio button
        light_radio = ttk.Radiobutton(
            frame,
            text="Light Mode (faster, less memory usage)",
            variable=mode_var,
            value="light"
        )
        light_radio.pack(anchor=tk.W, padx=5)
        
        # Create full mode radio button
        full_radio = ttk.Radiobutton(
            frame,
            text="Full Mode (slower, more memory usage)",
            variable=mode_var,
            value="full"
        )
        full_radio.pack(anchor=tk.W, padx=5)
        
        # Add OK button
        ok_button = ttk.Button(
            frame,
            text="OK",
            command=dialog.destroy
        )
        ok_button.pack(pady=(10, 0))
        
        # Make dialog modal and wait for user response
        dialog.wait_window()
        
        return mode_var.get()

    def is_loaded(self) -> bool:
        """Check if a PSD is loaded.
        
        Returns:
            bool: True if a PSD is loaded, False otherwise.
        """
        return self.psd_doc is not None and self.psd_doc.is_loaded()
