import re

import pdfplumber


def _normalize_ocr_text(text: str) -> str:
    text = (text or "").replace("\u00a0", " ")
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"[ \t]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _extract_with_pdfplumber(path: str) -> str:
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return _normalize_ocr_text("\n".join(chunks))


def _extract_with_ocr(path: str) -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except Exception as exc:
        raise RuntimeError("OCR dependencies missing: install pdf2image, pytesseract, and system tesseract-ocr") from exc

    images = convert_from_path(path, dpi=300)
    text_chunks = [pytesseract.image_to_string(img) for img in images]
    return _normalize_ocr_text("\n".join(text_chunks))


def extract_text_from_pdf(path: str) -> str:
    base_text = _extract_with_pdfplumber(path)
    if len(base_text) >= 200:
        return base_text
    return _extract_with_ocr(path)
