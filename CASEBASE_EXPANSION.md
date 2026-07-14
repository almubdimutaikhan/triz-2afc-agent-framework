# Expanding the TRIZ case problem list (`casebase.json`)

The master problem list lives at **`casebase.json`** (repo root). It currently
holds 45 cases: 28 textbook cases (`"001"`–`"028"`) and 17 patent-derived cases
(`"P01"`–`"P17"`). A separate, independent set of 84 TrizBench patent cases
lives in `casebase_uspatents.json` — new cases must not duplicate **either**
file. (`casebase_factorial_pilot12.json` and `casebase_pc_mouse.json` are
subsets/one-offs drawn for specific runs — never add cases there.)

Every new case must pass `scripts/validate_casebase.py` before it is used in
a run (see "Validate" below).

## 1. Schema — every case is one object in the `cases` array

```json
{
  "id": "029",
  "problem_description": "One paragraph stating system, conflict, and the ask.",
  "plus_factor_index": [32],
  "minus_factor_index": [30],
  "principle_index": [2, 24],
  "solutions": [
    {
      "content": "The documented/canonical solution, paraphrased.",
      "principle_index": [24]
    }
  ],
  "notes": "Author, Book/Source, page N."
}
```

| Field | Meaning |
|---|---|
| `id` | Unique. Textbook cases continue the numeric series: next free is `"029"`, zero-padded 3 digits. Patent-derived cases continue `"P18"`, `"P19"`, … |
| `problem_description` | The problem as shown to the models. See content rules below. |
| `plus_factor_index` | The improving parameter(s), as indices into Altshuller's 39 engineering parameters. |
| `minus_factor_index` | The worsening parameter(s), same indexing. |
| `principle_index` | The **canonical** inventive principle(s) (1–40) that resolve this case per the source. This field powers the future correct-vs-random-principle experiment — fill it carefully from the source, don't guess. Required for new cases (P01–P17 currently have it empty — a known gap worth back-filling). |
| `solutions` | The documented solution(s), each tagged with the principle(s) it embodies. |
| `notes` | Full source citation (author, title, page / patent number). Required — every case must be traceable. |

## 2. Content rules for `problem_description`

- **Self-contained**: a reader with no context must understand the system, the
  conflict, and what is wanted. No references to figures, "the patent", etc.
- **Length**: 20–130 words; aim for the current median of ~60.
- **No TRIZ vocabulary**: never use "TRIZ", "inventive principle",
  "contradiction" (the word), "ideality", "Altshuller", or a principle name.
  The conflict must be described in plain engineering language ("However, …",
  "but this causes …").
- **No solution leakage**: the description must not hint at the canonical
  solution or its mechanism. If the source problem statement embeds the
  answer, rewrite it to end *before* the solution idea appears.
- **End with the ask**: close by stating the difficulty or the requirement
  plainly (most existing cases end on a statement of the conflict; a closing
  question like "What can we do?" is fine too).
- **Translate/paraphrase, don't copy**: write your own wording even when the
  source is in English (copyright + memorization, see below).

## 3. Anti-duplicate protocol (the important part)

Three distinct kinds of duplication must be checked, in this order:

1. **ID collision** — mechanical; the validator catches it.
2. **Semantic duplicate** — the same underlying physical system *or* the same
   conflict in the same domain as an existing case, even with different
   wording. Examples that count as duplicates of case `001` (stones washed
   from under river-bank reinforcement): any other bank/shore erosion
   problem. Before adding a case, grep both casebases for the key nouns of
   your candidate (`grep -i "erosion" casebase*.json`) and read any hit.
   The validator also flags high word-overlap pairs, but wording can differ
   while the system is the same — the grep + read step is mandatory.
3. **Cluster duplication** — several *near-identical variants* of one problem
   family. Statistics resample whole cases, so clustered cases silently count
   one problem multiple times. (Precedent: a vehicle-classification cluster
   had to be dropped from the patent set.) Rule of thumb: **max 1–2 cases per
   narrow system family**, and prefer spreading new cases across domains we
   don't cover yet (check the spread with
   `python -c "import json; [print(c['id'], c['problem_description'][:70]) for c in json.load(open('casebase.json'))['cases']]"`).

Additionally, watch **memorization risk**: skip the ultra-famous textbook
set-pieces LLMs likely know verbatim with their canonical answers, or flag
them in `notes` (`memorization_risk: high` is the convention used in
`casebase_uspatents.json`).

## 4. Good sources

- TRIZ textbooks with worked case collections (e.g. Orloff *Modern TRIZ* —
  the source of most current cases; Altshuller *And Suddenly the Inventor
  Appeared*; Savransky; Fey & Rivin). Cite page numbers.
- Patents: pick ones with a clear before/after conflict; derive the problem
  from the *background/prior-art* section only, id as `P##`, cite the patent
  number. Check the candidate patent isn't already in
  `casebase_uspatents.json` (search by number).
- Domain diversity targets: the current set skews mechanical/civil; process
  engineering, electronics cooling, packaging, biomedical devices, and
  measurement problems broaden the pool.

## 5. Validate

```bash
uv run python scripts/validate_casebase.py            # checks casebase.json
uv run python scripts/validate_casebase.py --file casebase_uspatents.json
```

The validator enforces: schema completeness, id format & uniqueness, length
bounds, TRIZ-vocabulary leaks, principle/parameter index ranges, and flags
suspiciously similar problem pairs (word-overlap) both within the file and
against the other casebase. Fix every ERROR; read every WARN and either fix
it or consciously accept it.

## 6. Statistical sizing (why expand, how far)

CI width on the headline % scales as ≈ 72.6pp/√n_cases (fitted on our real
judgement data): 45 cases → ±11pp, 90 → ±7.7pp, 200 → ±5.1pp. Detecting a
small (~3pp) TRIZ-specific effect needs ~200+ cases; resolving a ~56% effect
needs ~45–90. Expansion helps only if the new cases are *independent* — which
is exactly what the anti-duplicate protocol protects.
