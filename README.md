# TRIZ-2AFC — a framework for A/B-testing a system prompt with a blind LLM jury

A small, reproducible pipeline for answering *"does prompt A beat prompt B?"* with
statistical rigor. You give it two system prompts, a set of problems, and a list of
models; it generates one solution per arm per model, then has a **jury of models ×
personas** pick the better one in a blind two-alternative forced choice (2AFC) — in both
A/B orders, cross-family, with case-clustered confidence intervals.

It ships configured for one concrete study — *does a **TRIZ** (Theory of Inventive Problem
Solving) system prompt make an LLM's engineering solutions more creative than no prompt at
all?* — but nothing in the machinery is TRIZ-specific. Swap the two prompts and the
casebase and you have a controlled evaluation of your own prompting hypothesis.

## The shipped result

On a blind, bias-controlled, cross-family jury, TRIZ-prompted solutions are judged **more
creative ~70% of the time**, and it replicates across two independent problem sets:

| Study | Problems | Trustworthy p(TRIZ chosen) | 95% CI |
|---|---|---|---|
| Textbook TRIZ problems (`run: main`) | 45 | **69.8%** | [63, 76] |
| Patent-derived problems (`run: us_patents`) | 84 | **72.2%** | [66, 78] |

*(50% = no effect; both intervals clear 50%.)*

![Jury verdict](results/main/figures/jury_verdict.png)

Full write-ups: [`results/main/README.md`](results/main/README.md) ·
[`results/us_patents/README.md`](results/us_patents/README.md).

## How it works

One independent variable — the **system prompt** — is toggled between two arms (`triz` /
`control`); everything else is held fixed. Four stateless, disk-cached stages:

```
casebase.json ─► generate ─► build pairs ─► judge (blind 2AFC, both orders) ─► report + charts
                 src/          scripts/       src/                              src/
```

The headline uses only **trustworthy** votes: cross-family (a model never judges its own
output) *and* order-consistent (same pick both ways). Because each stage caches by a hash
of its inputs, editing a prompt or changing sampling automatically invalidates just the
affected results, and re-runs re-call nothing.

## Quick start

Requires Python ≥ 3.12 ([uv](https://docs.astral.sh/uv/) recommended).

```bash
uv sync                                   # install
cp .env.example .env                      # then paste ONE API key into .env
# set gateway_base_url in config.yaml to match your key (OpenRouter or Vercel)

uv run python src/generate.py --list-models   # verify the gateway + model ids
uv run python main.py                          # run the whole pipeline
```

Outputs land in `results/<run>/`: a printed stats report, `judgements.csv`, and
`figures/*.png`. Run stages individually with `main.py --only <stage>` / `--from <stage>`,
or call `src/generate.py`, `scripts/build_pairs.py`, `src/judge.py`,
`src/judge_report.py`, `src/judge_charts.py` directly.

## Test your own hypothesis

1. Replace `prompts/triz_system.txt` (arm A) and `prompts/control_system.txt` (arm B) with
   your two conditions. Keep the shared task in `prompts/user_template.txt` so the prompt
   is the *only* thing that differs.
2. Point `casebase:` in `config.yaml` at your problems and set a fresh `run:` name.
3. `uv run python main.py`.

See **[`AGENTS.md`](AGENTS.md)** for the full framework guide (config reference, casebase
schema, extension points, and the invariants that keep the comparison fair) and
**[`DESIGN.md`](DESIGN.md)** for the experimental protocol, bias-control checklist, and
statistics plan.

## Repository layout

```
config.yaml            # the main knob: models, prompts arms, sampling, run isolation
prompts/               # the treatment — two system prompts + jury personas
src/                   # generate, judge, report, charts
scripts/build_pairs.py # match triz↔control into judgeable pairs
casebase*.json         # the two shipped problem sets
results/<run>/         # per-run write-up + figures
main.py                # one-command pipeline runner
```

## Data & licensing

The patent-derived stems in `casebase_uspatents.json` are **model-derived** (leak-free,
identifier-stripped) from the [TrizBench](https://github.com/ellenzhuwang/trizbench)
dataset — not the patents' own text; confirm upstream terms before redistributing derived
data. The TRIZ 40 inventive principles behind `prompts/triz_system.txt`: Altshuller, G.
(1997), *40 Principles: TRIZ Keys to Technical Innovation.* See `AGENTS.md` for full
provenance. This repository does not yet declare a software license.
