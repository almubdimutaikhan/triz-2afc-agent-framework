#!/usr/bin/env python3
"""
Stats + forest plot for the factorial (2x2 length x TRIZ) redesign's judgements.

For each of the 4 interpretable comparisons, computes:
  - p_hat = P(the "treatment" arm is picked as more creative)
  - odds ratio = p/(1-p)  (null OR = 1, i.e. p = 0.50)
  - 95% CI on both p and OR via a CASE-CLUSTERED BOOTSTRAP (resamples whole
    cases, not raw judgements — judgements from the same case aren't
    independent, same reasoning as src/judge_report.py's cluster_bootstrap_ci).

Only cross-family (judge_model != gen_model) + order-consistent (same pick in
both orders) judgements are used — the "trustworthy" subset, same convention
as the legacy pipeline.

Run:  python src/factorial_report.py [--run factorial_pilot12]
Outputs:
  stdout table (comparison, question, baseline, n, p, OR, 95% CI, direction)
  results/<run>/figures/factorial_forest.png  (dodge/whisker chart, ggplot2-style)
"""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
random.seed(7)

# Canonical (treatment, baseline) per comparison — matches
# scripts/build_pairs.py's FACTORIAL_COMPARISONS exactly, plus the plain-English
# question each answers (from the prof's requested table format).
COMPARISONS = [
    ("P_S_TRIZ_ON", "P_S_TRIZ_OFF", "Does the TRIZ keyword help in short prompts?"),
    ("P_L_TRIZ_ON", "P_L_TRIZ_OFF", "Does TRIZ help beyond matched long structure?"),
    ("P_L_TRIZ_OFF", "P_S_TRIZ_OFF", "Does long generic structure help?"),
    ("P_L_TRIZ_ON", "P_S_TRIZ_ON", "Does the full TRIZ scaffold help beyond the short TRIZ mention?"),
]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def load_trustworthy(csv_path):
    rows = list(csv.DictReader(open(csv_path)))
    good = [r for r in rows if r.get("picked_arm") and r["picked_arm"] != ""]
    off = [r for r in good if r["judge_model"] != r["gen_model"]]
    bykp = defaultdict(list)
    for r in off:
        bykp[(r["judge_model"], r["persona"], r["pair_id"])].append(r)
    keep = []
    for v in bykp.values():
        if len(v) == 2 and len({x["picked_arm"] for x in v}) == 1:  # order-consistent
            keep.append(v[0])
    return keep


def comparison_of(pair_id):
    # pair_id = "{case}__{model}__s{sidx}__{arm_a}_vs_{arm_b}" (scripts/build_pairs.py)
    return pair_id.rsplit("__", 1)[-1]


def case_clustered_ci_or(records, treatment, B=3000, lo=2.5, hi=97.5):
    """records: trustworthy judgements for ONE comparison.
    Returns (p_hat, p_lo, p_hi, or_hat, or_lo, or_hi, n_cases)."""
    picked_treat = lambda r: 1 if r["picked_arm"] == treatment else 0
    clusters = defaultdict(list)
    for r in records:
        clusters[r["case_id"]].append(picked_treat(r))
    names = list(clusters)
    if not names:
        return (float("nan"),) * 6 + (0,)

    p_means, ors = [], []
    for _ in range(B):
        pool = []
        for _ in range(len(names)):
            pool.extend(clusters[random.choice(names)])
        if pool:
            p = mean(pool)
            p_means.append(p)
            p_clamped = min(max(p, 1e-4), 1 - 1e-4)  # avoid div-by-zero at the extremes
            ors.append(p_clamped / (1 - p_clamped))
    p_means.sort()
    ors.sort()

    p_hat = mean(picked_treat(r) for r in records)
    p_lo = p_means[int(lo / 100 * len(p_means))]
    p_hi = p_means[min(len(p_means) - 1, int(hi / 100 * len(p_means)))]
    or_hat = p_hat / (1 - p_hat) if 0 < p_hat < 1 else float("inf") if p_hat == 1 else 0.0
    or_lo = ors[int(lo / 100 * len(ors))]
    or_hi = ors[min(len(ors) - 1, int(hi / 100 * len(ors)))]
    return p_hat, p_lo, p_hi, or_hat, or_lo, or_hi, len(names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None, help="run name (default: read from config.yaml)")
    args = ap.parse_args()

    run = args.run
    if run is None:
        import yaml
        run = yaml.safe_load((ROOT / "config.yaml").read_text()).get("run", "main")

    csv_path = ROOT / "results" / run / "judgements.csv"
    if not csv_path.exists():
        raise SystemExit(f"missing {csv_path}")

    records = load_trustworthy(csv_path)
    if not records:
        raise SystemExit("no trustworthy factorial judgements found (cross-family + order-consistent)")

    print(f"run='{run}'  {len(records)} trustworthy judgements  "
          f"({len({r['case_id'] for r in records})} cases)\n")

    results = []
    print(f"{'Comparison':38s} {'Baseline':13s} {'n':>5s} {'p (treat)':>10s} {'OR':>7s} {'95% CI (OR)':>16s}  Question")
    print("-" * 130)
    for treat, base, question in COMPARISONS:
        comp_key = f"{treat}_vs_{base}"
        sub = [r for r in records if comparison_of(r["pair_id"]) == comp_key]
        if not sub:
            print(f"{treat+' vs '+base:38s}  (no trustworthy judgements for this comparison)")
            continue
        p_hat, p_lo, p_hi, or_hat, or_lo, or_hi, n_cases = case_clustered_ci_or(sub, treat)
        sig = "*" if (or_lo > 1 or or_hi < 1) else " "
        print(f"{treat+' vs '+base:38s} {base:13s} {len(sub):5d} {p_hat*100:9.1f}% "
              f"{or_hat:7.2f} [{or_lo:5.2f},{or_hi:5.2f}]{sig}  {question}")
        results.append({
            "treat": treat, "base": base, "question": question,
            "n": len(sub), "n_cases": n_cases,
            "p": p_hat, "p_lo": p_lo, "p_hi": p_hi,
            "or": or_hat, "or_lo": or_lo, "or_hi": or_hi,
        })
    print("\n* = 95% CI excludes OR=1 (i.e. excludes p=0.50) -> significant at this sample size")
    print("NOTE: this is a PILOT. Wide CIs are expected; read direction/magnitude, not significance stars.")

    make_forest_plot(results, run)


def make_forest_plot(results, run):
    FIG = ROOT / "results" / run / "figures"
    FIG.mkdir(parents=True, exist_ok=True)

    INK = "#1b1f2a"
    TRIZ = "#5b8def"
    BASE = "#e07a5f"
    GREY = "#9aa0ad"
    plt.rcParams.update({
        "figure.dpi": 130, "font.size": 11,
        "axes.edgecolor": "#d0d4dc", "axes.linewidth": 0.8,
        "axes.grid": True, "grid.color": "#eef0f4", "grid.linewidth": 0.9,
        "axes.axisbelow": True, "figure.facecolor": "white",
    })

    fig, ax = plt.subplots(figsize=(8.5, 0.9 + 1.1 * len(results)))
    ys = list(range(len(results)))[::-1]
    for y, r in zip(ys, results):
        color = TRIZ if r["or"] >= 1 else BASE
        ax.plot([r["or_lo"], r["or_hi"]], [y, y], color=INK, lw=1.6, zorder=3)
        ax.plot(r["or"], y, "o", color=color, markersize=11, zorder=4,
                markeredgecolor="white", markeredgewidth=1)
        ax.text(r["or_hi"] + 0.08 * max(1, r["or_hi"]), y, f"OR={r['or']:.2f}",
                va="center", fontsize=9.5, color=INK)

    ax.axvline(1.0, color=INK, ls="--", lw=1.4, zorder=2)
    ax.set_xscale("log")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r['treat']}\nvs {r['base']}" for r in results], fontsize=9.5)
    ax.set_xlabel("Odds ratio (log scale) — treatment vs baseline, 95% CI  ·  dashed line = OR 1 (no effect)")
    ax.set_title(f"Factorial redesign — odds ratio by comparison  (run: {run})",
                 fontweight="bold", color=INK, pad=12)
    fig.tight_layout()
    out = FIG / "factorial_forest.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"\nforest plot -> {out}")


if __name__ == "__main__":
    main()
