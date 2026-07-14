#!/usr/bin/env python3
"""
Zero-cost CI power analysis: reuses ALREADY-CACHED judgements (no new API calls)
to estimate how much the trustworthy-subset 95% CI would narrow if the casebase
grew beyond its current size.

Method:
  1. Take the trustworthy (cross-family + order-consistent) judgements already on
     disk for a run.
  2. For each candidate case count n <= (cases actually available), repeatedly draw
     random n-case subsets from the real case pool, and compute the case-clustered
     bootstrap CI on just that subset's judgements. Average the CI width over many
     draws -> an empirical "CI width vs n_cases" curve, built entirely from data we
     already have.
  3. Fit width ~ c / sqrt(n) (the standard clustered-mean scaling law) to that curve
     and extrapolate to case counts we do NOT have yet, so you can see the expected
     payoff of adding more TRIZ cases BEFORE generating or judging a single new one.

Run:  python scripts/ci_power_analysis.py [--run main] [--draws 300] [--extrapolate 60 90 120 150 200]
"""
import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
random.seed(7)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def load_trustworthy(csv_path):
    rows = list(csv.DictReader(open(csv_path)))
    good = [r for r in rows if r.get("picked_arm") in ("triz", "control")]
    off = [r for r in good if r["judge_model"] != r["gen_model"]]
    bykp = defaultdict(list)
    for r in off:
        bykp[(r["judge_model"], r["persona"], r["pair_id"])].append(r)
    keep = []
    for v in bykp.values():
        arms = {x["picked_arm"] for x in v}
        if len(v) == 2 and len(arms) == 1:  # order-consistent
            keep.append(v[0])
    return keep


def case_clustered_ci(records, B=1500, lo=2.5, hi=97.5):
    """records: trustworthy judgements for ONE candidate case subset.
    Resamples CASES with replacement (not raw judgements) B times."""
    triz = lambda r: 1 if r["picked_arm"] == "triz" else 0
    clusters = defaultdict(list)
    for r in records:
        clusters[r["case_id"]].append(triz(r))
    names = list(clusters)
    if not names:
        return float("nan"), float("nan"), float("nan")
    means = []
    for _ in range(B):
        pool = []
        for _ in range(len(names)):
            pool.extend(clusters[random.choice(names)])
        if pool:
            means.append(mean(pool))
    means.sort()
    p_hat = mean(triz(r) for r in records)
    lo_v = means[int(lo / 100 * len(means))]
    hi_v = means[min(len(means) - 1, int(hi / 100 * len(means)))]
    return p_hat, lo_v, hi_v


def simulate_curve(records, all_case_ids, n_values, draws):
    """For each n in n_values: draw `draws` random n-case subsets from the REAL
    case pool (no synthetic data), compute the clustered CI on each subset's
    actual judgements, and average the width. Returns {n: (mean_width, mean_p)}."""
    by_case = defaultdict(list)
    for r in records:
        by_case[r["case_id"]].append(r)

    out = {}
    for n in n_values:
        if n > len(all_case_ids):
            continue
        widths, ps = [], []
        for _ in range(draws):
            subset = random.sample(all_case_ids, n)
            sub_records = [r for cid in subset for r in by_case[cid]]
            p, lo_v, hi_v = case_clustered_ci(sub_records, B=400)  # lighter B inside the outer loop
            if p == p:  # not NaN
                widths.append(hi_v - lo_v)
                ps.append(p)
        out[n] = (mean(widths), mean(ps))
        print(f"  n={n:3d} cases  (avg over {len(widths)} random draws)  "
              f"mean p_triz={out[n][1]*100:5.1f}%  mean CI width={out[n][0]*100:5.1f}pp",
              flush=True)
    return out


def fit_inverse_sqrt(curve):
    """Fit width = c / sqrt(n) by least squares on c (single free parameter,
    since the 1/sqrt(n) clustered-mean scaling law is the theoretical form)."""
    ns = [n for n, (w, _) in curve.items() if w == w]
    ws = [curve[n][0] for n in ns]
    if not ns:
        return None
    # width * sqrt(n) should be ~constant = c; take the mean as the LS estimate
    cs = [w * (n ** 0.5) for n, w in zip(ns, ws)]
    return mean(cs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--draws", type=int, default=300)
    ap.add_argument("--extrapolate", type=int, nargs="*", default=[60, 90, 120, 150, 200])
    args = ap.parse_args()

    csv_path = ROOT / "results" / args.run / "judgements.csv"
    if not csv_path.exists():
        sys.exit(f"missing {csv_path}")

    records = load_trustworthy(csv_path)
    all_case_ids = sorted({r["case_id"] for r in records})
    n_full = len(all_case_ids)
    print(f"run='{args.run}'  {len(records)} trustworthy judgements over {n_full} real cases\n")

    print(f"=== empirical CI-width curve (subsampled from the REAL {n_full}-case pool, "
          f"{args.draws} random draws per size, zero new API calls) ===")
    n_values = sorted(set(list(range(5, n_full, 5)) + [n_full]))
    curve = simulate_curve(records, all_case_ids, n_values, args.draws)

    c = fit_inverse_sqrt(curve)
    print(f"\nfitted scaling law: CI width ~ {c*100:.1f}pp / sqrt(n_cases)")

    print(f"\n=== extrapolated CI width at case counts beyond the current {n_full} "
          f"(no new data needed to project this — confirm by actually running more cases later) ===")
    for n in args.extrapolate:
        proj = c / (n ** 0.5)
        print(f"  n={n:4d} cases  ->  projected CI width ≈ {proj*100:5.1f}pp  "
              f"(vs {curve[n_full][0]*100:.1f}pp at the current {n_full})")

    print("\nNote: this assumes between-case variance dominates (the standard regime once\n"
          "each case already has several judges/models/samples, which is true here) — the\n"
          "projection is a planning estimate, not a guarantee; validate once real data lands.")


if __name__ == "__main__":
    main()
