# CrPO candidate-generator validation — v2 (full 45-case batch)

Validation of `gen_results_20260705_112513.json`: **CrPO-Llama-3.1-8B-Instruct-nov**
(`CNCL-Penn-State/CrPO-llama-3.1-8b-instruct-nov`) run as a candidate 5th generator on
all 45 cases of `casebase.json` (the `main` textbook run), matching the run's agreed
params (**k=2, temperature 0.8**). Supersedes the earlier 3-case spot check.

Generated on a local Colab GPU (bf16, greedy-off/sampled), not yet merged into
`data/main/generations/` or judged. This document is the go/no-go check before that
merge.

---

## 1. Structural integrity — clean

| Check | Result |
|---|---|
| Record count | **180 / 180** (45 cases x 2 arms x k2) |
| Required fields present | all 180 |
| Duplicate hashes | none |
| Case coverage vs `casebase.json` | all 45 present, none missing, none extra |
| (case, mode, sample) combo coverage | all 180 combos present, no duplicates |
| Records with `error` set | 0 |
| Model id consistency | single id throughout |

No structural problems. Every case, arm, and sample slot the pipeline expects is present.

---

## 2. Content quality — comparable to the weaker frontier models, not to the strongest

### `FINAL SOLUTION:` header compliance
The pipeline extracts only the text after this header as the judged answer (jargon-free,
length-capped); a missing header means the fallback is the **entire raw output**,
including internal TRIZ-style reasoning.

| Model | Header found | Missing | Missing rate |
|---|---|---|---|
| deepseek-v3.1 | 180 | 0 | 0.0% |
| gpt-4o | 180 | 0 | 0.0% |
| claude-sonnet-4.5 | 176 | 4 | 2.2% |
| **CrPO (this batch)** | **162** | **18** | **10.0%** |
| gemini-2.5-flash | 160 | 20 | 11.1% |

CrPO's compliance is worse than 3 of the 4 generators already in the study, but **not
an outlier** — it sits just under Gemini-2.5-flash's rate on the same casebase.

### Verbosity (word count of the extracted display text)
Target per `user_template.txt` is **120-180 words**.

| Model | mean | min | max |
|---|---|---|---|
| gpt-4o | 127.8 | 89 | 173 |
| deepseek-v3.1 | 152.9 | 99 | 204 |
| gemini-2.5-flash | 165.1 | 12 | 442 |
| claude-sonnet-4.5 | 182.1 | 0 | 228 |
| **CrPO (this batch)** | **200.6** | **0** | **696** |

CrPO overshoots the target length more than any current generator, and has the widest
spread (some answers 5-6x the target). This is a real property of the model (an 8B
model with weaker length control), not a bug in the harness.

### Specific defects found (18 flagged records)
- **1 genuine empty-answer truncation**: `crpo_P05_control_1` — the model wrote its
  reasoning, then the `FINAL SOLUTION:` header, then **stopped** (hit the 768-token
  cap exactly at the header, zero words follow it).
- **3 genuine mid-sentence truncations** at the 768-token cap (verified by inspecting
  raw output endings): `crpo_027_triz_1`, `crpo_006_control_0`, plus one more in the
  10-truncated-flag list below. These are real cutoffs, not a false-positive from a
  short preview.
- **4 jargon leaks into the visible answer** (all among the header-missing records,
  since without the header the reasoning-with-jargon text becomes the display):
  `crpo_008_triz_0`, `crpo_017_triz_1`, `crpo_027_triz_1`, `crpo_P03_triz_0` — all
  leak the word "contradiction".
- **14 records over 250 words** (up to 696) — verbose but not necessarily broken.

---

## 3. Simulated `build_pairs.py` outcome — 76/90 pairs would survive

Running the exact same jargon / length / truncation filter `scripts/build_pairs.py`
applies, on CrPO's 45 cases x k2 = 90 candidate pairs:

| | pairs formed | clean | dropped | survival rate |
|---|---|---|---|---|
| **CrPO** | 90 | **76** | 14 | **84.4%** |
| *(for comparison)* 4 current generators, pooled, same casebase | 360 | 333 | 27 | 92.5% |
| — claude-sonnet-4.5 | 90 | 86 | 4 | 95.6% |
| — deepseek-v3.1 | 90 | 90 | 0 | 100.0% |
| — gpt-4o | 90 | 90 | 0 | 100.0% |
| — gemini-2.5-flash | 90 | 67 | 23 | 74.4% |

CrPO's survival rate (84.4%) sits **between** the two extremes already accepted into
the study — worse than Claude/DeepSeek/GPT-4o, but noticeably better than
Gemini-2.5-flash's 74.4% on this same casebase. It is not disqualifying by the
standard already in use.

**Dropped pairs (14), with reason:**
```
005 s0:  control:truncated
006 s0:  control:truncated
006 s1:  triz:truncated
008 s0:  triz:jargon(contradiction)
012 s1:  control:truncated
015 s0:  triz:truncated
015 s1:  triz:truncated
017 s1:  triz:jargon(contradiction)
027 s1:  triz:jargon(contradiction), triz:truncated
P02 s1:  triz:truncated
P03 s0:  triz:jargon(contradiction)
P05 s1:  missing arm  (control display is empty — the P05 truncation above)
P13 s0:  control:truncated
P14 s1:  triz:truncated
```

---

## 4. Root cause and recommendation

Most drops (10 of 14) are **truncation at `max_new_tokens=768`**, driven directly by
CrPO's higher verbosity (mean 200.6 words vs. 120-180 target, max 696). The jargon
leaks (4 of 14) are a side effect of the missing-header cases, not an independent
problem.

**Recommendation:** if regenerating, raise `max_new_tokens` to ~1200-1500 for CrPO
specifically (the other 4 generators use `max_tokens: 4000` via the API; CrPO was
capped tighter for the Colab run). This would likely recover most of the 10
truncation-driven drops. Not required to proceed — 76 clean pairs is a usable batch
as-is — but worth doing if a re-run is convenient.

---

## 5. Verdict: usable, generator-only, ready to merge

**76 of 90 CrPO pairs (84.4%) pass the same quality bar already applied to every other
generator in the `main` study.** No structural defects, no case coverage gaps,
comparable (not exceptional) content quality against the weaker end of the current
4-model roster.

Per the earlier design decision, CrPO is added as a **5th generator only** — it does
not join the jury (`config.yaml`'s `models:` list stays the 4 API models; CrPO's
records are dropped straight into `data/main/generations/`, never into `judges:`).

**To merge and pick up the added pairs:**
```bash
python3 - <<'PY'
import json, pathlib
recs = json.loads(open("gen_results_20260705_112513.json").read())
out = pathlib.Path("data/main/generations"); out.mkdir(parents=True, exist_ok=True)
for r in recs:
    (out / f"{r['hash']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
print("wrote", len(recs), "files")
PY

uv run python scripts/build_pairs.py     # -> 333 + 76 = 409 pairs
uv run python src/judge.py --concurrency 10   # only the new CrPO pairs get judged
uv run python src/judge_report.py
uv run python src/judge_charts.py
```
