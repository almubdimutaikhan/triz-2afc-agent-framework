# TRIZ-on vs TRIZ-off — textbook study, v2 (5 generators, CrPO added)

**v2 of [`README.md`](README.md)**: adds **CrPO-Llama-3.1-8B-Instruct-nov**
(`CNCL-Penn-State/CrPO-llama-3.1-8b-instruct-nov`, a locally-run, DPO-tuned-for-novelty
8B model) as a **5th generator** to the 45-case textbook study, alongside the original
4 API models. CrPO's raw generations were structurally and content-validated first
(see [`crpo_report_v2.md`](crpo_report_v2.md): 90/90 pairs passed the quality filter
after one regeneration pass) before being merged in.

**Bottom line — still replicates.** TRIZ-prompted solutions are judged **more creative
68.2% of the time** on the trustworthy subset (95% CI **[62.4, 73.4]**, n=1,841,
significant), with all 5 generators — including the new local 8B model — landing above
the 50% no-effect line.

![Jury verdict](figures/jury_verdict.png)

---

## What changed from v1

- **Generators: 4 -> 5.** Added `cncl-penn-state/crpo-llama-3.1-8b-instruct-nov`,
  run locally (Colab, bf16) rather than through the API gateway, at the same agreed
  params as the rest of this run (**k=2, temperature 0.8**).
- **CrPO is generator-only, not a judge** — per the original design decision, the
  jury (`config.yaml`'s `models:` list) stays the 4 API models. Every judgement of a
  CrPO pair is therefore automatically cross-family.
- **Pairs: 333 -> 423** (+90, all from CrPO — 100% of its candidate pairs, after the
  v2 regeneration fixed 14 that were truncated at the original 768-token cap; see
  `crpo_report_v2.md`).
- **Judgements: 5,229 (v1 usable) -> 6,660 usable** (6,768 total, 108 unparsed —
  consistent with the pre-existing baseline unparsed rate, not newly introduced by
  CrPO).

---

## Results (v2, 5 generators)

### Overall (trustworthy)
**68.2%** TRIZ-preferred, n=1,841, **CI [62.4, 73.4]** — significant.
Pooled over all usable judgements: **62.6%** (n=6,660), CI [58.7, 66.4].

*(v1, 4 generators, for reference: 69.8% CI [63.1, 76.0], n=1,227 trustworthy; 63.5%
pooled. The effect is essentially unchanged — a fifth, much smaller, locally-run model
does not move the headline.)*

### By judge (all 8 significant, both personas)
| Judge | expert | naive |
|---|---|---|
| gpt-4o | 66.5% | 61.2% |
| gemini-2.5-flash | 65.8% | 61.8% |
| claude-sonnet-4.5 | 63.1% | 59.1% |
| deepseek-chat-v3.1 | 63.1% | 60.4% |

Experts prefer TRIZ a little more everywhere (Δ +2.6 to +5.3pp), but naive judges still
clearly prefer it (59-62%).

![p_triz by judge](figures/p_triz_by_judge.png)
![Persona contrast](figures/persona_contrast.png)

### By generator (cross-family) — all 5 above 50%, none reverses
| Generator | p_triz | n |
|---|---|---|
| gemini-2.5-flash | 67.8% | 793 |
| claude-sonnet-4.5 | 67.5% | 1,005 |
| deepseek-v3.1 | 62.3% | 1,417 |
| **crpo-llama-3.1-8b-instruct-nov** | **60.2%** | **1,440** |
| gpt-4o | 53.7% | 1,057 |

CrPO — an 8B, locally-run, non-frontier model — lands comfortably in the middle of
the pack, ahead of GPT-4o on this metric. The TRIZ effect is not exclusive to large
API-hosted models.

![By generator](figures/by_generator.png)

### By problem
Strong case-to-case heterogeneity persists across the 45 problems (case 016: 87.9%;
case 012: 39.7%) — unchanged in character from v1, now measured over more judgements
per case.

![By problem](figures/by_case.png)

### Sanity check: self-preference (report honestly — do not overstate)
Self (diagonal, a model judging its own output): **67.1%** (n=948) vs. cross-family:
**61.9%** (n=5,712) — a **+5.2pp self-preference gap**. This is larger than v1's ~3.3pp
textbook gap. The headline above uses **only cross-family** votes, so this does not
contaminate the reported 68.2% — but it should be stated plainly in any writeup, not
minimized. (CrPO cannot self-prefer, since it is never a judge — the gap comes from
the original 4 API models judging each other and themselves, over a now-larger pool of
generators/pairs.)

![Self-preference](figures/self_preference.png)

### Position sanity
Left-pick rate 41.4-63.6%, order-consistency 58.2-73.2% — slightly wider spread than
v1 (55-76%), still centered near the expected ~50%/high-consistency range. The
both-orders design cancels residual bias in the reported averages regardless.

---

## Comparison across all three tracks

| | Main v1 (4 gen) | **Main v2 (5 gen)** | US patents |
|---|---|---|---|
| Cases | 45 | 45 | 84 |
| Generators | 4 | **5 (+CrPO, local)** | 4 |
| Sampling | k=2, temp 0.8 | k=2, temp 0.8 | k=1, temp 0.0 |
| **Trustworthy p_triz** | 69.8% | **68.2%** | 72.2% |
| 95% CI | [63.1, 76.0] | **[62.4, 73.4]** | [66.2, 77.7] |

The effect replicates a third time — across textbook and patent problems, four
frontier API models, and now one small, locally-hosted, non-frontier model — with no
reversal anywhere.

---

## Limitations (in addition to v1's)

- **CrPO ran under different infrastructure** (local Colab GPU, bf16, not the shared
  API gateway) — a provider/precision difference versus the other 4, similar in kind
  to the main-vs-us_patents provider difference already disclosed.
- **CrPO required one regeneration pass** to reach 100% pair survival (14/90 records
  hit a token cap on the first attempt); see `crpo_report_v2.md` for the full QA trail.
  This is disclosed for transparency, not because it affects the reported numbers —
  only the corrected (v2) records were merged in.
- **Self-preference is now a somewhat larger gap (+5.2pp)** than in v1 (+3.3pp) —
  still excluded from the headline via the cross-family filter, but worth flagging
  explicitly rather than repeating a "no self-preference" claim.
