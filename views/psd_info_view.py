"""
PSD Info View - Displays PSD document information in a tabbed interface.
"""
import json
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from PIL import ImageTk

class PSDInfoView(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.psd_doc = None
        self._setup_ui()
        
    def _setup_ui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: General Info
        self.general_frame = ttk.Frame(self.notebook)
        self.general_text = tk.Text(
            self.general_frame, 
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        scrollbar = ttk.Scrollbar(
            self.general_frame, 
            command=self.general_text.yview
        )
        self.general_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.general_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.general_frame, text="General Info")
        
        # Tab 2: Layer Info
        self.layer_frame = ttk.Frame(self.notebook)
        self.layer_text = tk.Text(
            self.layer_frame,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        scrollbar = ttk.Scrollbar(
            self.layer_frame,
            command=self.layer_text.yview
        )
        self.layer_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.layer_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.layer_frame, text="Layer Info")
        
        # Tab 3: JSON View
        self.json_frame = ttk.Frame(self.notebook)
        self.json_text = tk.Text(
            self.json_frame,
            wrap=tk.NONE,
            state=tk.DISABLED,
            font=('Consolas', 9)
        )
        h_scrollbar = ttk.Scrollbar(
            self.json_frame,
            orient=tk.HORIZONTAL,
            command=self.json_text.xview
        )
        v_scrollbar = ttk.Scrollbar(
            self.json_frame,
            command=self.json_text.yview
        )
        self.json_text.configure(
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.json_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.json_frame, text="JSON View")
        
    def update_info(self, psd_doc):
        """Update all information tabs with PSD document data."""
        self.psd_doc = psd_doc
        self._update_general_info()
        self._update_layer_info()
        self._update_json_view()
        
    def _update_general_info(self):
        """Update the general information tab."""
        if not self.psd_doc or not hasattr(self.psd_doc, 'psd'):
            return
            
        psd = self.psd_doc.psd
        info = [
            f"File: {getattr(psd, 'name', 'N/A')}",
            f"Size: {getattr(psd, 'width', 0)}x{getattr(psd, 'height', 0)} px",
            f"Color Mode: {getattr(psd.header, 'color_mode', 'N/A')}",
            f"Channels: {getattr(psd.header, 'channels', 'N/A')}",
            f"Bits/Channel: {getattr(psd.header, 'depth', 'N/A')}",
            f"Resolution: {getattr(psd, 'resolution', 'N/A')}",
            f"Layers: {len(list(psd.descendants())) if hasattr(psd, 'descendants') else 0}",
            f"Has Thumbnail: {hasattr(psd, 'thumbnail')}",
            f"Has Preview: {hasattr(psd, 'preview')}",
            f"Has Vector Data: {hasattr(psd, 'vector_data')}",
            f"Has Grid and Guides: {hasattr(psd, 'grid_and_guides')}",
            f"Created: {getattr(psd, 'created_at', 'N/A')}",
            f"Modified: {getattr(psd, 'modified_at', 'N/A')}",
            f"Version: {getattr(psd, 'version', 'N/A')}",
        ]
        
        self._update_text_widget(self.general_text, "\n".join(info))
        
    def _update_layer_info(self):
        """Update the layer information tab."""
        if not self.psd_doc or not hasattr(self.psd_doc, 'psd'):
            return
            
        layers_info = []
        for i, layer in enumerate(self.psd_doc.psd.descendants()):
            layers_info.extend([
                f"Layer {i+1}: {getattr(layer, 'name', 'Unnamed')}",
                f"  Type: {getattr(layer, 'kind', 'N/A')}",
                f"  Size: {getattr(layer, 'width', 0)}x{getattr(layer, 'height', 0)}",
                f"  Position: ({getattr(layer, 'left', 0)}, {getattr(layer, 'top', 0)})",
                f"  Visible: {getattr(layer, 'visible', False)}",
                f"  Opacity: {getattr(layer, 'opacity', 100)}%",
                f"  Blend Mode: {getattr(layer, 'blend_mode', 'N/A')}",
                "-" * 40
            ])
            
        self._update_text_widget(
            self.layer_text, 
            "\n".join(layers_info) if layers_info else "No layers found"
        )
        
    def _update_json_view(self):
        """Update the JSON view tab with PSD document data."""
        if not self.psd_doc or not hasattr(self.psd_doc, 'psd'):
            return
            
        try:
            # Convert PSD document to a serializable dictionary
            def psd_to_dict(psd):
                if hasattr(psd, '__dict__'):
                    result = {}
                    for key, value in psd.__dict__.items():
                        if not key.startswith('_'):
                            try:
                                result[key] = psd_to_dict(value)
                            except:
                                result[key] = str(value)
                    return result
                elif isinstance(psd, (list, tuple)):
                    return [psd_to_dict(item) for item in psd]
                else:
                    return str(psd)
                    
            psd_dict = psd_to_dict(self.psd_doc.psd)
            json_str = json.dumps(
                psd_dict,
                indent=2,
                default=str,
                ensure_ascii=False
            )
            self._update_text_widget(self.json_text, json_str)
        except Exception as e:
            self._update_text_widget(
                self.json_text,
                f"Error generating JSON view: {str(e)}"
            )
            
    def _update_text_widget(self, widget, text):
        """Helper method to update a text widget."""
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)
        widget.see(tk.END)  # Scroll to the end of the text
