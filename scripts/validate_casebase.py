#!/usr/bin/env python3
"""
Validate a casebase file before using it in a run. See CASEBASE_EXPANSION.md.

Checks (ERROR = must fix, WARN = read and decide):
  - schema: required fields present, types sane
  - id: format (### or P##/US#######), uniqueness
  - problem_description: 20-130 words, ends with '?', no TRIZ vocabulary,
    no obvious solution leakage from its own `solutions` text
  - principle_index in 1..40, factor indices in 1..39
  - near-duplicates: word-overlap (Jaccard on content words) between all
    problem pairs, within the file AND against the sibling casebase
    (casebase.json <-> casebase_uspatents.json)

Usage:  uv run python scripts/validate_casebase.py [--file casebase.json]
Exit code 1 if any ERROR (WARNs alone exit 0).
"""
import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TRIZ_VOCAB = re.compile(
    r"\b(triz|altshuller|inventive principle|ideality|su-field|contradiction)\b", re.I)
# ### textbook | P## patent-derived | patent number: 2-letter office code
# (US/GB/EP/WO/AU/...) + digits (hyphens ok) + optional kind code (A, B1, ...)
ID_RE = re.compile(r"^(\d{3}|P\d{2,}|[A-Z]{2}[\d-]{5,}[A-Z]?\d?)$")
STOP = set("""a an the and or but of to in on for with without from by as at is are was
were be been it its this that these those which what how can could we you they he she
do does did not no however when then than there their them its very more most much
""".split())

# Jaccard similarity above this = ERROR (near-verbatim), above the lower = WARN.
DUP_HARD, DUP_SOFT = 0.55, 0.35


def content_words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def load(path):
    d = json.loads(Path(path).read_text())
    return d["cases"] if isinstance(d, dict) and "cases" in d else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="casebase.json")
    args = ap.parse_args()

    path = ROOT / args.file
    cases = load(path)
    errors, warns = [], []

    # sibling file for cross-duplicate checking
    sibling_name = ("casebase_uspatents.json" if args.file == "casebase.json"
                    else "casebase.json")
    sibling_path = ROOT / sibling_name
    sibling = load(sibling_path) if sibling_path.exists() else []

    seen_ids = set()
    for c in cases:
        cid = c.get("id", "<missing id>")
        for field in ("id", "problem_description", "notes"):
            if field not in c or c[field] in (None, "", []):
                errors.append(f"{cid}: missing/empty required field '{field}'")
        if not c.get("principle_index"):
            warns.append(f"{cid}: canonical principle_index empty - required for NEW "
                         "cases (P01-P17 are a known pre-existing gap)")
        if not ID_RE.match(str(cid)):
            errors.append(f"{cid}: id doesn't match ### / P## / US####### format")
        if cid in seen_ids:
            errors.append(f"{cid}: duplicate id")
        seen_ids.add(cid)

        desc = c.get("problem_description", "")
        n = len(desc.split())
        if not 20 <= n <= 130:
            warns.append(f"{cid}: problem is {n} words (house range 20-130)")
        m = TRIZ_VOCAB.search(desc)
        if m:
            errors.append(f"{cid}: TRIZ vocabulary in problem: '{m.group()}'")

        for k, hi in (("principle_index", 40), ("plus_factor_index", 39),
                      ("minus_factor_index", 39)):
            vals = c.get(k)
            if vals is None:
                continue
            if isinstance(vals, int):  # us_patents file uses scalars here
                vals = [vals]
            for v in vals:
                if not (isinstance(v, int) and 1 <= v <= hi):
                    errors.append(f"{cid}: {k} value {v!r} outside 1..{hi}")

        # crude solution-leak check: solution's distinctive words in the problem
        for sol in c.get("solutions") or []:
            sw = content_words(sol.get("content", "")) - content_words(desc)
            overlap = jaccard(content_words(sol.get("content", "")), content_words(desc))
            if overlap > 0.5:
                warns.append(f"{cid}: solution text overlaps problem heavily "
                             f"({overlap:.0%}) - check for solution leakage")

    # near-duplicate scan
    bags = {c["id"]: content_words(c.get("problem_description", "")) for c in cases}
    for (i1, b1), (i2, b2) in combinations(bags.items(), 2):
        s = jaccard(b1, b2)
        if s >= DUP_HARD:
            errors.append(f"{i1} ~ {i2}: near-duplicate problems (overlap {s:.0%})")
        elif s >= DUP_SOFT:
            warns.append(f"{i1} ~ {i2}: similar problems (overlap {s:.0%}) - same system?")
    sib_bags = {c["id"]: content_words(c.get("problem_description", "")) for c in sibling}
    for i1, b1 in bags.items():
        for i2, b2 in sib_bags.items():
            s = jaccard(b1, b2)
            if s >= DUP_SOFT:
                warns.append(f"{i1} ~ {sibling_name}:{i2}: cross-file overlap {s:.0%}")

    print(f"{args.file}: {len(cases)} cases  "
          f"({sum(1 for i in seen_ids if str(i)[0].isdigit())} numeric, "
          f"{sum(1 for i in seen_ids if str(i).startswith('P'))} P-series, "
          f"{sum(1 for i in seen_ids if str(i).startswith('US'))} US-series)")
    for e in errors:
        print(f"  ERROR {e}")
    for w in warns:
        print(f"  WARN  {w}")
    print(f"\n{len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
