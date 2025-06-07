"""
Rendering module for PSD files.

This module provides different rendering strategies for PSD files,
including full and light rendering modes.
"""

import logging
import threading
from typing import Optional, Callable
from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
from psd_tools.api.layers import Layer, Group, TypeLayer, ShapeLayer, PixelLayer, SmartObjectLayer

logger = logging.getLogger(__name__)

class Renderer:
    """Base class for PSD renderers."""
    def get_composite_image(self) -> Image.Image:
        raise NotImplementedError()


class PSDFullRenderer(Renderer):
    """Full rendering mode with caching and background loading."""
    def __init__(self, psd: PSDImage, filepath: Optional[str] = None):
        self.psd = psd
        self.filepath = filepath
        self._composite: Optional[Image.Image] = None
        self._loading = False
        self._callbacks: list[Callable[[Image.Image], None]] = []

        if filepath and hasattr(psd, 'composite'):
            try:
                from utils.cache_manager import psd_cache
                cached = psd_cache.get_cached_image(filepath, "_full")
                if cached:
                    self._composite = cached
            except Exception as e:
                logger.warning(f"Failed to load from cache: {e}")

    def _generate_composite(self) -> Image.Image:
        composite = None
        methods_tried = []

        logger.debug(f"Generating composite for PSD: {type(self.psd).__name__}")

        try_methods = [
            ('psd.composite()', lambda: self.psd.composite()),
            ('psd.topil()', lambda: self.psd.topil()),
            ('psd.get_composite_image()', lambda: self.psd.get_composite_image())
        ]

        for method_name, method in try_methods:
            try:
                if hasattr(self.psd, method.__name__.split('.')[-1]):
                    composite = method()
                    if composite:
                        logger.debug(f"Success with {method_name}")
                        methods_tried.append(method_name)
                        break
            except Exception as e:
                logger.warning(f"{method_name} failed: {e}")
                methods_tried.append(f"{method_name} failed: {e}")

        if composite is None and getattr(self.psd, 'layers', None):
            try:
                logger.debug("Attempting manual layer composition")
                width = getattr(self.psd.header, 'width', None) or getattr(self.psd, 'width', 0)
                height = getattr(self.psd.header, 'height', None) or getattr(self.psd, 'height', 0)

                if not width or not height:
                    first_layer = self.psd.layers[0]
                    width = getattr(first_layer, 'width', 0)
                    height = getattr(first_layer, 'height', 0)

                if not width or not height:
                    raise ValueError("Unable to determine image dimensions")

                composite = Image.new('RGBA', (width, height), (0, 0, 0, 0))

                for i, layer in enumerate(reversed(self.psd.layers)):
                    if getattr(layer, 'visible', True):
                        try:
                            if callable(getattr(layer, 'topil', None)):
                                layer_img = layer.topil()
                                if layer_img:
                                    composite.alpha_composite(layer_img, (layer.left, layer.top))
                                    logger.debug(f"Layer {i} composited: {getattr(layer, 'name', 'unnamed')}")
                        except Exception as e:
                            logger.warning(f"Layer {i} error ({getattr(layer, 'name', 'unnamed')}): {e}")
                methods_tried.append("manual layer composition")
            except Exception as e:
                logger.error(f"Manual composition failed: {e}")
                methods_tried.append(f"manual composition failed: {e}")

        if not composite:
            error_msg = "Could not generate composite. Tried methods: " + ", ".join(methods_tried)
            logger.error(error_msg)
            try:
                img = Image.new('RGB', (800, 200), (255, 200, 200))
                draw = ImageDraw.Draw(img)
                font = ImageFont.load_default()
                text = f"Failed to load PSD file.\n\nTried methods:\n" + "\n".join(f"- {m}" for m in methods_tried)
                for i, line in enumerate(text.split('\n')):
                    draw.text((10, 10 + i * 20), line, fill=(200, 0, 0), font=font)
                return img
            except Exception as fallback_error:
                logger.error(f"Failed to create error placeholder: {fallback_error}")
                raise ValueError(error_msg)

        if self.filepath:
            try:
                from utils.cache_manager import psd_cache
                psd_cache.save_image_to_cache(composite, self.filepath, "_full")
            except Exception as e:
                logger.warning(f"Failed to save to cache: {e}")

        return composite

    def _on_composite_ready(self, composite: Image.Image) -> None:
        self._composite = composite
        self._loading = False
        for callback in self._callbacks:
            try:
                callback(composite)
            except Exception as e:
                logger.error(f"Error in callback {callback}: {e}")
        self._callbacks.clear()

    def get_composite_image(self, callback: Optional[Callable[[Image.Image], None]] = None) -> Optional[Image.Image]:
        if self._composite is not None:
            return self._composite

        if callback:
            self._callbacks.append(callback)

        if not self._loading:
            self._loading = True
            threading.Thread(
                target=lambda: self._on_composite_ready(self._generate_composite()),
                daemon=True
            ).start()

        return None


class PSDLightRenderer(Renderer):
    """Light rendering mode that converts PSD to PNG and renders from PNG."""
    def __init__(self, psd: PSDImage, preview_path: str):
        self.psd = psd
        self.preview_path = preview_path
        self._png_image: Optional[Image.Image] = None

    def _convert_to_png(self) -> str:
        try:
            composite = self.psd.composite()
            composite.save(self.preview_path, format='PNG')
            self._png_image = composite
            return self.preview_path
        except Exception as e:
            logger.error(f"Error converting PSD to PNG: {e}")
            raise

    def get_composite_image(self) -> Image.Image:
        try:
            if self._png_image is None:
                self._convert_to_png()
            return self._png_image
        except Exception as e:
            logger.error(f"Error in light rendering: {e}")
            raise

    def cleanup(self):
        try:
            if self._png_image:
                self._png_image.close()
                self._png_image = None
        except Exception as e:
            logger.error(f"Error cleaning up PNG cache: {e}")


def create_renderer(psd: PSDImage, render_mode: str = 'full', preview_path: Optional[str] = None) -> Renderer:
    if render_mode == 'full':
        return PSDFullRenderer(psd, filepath=preview_path)
    elif render_mode == 'light':
        if not preview_path:
            raise ValueError("preview_path is required for light rendering mode")
        return PSDLightRenderer(psd, preview_path)
    else:
        raise ValueError(f"Unsupported render mode: {render_mode}")