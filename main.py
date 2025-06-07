"""
PSD Editor - A tool for viewing and editing PSD files with drawing capabilities.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu, font
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('psd_editor.log', mode='w')  # Overwrite log file each run
    ]
)

# Set psd_tools to WARNING level to reduce noise
logging.getLogger('psd_tools').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
if __name__ == "__main__":
    # Add the project root to the Python path
    project_root = Path(__file__).parent.absolute()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Also add the parent directory to the Python path
    parent_dir = project_root.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

# Import from local modules using absolute imports
from psd_editor.views.psd_view import PSDView
from psd_editor.views.drawing_view import DrawingView
from psd_editor.views.layers import LayerManagerView
from psd_editor.controllers.psd_controller import PSDController
from psd_editor.controllers.drawing_controller import DrawingController

class PSDEditor:
    """Main application class for the PSD Editor."""
    
    def __init__(self, root):
        """Initialize the PSD Editor with modern UI practices.
        
        Args:
            root: The root Tkinter window.
        """
        try:
            self.root = root
            self.root.title("PSD Editor & Template Creator")
            
            # Set minimum window size
            self.root.minsize(1024, 768)
            
            # Configure window style
            self.root.configure(bg='#f0f0f0')
            
            # Configure styles
            self._setup_styles()
            
            # Create main containers
            self._create_ui()
            
            # Initialize controllers
            self.psd_controller = PSDController(self.psd_view)
            self.drawing_controller = DrawingController(self.drawing_view, self.layer_view)
            
            # Set up menu
            self._create_menu()
            
            # Bind keyboard shortcuts
            self._bind_shortcuts()
            
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            logger.info("PSD Editor initialized successfully")
            
        except Exception as e:
            logger.exception("Error initializing PSD Editor")
            messagebox.showerror("Initialization Error", 
                              f"Failed to initialize the application: {str(e)}")
            self.root.quit()
    
    def _setup_styles(self) -> None:
        """Configure ttk styles with modern appearance."""
        style = ttk.Style()
        
        # Configure the notebook style
        style.configure("TNotebook", 
                       tabposition='n',
                       background='#f0f0f0',
                       padding=5)
        style.configure("TNotebook.Tab", 
                       padding=[20, 10],
                       font=('Arial', 10, 'bold'))
        
        # Configure button styles
        style.configure("TButton", 
                       padding=10,
                       relief='flat',
                       background='#f0f0f0',
                       foreground='#333333')
        style.map("TButton",
                 background=[('active', '#e0e0e0')])
        
        # Configure frame styles
        style.configure("TFrame", 
                       background='#f0f0f0')
        
        # Configure label styles
        style.configure("TLabel", 
                       padding=5,
                       background='#f0f0f0',
                       font=('Arial', 10))
        
        # Configure scrollbar styles
        style.configure("TScrollbar", 
                       gripcount=0,
                       background='#f0f0f0',
                       troughcolor='#e0e0e0',
                       width=12)
        
        # Configure menu styles
        style.configure("TMenubutton",
                       padding=5,
                       relief='flat',
                       background='#f0f0f0')
        
        logger.debug("Styles configured successfully")
    
    def _create_ui(self) -> None:
        """Create the main user interface with modern layout."""
        try:
            # Create main container with padding
            self.main_frame = ttk.Frame(self.root, padding="12")
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create notebook for tabs with padding
            self.notebook = ttk.Notebook(self.main_frame)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            
            # Create PSD tab with modern styling
            self.psd_tab = ttk.Frame(self.notebook, padding="12")
            self.notebook.add(self.psd_tab, text="PSD View")
            
            # Create Drawing tab with modern styling
            self.drawing_tab = ttk.Frame(self.notebook, padding="12")
            self.notebook.add(self.drawing_tab, text="Drawing")
            
            # Set up PSD view
            self._setup_psd_view()
            
            # Set up Drawing view
            self._setup_drawing_view()
            
            # Bind tab change event
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
            
            logger.debug("UI components created successfully")
            
        except Exception as e:
            logger.exception("Error creating UI components")
            messagebox.showerror("UI Error", 
                              f"Failed to create UI components: {str(e)}")
            self.root.quit()

    def show_status(self, message: str, msg_type: str = "info", duration: int = 5000) -> None:
        """Show a status message in the status bar with proper styling."""
        try:
            if hasattr(self, 'status_var') and self.status_var:
                # Apply styling based on message type
                if msg_type == "success":
                    self.status_var.set(f"✓ {message}")
                elif msg_type == "error":
                    self.status_var.set(f"✗ {message}")
                else:
                    self.status_var.set(message)
                
                # Clear message after duration if not info
                if msg_type != "info":
                    if hasattr(self, '_status_timer') and self._status_timer:
                        self.root.after_cancel(self._status_timer)
                    self._status_timer = self.root.after(duration, self.clear_status)
        except Exception as e:
            logger.exception("Error showing status message")

    def clear_status(self) -> None:
        """Clear the status message."""
        try:
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set("")
        except Exception as e:
            logger.exception("Error clearing status message")

    def _on_tab_changed(self, event: tk.Event) -> None:
        """Handle tab changes in the notebook."""
        try:
            # Get the selected tab
            selected_tab = self.notebook.select()
            tab_text = self.notebook.tab(selected_tab, "text")
            
            # Update status bar
            self.show_status(f"Switched to {tab_text} tab")
            
            # Update controllers based on tab
            if tab_text == "PSD View":
                self.psd_controller.update_view()
            elif tab_text == "Drawing":
                self.drawing_controller.update_view()
            
        except Exception as e:
            logger.exception("Error handling tab change")
            messagebox.showerror("Tab Error", 
                              f"Failed to handle tab change: {str(e)}")

    def _on_closing(self) -> None:
        """Handle window closing event."""
        try:
            # Ask for confirmation
            if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
                # Clean up controllers
                self.psd_controller.cleanup()
                self.drawing_controller.cleanup()
                
                # Close the window
                self.root.destroy()
                
        except Exception as e:
            logger.exception("Error during window closing")
            messagebox.showerror("Error", 
                              f"Failed to close properly: {str(e)}")
            self.root.destroy()
    
    def _setup_psd_view(self) -> None:
        """Set up the PSD view tab."""
        # Create PSD view
        self.psd_view = PSDView(self.psd_tab)
        self.psd_view.pack(fill=tk.BOTH, expand=True)
    
    def _setup_drawing_view(self) -> None:
        """Set up the drawing view tab."""
        # Create main container with paned window
        self.drawing_paned = ttk.PanedWindow(self.drawing_tab, orient=tk.HORIZONTAL)
        self.drawing_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left pane - drawing canvas
        self.canvas_frame = ttk.Frame(self.drawing_paned)
        self.drawing_paned.add(self.canvas_frame, weight=3)
        
        # Right pane - layers and tools
        self.tools_frame = ttk.Frame(self.drawing_paned, width=250)
        self.drawing_paned.add(self.tools_frame, weight=1)
        
        # Create drawing view
        self.drawing_view = DrawingView(self.canvas_frame)
        self.drawing_view.pack(fill=tk.BOTH, expand=True)
        
        # Create layer view
        self.layer_view = LayerManagerView(self.tools_frame)
        self.layer_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_menu(self) -> None:
        """Create the main menu with modern styling."""
        try:
            menubar = Menu(self.root, tearoff=0)
            self.root.config(menu=menubar)
            
            # File menu
            file_menu = Menu(menubar, tearoff=0)
            file_menu.add_command(
                label="Open PSD...",
                command=self.open_psd,
                accelerator="Ctrl+O",
                font=('Arial', 10)
            )
            file_menu.add_separator()
            file_menu.add_command(
                label="Save Template As...",
                command=self.save_template,
                font=('Arial', 10)
            )
            file_menu.add_command(
                label="Load Template...",
                command=self.load_template,
                font=('Arial', 10)
            )
            file_menu.add_separator()
            file_menu.add_command(
                label="Export Image...",
                command=self.export_image,
                font=('Arial', 10)
            )
            file_menu.add_separator()
            file_menu.add_command(
                label="Exit",
                command=self.root.quit,
                font=('Arial', 10)
            )
            menubar.add_cascade(
                label="File",
                menu=file_menu,
                font=('Arial', 10, 'bold')
            )
            
            # Edit menu
            edit_menu = Menu(menubar, tearoff=0)
            edit_menu.add_command(
                label="Undo",
                command=self.undo,
                accelerator="Ctrl+Z",
                font=('Arial', 10)
            )
            edit_menu.add_command(
                label="Clear Drawing",
                command=self.clear_drawing,
                font=('Arial', 10)
            )
            menubar.add_cascade(
                label="Edit",
                menu=edit_menu,
                font=('Arial', 10, 'bold')
            )
            
            # View menu
            view_menu = Menu(menubar, tearoff=0)
            view_menu.add_command(
                label="Zoom In",
                command=self.zoom_in,
                accelerator="Ctrl++",
                font=('Arial', 10)
            )
            view_menu.add_command(
                label="Zoom Out",
                command=self.zoom_out,
                accelerator="Ctrl+-",
                font=('Arial', 10)
            )
            view_menu.add_command(
                label="Fit to Window",
                command=self.fit_to_window,
                accelerator="Ctrl+0",
                font=('Arial', 10)
            )
            view_menu.add_separator()
            view_menu.add_command(
                label="Show PSD Structure",
                command=self._show_psd_structure,
                font=('Arial', 10)
            )
            menubar.add_cascade(
                label="View",
                menu=view_menu,
                font=('Arial', 10, 'bold')
            )
            
            # Layer menu
            layer_menu = Menu(menubar, tearoff=0)
            layer_menu.add_command(
                label="New Layer",
                command=self.add_layer,
                accelerator="Ctrl+N",
                font=('Arial', 10)
            )
            layer_menu.add_command(
                label="Delete Layer",
                command=self.delete_layer,
                accelerator="Delete",
                font=('Arial', 10)
            )
            layer_menu.add_separator()
            layer_menu.add_command(
                label="Move Layer Up",
                command=self.move_layer_up,
                accelerator="Ctrl+Up",
                font=('Arial', 10)
            )
            layer_menu.add_command(
                label="Move Layer Down",
                command=self.move_layer_down,
                accelerator="Ctrl+Down",
                font=('Arial', 10)
            )
            menubar.add_cascade(
                label="Layer",
                menu=layer_menu,
                font=('Arial', 10, 'bold')
            )
            
            logger.debug("Menu created successfully")
            
        except Exception as e:
            logger.exception("Error creating menu")
            messagebox.showerror("Error", 
                              f"Failed to create menu: {str(e)}")
    
    def open_psd(self) -> None:
        """Open a PSD file for editing."""
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("PSD files", "*.psd"),
                ("All files", "*.*")
            ],
            title="Open PSD File"
        )
        
        if filepath:
            try:
                if self.psd_controller.load_psd(filepath):
                    self.notebook.select(0)  # Switch to PSD view
                    self.show_status(f"Loaded PSD: {os.path.basename(filepath)}", "info")
                else:
                    messagebox.showerror("Error", "Failed to load PSD file")
            except Exception as e:
                logger.exception("Error loading PSD file")
                messagebox.showerror("Error", f"Failed to load PSD file: {str(e)}")
    
    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        # File operations
        self.root.bind("<Control-o>", lambda e: self.open_psd())
        
        # Navigation
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.fit_to_window())
        
        # Layer operations
        self.root.bind("<Control-n>", lambda e: self.add_layer())
        self.root.bind("<Delete>", lambda e: self.delete_layer())
        self.root.bind("<Control-Up>", lambda e: self.move_layer_up())
        self.root.bind("<Control-Down>", lambda e: self.move_layer_down())
        
        # Edit operations
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-s>", lambda e: self.save_psd())
        self.root.bind("<Control-e>", lambda e: self.export_image())
    
    def save_psd(self) -> None:
        """Save the current PSD."""
        if not self.psd_controller.is_loaded():
            messagebox.showinfo("Info", "No PSD file is currently open")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".psd",
            filetypes=[("PSD files", "*.psd"), ("All files", "*.*")],
            title="Save PSD As"
        )
        
        if filepath:
            if self.psd_controller.save_psd(filepath):
                messagebox.showinfo("Success", f"PSD saved to {filepath}")
            else:
                messagebox.showerror("Error", f"Failed to save PSD: {filepath}")
    
    def save_template(self) -> None:
        """Save the current drawing as a template."""
        self.notebook.select(1)  # Switch to Drawing view
        self.drawing_controller.save_template()
    
    def load_template(self) -> None:
        """Load a template."""
        self.notebook.select(1)  # Switch to Drawing view
        self.drawing_controller.load_template()
    
    def export_image(self) -> None:
        """Export the current view as an image."""
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:  # PSD View
            if self.psd_controller.is_loaded():
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[
                        ("PNG files", "*.png"),
                        ("JPEG files", "*.jpg;*.jpeg"),
                        ("All files", "*.*")
                    ],
                    title="Export PSD As"
                )
                
                if filepath:
                    try:
                        img = self.psd_controller.psd_doc.get_composite_image()
                        if img:
                            img.save(filepath)
                            messagebox.showinfo("Success", f"Image exported to {filepath}")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to export image: {e}")
            else:
                messagebox.showinfo("Info", "No PSD file is currently open")
        else:  # Drawing View
            self.drawing_controller.export_image()
    
    def undo(self) -> None:
        """Undo the last action."""
        # This is a placeholder - actual implementation would depend on the drawing view
        messagebox.showinfo("Info", "Undo functionality not yet implemented")
    
    def clear_drawing(self) -> None:
        """Clear the current drawing."""
        self.drawing_controller.clear_drawing()
    
    def zoom_in(self) -> None:
        """Zoom in the current view."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # PSD View
            self.psd_controller.zoom_in()
        # Drawing view zoom would be handled by the drawing controller
    
    def zoom_out(self) -> None:
        """Zoom out the current view."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # PSD View
            self.psd_controller.zoom_out()
        # Drawing view zoom would be handled by the drawing controller
    
    def fit_to_window(self) -> None:
        """Fit the current view to the window."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # PSD View
            self.psd_controller.fit_to_window()
        # Drawing view fit would be handled by the drawing controller
    
    def add_layer(self) -> None:
        """Add a new layer."""
        self.notebook.select(1)  # Switch to Drawing view
        self.drawing_controller.add_layer()
    
    def delete_layer(self) -> None:
        """Delete the active layer."""
        self.drawing_controller.delete_layer(self.drawing_controller.active_layer_id)
    
    def move_layer_up(self) -> None:
        """Move the active layer up."""
        if self.drawing_controller.active_layer_id is not None:
            self.drawing_controller.move_layer(self.drawing_controller.active_layer_id, 'up')
    
    def move_layer_down(self) -> None:
        """Move the active layer down."""
        if self.drawing_controller.active_layer_id is not None:
            self.drawing_controller.move_layer(self.drawing_controller.active_layer_id, 'down')

    def _show_psd_structure(self) -> None:
        """Display the PSD structure in a new window."""
        if not hasattr(self, 'psd_controller') or not self.psd_controller.psd_doc:
            messagebox.showinfo("No PSD Loaded", "Please open a PSD file first.")
            return
            
        try:
            # Create a new top-level window
            window = tk.Toplevel(self.root)
            window.title("PSD Structure")
            window.geometry("800x600")
            
            # Create a frame for the text widget and scrollbars
            frame = ttk.Frame(window)
            frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Add scrollbars
            y_scroll = ttk.Scrollbar(frame)
            x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
            
            # Create the text widget
            text = tk.Text(
                frame,
                wrap=tk.NONE,
                yscrollcommand=y_scroll.set,
                xscrollcommand=x_scroll.set,
                font=('Consolas', 10),
                bg='white',
                fg='black'
            )
            
            # Configure scrollbars
            y_scroll.config(command=text.yview)
            x_scroll.config(command=text.xview)
            
            # Grid layout
            text.grid(row=0, column=0, sticky='nsew')
            y_scroll.grid(row=0, column=1, sticky='ns')
            x_scroll.grid(row=1, column=0, sticky='ew')
            
            # Configure grid weights
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            
            # Add a button to copy to clipboard
            button_frame = ttk.Frame(window)
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            copy_btn = ttk.Button(
                button_frame,
                text="Copy to Clipboard",
                command=lambda: self._copy_to_clipboard(text.get("1.0", tk.END))
            )
            copy_btn.pack(side=tk.RIGHT, padx=5)
            
            # Get the PSD structure as JSON
            json_str = self.psd_controller.psd_doc.to_json(indent=2)
            
            # Insert the JSON into the text widget
            text.insert(tk.END, json_str)
            
            # Make the text read-only
            text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.exception("Error displaying PSD structure")
            messagebox.showerror("Error", f"Failed to display PSD structure: {str(e)}")
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to the system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # Required to make the clipboard work on some platforms
        messagebox.showinfo("Copied", "PSD structure copied to clipboard.")

def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = PSDEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()