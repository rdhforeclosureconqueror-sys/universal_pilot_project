from ingestion.pdf import extractor


def test_normalize_ocr_text_preserves_lines():
    text = "A\u00a0B   C\n\n  D\t\tE  "
    normalized = extractor._normalize_ocr_text(text)
    assert normalized.splitlines() == ["A B C", "D E"]


def test_extract_text_from_pdf_uses_pdfplumber_when_sufficient(monkeypatch):
    monkeypatch.setattr(extractor, "_extract_with_pdfplumber", lambda _: "x" * 250)
    called = {"ocr": False}

    def _fake_ocr(_):
        called["ocr"] = True
        return "ocr"

    monkeypatch.setattr(extractor, "_extract_with_ocr", _fake_ocr)
    out = extractor.extract_text_from_pdf("dummy.pdf")
    assert out == "x" * 250
    assert called["ocr"] is False


def test_extract_text_from_pdf_falls_back_to_ocr(monkeypatch):
    monkeypatch.setattr(extractor, "_extract_with_pdfplumber", lambda _: "short")
    monkeypatch.setattr(extractor, "_extract_with_ocr", lambda _: "ocr output")
    assert extractor.extract_text_from_pdf("dummy.pdf") == "ocr output"
