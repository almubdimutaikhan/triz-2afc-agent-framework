#!/usr/bin/env python3
"""
Post-process results/p40_review/generations.csv into manual-review formats:

  results/p40_review/review.csv    one row per output, human-friendly columns
                                   (condition decoded to "TRIZ on + P13 The
                                   Other Way Around" etc.), sorted for reading
  results/p40_review/review.json   nested per-problem structure for the 2AFC
                                   game's review/rate tab:
                                   problems[] -> outputs[] with all labels

Principle names are parsed from prompts/p40/principles/P##.txt (first line
"Principle N: Name") so there is no import coupling with the build script.

Run:  uv run python scripts/export_p40_review.py
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = "p40_review"
RES = ROOT / "results" / RUN

sys.path.insert(0, str(ROOT / "scripts"))
from build_pairs import final_solution  # same extraction the judging path uses


def principle_names():
    names = {}
    for f in sorted((ROOT / "prompts" / "p40" / "principles").glob("P*.txt")):
        m = re.match(r"Principle (\d+): (.+)", f.read_text().splitlines()[0])
        names[int(m.group(1))] = m.group(2).strip()
    return names


def decode(mode, names):
    """condition id -> (kind, principle_num, principle_name, label)"""
    if mode == "T_OFF":
        return "baseline", None, None, "TRIZ off (baseline)"
    if mode == "T_ON":
        return "keyword", None, None, "TRIZ on (keyword only)"
    if mode == "T_ON_ALL40":
        return "all40", None, None, "TRIZ on + all-40 attachment"
    m = re.match(r"T_ON_P(\d+)", mode)
    n = int(m.group(1))
    return "principle", n, names[n], f"TRIZ on + P{n:02d} {names[n]}"


def main():
    names = principle_names()
    cases = {c["id"]: c for c in json.loads(
        (ROOT / "casebase_p5.json").read_text())["cases"]}

    # Read the raw per-call cache records, NOT generations.csv - the CSV
    # flattens newlines, which breaks FINAL SOLUTION extraction (line-anchored)
    # and loses paragraph formatting the review UI needs.
    rows = []
    for f in (ROOT / "data" / RUN / "generations").glob("*.json"):
        r = json.loads(f.read_text())
        rows.append({"case_id": r["case_id"], "mode": r["mode"],
                     "model": r["model"], "solution": r.get("output") or "",
                     "words": len((r.get("output") or "").split()),
                     "error": r.get("error") or ""})

    def sort_key(r):
        kind, n, _, _ = decode(r["mode"], names)
        kind_order = {"baseline": 0, "keyword": 1, "all40": 2, "principle": 3}
        return (r["case_id"], kind_order[kind], n or 0, r["model"])

    rows.sort(key=sort_key)

    with (RES / "review.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "problem_preview", "condition", "kind",
                    "principle_num", "principle_name", "model", "words", "error",
                    "final_solution", "full_output"])
        for r in rows:
            kind, n, pname, label = decode(r["mode"], names)
            w.writerow([r["case_id"],
                        cases[r["case_id"]]["problem_description"][:90],
                        label, kind, n or "", pname or "",
                        r["model"].split("/")[-1], r["words"], r["error"],
                        final_solution(r["solution"]), r["solution"]])

    problems = []
    for cid, c in cases.items():
        outs = []
        for r in rows:
            if r["case_id"] != cid:
                continue
            kind, n, pname, label = decode(r["mode"], names)
            outs.append({
                "condition": r["mode"], "kind": kind, "label": label,
                "principle_num": n, "principle_name": pname,
                "model": r["model"].split("/")[-1], "model_full": r["model"],
                "words": int(r["words"] or 0), "error": r["error"] or None,
                "text": final_solution(r["solution"]),   # what the rate tab shows
                "full_text": r["solution"],              # reasoning incl., expandable
            })
        problems.append({"case_id": cid,
                         "problem": c["problem_description"],
                         "source": c.get("source", ""),
                         "outputs": outs})
    (RES / "review.json").write_text(json.dumps({"run": RUN, "problems": problems},
                                                indent=1, ensure_ascii=False))

    n_err = sum(1 for r in rows if r["error"])
    print(f"{len(rows)} outputs -> {RES/'review.csv'} and review.json  ({n_err} errors)")
    by_kind = {}
    for r in rows:
        by_kind[decode(r['mode'], names)[0]] = by_kind.get(decode(r['mode'], names)[0], 0) + 1
    print("by kind:", by_kind)


if __name__ == "__main__":
    main()
