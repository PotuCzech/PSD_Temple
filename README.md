# PSD Editor & Template Creator

A powerful Python application for viewing PSD files and creating drawing templates. This application allows you to:

- Open and view PSD files with their layer structure
- Toggle layer visibility and adjust opacity
- Navigate through the PSD with zoom and pan
- Create and manage multiple drawing layers
- Draw shapes (rectangle, ellipse, line, freehand)
- Customize colors, line width, and fill
- Save and load drawing templates
- Export your work as images

## Features

### PSD View
- View PSD files with layer hierarchy
- Toggle layer visibility
- Zoom and pan for navigation
- Fit to window option

### Drawing Tools
- Multiple drawing layers with independent visibility
- Shape tools: Rectangle, Ellipse, Line, Freehand
- Customizable colors and line width
- Fill options with transparency support
- Grid overlay with different styles

### Template Management
- Save and load drawing templates
- Export drawings as images (PNG, JPEG)
- Layer management (add, delete, reorder)
- Undo functionality

## Requirements

- Python 3.7+
- pip (Python package manager)
- Tkinter (usually included with Python)

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application with:

```bash
python main.py
```

## Project Structure

```
psd_editor/
├── __init__.py           # Package initialization
├── main.py               # Main application entry point
├── models/               # Data models
│   ├── __init__.py
│   ├── drawing.py       # Drawing layer and shape models
│   └── psd.py           # PSD document model
├── views/                # UI components
│   ├── __init__.py
│   ├── base.py          # Base view class
│   ├── psd_view.py      # PSD viewing components
│   ├── drawing_view.py  # Drawing canvas and tools
│   └── layers.py        # Layer management UI
└── controllers/          # Application logic
    ├── __init__.py
    ├── psd_controller.py     # PSD operations
    └── drawing_controller.py # Drawing operations
```

## Controls

### PSD View
- **Mouse wheel**: Zoom in/out
- **Right-click + drag**: Pan around the image
- **Ctrl + Mouse wheel**: Fine zoom control
- **Ctrl + 0**: Fit to window

### Drawing Tools
- **Select**: Choose a tool from the toolbar
- **Left-click + drag**: Draw shapes
- **Right-click**: Cancel current drawing
- **Delete**: Remove selected layer
- **Ctrl + Z**: Undo last action

### Layer Management
- **+/- Buttons**: Add/remove layers
- **Up/Down Arrows**: Reorder layers
- **Checkbox**: Toggle layer visibility
- **Click layer**: Select layer for editing

## Keyboard Shortcuts

- **Ctrl + O**: Open PSD file
- **Ctrl + S**: Save template
- **Ctrl + E**: Export image
- **Ctrl + N**: New layer
- **Delete**: Delete selected layer
- **Ctrl + ↑/↓**: Move layer up/down
- **Ctrl + Z**: Undo
- **Ctrl + +**: Zoom in
- **Ctrl + -**: Zoom out
- **Ctrl + 0**: Fit to window

## License

MIT License - Feel free to use and modify this project for your needs.

## License

This project is not open source

## Dependencies

- [psd-tools](https://github.com/psd-tools/psd-tools) - For PSD file manipulation
- [Pillow](https://python-pillow.org/) - For image processing
- [NumPy](https://numpy.org/) - Required by psd-tools
