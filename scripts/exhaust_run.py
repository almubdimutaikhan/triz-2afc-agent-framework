#!/usr/bin/env python3
"""
Solution-space exhaustion run ("don't repeat yourself" chains).

One problem (the Mars haptic boot, case 029), T_ON system prompt, 4 models.
Each model runs its OWN sequential chain of ROUNDS generations: after every
round, the extracted FINAL SOLUTION is appended to a growing "do not repeat"
list inside the next round's user message, forcing a genuinely new solution
each time. Chains are independent per model (a model never sees another
model's solutions) and run in parallel threads; rounds within a chain are
strictly sequential.

Novelty is then measured post-hoc: for every solution, the maximum
content-word overlap (Jaccard) against all previous solutions in its chain -
i.e. did the model comply, and at which round does it start self-repeating?

Cache: data/exhaust_boot/<model>_r<round>.json (chain is deterministic at
temp 0, so (model, round) identifies a record; interrupt + rerun resumes).

Run:  uv run python scripts/exhaust_run.py
Out:  results/exhaust_boot/chains.csv, chains.md
"""
import concurrent.futures as cf
import csv
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from generate import call_gateway  # noqa: E402  (retries + key handling)
from build_pairs import final_solution  # noqa: E402

CASE_ID = "029"
ROUNDS = 40
MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4.5",
    "deepseek/deepseek-chat-v3.1",
    "google/gemini-2.5-flash",
]
BASE_URL = "https://openrouter.ai/api/v1"
PARAMS = {"temperature": 0.0, "max_tokens": 4000}

GEN_DIR = ROOT / "data" / "exhaust_boot"
RES = ROOT / "results" / "exhaust_boot"

FORBID_HEADER = (
    "\n\nPREVIOUSLY GENERATED SOLUTIONS - DO NOT REPEAT:\n"
    "You have already produced the {n} solution(s) below for this exact problem. "
    "Your new solution must rely on a FUNDAMENTALLY DIFFERENT working mechanism "
    "from every one of them. Do not repeat, rephrase, combine, or trivially vary "
    "any of them.\n"
)

STOP = set("""a an the and or but of to in on for with without from by as at is are was
were be been it its this that these those which what how can could we you they not no
when then than there their them very more most much will would should each other
""".split())


def content_words(t):
    return {w for w in re.findall(r"[a-z]+", (t or "").lower()) if w not in STOP and len(w) > 2}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def build_user(user_tpl, problem, history):
    user = user_tpl.format(problem_description=problem)
    if history:
        parts = [FORBID_HEADER.format(n=len(history))]
        for i, h in enumerate(history, 1):
            parts.append(f"[{i}] {h}\n")
        user += "\n".join(parts)
    return user


def run_chain(model, system, user_tpl, problem):
    slug = model.split("/")[-1]
    history, records = [], []
    for rnd in range(1, ROUNDS + 1):
        path = GEN_DIR / f"{slug}_r{rnd:02d}.json"
        if path.exists():
            rec = json.loads(path.read_text())
        else:
            user = build_user(user_tpl, problem, history)
            out, err = call_gateway(BASE_URL, model, system, user, PARAMS)
            rec = {"model": model, "round": rnd, "n_forbidden": len(history),
                   "user_words": len(user.split()), "output": out, "error": err,
                   "final": final_solution(out or ""),
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
            path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        if rec.get("error"):
            print(f"  !! {slug} r{rnd}: {rec['error'][:80]}", flush=True)
            break
        history.append(rec["final"])
        records.append(rec)
        print(f"  {slug} r{rnd:02d} done ({len(rec['final'].split())}w)", flush=True)
    return records


def main():
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)

    system = (ROOT / "prompts" / "p40" / "T_ON.txt").read_text().strip()
    user_tpl = (ROOT / "prompts" / "user_template.txt").read_text()
    case = next(c for c in json.loads((ROOT / "casebase_p5.json").read_text())["cases"]
                if c["id"] == CASE_ID)

    print(f"exhaustion run: case {CASE_ID}, {len(MODELS)} models x {ROUNDS} rounds "
          f"(chains parallel, rounds sequential)", flush=True)
    with cf.ThreadPoolExecutor(max_workers=len(MODELS)) as ex:
        chains = list(ex.map(
            lambda m: run_chain(m, system, user_tpl, case["problem_description"]), MODELS))

    # ---- novelty metrics + exports ----
    rows = []
    for recs in chains:
        bags = [content_words(r["final"]) for r in recs]
        for i, r in enumerate(recs):
            sims = [(jaccard(bags[i], bags[j]), j + 1) for j in range(i)]
            mx, at = max(sims) if sims else (0.0, "")
            rows.append({
                "model": r["model"].split("/")[-1], "round": r["round"],
                "words": len(r["final"].split()),
                "prompt_words": r["user_words"],
                "max_overlap_prev_pct": round(mx * 100, 1),
                "most_similar_round": at,
                # one line per row: editors/IDE previews choke on quoted
                # multi-line CSV fields (chains.md keeps the formatted text)
                "final_solution": " ".join(r["final"].split()),
            })

    cols = list(rows[0].keys())
    with (RES / "chains.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    md = [f"# Exhaustion chains - case {CASE_ID} (T_ON, temp 0, {ROUNDS} rounds/model)", ""]
    for recs in chains:
        if not recs:
            continue
        slug = recs[0]["model"].split("/")[-1]
        md.append(f"## {slug}\n")
        for r in rows:
            if r["model"] != slug:
                continue
            md.append(f"### Round {r['round']}  "
                      f"(max overlap with earlier: {r['max_overlap_prev_pct']}%"
                      f"{' vs r' + str(r['most_similar_round']) if r['most_similar_round'] else ''})\n")
            md.append(r["final_solution"] + "\n")
    (RES / "chains.md").write_text("\n".join(md))

    print(f"\n{len(rows)} solutions -> {RES/'chains.csv'} and chains.md", flush=True)
    for m in {r['model'] for r in rows}:
        mrows = [r for r in rows if r["model"] == m]
        hi = [r for r in mrows if r["max_overlap_prev_pct"] >= 50]
        first = min((r["round"] for r in hi), default="-")
        print(f"  {m:22s} {len(mrows)} rounds, first >=50% overlap at round {first}", flush=True)


if __name__ == "__main__":
    main()
