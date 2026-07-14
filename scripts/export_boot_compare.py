#!/usr/bin/env python3
"""
Build the data file for the game's /compare page: for the Mars haptic-boot
problem (case 029), method A = the 40 per-principle outputs (p40_review run)
vs method B = the 40 iterative "don't repeat" chain outputs (exhaust_boot run),
per model.

Run:  uv run python scripts/export_boot_compare.py
Out:  results/exhaust_boot/boot_compare.json
      + copied to ../triz-2afc-game/public/boot_compare.json if that repo exists
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_PUBLIC = ROOT.parent / "triz-2afc-game" / "public"
CASE_ID = "029"


def main():
    review = json.loads((ROOT / "results" / "p40_review" / "review.json").read_text())
    prob = next(p for p in review["problems"] if p["case_id"] == CASE_ID)

    a = {}  # model -> [{id, title, text, words}]
    for o in prob["outputs"]:
        if o["kind"] != "principle":
            continue
        pid = f"P{o['principle_num']:02d}"
        a.setdefault(o["model"], []).append({
            "id": pid, "title": f"{pid} {o['principle_name']}",
            "text": o["text"], "words": o["words"],
        })
    for v in a.values():
        v.sort(key=lambda x: x["id"])

    b = {}  # model -> [{id, title, text, words}]
    for f in sorted((ROOT / "data" / "exhaust_boot").glob("*_r*.json")):
        r = json.loads(f.read_text())
        if r.get("error"):
            continue
        slug = r["model"].split("/")[-1]
        b.setdefault(slug, []).append({
            "id": f"R{r['round']:02d}", "title": f"Round {r['round']}",
            "text": r["final"], "words": len(r["final"].split()),
        })
    for v in b.values():
        v.sort(key=lambda x: x["id"])

    models = sorted(set(a) & set(b))
    out = {
        "case_id": CASE_ID,
        "problem": prob["problem"],
        "models": models,
        "methodA": {"label": "Per-principle prompts (one output per inventive principle)", "outputs": a},
        "methodB": {"label": "Iterative chain (each round must differ from all previous)", "outputs": b},
    }
    dst = ROOT / "results" / "exhaust_boot" / "boot_compare.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {dst}")
    for m in models:
        print(f"  {m}: A={len(a[m])} B={len(b[m])}")
    if GAME_PUBLIC.exists():
        (GAME_PUBLIC / "boot_compare.json").write_text(dst.read_text())
        print(f"copied -> {GAME_PUBLIC/'boot_compare.json'}")


if __name__ == "__main__":
    main()
