from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from FIR photo or scan using OCR when available."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Image support not installed") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise ValueError(
            "OCR not available — install Tesseract (brew install tesseract) or paste FIR text"
        ) from exc

    image = Image.open(io.BytesIO(file_bytes))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    text = pytesseract.image_to_string(image, lang="eng")
    cleaned = text.strip()
    if len(cleaned) < 20:
        raise ValueError("Could not read enough text from image — try a clearer photo or paste text")
    return cleaned
