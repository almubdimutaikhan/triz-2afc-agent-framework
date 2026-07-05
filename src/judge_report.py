#!/usr/bin/env python3
"""
Analyze the LLM jury (results/judgements.csv) and print all stats to the console.

Core estimand: p_triz = P(judge picks the TRIZ arm as the better solution).
0.50 = no preference. Above 0.50 = TRIZ-on judged better.

Reports, all to stdout:
  1. Per-judge p_triz (model x persona) + 95% case-clustered bootstrap CI, vs 0.50
  2. Position sanity: left(A)-pick rate, and order-consistency rate per judge
  3. Persona contrast: expert vs naive
  4. Self-preference matrix: judge_model x gen_model (trust the OFF-diagonal)
  5. Jury aggregate over cross-family, order-consistent judgements
  6. Per-case and per-generator breakdown
  7. Human <-> jury agreement, if the game's responses file is present

Run:  python src/judge_report.py
"""
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "results" / "judgements.csv"
HUMAN = ROOT / ".." / "triz-2afc-game" / ".data" / "responses.ndjson"

random.seed(7)


# ---------- stats helpers (stdlib only) ----------
def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def cluster_bootstrap_ci(items, key, val, B=3000, lo=2.5, hi=97.5):
    """items: list of records. Resample CLUSTERS (by key) with replacement;
    each draw recomputes mean(val). Returns (low, high) percentile CI."""
    clusters = defaultdict(list)
    for r in items:
        clusters[key(r)].append(val(r))
    names = list(clusters)
    if not names:
        return (float("nan"), float("nan"))
    means = []
    for _ in range(B):
        pool = []
        for _ in range(len(names)):
            pool.extend(clusters[random.choice(names)])
        if pool:
            means.append(mean(pool))
    means.sort()
    return (means[int(lo / 100 * len(means))], means[min(len(means) - 1, int(hi / 100 * len(means)))])


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else float("nan")


def bar(p, width=20):
    n = int(round(p * width))
    return "█" * n + "·" * (width - n)


def short(model):
    return model.split("/")[-1]


# ---------- load ----------
def load_judgements():
    if not CSV.exists():
        raise SystemExit(f"missing {CSV}; run: python src/judge.py")
    rows = list(csv.DictReader(CSV.open()))
    good = [r for r in rows if r.get("picked_arm") in ("triz", "control")]
    return rows, good


def header(t):
    print("\n" + "=" * 72)
    print(t)
    print("=" * 72)


def line(label, p, n, ci=None, extra=""):
    s = f"  {label:34s} {bar(p)} {p*100:5.1f}%  (n={n})"
    if ci:
        s += f"  CI[{ci[0]*100:4.1f},{ci[1]*100:4.1f}]"
    if extra:
        s += "  " + extra
    print(s)


def main():
    # Per-run path isolation: read results/<run>/judgements.csv.
    global CSV
    try:
        import yaml
        run = yaml.safe_load((ROOT / "config.yaml").read_text()).get("run", "main")
    except Exception:
        run = "main"
    CSV = ROOT / "results" / run / "judgements.csv"
    print(f"run='{run}'  reading {CSV}")
    rows, good = load_judgements()
    n_drop = len(rows) - len(good)
    print(f"loaded {len(rows)} judgements ({len(good)} usable, {n_drop} unparsed/errors)")
    triz = lambda r: 1 if r["picked_arm"] == "triz" else 0
    case = lambda r: r["case_id"]

    # 1. per-judge p_triz
    header("1. p_triz by judge  (model x persona) — fraction calling TRIZ the better answer")
    judges = sorted({(r["judge_model"], r["persona"]) for r in good})
    for jm, persona in judges:
        sub = [r for r in good if r["judge_model"] == jm and r["persona"] == persona]
        p = mean(triz(r) for r in sub)
        ci = cluster_bootstrap_ci(sub, case, triz)
        sig = "*" if (ci[0] > 0.5 or ci[1] < 0.5) else " "
        line(f"{short(jm)} / {persona}", p, len(sub), ci, extra=f"{sig} vs .50")
    overall = mean(triz(r) for r in good)
    line("ALL judges pooled", overall, len(good), cluster_bootstrap_ci(good, case, triz))

    # 2. position sanity
    header("2. position sanity  (left/A-pick should be ~50%; consistency = same arm both orders)")
    for jm, persona in judges:
        sub = [r for r in good if r["judge_model"] == jm and r["persona"] == persona]
        left = mean(1 if r["pick"] == "A" else 0 for r in sub)
        # consistency: per pair, do the two orders agree on the arm?
        bypair = defaultdict(list)
        for r in sub:
            bypair[r["pair_id"]].append(r["picked_arm"])
        cons = mean(1 if len(set(v)) == 1 else 0 for v in bypair.values() if len(v) == 2)
        print(f"  {short(jm):26s} {persona:6s}  left-pick {left*100:5.1f}%   consistent {cons*100:5.1f}%")

    # 3. persona contrast
    header("3. persona contrast  (expert vs naive, same models)")
    for jm in sorted({r["judge_model"] for r in good}):
        e = [r for r in good if r["judge_model"] == jm and r["persona"] == "expert"]
        nv = [r for r in good if r["judge_model"] == jm and r["persona"] == "naive"]
        pe, pn = mean(triz(r) for r in e), mean(triz(r) for r in nv)
        print(f"  {short(jm):26s}  expert {pe*100:5.1f}%   naive {pn*100:5.1f}%   Δ(exp-naive) {(pe-pn)*100:+5.1f} pp")

    # 4. self-preference matrix
    header("4. self-preference  judge_model x gen_model  (p_triz; diagonal = judging own output)")
    jms = sorted({r["judge_model"] for r in good})
    gms = sorted({r["gen_model"] for r in good})
    print("  " + " " * 26 + "".join(f"{short(g)[:12]:>14s}" for g in gms))
    for jm in jms:
        cells = []
        for gm in gms:
            sub = [r for r in good if r["judge_model"] == jm and r["gen_model"] == gm]
            mark = "*" if jm == gm else " "
            cells.append(f"{mean(triz(r) for r in sub)*100:11.1f}%{mark}" if sub else f"{'-':>13s}")
        print(f"  judge {short(jm):20s}" + "".join(f"{c:>14s}" for c in cells))
    diag = [r for r in good if r["judge_model"] == r["gen_model"]]
    off = [r for r in good if r["judge_model"] != r["gen_model"]]
    print(f"\n  self  (diagonal)      p_triz = {mean(triz(r) for r in diag)*100:5.1f}%  (n={len(diag)})")
    print(f"  cross-family (trust)  p_triz = {mean(triz(r) for r in off)*100:5.1f}%  (n={len(off)})")

    # 5. jury aggregate (cross-family, order-consistent)
    header("5. jury verdict  (cross-family + order-consistent judgements only — most trustworthy)")
    keep = []
    bykp = defaultdict(list)
    for r in off:
        bykp[(r["judge_model"], r["persona"], r["pair_id"])].append(r)
    for v in bykp.values():
        arms = {x["picked_arm"] for x in v}
        if len(v) == 2 and len(arms) == 1:   # consistent across both orders
            keep.append(v[0])
    if keep:
        p = mean(triz(r) for r in keep)
        ci = cluster_bootstrap_ci(keep, case, triz)
        line("TRIZ better (jury)", p, len(keep), ci,
             extra="* significant" if (ci[0] > 0.5 or ci[1] < 0.5) else "n.s.")

    # 6. per-case / per-generator
    header("6. breakdown  (cross-family judgements)")
    print("  by generator model:")
    for gm in gms:
        sub = [r for r in off if r["gen_model"] == gm]
        line(f"   {short(gm)}", mean(triz(r) for r in sub), len(sub))
    print("  by case:")
    for cid in sorted({r["case_id"] for r in off}):
        sub = [r for r in off if r["case_id"] == cid]
        line(f"   case {cid}", mean(triz(r) for r in sub), len(sub))

    # 7. human <-> jury
    header("7. human ↔ jury agreement  (per pair: did both lean to the same arm?)")
    if not HUMAN.resolve().exists():
        print("  (no human responses file yet — skipping)")
        return
    hrows = [json.loads(l) for l in HUMAN.resolve().read_text().splitlines() if l.strip()]
    h_by_pair = defaultdict(list)
    for r in hrows:
        arm = r.get("chosen_arm") or r.get("chosenArm")
        pid = r.get("pair_id") or r.get("pairId")
        if arm in ("triz", "control") and pid:
            h_by_pair[pid].append(1 if arm == "triz" else 0)
    j_by_pair = defaultdict(list)
    for r in off:
        j_by_pair[r["pair_id"]].append(triz(r))
    common = sorted(set(h_by_pair) & set(j_by_pair))
    print(f"  human responses: {len(hrows)} rows over {len(h_by_pair)} pairs; "
          f"{len(common)} pairs overlap the jury")
    if not common:
        print("  (no overlapping pairs yet — collect more human plays)")
        return
    hx = [mean(h_by_pair[p]) for p in common]
    jy = [mean(j_by_pair[p]) for p in common]
    agree = mean(1 if (h > 0.5) == (j > 0.5) else 0 for h, j in zip(hx, jy) if h != 0.5)
    print(f"  per-pair lean agreement (excl. human ties): {agree*100:.1f}%")
    print(f"  Pearson r (human triz-rate vs jury triz-rate): {pearson(hx, jy):.2f}")
    print(f"  human  mean p_triz = {mean(hx)*100:.1f}%   jury mean p_triz = {mean(jy)*100:.1f}%")


if __name__ == "__main__":
    main()
