# AGENTS.md — TRIZ-on vs TRIZ-off

A small, reproducible **framework for A/B-testing a system prompt** with a blind
LLM jury. It ships configured for one question — *does priming a model with a
[TRIZ](https://en.wikipedia.org/wiki/TRIZ) (Theory of Inventive Problem Solving)
system prompt make its engineering solutions more creative?* — but the machinery
is prompt- and dataset-agnostic: swap the two system prompts and the casebase and
you have a controlled evaluation of any "prompt A vs prompt B" hypothesis.

> **Headline result (shipped runs):** on a blind, bias-controlled, cross-family
> jury, TRIZ-prompted solutions are judged **more creative ~70% of the time**
> (textbook problems 69.8% CI [63.1, 76.0]; patent-derived problems 72.2% CI
> [66.2, 77.7]). See `results/<run>/README.md`.

This file orients both humans and coding agents. If you are an agent working in
this repo, read this top-to-bottom before editing — the design constraints in
§"Invariants" are load-bearing and easy to break.

---

## What the framework does

One independent variable — the **system prompt** — is toggled between two arms
(`triz` and `control`), everything else held fixed. For each problem, each model
produces one solution per arm; a jury of models×personas then picks the more
creative one in a blind two-alternative forced choice (2AFC), in both A/B orders.
The reported effect uses only the **trustworthy** votes: cross-family (a model
never judges its own output) and order-consistent (same pick both ways).

The pipeline is four stages, each **stateless and disk-cached** (keyed by a hash
of the inputs), so a re-run re-calls nothing and a single odd result can be
invalidated surgically:

```
 casebase.json
      │
      ▼
1. generate      src/generate.py          case × model × arm × k  ─►  data/<run>/generations/*.json
      │
      ▼
2. build pairs   scripts/build_pairs.py   match triz↔control      ─►  data/<run>/pairs.json
      │
      ▼
3. judge         src/judge.py             jury × persona × order  ─►  data/<run>/judgements/*.json
      │                                                               results/<run>/judgements.csv
      ▼
4. report        src/judge_report.py      stats to stdout
   charts        src/judge_charts.py      results/<run>/figures/*.png
```

Run the whole thing with `python main.py`, or stage by stage (below).

---

## Quick start

Requires Python ≥ 3.12. The project uses [uv](https://docs.astral.sh/uv/), but
plain `pip`/`venv` works too.

```bash
# 1. install
uv sync                      # or: pip install -e .

# 2. add an API key
cp .env.example .env         # then paste ONE key into .env

# 3. point config.yaml at a gateway that matches your key
#    (gateway_base_url: OpenRouter or Vercel AI Gateway — see .env.example)

# 4. sanity-check the gateway and model ids
uv run python src/generate.py --list-models

# 5. run the pipeline
uv run python main.py
```

Outputs land in `results/<run>/`: a printed stats report, `judgements.csv`, and
`figures/*.png`. A per-run write-up lives at `results/<run>/README.md`.

### Running a stage at a time

```bash
uv run python src/generate.py                    # stage 1  (add --limit 1 for a smoke test)
uv run python scripts/build_pairs.py             # stage 2
uv run python src/judge.py --concurrency 10      # stage 3
uv run python src/judge_report.py                # stage 4 (stats to stdout)
uv run python src/judge_charts.py                # stage 4 (figures)
```

`main.py` also supports `--from <stage>` and `--only <stage>`.

---

## Configuration — `config.yaml`

```yaml
gateway_base_url: https://openrouter.ai/api/v1   # any OpenAI-compatible gateway

run: us_patents                 # experiment name → isolates all artifacts
casebase: casebase_uspatents.json

models:                         # generators AND jury (one list; cross-family voting handles overlap)
  - openai/gpt-4o
  - anthropic/claude-sonnet-4.5
  - deepseek/deepseek-chat-v3.1
  - google/gemini-2.5-flash

modes: [triz, control]          # the two arms — do not rename without updating prompts/
k: 1                            # samples per (case, model, arm)
temperature: 0.0                # 0.0 for a deterministic k=1 baseline; raise for k>1
max_tokens: 4000                # headroom — "thinking" models burn budget on hidden reasoning
limit: null                     # cap number of cases (null = all)
```

**Run isolation.** `run:` namespaces *everything* — `data/<run>/`,
`results/<run>/`, and the pairs file — so independent experiments never collide.
To start a new experiment, set a new `run:` name and point `casebase:` at its case
file. The two shipped runs are `main` (45 textbook problems) and `us_patents`
(84 patent-derived problems).

**Caching & cache-busting.** Every result is keyed by
`sha256(model + arm + case + sample + prompt_version + params)`, where
`prompt_version` is a hash of the prompt files. So **editing a prompt, or changing
temperature/max_tokens, invalidates the relevant cache automatically**; identical
config re-reads cache and calls nothing. Errored calls are cached *as failures* and
will not auto-retry — delete the offending `data/<run>/**/*.json` record to re-run it.

---

## Project structure

```
triz-on-vs-off-agent/
├── main.py                     # one-command pipeline runner
├── config.yaml                 # the only knob you normally touch
├── .env.example                # copy to .env, add one API key
│
├── prompts/                    # the treatment lives here — edit to change the experiment
│   ├── triz_system.txt         #   arm A  (the "on" system prompt: 40 inventive principles)
│   ├── control_system.txt      #   arm B  (empty = the un-prompted baseline)
│   ├── user_template.txt       #   shared task; identical across arms (isolates the IV)
│   ├── judge_expert.txt        #   jury persona: TRIZ-literate reviewer
│   ├── judge_naive.txt         #   jury persona: layperson (no framework)
│   └── judge_user.txt          #   the 2AFC question shown to every judge
│
├── src/
│   ├── generate.py             # stage 1 — stateless gateway calls, disk cache
│   ├── judge.py                # stage 3 — blind 2AFC jury, both orders
│   ├── judge_report.py         # stage 4 — bootstrap CIs + bias diagnostics → stdout
│   ├── judge_charts.py         # stage 4 — the six result figures
│   ├── report.py               # optional HTML report of the generations
│   └── probe_models.py         # quick gateway/model connectivity probe
├── scripts/
│   └── build_pairs.py          # stage 2 — match triz↔control into judgeable pairs
│
├── casebase.json               # 45 textbook TRIZ problems  (run: main)
├── casebase_uspatents.json     # 84 patent-derived problems (run: us_patents)
│
├── DESIGN.md                   # the full protocol, bias-control checklist, stats plan
└── results/<run>/              # README.md write-up + figures/ (committed; CSVs are git-ignored)
```

What is **not** committed (see `.gitignore`): `.env`, the `data/` cache, `*.csv`
exports, rendered `*.html`/`*.pdf`, archived `runs/`, and scratch under `search/`.
These all regenerate from the pipeline.

---

## The casebase schema

A casebase is `{"cases": [ ... ]}`. Only `id` and `problem_description` are fed to
the model; the rest is offline scaffolding/metadata.

```jsonc
{
  "id": "001",
  "problem_description": "…the problem statement, and ONLY the problem…",
  "plus_factor_index":  [32],      // gold: TRIZ parameter that improves  (metadata)
  "minus_factor_index": [30],      // gold: TRIZ parameter that worsens   (metadata)
  "principle_index":    [2, 24],   // gold: inventive principle(s)        (metadata)
  "solutions":  [ ... ],           // gold answer — NEVER shown to the model
  "notes":      "provenance"
}
```

**Leak rule (invariant):** the generator sees `problem_description` and nothing
else. Gold parameters, principles, and solutions must never enter a generation
prompt — deriving the contradiction is exactly what the TRIZ arm is being tested on.

---

## Extending / reusing the framework

- **Test your own prompt hypothesis.** Replace `prompts/triz_system.txt` (arm A)
  and `prompts/control_system.txt` (arm B) with your two conditions, point
  `casebase:` at your problems, set a fresh `run:` name, and run `main.py`. Nothing
  about the pipeline is TRIZ-specific.
- **Add / change models.** Edit `models:` in `config.yaml` (validate ids with
  `--list-models`). The same list is used for generation and the jury; the report
  counts only cross-family votes, so overlap is fine.
- **Add a jury persona.** Drop a `prompts/judge_<name>.txt` and register it in the
  `PERSONAS` dict in `src/judge.py`.
- **Change sampling.** `k>1` with `temperature>0` captures within-arm stochastic
  variance; sample *i* of the TRIZ arm is paired to sample *i* of control.

**Statistical honesty (from `DESIGN.md`):** the **case is the unit of analysis**.
More models, more samples (`k`), and more judges multiply *judgements* but not
*independent cases* — CIs come from a **case-clustered bootstrap**, so the way to
tighten them is *more problems*, not more re-runs of the same ones.

---

## Invariants (do not break these when editing)

1. **One IV.** Only the *system* prompt differs between arms. Task, length, and
   format instructions live in the shared `user_template.txt`, so the TRIZ arm can
   never win on formatting alone.
2. **Stateless calls.** One request = one `(case, arm, model, sample)`, no
   conversation history, no cross-arm bleed. Never generate inside an agentic
   session that accumulates context.
3. **Blind, format-matched judging.** Both arms end with a plain-language
   `FINAL SOLUTION:` section (TRIZ vocabulary forbidden in it); only that section
   is shown to judges, so they can't spot the arm by style. `build_pairs.py` drops
   any pair that leaks jargon, is truncated, or is too short.
4. **Trustworthy subset only for the headline.** Cross-family + order-consistent.
   Report pooled numbers separately, never as the headline.
5. **The leak rule** (see casebase schema).

---

## Data provenance & licensing

- `casebase.json` — classic TRIZ textbook problems (Altshuller/Petrov lineage);
  cite the source texts noted per case.
- `casebase_uspatents.json` — **model-derived** problem stems grounded in the
  [TrizBench](https://github.com/ellenzhuwang/trizbench) dataset
  (`data/patent_task1_classical_all_text.jsonl`). The stems are rewritten,
  leak-free, and identifier-stripped — **not** the patents' own text. TrizBench has
  no license file at time of writing, so treat the upstream data as
  all-rights-reserved: cite the TrizBench paper and confirm terms with its authors
  before redistributing derived data.
- The TRIZ 40 inventive principles behind `prompts/triz_system.txt`: Altshuller, G.
  (1997), *40 Principles: TRIZ Keys to Technical Innovation.*

This repository does not yet declare a software license; add one before relying on
it as open source.
