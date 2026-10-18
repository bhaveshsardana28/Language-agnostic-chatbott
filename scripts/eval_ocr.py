"""Measure OCR CER/WER on deterministic, non-sensitive synthetic fixtures.

Run from the repository root:

    ./venv/bin/python scripts/eval_ocr.py --json

The script reports only the fixtures it can execute with the local OCR
capabilities.  It does not imply production accuracy for handwriting,
photographs, tables, or languages not installed in Tesseract.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import documents  # noqa: E402


def _image(text: str, *, angle: int = 0, background="white", foreground="black") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (3200, 900), background)
    draw = ImageDraw.Draw(image)
    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        if os.path.exists(path):
            font = ImageFont.truetype(path, 55)
            break
    draw.multiline_text((80, 100), text, fill=foreground, font=font, spacing=20)
    if angle:
        image = image.rotate(angle, expand=True)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _scanned_pdf(image_bytes: bytes) -> bytes:
    import fitz

    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(0, 0, 612, 792), stream=image_bytes)
    data = pdf.tobytes()
    pdf.close()
    return data


def _normalise(text: str) -> str:
    text = re.sub(r"\[Page\s+\d+\]", "", text or "", flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip().upper()


def _distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, 1):
        current = [i]
        for j, right_item in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (left_item != right_item),
            ))
        previous = current
    return previous[-1]


def _metrics(expected: str, actual: str) -> dict:
    expected_norm, actual_norm = _normalise(expected), _normalise(actual)
    expected_words, actual_words = expected_norm.split(), actual_norm.split()
    return {
        "cer": round(_distance(list(expected_norm), list(actual_norm)) / max(len(expected_norm), 1), 4),
        "wer": round(_distance(expected_words, actual_words) / max(len(expected_words), 1), 4),
        "recognized": actual_norm,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    capabilities = documents.ocr_capabilities()
    result = {"capabilities": capabilities, "cases": []}
    if not capabilities["available"]:
        result["note"] = "Tesseract Python/runtime capability is unavailable; no accuracy claim was made."
    else:
        cases = [
            ("image", "INVOICE TOTAL 123.45", _image("INVOICE TOTAL 123.45"), "invoice.png"),
            ("rotated_image",
             "THIS IS A ROTATED SYNTHETIC DOCUMENT WITH ENOUGH WORDS FOR ORIENTATION DETECTION TOTAL 77.00",
             _image("THIS IS A ROTATED SYNTHETIC DOCUMENT WITH ENOUGH WORDS FOR ORIENTATION DETECTION TOTAL 77.00", angle=90),
             "rotated.png"),
            ("low_contrast_image", "LOW CONTRAST TOTAL 88.00", _image(
                "LOW CONTRAST TOTAL 88.00", background=(220, 220, 220), foreground=(160, 160, 160),
            ), "low-contrast.png"),
        ]
        for name, expected, data, filename in cases:
            report = documents.extract_document(data, filename)
            result["cases"].append({"case": name, **_metrics(expected, report.full_text),
                                    "method": report.extraction_method})
        if capabilities["pdf_available"]:
            expected = "SCANNED PDF TOTAL 543.21"
            report = documents.extract_document(_scanned_pdf(_image(expected)), "scanned.pdf")
            result["cases"].append({"case": "scanned_pdf", **_metrics(expected, report.full_text),
                                    "method": report.extraction_method})
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
