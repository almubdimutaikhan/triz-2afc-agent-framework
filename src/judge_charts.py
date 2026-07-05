#!/usr/bin/env python3
"""
Render the LLM-jury results (results/judgements.csv) as PNG figures into
results/figures/. Mirrors the numbers in src/judge_report.py.

Run:  python src/judge_charts.py
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "results" / "judgements.csv"
FIG = ROOT / "results" / "figures"
random.seed(7)

INK = "#1b1f2a"
TRIZ = "#5b8def"      # blue  = TRIZ favoured
CTRL = "#e07a5f"      # red   = control favoured
GREY = "#9aa0ad"
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 11,
    "axes.edgecolor": "#d0d4dc", "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": "#eef0f4", "grid.linewidth": 0.9,
    "axes.axisbelow": True, "figure.facecolor": "white",
})


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def boot_ci(items, key, val, B=3000):
    clusters = defaultdict(list)
    for r in items:
        clusters[key(r)].append(val(r))
    names = list(clusters)
    if not names:
        return (float("nan"), float("nan"))
    ms = []
    for _ in range(B):
        pool = []
        for _ in range(len(names)):
            pool.extend(clusters[random.choice(names)])
        ms.append(mean(pool))
    ms.sort()
    return ms[int(0.025 * len(ms))], ms[int(0.975 * len(ms))]


def short(m):
    return m.split("/")[-1].replace("-sonnet", "").replace("-v3.1", "")


def color_for(p):
    return TRIZ if p >= 0.5 else CTRL


def fmt_pct(ax):
    ax.set_ylim(0, 1)
    ax.set_yticks([0, .25, .5, .75, 1])
    ax.set_yticklabels(["0", "25", "50", "75", "100%"])
    ax.axhline(0.5, color=INK, lw=1.4, ls="--", zorder=5)


def annotate(ax, xs, ps, ns=None):
    for i, p in enumerate(ps):
        lbl = f"{p*100:.0f}%"
        ax.text(xs[i], p + 0.025, lbl, ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=INK)


def load():
    rows = list(csv.DictReader(CSV.open()))
    return [r for r in rows if r.get("picked_arm") in ("triz", "control")]


triz = lambda r: 1 if r["picked_arm"] == "triz" else 0
case = lambda r: r["case_id"]


# ---------- figures ----------
def fig_by_judge(good):
    judges = sorted({(r["judge_model"], r["persona"]) for r in good})
    labels, ps, los, his = [], [], [], []
    for jm, persona in judges:
        sub = [r for r in good if r["judge_model"] == jm and r["persona"] == persona]
        p = mean(triz(r) for r in sub)
        lo, hi = boot_ci(sub, case, triz)
        labels.append(f"{short(jm)}\n{persona}")
        ps.append(p); los.append(p - lo); his.append(hi - p)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = range(len(labels))
    ax.bar(x, ps, color=[color_for(p) for p in ps], width=0.62, zorder=3,
           edgecolor="white", linewidth=1)
    ax.errorbar(x, ps, yerr=[los, his], fmt="none", ecolor=INK, capsize=4, lw=1.3, zorder=6)
    annotate(ax, list(x), ps)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    fmt_pct(ax)
    ax.set_title("How often each judge calls the TRIZ answer more creative",
                 fontweight="bold", color=INK)
    ax.set_ylabel("p(TRIZ chosen)")
    ax.text(0.0, -0.22, "dashed line = 50% (no preference) · bars = 95% CI",
            transform=ax.transAxes, fontsize=9, color=GREY)
    save(fig, "p_triz_by_judge.png")


def fig_persona(good):
    models = sorted({r["judge_model"] for r in good})
    exp = [mean(triz(r) for r in good if r["judge_model"] == m and r["persona"] == "expert") for m in models]
    nai = [mean(triz(r) for r in good if r["judge_model"] == m and r["persona"] == "naive") for m in models]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    x = range(len(models)); w = 0.36
    ax.bar([i - w/2 for i in x], exp, w, label="expert (TRIZ master)", color=TRIZ, zorder=3, edgecolor="white")
    ax.bar([i + w/2 for i in x], nai, w, label="naive (layperson)", color="#9bb8f0", zorder=3, edgecolor="white")
    for i in x:
        ax.text(i - w/2, exp[i] + 0.02, f"{exp[i]*100:.0f}%", ha="center", fontsize=9, fontweight="bold")
        ax.text(i + w/2, nai[i] + 0.02, f"{nai[i]*100:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels([short(m) for m in models])
    fmt_pct(ax)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("Persona contrast: does TRIZ-expertise change the verdict?",
                 fontweight="bold", color=INK)
    ax.set_ylabel("p(TRIZ chosen)")
    save(fig, "persona_contrast.png")


def fig_breakdown(good, field, title, fname, sortby=None):
    off = [r for r in good if r["judge_model"] != r["gen_model"]]  # cross-family
    keys = sorted({r[field] for r in off})
    data = [(k, mean(triz(r) for r in off if r[field] == k)) for k in keys]
    if sortby == "value":
        data.sort(key=lambda t: t[1])
    labels = [short(k) if "/" in k else k for k, _ in data]
    ps = [p for _, p in data]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    x = range(len(labels))
    ax.bar(x, ps, color=[color_for(p) for p in ps], zorder=3, edgecolor="white", width=0.66)
    annotate(ax, list(x), ps)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, rotation=0 if len(labels) <= 6 else 30, ha="center")
    fmt_pct(ax)
    ax.set_title(title, fontweight="bold", color=INK)
    ax.set_ylabel("p(TRIZ chosen)")
    ax.text(0.0, -0.2, "cross-family judgements only · blue = TRIZ wins, red = control wins",
            transform=ax.transAxes, fontsize=9, color=GREY)
    save(fig, fname)


def fig_selfpref(good):
    jms = sorted({r["judge_model"] for r in good})
    gms = sorted({r["gen_model"] for r in good})
    M = [[mean(triz(r) for r in good if r["judge_model"] == j and r["gen_model"] == g)
          for g in gms] for j in jms]
    fig, ax = plt.subplots(figsize=(6.6, 5))
    im = ax.imshow(M, cmap="RdBu", vmin=0.2, vmax=0.8, aspect="auto")
    ax.set_xticks(range(len(gms))); ax.set_xticklabels([short(g) for g in gms], rotation=20, ha="right")
    ax.set_yticks(range(len(jms))); ax.set_yticklabels([short(j) for j in jms])
    ax.set_xlabel("solution written by"); ax.set_ylabel("judged by")
    for i in range(len(jms)):
        for j in range(len(gms)):
            diag = "\n(self)" if jms[i] == gms[j] else ""
            ax.text(j, i, f"{M[i][j]*100:.0f}%{diag}", ha="center", va="center",
                    fontsize=10, fontweight="bold",
                    color="white" if abs(M[i][j]-0.5) > 0.18 else INK)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="p(TRIZ chosen)")
    ax.set_title("Self-preference check (diagonal = judging own output)",
                 fontweight="bold", color=INK)
    save(fig, "self_preference.png")


def fig_verdict(good):
    # the trustworthy subset: cross-family + order-consistent
    off = [r for r in good if r["judge_model"] != r["gen_model"]]
    keep = []
    byk = defaultdict(list)
    for r in off:
        byk[(r["judge_model"], r["persona"], r["pair_id"])].append(r)
    for v in byk.values():
        if len(v) == 2 and len({x["picked_arm"] for x in v}) == 1:
            keep.append(v[0])
    p = mean(triz(r) for r in keep)
    lo, hi = boot_ci(keep, case, triz)
    fig, ax = plt.subplots(figsize=(7.4, 2.8))
    ax.barh([0], [p], color=TRIZ, height=0.55, zorder=3, edgecolor="white")
    ax.barh([0], [1-p], left=[p], color=CTRL, height=0.55, zorder=3, edgecolor="white")
    ax.errorbar([p], [0], xerr=[[p-lo], [hi-p]], fmt="none", ecolor=INK, capsize=6, lw=1.8, zorder=6)
    ax.axvline(0.5, color=INK, ls="--", lw=1.4, zorder=5)
    ax.set_xlim(0, 1); ax.set_ylim(-0.6, 0.6); ax.set_yticks([])
    ax.set_xticks([0, .25, .5, .75, 1]); ax.set_xticklabels(["0", "25", "50", "75", "100%"])
    ax.text(p/2, 0, f"TRIZ {p*100:.0f}%", va="center", ha="center",
            fontweight="bold", color="white", fontsize=13, zorder=7)
    ax.text(p + (1-p)/2, 0, f"control {(1-p)*100:.0f}%", va="center", ha="center",
            fontweight="bold", color="white", fontsize=11, zorder=7)
    ax.set_title("Jury verdict — TRIZ vs control on creativity (trustworthy subset)",
                 fontweight="bold", color=INK, pad=12)
    ax.set_xlabel(f"95% CI [{lo*100:.0f}%, {hi*100:.0f}%]   ·   n={len(keep)} clean judgements   ·   "
                  f"interval clears 50% → significant", fontsize=9.5, color=GREY)
    save(fig, "jury_verdict.png")


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote results/figures/{name}")


def main():
    # Per-run path isolation: results/<run>/judgements.csv -> results/<run>/figures/.
    global CSV, FIG
    try:
        import yaml
        run = yaml.safe_load((ROOT / "config.yaml").read_text()).get("run", "main")
    except Exception:
        run = "main"
    CSV = ROOT / "results" / run / "judgements.csv"
    FIG = ROOT / "results" / run / "figures"
    print(f"run='{run}'  reading {CSV}")
    if not CSV.exists():
        raise SystemExit(f"missing {CSV}; run src/judge.py first")
    good = load()
    print(f"rendering figures from {len(good)} judgements ->")
    fig_verdict(good)
    fig_by_judge(good)
    fig_persona(good)
    fig_breakdown(good, "gen_model", "TRIZ creativity win-rate, by which model wrote the solution",
                  "by_generator.png")
    fig_breakdown(good, "case_id", "TRIZ creativity win-rate, by problem", "by_case.png", sortby="value")
    fig_selfpref(good)
    print("done.")


if __name__ == "__main__":
    main()
