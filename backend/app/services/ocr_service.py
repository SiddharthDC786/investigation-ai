from __future__ import annotations

import io
import logging
import re

logger = logging.getLogger(__name__)


def normalize_ocr_text(raw: str) -> str:
    """Clean OCR output into readable FIR-style paragraphs."""
    text = raw.replace("\x0c", "\n")
    text = text.replace("|", "I").replace("—", "-")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [ln for ln in lines if len(ln) >= 2]
    merged: list[str] = []
    for line in lines:
        if merged and len(line) < 28 and not re.search(r"[.!?]$", merged[-1]):
            merged[-1] = f"{merged[-1]} {line}"
        else:
            merged.append(line)
    cleaned = "\n".join(merged).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


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
    cleaned = normalize_ocr_text(text.strip())
    if len(cleaned) < 20:
        raise ValueError("Could not read enough text from image — try a clearer photo or paste text")
    return cleaned
