# Does TRIZ prompting make an LLM more creative?

A controlled study of whether priming a language model with a **TRIZ** (Theory of
Inventive Problem Solving) system prompt produces more creative engineering
solutions than the same model with no special prompt — judged blind by an LLM jury.

**Bottom line:** yes. On a blind, bias-controlled, cross-model jury, TRIZ-prompted
solutions are judged **more creative ~65% of the time** (vs. the 50% no-difference
line), and the effect is statistically significant. It is strongest for solutions
written by Claude and GPT-4o, and reverses for DeepSeek.

![Jury verdict](results/figures/jury_verdict.png)

---

## Insights

- **TRIZ prompting works, on the creativity axis.** Across the trustworthy subset
  of judgements, the TRIZ arm is picked as more creative **65%** of the time
  (95% CI **[52%, 77%]**, clears 50% → significant).
- **It's not just experts who see it.** Even the *naive* (layperson) judges, with
  no idea what TRIZ is, prefer the TRIZ answers (60–64%). The TRIZ-expert persona
  prefers them a little *more* (the persona gap Δ is +2 to +7pp), but the bulk of
  the effect is visible to a general reader — so it isn't an artefact of an
  expert judge rewarding TRIZ-flavoured language.
- **It depends heavily on the model that wrote the solution.** TRIZ clearly lifts
  **Claude (74%)** and **GPT-4o (68%)**, but **hurts DeepSeek (41%)** — DeepSeek's
  TRIZ-prompted answers are judged *less* creative than its un-prompted ones.
- **And on the problem.** Big TRIZ wins on some problems (case 008: 83%, case 010:
  75%), losses on others (case 003: 33%). The headline average hides real
  problem-to-problem variation.
- **No self-flattery.** Models judging their own output (61%) scored it no higher
  than other models' output (60%), so the effect is not a self-preference artefact.

---

## Methodology

### The generation step
Each of **3 models** (`openai/gpt-4o`, `anthropic/claude-sonnet-4.5`,
`deepseek/deepseek-v3.1`) solved **10 engineering problems** twice:

| Arm | System prompt |
|---|---|
| **TRIZ** | a TRIZ-expert system prompt (39 parameters, 40 inventive principles, contradictions, ideality) |
| **control** | no system prompt |

Every generation is a single **stateless** call (no shared history between arms),
temperature 0, results cached on disk by a content hash. Both arms end with a
**`FINAL SOLUTION:`** section written in plain language, with all TRIZ vocabulary
forbidden — so the visible solution is **indistinguishable in format** and carries
no surface tell of which arm produced it. Only that section is shown to judges.
After a quality pass (dropping truncated or jargon-leaking pairs) this yields
**29 clean (problem × model) pairs**, each holding one TRIZ and one control solution.

### The judging step
An **LLM jury** does a blind two-alternative forced choice (2AFC): given a problem
and two solutions A/B, *which is more creative?*

- **6 judges** = 3 models × 2 personas:
  - **expert** — a TRIZ master's inventive lens
  - **naive** — a thoughtful layperson with no methodology
  - (the persona is the *only* thing that changes; the task wording is shared and fixed.)
- **Both orders.** Every pair is judged twice, once with TRIZ as A and once as B,
  so a position-biased judge can't fake a signal.
- **Position-bias controls.** The judge is told explicitly that A/B are random and
  must not be favoured by slot, and is forced to give one sentence of reasoning
  *before* its verdict — which sharply raised order-consistency (from ~30% to
  55–76%) over an earlier letter-only design.
- **3 models × 2 personas × 29 pairs × 2 orders = 348 judgements.** Stateless,
  temperature 0, disk-cached.

### How results are read
- **`p_triz`** = fraction of judgements that pick the TRIZ arm. **50% = no effect.**
- **95% confidence intervals** come from a **case-clustered bootstrap** (resampling
  whole problems, since several pairs share a problem and aren't independent). An
  effect is "significant" when the entire interval sits above 50%.
- The **trustworthy verdict** uses only **cross-family** (a model never judges its
  own output) and **order-consistent** (same pick in both orders) judgements.

All model calls run through a single OpenAI-compatible gateway, at temperature 0
with results cached, so the entire study is deterministic and reproducible.

---

## Results

### Overall verdict
TRIZ is judged more creative **65%** of the time on the trustworthy subset
(cross-family + order-consistent, n=78), CI **[52%, 77%]** — significant.
Pooled over all 348 judgements it's **60.6%**.

### Every judge agrees on the direction
All six judges land above the 50% line; DeepSeek's two and the experts are the
firmest.

![p_triz by judge](results/figures/p_triz_by_judge.png)

### Expert vs naive: the effect survives without TRIZ knowledge
Naive judges (who've never heard of TRIZ) still prefer the TRIZ answers; experts
prefer them slightly more.

![Persona contrast](results/figures/persona_contrast.png)

### It depends on who wrote the solution
TRIZ helps Claude and GPT-4o, but backfires for DeepSeek.

![By generator](results/figures/by_generator.png)

### …and on the problem
Strong heterogeneity across the 10 problems.

![By problem](results/figures/by_case.png)

### Sanity check: no self-preference
A model judging its own output (diagonal) is no more TRIZ-favouring than when it
judges others — the effect isn't models flattering themselves.

![Self-preference](results/figures/self_preference.png)

---

## Limitations

- **Small dataset → wide intervals.** Only 10 problems / 29 pairs. The verdict is
  significant but the confidence interval is broad ([52%, 77%]); more problems
  (30–50) would sharpen it considerably.
- **One axis: creativity.** This measures *creativity/inventiveness*, which is
  TRIZ's stated aim — **not** practical problem-solving quality. An earlier run
  asking "which solves the problem better?" found **no** overall effect (~50%).
  So the claim is specifically about creativity, not general solution quality.
- **Residual position bias.** The reasoning-before-answer fix raised
  order-consistency to 55–76%, but it isn't 100%, and left-pick rates still run a
  little high (53–69%). The both-orders design cancels this in the averages, but
  the judges are imperfect instruments.
- **Judge ≠ human.** This is an LLM jury, not human raters. A parallel human 2AFC
  used a different question ("which is better?"), so the two are not directly
  comparable and human validation of the *creativity* criterion is still open.
- **LLM creativity is fuzzy.** "More creative" is a soft, subjective construct;
  models may equate it with novelty or unusualness. Verdicts were not audited
  against rubric-coded human creativity ratings.
- **Model/version specific.** Results are tied to these three model versions and
  this particular TRIZ system prompt; they may not transfer to other models or
  prompt phrasings — and the DeepSeek reversal shows the effect is genuinely
  model-dependent.
