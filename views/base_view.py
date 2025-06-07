"""
Base view module providing common functionality for all views in the PSD Editor.

This module contains the BaseView class which serves as a base class for all view components.
It provides common functionality such as:
- Basic widget management
- Common UI operations
- Event handling
- Utility methods
"""

import tkinter as tk
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Callable, TypeVar, Type

T = TypeVar('T', bound='BaseView')


class BaseView(tk.Frame, ABC):
    """Base class for all views in the PSD Editor.
    
    This class provides common functionality and serves as an interface
    that all view components should implement.
    """
    
    def __init__(self, parent: Optional[tk.Widget] = None, **kwargs: Any) -> None:
        """Initialize the base view.
        
        Args:
            parent: The parent widget. If None, the root window will be used.
            **kwargs: Additional keyword arguments to pass to the parent class.
        """
        super().__init__(parent or tk.Tk(), **kwargs)
        self.parent = parent
        self._setup_ui()
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """Set up the user interface components.
        
        This method should be implemented by subclasses to create and arrange
        the widgets that make up the view.
        """
        pass
    
    def show(self) -> None:
        """Show the view.
        
        This method makes the view visible and brings it to the front.
        """
        self.lift()
        self.focus_set()
    
    def hide(self) -> None:
        """Hide the view.
        
        This method makes the view invisible.
        """
        self.lower()
    
    def center_on_screen(self) -> None:
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def show_error(self, message: str, title: str = "Error") -> None:
        """Show an error message dialog.
        
        Args:
            message: The error message to display.
            title: The title of the error dialog. Defaults to "Error".
        """
        from tkinter import messagebox
        messagebox.showerror(title, message)
    
    def show_info(self, message: str, title: str = "Information") -> None:
        """Show an information message dialog.
        
        Args:
            message: The information message to display.
            title: The title of the information dialog. Defaults to "Information".
        """
        from tkinter import messagebox
        messagebox.showinfo(title, message)
    
    def show_warning(self, message: str, title: str = "Warning") -> None:
        """Show a warning message dialog.
        
        Args:
            message: The warning message to display.
            title: The title of the warning dialog. Defaults to "Warning".
        """
        from tkinter import messagebox
        messagebox.showwarning(title, message)
    
    def ask_yes_no(self, question: str, title: str = "Confirm") -> bool:
        """Ask a yes/no question.
        
        Args:
            question: The question to ask.
            title: The title of the dialog. Defaults to "Confirm".
            
        Returns:
            bool: True if the user clicked Yes, False otherwise.
        """
        from tkinter import messagebox
        return messagebox.askyesno(title, question)
    
    def ask_ok_cancel(self, question: str, title: str = "Confirm") -> bool:
        """Ask an OK/Cancel question.
        
        Args:
            question: The question to ask.
            title: The title of the dialog. Defaults to "Confirm".
            
        Returns:
            bool: True if the user clicked OK, False otherwise.
        """
        from tkinter import messagebox
        return messagebox.askokcancel(title, question)
    
    def ask_retry_cancel(self, question: str, title: str = "Retry") -> bool:
        """Ask a Retry/Cancel question.
        
        Args:
            question: The question to ask.
            title: The title of the dialog. Defaults to "Retry".
            
        Returns:
            bool: True if the user clicked Retry, False otherwise.
        """
        from tkinter import messagebox
        return messagebox.askretrycancel(title, question)
    
    def ask_yes_no_cancel(self, question: str, title: str = "Confirm") -> str:
        """Ask a Yes/No/Cancel question.
        
        Args:
            question: The question to ask.
            title: The title of the dialog. Defaults to "Confirm".
            
        Returns:
            str: 'yes', 'no', or 'cancel' based on user's choice.
        """
        from tkinter import messagebox
        result = messagebox.askyesnocancel(title, question)
        if result is None:
            return 'cancel'
        return 'yes' if result else 'no'
    
    def ask_string(self, prompt: str, title: str = "Input", default: str = "") -> Optional[str]:
        """Ask the user to enter a string.
        
        Args:
            prompt: The prompt to display.
            title: The title of the dialog. Defaults to "Input".
            default: The default value for the input field. Defaults to "".
            
        Returns:
            Optional[str]: The string entered by the user, or None if cancelled.
        """
        from tkinter import simpledialog
        return simpledialog.askstring(title, prompt, initialvalue=default)
    
    def ask_integer(self, prompt: str, title: str = "Input", default: int = 0, 
                   min_value: Optional[int] = None, max_value: Optional[int] = None) -> Optional[int]:
        """Ask the user to enter an integer.
        
        Args:
            prompt: The prompt to display.
            title: The title of the dialog. Defaults to "Input".
            default: The default value. Defaults to 0.
            min_value: Optional minimum allowed value.
            max_value: Optional maximum allowed value.
            
        Returns:
            Optional[int]: The integer entered by the user, or None if cancelled.
        """
        from tkinter import simpledialog
        while True:
            result = simpledialog.askinteger(title, prompt, initialvalue=default, minvalue=min_value, maxvalue=max_value)
            if result is None:  # User cancelled
                return None
            if min_value is not None and result < min_value:
                self.show_error(f"Value must be at least {min_value}")
                continue
            if max_value is not None and result > max_value:
                self.show_error(f"Value must be at most {max_value}")
                continue
            return result
    
    def ask_float(self, prompt: str, title: str = "Input", default: float = 0.0, 
                 min_value: Optional[float] = None, max_value: Optional[float] = None) -> Optional[float]:
        """Ask the user to enter a float.
        
        Args:
            prompt: The prompt to display.
            title: The title of the dialog. Defaults to "Input".
            default: The default value. Defaults to 0.0.
            min_value: Optional minimum allowed value.
            max_value: Optional maximum allowed value.
            
        Returns:
            Optional[float]: The float entered by the user, or None if cancelled.
        """
        from tkinter import simpledialog
        while True:
            result = simpledialog.askfloat(title, prompt, initialvalue=default, minvalue=min_value, maxvalue=max_value)
            if result is None:  # User cancelled
                return None
            if min_value is not None and result < min_value:
                self.show_error(f"Value must be at least {min_value}")
                continue
            if max_value is not None and result > max_value:
                self.show_error(f"Value must be at most {max_value}")
                continue
            return result
    
    def ask_open_file(self, title: str = "Open File", filetypes: Optional[List[tuple]] = None, 
                     initialdir: Optional[str] = None) -> Optional[str]:
        """Show a file open dialog.
        
        Args:
            title: The title of the dialog. Defaults to "Open File".
            filetypes: List of (label, pattern) tuples for file filtering.
            initialdir: Initial directory to show in the dialog.
            
        Returns:
            Optional[str]: The selected file path, or None if cancelled.
        """
        from tkinter import filedialog
        return filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=initialdir)
    
    def ask_save_file(self, title: str = "Save File", filetypes: Optional[List[tuple]] = None, 
                     initialfile: str = "", defaultextension: str = "",
                     initialdir: Optional[str] = None) -> Optional[str]:
        """Show a file save dialog.
        
        Args:
            title: The title of the dialog. Defaults to "Save File".
            filetypes: List of (label, pattern) tuples for file filtering.
            initialfile: Default filename.
            defaultextension: Default file extension.
            initialdir: Initial directory to show in the dialog.
            
        Returns:
            Optional[str]: The selected file path, or None if cancelled.
        """
        from tkinter import filedialog
        return filedialog.asksaveasfilename(
            title=title, 
            filetypes=filetypes, 
            initialfile=initialfile,
            defaultextension=defaultextension,
            initialdir=initialdir
        )
    
    def ask_directory(self, title: str = "Select Directory", initialdir: Optional[str] = None) -> Optional[str]:
        """Show a directory selection dialog.
        
        Args:
            title: The title of the dialog. Defaults to "Select Directory".
            initialdir: Initial directory to show in the dialog.
            
        Returns:
            Optional[str]: The selected directory path, or None if cancelled.
        """
        from tkinter import filedialog
        return filedialog.askdirectory(title=title, mustexist=True, initialdir=initialdir)
    
    def ask_color(self, title: str = "Choose a color", initialcolor: Optional[str] = None) -> Optional[str]:
        """Show a color chooser dialog.
        
        Args:
            title: The title of the dialog. Defaults to "Choose a color".
            initialcolor: Initial color to show in the dialog (e.g., "#ff0000" for red).
            
        Returns:
            Optional[str]: The selected color as a hex string (e.g., "#ff0000"), or None if cancelled.
        """
        from tkinter import colorchooser
        color = colorchooser.askcolor(title=title, color=initialcolor)
        return color[1] if color and color[1] else None
    
    def create_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Create a tooltip that appears when hovering over a widget.
        
        Args:
            widget: The widget to attach the tooltip to.
            text: The text to display in the tooltip.
        """
        from tkinter import Toplevel, Label
        
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create the tooltip window
            tooltip = Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Add the tooltip text
            label = Label(tooltip, text=text, justify='left',
                         background='#ffffe0', relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
            label.pack(ipadx=1)
            
            # Store the tooltip reference
            widget.tooltip = tooltip
            
            # Bind events to remove the tooltip
            widget.bind('<Leave>', lambda e: tooltip.destroy(), add='+')
            widget.bind('<ButtonPress>', lambda e: tooltip.destroy(), add='+')
        
        # Bind the enter event to show the tooltip
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', lambda e: widget.tooltip.destroy() if hasattr(widget, 'tooltip') else None)
    
    def create_context_menu(self, widget: tk.Widget, menu_items: List[Dict[str, Any]]) -> None:
        """Create a context menu for a widget.
        
        Args:
            widget: The widget to attach the context menu to.
            menu_items: List of menu item dictionaries. Each dictionary should have:
                - 'label': The text to display for the menu item
                - 'command': The function to call when the item is selected
                - 'state': Optional state of the menu item ('normal', 'disabled')
                - 'separator': Optional boolean to add a separator after the item
        """
        from tkinter import Menu
        
        context_menu = Menu(widget, tearoff=0)
        
        for item in menu_items:
            if 'separator' in item and item['separator']:
                context_menu.add_separator()
            else:
                state = item.get('state', 'normal')
                context_menu.add_command(
                    label=item['label'],
                    command=item['command'],
                    state=state
                )
        
        def show_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        widget.bind("<Button-3>", show_menu)
    
    def create_toolbar(self, parent: tk.Widget, buttons: List[Dict[str, Any]], 
                      orientation: str = 'horizontal', padx: int = 2, pady: int = 2) -> tk.Frame:
        """Create a toolbar with buttons.
        
        Args:
            parent: The parent widget.
            buttons: List of button dictionaries. Each dictionary should have:
                - 'text': The text to display on the button
                - 'command': The function to call when the button is clicked
                - 'image': Optional image to display on the button
                - 'tooltip': Optional tooltip text
                - 'state': Optional state of the button ('normal', 'disabled')
            orientation: The orientation of the toolbar ('horizontal' or 'vertical').
            padx: Horizontal padding between buttons.
            pady: Vertical padding between buttons.
            
        Returns:
            tk.Frame: The frame containing the toolbar buttons.
        """
        toolbar = tk.Frame(parent)
        
        for i, button_def in enumerate(buttons):
            btn = tk.Button(
                toolbar,
                text=button_def.get('text', ''),
                image=button_def.get('image'),
                compound=tk.LEFT,
                command=button_def['command'],
                state=button_def.get('state', 'normal')
            )
            
            if orientation == 'horizontal':
                btn.pack(side=tk.LEFT, padx=padx, pady=pady)
            else:  # vertical
                btn.pack(fill=tk.X, padx=padx, pady=pady)
            
            if 'tooltip' in button_def:
                self.create_tooltip(btn, button_def['tooltip'])
        
        return toolbar
