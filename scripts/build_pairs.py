#!/usr/bin/env python3
"""
Stage 2 of the pipeline: turn cached generations into matched pairs for judging.

Two schemas, chosen automatically by whether config.yaml has a `conditions:` list:

  - Legacy (no `conditions:`, e.g. main/us_patents/pc_mouse): one pair per
    (case, model, sample), TRIZ-on vs TRIZ-off, schema unchanged:
    {"id","case_id","model","sample_idx","problem","triz","control"}.

  - Factorial (config.yaml has `conditions:`, e.g. the 2x2 redesign): one pair
    per (case, model, sample, comparison), for each of the 4 interpretable
    "simple effect" contrasts of the 2x2 design (the two conflated diagonal
    pairs — P_L_TRIZ_ON vs P_S_TRIZ_OFF and P_L_TRIZ_OFF vs P_S_TRIZ_ON — are
    intentionally omitted). Schema:
    {"id","case_id","model","sample_idx","comparison","arm_a","arm_b","problem","text_a","text_b"}.

Only the stripped `FINAL SOLUTION` text is carried forward, so judges (and any
human raters) see solutions that are indistinguishable in format across arms.

Reads  : data/<run>/generations/*.json   (written by src/generate.py)
Writes : data/<run>/pairs.json           (consumed by src/judge.py)

Pairs that would tip a rater to the arm are dropped (method-talk jargon leaking
into the visible text, truncated output, or a too-short fragment).

Run:  python scripts/build_pairs.py
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The 4 interpretable "simple effect" contrasts of the 2x2 (length x TRIZ) design.
# Each row answers one plain-English question; the two conflated diagonals
# (P_L_TRIZ_ON vs P_S_TRIZ_OFF, P_L_TRIZ_OFF vs P_S_TRIZ_ON) are omitted on purpose.
FACTORIAL_COMPARISONS = [
    ("P_S_TRIZ_ON", "P_S_TRIZ_OFF"),   # does the TRIZ keyword help in short prompts?
    ("P_L_TRIZ_ON", "P_L_TRIZ_OFF"),   # does TRIZ help beyond matched long structure?
    ("P_L_TRIZ_OFF", "P_S_TRIZ_OFF"),  # does long generic structure help?
    ("P_L_TRIZ_ON", "P_S_TRIZ_ON"),    # does the full TRIZ scaffold help beyond the short TRIZ mention?
]


def read_cfg(root):
    """Minimal read of `run`, `casebase`, and (if present) the `conditions:`
    block from config.yaml — no yaml dependency. `conditions` is [] for the
    legacy 2-mode runs (main/us_patents/pc_mouse)."""
    run, casebase, conditions = "main", "casebase.json", []
    in_conditions = False
    try:
        for raw in open(os.path.join(root, "config.yaml")):
            line = raw.split("#", 1)[0].rstrip()   # strip inline/full-line comments
            stripped = line.strip()
            if in_conditions:
                if stripped.startswith("-"):
                    conditions.append(stripped[1:].strip())
                    continue
                in_conditions = False  # list block ended
            if not stripped:
                continue
            if stripped.startswith("run:"):
                run = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("casebase:"):
                casebase = stripped.split(":", 1)[1].strip()
            elif stripped == "conditions:":
                in_conditions = True
                conditions = []
    except FileNotFoundError:
        pass
    return run, casebase, conditions


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


def pair_issues(arms):
    """arms: {label: text}. Reasons a pair shouldn't be shown to raters: method-talk
    jargon leaking into the visible solution, truncated (mid-sentence) text, or a
    too-short fragment. Label-agnostic, so it works for both the legacy
    triz/control schema and the factorial arm_a/arm_b schema."""
    jargon = re.compile(r"\b(contradiction|principle\s*\d|TRIZ|ideality|parameter\s*#?\d)\b", re.I)
    issues = []
    for label, t in arms.items():
        m = jargon.search(t)
        if m:
            issues.append(f"{label}:jargon({m.group(0)})")
        if len(t.split()) < 50:
            issues.append(f"{label}:short({len(t.split())}w)")
        if t.rstrip()[-1:] not in '.!?")':
            issues.append(f"{label}:truncated")
    return issues


def main():
    run, casebase, conditions = read_cfg(ROOT)
    gen_paths = glob.glob(os.path.join(ROOT, "data", run, "generations", "*.json"))
    if not gen_paths:
        raise SystemExit(
            f"No generations under data/{run}/generations/. Run `python src/generate.py` first."
        )

    cases = {c["id"]: c["problem_description"]
             for c in json.load(open(os.path.join(ROOT, casebase)))["cases"]}

    # Key by (case, model, sample_idx) so k>1 yields k matched pairs per (case, model)
    # instead of collapsing to one. Sample i of one arm is matched to sample i of another.
    groups = {}
    for path in gen_paths:
        g = json.load(open(path))
        text = final_solution(g.get("output") or "")
        sidx = g.get("sample_idx", 0)
        groups.setdefault((g["case_id"], g["model"], sidx), {})[g["mode"]] = text

    comparisons = FACTORIAL_COMPARISONS if conditions else [("triz", "control")]

    scored = []  # list of (pair_dict, issues)
    for (cid, model, sidx), modes in sorted(groups.items()):
        for arm_a, arm_b in comparisons:
            text_a, text_b = modes.get(arm_a), modes.get(arm_b)
            if not (text_a and text_b):
                continue
            text_a, text_b = text_a.strip(), text_b.strip()
            if conditions:
                pair = {
                    "id": f"{cid}__{model.replace('/', '-')}__s{sidx}__{arm_a}_vs_{arm_b}",
                    "case_id": cid, "model": model, "sample_idx": sidx,
                    "comparison": f"{arm_a}_vs_{arm_b}",
                    "arm_a": arm_a, "arm_b": arm_b,
                    "problem": cases[cid],
                    "text_a": text_a, "text_b": text_b,
                }
                issues = pair_issues({"arm_a": text_a, "arm_b": text_b})
            else:
                # legacy schema — unchanged, so main/us_patents/pc_mouse and the
                # sibling 2AFC game keep working exactly as before.
                pair = {
                    "id": f"{cid}__{model.replace('/', '-')}__s{sidx}",
                    "case_id": cid, "model": model, "sample_idx": sidx,
                    "problem": cases[cid],
                    "triz": text_a, "control": text_b,
                }
                issues = pair_issues({"triz": text_a, "control": text_b})
            scored.append((pair, issues))

    clean = [(p, i) for p, i in scored if not i]
    dropped = [(p, i) for p, i in scored if i]

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
    if conditions:
        by_comp = {}
        for p, _ in clean:
            by_comp[p["comparison"]] = by_comp.get(p["comparison"], 0) + 1
        print("by comparison:")
        for c, n in sorted(by_comp.items()):
            print(f"  {c}: {n}")
    if dropped:
        print("\ndropped:")
        for p, issues in dropped:
            print(f"  - {p['id']}: {', '.join(issues)}")


if __name__ == "__main__":
    main()
