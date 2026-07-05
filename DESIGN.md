# TRIZ-Prompted vs Unprompted Agent — 2AFC Evaluation Protocol

**Status:** design doc (pre-implementation)
**Date:** 2026-06-19
**Data:** `casebase.json` (10 TRIZ contradiction cases)

---

## 1. Research question & hypotheses

**RQ.** Does equipping an agent with a TRIZ-expert system prompt produce *better engineering
solutions* than the same agent with no such prompt — and does the effect hold across generator
models?

- **H1 (primary).** TRIZ-prompted solutions win the 2AFC preference against unprompted solutions
  at a rate > 50% (case-clustered).
- **H2 (objective).** TRIZ-prompted solutions recover more of the gold `principle_index` /
  contradiction parameters than unprompted ones.
- **H0.** Win rate = 50%; no difference in principle recovery.

Two independent outcome tracks are measured so a biased judge can't be the *only* evidence:

- **Track 1 — Objective (label-based, bias-free):** overlap of used principles/parameters vs gold.
- **Track 2 — Subjective (2AFC, bias-controlled):** human-like preference via an LLM jury.

---

## 2. Design

| Factor | Levels | Role |
|---|---|---|
| **Prompt (IV)** | `triz` / `control` | the treatment — the *only* thing that differs at generation |
| Generator model | ≥2 models (see §11) | tests robustness of the prompt effect across models |
| Sample k | k = 3–5 per (case, arm, model) | captures within-arm stochastic variance |
| Judge model | jury of ≥3 cross-family models | Track-2 measurement |
| Case | 10 (expandable) | **unit of statistical analysis** |

**Held fixed across arms:** generator model, temperature, max tokens, the *user* message (incl.
output-format instructions), decoding seed where supported. Only the **system prompt** changes.
This isolates the IV — output format/length instructions live in the shared user message, not the
TRIZ prompt, so the TRIZ arm can't win on formatting alone.

---

## 3. Data handling & the leakage rule

Each case exposes: `problem_description`, `plus_factor_index`, `minus_factor_index`,
`principle_index`, `solutions[].content`, `notes`.

**LEAK RULE — feed the agent ONLY `problem_description`.**
`plus/minus_factor_index` and `principle_index` are gold scaffolding; `solutions` and `notes` are
gold answers. None may appear in any generation prompt. The TRIZ arm must *derive* the contradiction
itself — that derivation is exactly what we're testing. The gold fields are used **only** offline in
Track-1 scoring and (optionally) as reference for the judge in a separate robustness run.

---

## 4. The two arms (exact prompts)

### 4a. Control arm — system prompt
Empty / none. The model receives only the shared user message (§4c). This is the literal
"no prompt" baseline.

### 4b. TRIZ arm — system prompt (draft)
```
You are an expert in TRIZ (the Theory of Inventive Problem Solving). When given an
engineering problem you reason explicitly through the TRIZ method:
1. Identify the core technical contradiction: which parameter improves and which
   parameter worsens (in TRIZ's 39 engineering parameters).
2. Map the contradiction to candidate inventive principles (TRIZ's 40 principles).
3. Apply the most relevant principles to generate a concrete, physically realizable
   solution that resolves the contradiction rather than trading off between its sides.
4. Prefer solutions that increase ideality (more benefit, less cost/harm).
State the contradiction and the principle(s) you used, then give the solution.
```
> Note: this prompt names the method generically. It must **not** contain the gold
> parameters/principles for any specific case.

### 4c. Shared user message (identical for both arms)
```
Solve the following engineering problem. Give a single concrete, physically realizable
solution in roughly 120–180 words. End with one short paragraph explaining why it works.

PROBLEM:
{problem_description}
```
Length band + format here (not in the system prompt) keep verbosity comparable so length bias
is controllable rather than baked into the treatment.

---

## 5. Generation protocol (contamination control)

This section answers the "context contamination from previous sessions" concern directly.

- **Stateless, one call = one (case, arm, model, sample).** Each call is `system + single user
  message` with **no conversation history, no agent memory, no carryover**. Never run generation
  inside an interactive/agentic session that accumulates context.
- **No cross-arm bleed.** Arm A's output is never in context when generating Arm B. They are
  independent requests, ideally interleaved/shuffled in execution order.
- **Determinism & logging.** Fixed `temperature` (0.7 for k>1 sampling; or 0.0 for a k=1
  deterministic pass), fixed `max_tokens`, `seed` when the provider supports it. Log model id,
  params, full request/response, timestamp, and a content hash.
- **Idempotent disk cache.** Key each result by `sha256(model + arm + case_id + sample_idx +
  prompt_version + params)`. Reruns read cache and never re-call → reproducible, and a poisoned/odd
  result can be invalidated surgically.

---

## 6. 2AFC judging protocol

For each **case**, for each **generator model**, pair every TRIZ sample against every control
sample (or a fixed random subset to cap cost). Each pair is judged by **every juror**, in **both
orderings**.

- **Jury, not a single judge.** ≥3 jurors from different model families (§11). Self-preference is
  reduced by (a) requiring `judge_family ≠ generator_family` for the counted votes, and (b) majority
  vote across the panel. Per-juror results are always reported separately.
- **Order-flip consistency.** Present each pair as (A,B) and (B,A). A solution "wins" the pair only
  if it's preferred in **both** orders; split = **tie**. This neutralizes position bias and is the
  unit fed to stats.
- **Forced choice + rubric.** The juror must pick `1` or `2` (ties allowed only via the order-flip
  rule, not as a direct option) and rate on explicit criteria.
- **Stateless judging.** Each comparison is its own fresh call — no history across comparisons.

### Judge prompt (draft)
```
You are evaluating two candidate solutions to an engineering problem. Decide which is the
better solution overall, judging on: (1) does it resolve the core conflict rather than just
trade off, (2) physical feasibility, (3) specificity/actionability, (4) inventiveness.

PROBLEM:
{problem_description}

SOLUTION 1:
{sol_1}

SOLUTION 2:
{sol_2}

Respond as JSON: {"winner": 1 | 2, "scores": {"1": {<criterion>:1-5,...}, "2": {...}},
"reason": "<=40 words"}. You must pick a winner.
```

> **Blinding caveat (per the "keep TRIZ presentation" decision).** Because TRIZ outputs may state
> "the contradiction is… by Principle 24…", jurors can often *tell* which solution is the TRIZ arm.
> The measured effect is therefore the **whole TRIZ package (reasoning + presentation)**, not pure
> substance. This is a valid thing to measure — but report it as such. See Appendix A for the
> optional normalized re-judge that isolates substance.

---

## 7. Bias-control checklist

| Bias | Control in this design |
|---|---|
| Position/order | both orderings; win only if order-consistent; position logged |
| Self-preference | cross-family jury; `judge_family ≠ generator_family` for counted votes; per-juror reporting |
| Length/verbosity | shared length band in user message; post-hoc win~length correlation reported |
| Prompt×model confound | generator model fixed within a comparison; model varied as a separate factor |
| Condition un-blinding | acknowledged (presentation kept); Appendix-A normalized re-judge as robustness |
| Stochastic noise | k samples/arm; variance reported |
| Context contamination | stateless calls, no cross-arm/session bleed, idempotent cache |
| Judge ambiguity | explicit multi-criterion rubric; forced JSON choice |

---

## 8. Metrics & statistics

**Track 2 (primary).**
- Per (case, generator model): TRIZ win rate over order-consistent pairs, jury-majority.
- Aggregate TRIZ win rate with **case-clustered bootstrap** (resample the 10 cases, 10k iters) →
  point estimate + 95% CI. Significance = CI excludes 0.5.
- Report **per-juror** win rates and inter-juror agreement (Fleiss' κ) — a result that only one
  juror likes is fragile.
- **Diagnostics:** position-win rate (should be ~50% after flipping), Spearman(win, length_diff).

**Track 1 (corroborating).**
- Extract principles/parameters each solution actually used (neutral extractor model, stateless),
  map to the 40/39 index. Compute precision/recall/F1 vs gold `principle_index` (+ plus/minus
  factors). Compare arms with a case-paired test (Wilcoxon).

**Reporting unit is the case**, never the individual pairwise comparison — comparisons within a case
are not independent.

---

## 9. Power & limitations

- N=10 is thin. k-sampling + jury + 2 generator models multiplies *comparisons* but **not**
  independent cases; the honest CI comes from the 10-case bootstrap. Expect wide CIs — report effect
  size, don't chase a p-value.
- **Casebase expansion** is the highest-leverage upgrade; the pipeline is written N-agnostic so new
  cases are just more rows. Target ≥30–50 cases for a tight CI.

---

## 10. Pipeline & layout

```
triz-on-vs-off-agent/
  casebase.json
  DESIGN.md
  config.yaml            # models, k, temp, prompt versions, gateway settings
  prompts/
    triz_system.txt  control_system.txt  user_template.txt  judge.txt  extractor.txt
  src/
    generate.py          # case×arm×model×sample -> stateless gateway call -> cache
    judge.py             # build pairs, both orders, jury, stateless -> cache
    extract.py           # Track-1 principle/parameter tagging
    analyze.py           # bootstrap CIs, bias diagnostics, both tracks, tables/plots
  data/
    generations/<hash>.json
    judgments/<hash>.json
  results/
    summary.md  figures/  human_eval.csv   # human_eval.csv = blinded pairs for later human 2AFC
```

**Schemas.**
```jsonc
// generation
{ "hash","case_id","arm","model","sample_idx","prompt_version",
  "params":{"temperature","max_tokens","seed"}, "system","user","output","ts" }
// judgment
{ "hash","case_id","gen_model","pair":{"triz_hash","control_hash"},
  "order":"AB|BA","judge_model","winner_arm","scores","reason","ts" }
```

---

## 11. Model roster (Vercel AI Gateway)

All calls go through the gateway as `"provider/model"` strings — one key, many families, which is
exactly what the cross-family jury needs.

- **Generators (≥2, run full A/B per model):** e.g. `anthropic/claude-sonnet-4-6`,
  `openai/gpt-*`, optionally `google/gemini-*`.
- **Jury (≥3, different families; exclude a juror's own family from counted votes when it matches
  the generator):** one Anthropic, one OpenAI, one Google.
- **Neutral extractor (Track 1):** any one capable model, fixed, temp 0.

Exact ids picked at build time from current gateway availability. Claude ids if used directly:
`claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-fable-5`.

---

## 12. Human evaluation hook (later)

`analyze.py` emits `results/human_eval.csv`: each row = one order-randomized, source-blinded pair
(problem + two solutions, arm labels hidden, mapping stored separately). You rate the same pairs
later; we then compute human–jury agreement (κ) to validate the LLM jury before trusting it at
scale.

---

## Appendix A — Robustness: normalized substance-only re-judge (optional)

Because presentation is kept visible (§6), add a *second* judging pass on **normalized** outputs: a
cheap model rewrites both solutions into one neutral style/format (strip "Principle N", uniform
structure), then the same jury re-judges. Comparing raw vs normalized win rates decomposes any TRIZ
advantage into **substance** (survives normalization) vs **presentation** (disappears). Pure
add-on — no change to the rest of the design.

---

## Open items before coding
1. Confirm generator model set (which 2–3) and jury set from gateway availability.
2. k (3 vs 5) and temperature (0.7 sampled vs 0.0 deterministic baseline).
3. Pairing scheme: all k×k pairs vs a capped random subset (cost).
4. Whether to run Appendix-A normalized pass in v1 or defer.
```
