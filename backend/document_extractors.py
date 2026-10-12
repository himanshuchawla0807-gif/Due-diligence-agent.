"""Coordinate-preserving extraction. Scans fail explicitly rather than invent text."""
from __future__ import annotations
import csv
import zipfile
from pathlib import Path
from xml.etree import ElementTree

class ExtractionError(ValueError):
    pass

def extract_segments(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ExtractionError("Encrypted PDF requires a decrypted source")
        segments = []
        for page_number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                raise ExtractionError(f"Page {page_number} has no extractable text; OCR required")
            segments.append({"text": text, "page": page_number})
        return segments
    if suffix == ".docx":
        with zipfile.ZipFile(path) as package:
            info = package.getinfo("word/document.xml")
            if info.file_size > 32 * 1024 * 1024:
                raise ExtractionError("DOCX expanded content exceeds extraction limit")
            root = ElementTree.fromstring(package.read(info))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        parts = ["".join(p.itertext()) for p in root.findall(".//w:p", ns)]
        return [{"text": "\n".join(parts), "page": None}]
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        with zipfile.ZipFile(path) as package:
            if sum(info.file_size for info in package.infolist()) > 64 * 1024 * 1024:
                raise ExtractionError("XLSX expanded content exceeds extraction limit")
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            return [{"text": "\n".join(" | ".join("" if value is None else str(value) for value in row) for row in sheet.iter_rows(values_only=True)), "sheet": sheet.title, "page": None} for sheet in book]
        finally:
            book.close()
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            text = "\n".join(" | ".join(row) for row in csv.reader(handle))
    elif suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8-sig")
    else:
        raise ExtractionError("Unsupported document type")
    if not text.strip():
        raise ExtractionError("Document has no extractable text")
    return [{"text": text, "page": None}]

def extract_text(path: Path) -> str:
    return "\n".join(segment["text"] for segment in extract_segments(path))
