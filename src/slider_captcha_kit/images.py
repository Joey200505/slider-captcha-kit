"""Bounded image decoding; no HTTP client, credentials, or telemetry."""
import base64
import io
import warnings

import numpy as np
from PIL import Image

MAX_BYTES = 4_000_000
MAX_PIXELS = 4_194_304


class ImageError(ValueError):
    pass


def pixels(content: bytes, mode: str) -> np.ndarray:
    if not isinstance(content, bytes) or not content or len(content) > MAX_BYTES:
        raise ImageError("IMAGE_SIZE_INVALID")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                w, h = image.size
                if image.format not in {"PNG", "JPEG", "WEBP"} or not (0 < w <= 4096 and 0 < h <= 4096 and w*h <= MAX_PIXELS):
                    raise ImageError("IMAGE_DIMENSIONS_UNSUPPORTED")
                return np.array(image.convert(mode))
    except ImageError:
        raise
    except Exception:
        raise ImageError("IMAGE_DECODE_FAILED") from None


def decode_data_url(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > MAX_BYTES * 4 // 3 + 200:
        raise ImageError("IMAGE_DATA_URL_INVALID")
    prefix, separator, encoded = value.partition(",")
    if not separator or prefix not in {"data:image/png;base64", "data:image/jpeg;base64", "data:image/webp;base64"}:
        raise ImageError("IMAGE_DATA_URL_INVALID")
    try:
        content = base64.b64decode(encoded, validate=True)
    except Exception:
        raise ImageError("IMAGE_DATA_URL_INVALID") from None
    pixels(content, "RGBA")
    return content


# Executes only in the caller's already-open browser context. A cross-origin
# canvas without CORS permission fails closed; no separate network fetch occurs.
READ_IMAGE_JS = """node => {
  if (node instanceof HTMLImageElement) {
    if (!node.complete || !node.naturalWidth) throw new Error('IMAGE_NOT_READY');
    if (node.naturalWidth > 4096 || node.naturalHeight > 4096 || node.naturalWidth * node.naturalHeight > 4194304)
      throw new Error('IMAGE_TOO_LARGE');
    const src = node.currentSrc || node.src;
    if (/^data:image\\/(png|jpeg|webp);base64,/.test(src)) return src;
    const canvas = document.createElement('canvas');
    canvas.width = node.naturalWidth; canvas.height = node.naturalHeight;
    canvas.getContext('2d').drawImage(node, 0, 0);
    return canvas.toDataURL('image/png');
  }
  if (node instanceof HTMLCanvasElement && node.width > 0 && node.height > 0 &&
      node.width <= 4096 && node.height <= 4096 && node.width * node.height <= 4194304)
    return node.toDataURL('image/png');
  throw new Error('IMAGE_ELEMENT_UNSUPPORTED');
}"""

IMAGE_READY_JS = """node => node instanceof HTMLImageElement
    ? node.complete && node.naturalWidth > 0
    : node instanceof HTMLCanvasElement && node.width > 0 && node.height > 0"""
