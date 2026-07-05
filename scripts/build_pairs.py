#!/usr/bin/env python3
"""
Stage 2 of the pipeline: turn cached generations into matched TRIZ-vs-control pairs.

Each pair = one (case, model, sample) with its TRIZ-on and TRIZ-off FINAL SOLUTION.
Only the stripped `FINAL SOLUTION` text is carried forward, so judges (and any human
raters) see solutions that are indistinguishable in format across the two arms.

Reads  : data/<run>/generations/*.json   (written by src/generate.py)
Writes : data/<run>/pairs.json           (consumed by src/judge.py)

Pairs that would tip a rater to the arm are dropped (TRIZ jargon leaking into the
visible text, truncated output, or a too-short fragment).

Run:  python scripts/build_pairs.py
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read_cfg(root):
    """Minimal read of `run` + `casebase` from config.yaml (no yaml dependency)."""
    run, casebase = "main", "casebase.json"
    try:
        for line in open(os.path.join(root, "config.yaml")):
            line = line.split("#", 1)[0].strip()
            if line.startswith("run:"):
                run = line.split(":", 1)[1].strip()
            elif line.startswith("casebase:"):
                casebase = line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    return run, casebase


# "FINAL SOLUTION:" header, tolerating markdown heading (#) / bold (*) prefixes.
_FINAL_HEADER = re.compile(r"^[ \t#*>]*final\s+solution[ \t#*]*:?[ \t]*", re.IGNORECASE | re.MULTILINE)


def final_solution(text):
    """Extract only the FINAL SOLUTION section from a full generation output.
    Falls back to the whole text if the header is absent (empty -> empty)."""
    if not text:
        return ""
    m = _FINAL_HEADER.search(text)
    if not m:
        return text.strip()
    return re.sub(r"^[\s:*#>\-]+", "", text[m.end():]).strip()


def pair_issues(p):
    """Reasons a pair shouldn't be shown to raters: TRIZ jargon leaking into the
    visible solution, truncated (mid-sentence) text, or a too-short fragment."""
    jargon = re.compile(r"\b(contradiction|principle\s*\d|TRIZ|ideality|parameter\s*#?\d)\b", re.I)
    issues = []
    for arm in ("triz", "control"):
        t = p[arm]
        m = jargon.search(t)
        if m:
            issues.append(f"{arm}:jargon({m.group(0)})")
        if len(t.split()) < 50:
            issues.append(f"{arm}:short({len(t.split())}w)")
        if t.rstrip()[-1:] not in '.!?")':
            issues.append(f"{arm}:truncated")
    return issues


def main():
    run, casebase = read_cfg(ROOT)
    gen_paths = glob.glob(os.path.join(ROOT, "data", run, "generations", "*.json"))
    if not gen_paths:
        raise SystemExit(
            f"No generations under data/{run}/generations/. Run `python src/generate.py` first."
        )

    cases = {c["id"]: c["problem_description"]
             for c in json.load(open(os.path.join(ROOT, casebase)))["cases"]}

    # Key by (case, model, sample_idx) so k>1 yields k matched pairs per (case, model)
    # instead of collapsing to one. TRIZ sample i is matched to control sample i.
    groups = {}
    for path in gen_paths:
        g = json.load(open(path))
        text = final_solution(g.get("output") or "")
        sidx = g.get("sample_idx", 0)
        groups.setdefault((g["case_id"], g["model"], sidx), {})[g["mode"]] = text

    pairs = []
    for (cid, model, sidx), modes in sorted(groups.items()):
        triz, control = modes.get("triz"), modes.get("control")
        if triz and control:
            pairs.append({
                "id": f"{cid}__{model.replace('/', '-')}__s{sidx}",
                "case_id": cid,
                "model": model,
                "sample_idx": sidx,
                "problem": cases[cid],
                "triz": triz.strip(),
                "control": control.strip(),
            })

    clean, dropped = [], []
    for p in pairs:
        issues = pair_issues(p)
        (dropped if issues else clean).append((p, issues))

    out_dir = os.path.join(ROOT, "data", run)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "pairs.json")
    json.dump({"pairs": [p for p, _ in clean]}, open(out, "w"), indent=2, ensure_ascii=False)

    print(f"wrote {len(clean)} pairs -> {out}  (dropped {len(dropped)} on quality)")
    by_model = {}
    for p, _ in clean:
        by_model[p["model"]] = by_model.get(p["model"], 0) + 1
    for m, n in sorted(by_model.items()):
        print(f"  {m}: {n}")
    if dropped:
        print("\ndropped:")
        for p, issues in dropped:
            print(f"  - {p['id']}: {', '.join(issues)}")


if __name__ == "__main__":
    main()
