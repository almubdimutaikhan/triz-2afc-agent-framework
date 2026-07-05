#!/usr/bin/env python3
"""
LLM-jury 2AFC over the TRIZ-on vs TRIZ-off pairs.

Each judge sees a problem and two blinded FINAL SOLUTIONs (the SAME stripped text
the human raters saw) and picks the BETTER response. Identical task to the human
game, so the jury can be compared pair-for-pair with the humans.

Judge fleet = models x personas:
  - expert : a TRIZ-literate senior reviewer
  - naive  : a practical engineer with no framework
3 models x 2 personas = 6 judges.

Every pair is shown to every judge in BOTH orders (triz-as-A and triz-as-B) so a
side-biased judge can't fake a signal. Calls are stateless, temperature 0, and
cached on disk by a content hash, so reruns never re-call the API.

Usage:
  python src/judge.py                 # run full jury (uses cache)
  python src/judge.py --limit 3       # only first 3 pairs (smoke test)
  python src/judge.py --concurrency 8
Outputs:
  data/judgements/*.json   one cached record per (judge, persona, pair, order)
  results/judgements.csv   flat table for analysis  (see src/judge_report.py)
"""
import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import yaml

import generate  # reuse gateway plumbing: api_key(), call_gateway()

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
JUDGE_DIR = ROOT / "data" / "judgements"
RESULTS = ROOT / "results"
PAIRS = ROOT / ".." / "triz-2afc-game" / "data" / "pairs.json"

PERSONAS = {"expert": "judge_expert.txt", "naive": "judge_naive.txt"}


def load_text(name: str) -> str:
    return (PROMPTS / name).read_text()


def judge_prompt_version() -> str:
    """Hash of the judge prompt files so edits invalidate the cache."""
    h = hashlib.sha256()
    for n in sorted(["judge_expert.txt", "judge_naive.txt", "judge_user.txt"]):
        h.update((PROMPTS / n).read_bytes())
    return h.hexdigest()[:12]


def parse_pick(text):
    """Pull the FINAL A/B verdict out of the model's reply. The judge now reasons
    for one sentence first (where 'Solution A'/'B' may be mentioned), then writes
    'ANSWER: X'. So we take the LAST explicit verdict; failing that, the LAST
    standalone A/B in the text (the verdict sits at the end)."""
    if not text:
        return None
    tags = re.findall(r'answer\s*[:=]\s*"?\(?([AB])', text, re.I)
    if tags:
        return tags[-1].upper()
    tags = re.findall(r'pick"?\s*[:=]\s*"?([AB])', text, re.I)
    if tags:
        return tags[-1].upper()
    m = re.findall(r'\b([AB])\b', text)
    if m:
        return m[-1].upper()
    return None


def cache_key(judge_model, persona, pair_id, order, jpv) -> str:
    blob = json.dumps(
        {"judge_model": judge_model, "persona": persona, "pair_id": pair_id,
         "order": order, "judge_prompt_version": jpv},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def run_one(base_url, pair, judge_model, persona, order, jpv,
            persona_sys, user_tpl, params):
    """order 'tc' => A=triz, B=control ; 'ct' => A=control, B=triz."""
    key = cache_key(judge_model, persona, pair["id"], order, jpv)
    out_path = JUDGE_DIR / f"{key}.json"
    if out_path.exists():
        rec = json.loads(out_path.read_text())
        rec["_cached"] = True
        return rec

    if order == "tc":
        a_arm, b_arm, a_text, b_text = "triz", "control", pair["triz"], pair["control"]
    else:
        a_arm, b_arm, a_text, b_text = "control", "triz", pair["control"], pair["triz"]

    user = user_tpl.format(problem=pair["problem"], A=a_text, B=b_text)
    content, err = generate.call_gateway(base_url, judge_model, persona_sys, user, params)
    pick = parse_pick(content)
    picked_arm = (a_arm if pick == "A" else b_arm if pick == "B" else None)

    rec = {
        "hash": key,
        "pair_id": pair["id"],
        "case_id": pair["case_id"],
        "gen_model": pair["model"],      # model that PRODUCED the pair
        "judge_model": judge_model,
        "persona": persona,
        "order": order,                  # tc | ct
        "a_arm": a_arm, "b_arm": b_arm,
        "pick": pick,                    # A | B | None
        "picked_arm": picked_arm,        # triz | control | None
        "raw": (content or "")[:400],
        "error": err if (err or pick is None) else None,
        "judge_prompt_version": jpv,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    rec["_cached"] = False
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--models", nargs="*", help="override judge model list")
    ap.add_argument("--limit", type=int, help="only first N pairs (smoke test)")
    ap.add_argument("--concurrency", type=int, default=5)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    base_url = cfg["gateway_base_url"].rstrip("/")

    # Per-run path isolation: data/<run>/judgements, results/<run>.
    global JUDGE_DIR, RESULTS, PAIRS
    run = cfg.get("run", "main")
    JUDGE_DIR = ROOT / "data" / run / "judgements"
    RESULTS = ROOT / "results" / run
    # Pairs from `scripts/build_pairs.py` (this repo). Fall back to the sibling
    # 2AFC game repo's export if a local file isn't present.
    local_pairs = ROOT / "data" / run / "pairs.json"
    sibling_pairs = ROOT / ".." / "triz-2afc-game" / "data" / f"pairs_{run}.json"
    PAIRS = local_pairs if local_pairs.exists() else sibling_pairs
    print(f"run='{run}'  pairs={PAIRS}  -> {JUDGE_DIR}")

    judge_models = args.models or cfg["models"]
    params = {"temperature": 0.0, "max_tokens": 250}  # one reasoning sentence + ANSWER line

    jpv = judge_prompt_version()
    persona_sys = {p: load_text(f).strip() for p, f in PERSONAS.items()}
    user_tpl = load_text("judge_user.txt")

    pairs = json.loads(PAIRS.resolve().read_text())["pairs"]
    if args.limit:
        pairs = pairs[: args.limit]

    JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(pair, jm, persona, order)
            for pair in pairs
            for jm in judge_models
            for persona in PERSONAS
            for order in ("tc", "ct")]
    print(f"{len(jobs)} judgements: {len(pairs)} pairs x {len(judge_models)} models "
          f"x {len(PERSONAS)} personas x 2 orders  (judge_prompt_version={jpv})")

    records = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, base_url, pair, jm, persona, order, jpv,
                          persona_sys[persona], user_tpl, params):
                (pair["id"], jm, persona, order)
                for (pair, jm, persona, order) in jobs}
        for fut in cf.as_completed(futs):
            rec = fut.result()
            records.append(rec)
            tag = "cache" if rec.get("_cached") else ("ERR " if rec.get("error") else "new ")
            print(f"  [{tag}] {rec['pair_id'][:18]:18s} {rec['judge_model']:26s} "
                  f"{rec['persona']:6s} {rec['order']} -> {rec['picked_arm'] or rec.get('error')}")

    write_csv(records)
    n_err = sum(1 for r in records if r.get("error"))
    print(f"\nDone. {len(records)} judgements, {n_err} unparsed/errors.")
    print(f"  csv -> {RESULTS/'judgements.csv'}")
    print(f"  next: python src/judge_report.py")


def write_csv(records):
    RESULTS.mkdir(parents=True, exist_ok=True)
    records = sorted(records, key=lambda r: (r["pair_id"], r["judge_model"], r["persona"], r["order"]))
    cols = ["pair_id", "case_id", "gen_model", "judge_model", "persona", "order",
            "a_arm", "b_arm", "pick", "picked_arm", "error"]
    with (RESULTS / "judgements.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in records:
            w.writerow([r.get(c, "") for c in cols])


if __name__ == "__main__":
    main()
