"""
Base view class for the PSD Editor.
"""
import tkinter as tk
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable

class BaseView(ABC):
    """Base class for all views in the application."""
    
    def __init__(self, parent: tk.Widget, **kwargs):
        """Initialize the base view.
        
        Args:
            parent: The parent widget.
            **kwargs: Additional keyword arguments for the frame.
        """
        self.parent = parent
        self.frame = tk.Frame(parent, **kwargs)
        self._callbacks: Dict[str, Callable] = {}
        
        self._setup_ui()
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        pass
    
    def pack(self, **kwargs) -> None:
        """Pack the view's frame.
        
        Args:
            **kwargs: Pack options.
        """
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the view's frame.
        
        Args:
            **kwargs: Grid options.
        """
        self.frame.grid(**kwargs)
    
    def place(self, **kwargs) -> None:
        """Place the view's frame.
        
        Args:
            **kwargs: Place options.
        """
        self.frame.place(**kwargs)
    
    def register_callback(self, name: str, callback: Callable) -> None:
        """Register a callback function.
        
        Args:
            name: Name of the callback.
            callback: The callback function.
        """
        self._callbacks[name] = callback
    
    def trigger_callback(self, name: str, *args, **kwargs) -> Any:
        """Trigger a registered callback.
        
        Args:
            name: Name of the callback to trigger.
            *args: Positional arguments to pass to the callback.
            **kwargs: Keyword arguments to pass to the callback.
            
        Returns:
            The result of the callback, or None if not found.
        """
        if name in self._callbacks:
            return self._callbacks[name](*args, **kwargs)
        return None
