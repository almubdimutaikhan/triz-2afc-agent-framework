#!/usr/bin/env python3
"""
One-time extraction of the T_ON_ALL40 attachment text from
docs/triz_40_inventive_principles_with_examplesfeb15.pdf
("40 Inventive Principles With Examples", (c) Oxford Creativity, triz.co.uk).

Cleans per-page copyright footers and converts symbol-font bullets to "- ".
The output is committed so the exact attachment bytes are versioned; the
source PDF itself stays gitignored (copyrighted material).

Run:  uv run --with pypdf python scripts/extract_p40_attachment.py
Writes:  prompts/p40/attachments/40_principles_oxford.txt
"""
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "triz_40_inventive_principles_with_examplesfeb15.pdf"
OUT = ROOT / "prompts" / "p40" / "attachments" / "40_principles_oxford.txt"

FOOTER = re.compile(r"^\s*Copyright © Oxford Creativity.*$", re.M)


def main():
    reader = PdfReader(str(SRC))
    pages = [p.extract_text() or "" for p in reader.pages]
    text = "\n".join(pages)

    text = FOOTER.sub("", text)
    text = text.replace("\uf02d\uf020", "- ").replace("\uf02d", "- ").replace("\uf020", " ")
    # collapse the blank scaffolding left by header/footer removal
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # blank line before each principle header for readability
    text = re.sub(r"\n(Principle \d+ )", r"\n\n\1", text)
    text = text.strip() + "\n"

    nums = sorted(set(int(m) for m in re.findall(r"^Principle (\d+) ", text, re.M)))
    assert nums == list(range(1, 41)), f"expected principles 1..40, got {nums}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT}  ({len(text.split())} words, all 40 principle headers present)")


if __name__ == "__main__":
    main()
