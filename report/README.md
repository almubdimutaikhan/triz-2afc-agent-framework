# Does TRIZ prompting make LLMs more inventive? — RA progress report

**Almubdi Mutaikhan** · supervised by Prof. Jose Berengueres · July 17, 2026
Repos: [triz-2afc-agent-framework](https://github.com/almubdimutaikhan/triz-2afc-agent-framework) (experiments) · [2afc-game-platform](https://github.com/almubdimutaikhan/2afc-game-platform) (human-rating web app)

---

## TL;DR — in the project's hypothesis terms

- **H1 (TRIZ prompt injection improves 2AFC creativity) — tested and REJECTED, with
  evidence.** The raw effect replicated 3× (~68–72%, n up to 1,841), but the 2×2 factorial
  pilot isolated the cause: **prompt structure, not TRIZ content** (structure-only contrast
  63.4%, OR 1.73, significant; TRIZ-specific contrasts ~49–57%, n.s.). Phases 1–2 below are
  the full evidence chain for that verdict.
- **H2 (iterative agentic workflows) — ACTIVE and promising.** Phase 4's 40-round
  "don't repeat yourself" exhaustion chains are the first controlled probe: models differ
  enormously in ideation depth under iteration (Claude: 40/40 distinct mechanisms; GPT-4o
  recycles from round 4). The live Netlify tools (Review tab + /compare) are the current
  H2 test instruments.
- **Toward the "absolute novelty" agenda:** the chains already carry a first computational
  novelty metric (content-overlap distance to all prior solutions) — a primitive ancestor
  of the planned SOTA-database "Compute Distance" measure.
- **Infrastructure delivered:** reproducible generation/judging/stats pipeline
  (open-sourced), two deployed human-rating web tools, validated & expandable casebases.

---

## Timeline (matches the project log, weeks 1–6)

| Week | What I delivered |
|---|---|
| 1 (Jun 11–13) | Kickoff; pipeline design (2AFC protocol, bias controls, leakage rule) |
| 2 (Jun 22–27) | 45-case dataset; 4-model pipeline (+ Gemini 2.5 Flash); first trustworthy-subset signal 69.8% |
| 3 (Jul 1) | Framework published as open source; stylistic-leakage suppression verified; CrPO 5th generator on Colab |
| 4 (Jul 5) | ELEC-042 mouse probe (89.5% across 8 blind judge configurations); human-eval game deployed (Netlify + Firebase) |
| 5 (Jul 7) | 12-case factorial pilot → **H1 rejection evidence** (structure, not TRIZ content); CI power law fitted |
| 6 (Jul 14–now) | Per-principle p40 design (860 generations), exhaustion chains (160 rounds) with novelty metric, Review + Compare rating tools deployed |

## Phase 1 — Framework + the original question (TRIZ on vs off) → H1 evidence

**Design.** Each model solves each problem twice — TRIZ-expert system prompt vs no system
prompt — with an identical user message that forces a plain-language `FINAL SOLUTION`
section (no TRIZ vocabulary allowed → judges can't detect the condition; verified 0
leaks). Solutions are paired and judged blind by a 4-model jury, both A/B orders.
**Trustworthy subset** = cross-family (judge ≠ generator family) + order-consistent.
CIs come from a case-clustered bootstrap (cases resampled, not judgements).

**Results** (full details: [`02_main_study_results.md`](02_main_study_results.md)):

| Run | Cases | TRIZ preferred | 95% CI | n trustworthy |
|---|---|---|---|---|
| main (4 generators) | 45 | 69.8% | [63.1, 76.0] | 1,227 |
| main v2 (+ CrPO 5th generator) | 45 | 68.2% | [62.4, 73.4] | 1,841 |
| us_patents (patent-derived problems) | 84 | 72.2% | [66.2, 77.7] | 1,382 |
| pc-mouse single-case probe (ELEC-042) | 1 | 89.5% | n/a (1 case) | 38 |

Extras: ran **CrPO** (creativity-finetuned Llama-3.1-8B) on Colab as a generator-only 5th
model (60.2% cross-family — the TRIZ effect transfers to a small creative-tuned model);
quantified self-preference bias (~+5pp) and reported it honestly.

## Phase 2 — The factorial redesign → why H1 was rejected

Prof's critique: TRIZ-vs-empty-control conflates TRIZ *content* with prompt *length,
structure and expert framing*. Redesign implemented exactly as specified:

- **4 generation conditions** (2×2): long-TRIZ / long-generic-matched (330 words, zero TRIZ
  terms) / short-TRIZ ("Use TRIZ to solve…") / short-baseline ("Solve…").
- **Single criterion-based, TRIZ-blind evaluator** (originality, usefulness, feasibility,
  specificity, elegance) replacing personas; odds ratios + forest plot.

**Pilot, n=12 cases** ([`03_factorial_pilot_results.md`](03_factorial_pilot_results.md), forest plot in `figures/`):

| Comparison | % treatment | OR | 95% CI | |
|---|---|---|---|---|
| structure only (long-generic vs short-baseline) | **63.4%** | **1.73** | [1.04, 3.25] | **significant** |
| TRIZ keyword (short) | 56.5% | 1.30 | [0.90, 1.95] | n.s. |
| TRIZ beyond matched structure (long) | 53.0% | 1.13 | [0.72, 1.75] | n.s. |
| TRIZ scaffold vs bare keyword | 48.7% | 0.95 | [0.62, 1.52] | n.s. |

**Reading:** the earlier ~70% was carried substantially by *structured prompting*; the
TRIZ-specific residual is small and needs either more cases (power analysis: CI width ≈
72.6pp/√n_cases) or a sharper manipulation → Phase 3. This decomposition is itself a
publishable finding.

## Phase 3 — Per-principle injection (the "40×" design)

Prof's next design: don't ask whether "TRIZ" as a word helps — inject each **individual
inventive principle** and see which ones actually move solutions.

- **43 conditions**: baseline / TRIZ-keyword / TRIZ + full 40-principles document attached
  (Oxford Creativity, extracted & embedded as text) / TRIZ + principle *i* alone
  (i = 1…40, explanation paragraphs length-controlled at 55–71 words, sourced from the
  prof-shared repos).
- **Casebase tooling**: expansion guide + automated validator (schema, TRIZ-vocabulary
  leaks, 3-layer anti-duplicate protocol). New case authored from the prof's own IEEE
  Access haptic-boot paper: *design a haptic space boot for Mars exploration*.
- **Run**: 5 problems (2 textbook, 2 patent, 1 Mars boot) × 43 conditions × 4 models =
  **860 generations, 0 errors, 0 vocabulary leaks** →
  [`04_p40_review_860_outputs.csv`](04_p40_review_860_outputs.csv).
- **Human-rating tool** (deployed): the game's new **Review tab** — per problem × model,
  star the top-3 principle outputs, like/dislike the baselines, live dashboard of
  which principle wins per problem, public CSV export of all ballots.

## Phase 4 — Solution-space exhaustion (iterative "don't repeat") → first H2 probe

New protocol probing how *deep* a model's idea well is: same problem (Mars boot), TRIZ-on
prompt, 40 sequential rounds per model where every previous solution is appended as
forbidden — the model must produce a fundamentally different mechanism each round.
160 chained generations → [`05_exhaust_chains_160_rounds.csv`](05_exhaust_chains_160_rounds.csv)
(readable version: [`05_exhaust_chains_readable.md`](05_exhaust_chains_readable.md)).

**Finding — models differ enormously in ideation depth** (overlap = max content-word
similarity to any earlier round in the chain):

| Model | First round ≥50% overlap | Mean overlap | Peak |
|---|---|---|---|
| claude-sonnet-4.5 | never in 40 rounds | 23.5% | 31% |
| deepseek-v3.1 | round 7 | 36.5% | 73% |
| gpt-4o | round 4 | 67.6% | 89% |
| gemini-2.5-flash | round 14 | 65.1% | 100% (verbatim repeat) |

- **Head-to-head rating tool** (deployed): **/compare** page — per model, rank top-5 of the
  40 per-principle outputs vs top-5 of the 40 exhaustion rounds, then a side-by-side view
  of the winners. This directly feeds the "three outputs to compare" plan from our meeting.

---

## Infrastructure delivered (all open-source, reproducible)

- **Generation pipeline**: N named conditions, per-run isolation, sha256 disk cache
  (interrupt/resume free, byte-reproducible), 4 API model families + Colab pipeline for
  local HF models (CrPO).
- **Judging pipeline**: blind 2AFC, both orders, cross-family jury, jargon/truncation
  leak filter (drop, never rewrite), criterion-based TRIZ-blind evaluator.
- **Statistics**: case-clustered bootstrap CIs, odds ratios, forest plots, CI-width power
  law fitted on our own data, position-bias and self-preference diagnostics.
- **Human-eval platform**: Next.js + Firebase on Netlify — blind 2AFC game, Review tab
  (principle ranking), Compare page (method ranking), public CSV exports, live dashboards.
- **Data assets**: 45-case textbook casebase (+ canonical principles), 84-case patent
  casebase, validator + expansion protocol.

## Proposed next steps (aligned with the project roadmap)

1. **Collect ballots** in the Review + Compare tools (team pass), then report which
   principles win per problem and whether principle-injection beats iterative exhaustion —
   this is the direct A/B evidence for H2.
2. **Problem decomposition (Insight 1):** extend the pipeline so a problem is first
   decomposed into functional components (Innovation Matrix / Wardley-style "boxes") and
   agents apply principles to the *relationships between components* — the casebase schema
   and N-condition generator are ready to host this.
3. **Novelty metric (literature blindspot):** grow the chains' content-overlap measure into
   the planned **Compute Distance** vs a SOTA/patent database — the exhaustion protocol is
   the natural testbed, since it already produces graded novelty under pressure.
4. **Adaptation check:** automated verification that each per-principle output actually
   *used* its injected principle, crossed with the human picks; then correct-vs-random
   principle assignment at the ~50-problem scale (canonical principle labels exist).
5. **Paper:** H1 rejection (Phases 1–2) → H2 mechanism (Phases 3–4) is the narrative;
   methods + prompt/problem tables ready to draft against Suake's literature review.

## Files in this folder

| File | What it shows |
|---|---|
| `02_main_study_results.md` | Full 5-generator study report (Phase 1) |
| `02b_us_patents_results.md` | Patent-problem replication report (Phase 1) |
| `03_factorial_pilot_results.md` | Factorial pilot report + interpretation (Phase 2) |
| `figures/factorial_forest.png` | Odds-ratio forest plot of the 4 factorial contrasts |
| `figures/by_generator.png`, `figures/p_triz_by_judge.png` | Phase-1 breakdowns |
| `04_p40_review_860_outputs.csv` | All 860 per-principle generations, decoded & readable |
| `05_exhaust_chains_160_rounds.csv` | 160 exhaustion rounds with novelty metrics |
| `05_exhaust_chains_readable.md` | The same chains formatted for reading |
