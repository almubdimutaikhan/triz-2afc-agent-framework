#!/usr/bin/env python3
"""
Generate solutions to a casebase under either:
  - the legacy 2-mode design (triz / control), via config.yaml's `modes:` key, or
  - a generalized N-named-condition design, via config.yaml's `conditions:` key
    (e.g. the factorial run: P_L_TRIZ_ON, P_L_TRIZ_OFF, P_S_TRIZ_ON, P_S_TRIZ_OFF),
    with one system-prompt file per condition at prompts/<run>/<condition>.txt.

Every call is a single STATELESS request (system + one user message) through the
Vercel AI Gateway. No conversation history, no cross-call/cross-arm context.
Results are cached on disk by a content hash, so reruns never re-call the API.

Usage:
  export AI_GATEWAY_API_KEY=...
  python src/generate.py --list-models          # discover valid model ids
  python src/generate.py                         # run with config.yaml
  python src/generate.py --models anthropic/claude-sonnet-4.5 --limit 2
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
GEN_DIR = ROOT / "data" / "generations"      # overridden per-run in main()
RESULTS = ROOT / "results"                    # overridden per-run in main()
CASEBASE = ROOT / "casebase.json"             # overridden per-run in main()


def load_text(name: str) -> str:
    return (PROMPTS / name).read_text()


# Matches the "FINAL SOLUTION:" header on its own line, tolerating markdown
# heading (#) and bold (*) prefixes — e.g. "# FINAL SOLUTION:", "**FINAL SOLUTION**".
_FINAL_HEADER = re.compile(r"^[ \t#*>]*final\s+solution[ \t#*]*:?[ \t]*", re.IGNORECASE | re.MULTILINE)


def extract_solution(text):
    """Return only the FINAL SOLUTION section — the solution-only text raters see
    in the 2AFC game. Applies to BOTH arms (identical format), so the displayed
    solutions are indistinguishable while the full REASONING is still stored.
    Falls back to the full text if the header is absent."""
    if not text:
        return text
    m = _FINAL_HEADER.search(text)
    if not m:
        return text
    sol = text[m.end():]
    sol = re.sub(r"^[\s:*#>\-]+", "", sol)  # strip residual markdown/punctuation
    return sol.strip()


def prompt_version(paths) -> str:
    """Hash of the given prompt files so edits invalidate the cache."""
    h = hashlib.sha256()
    for p in sorted(paths, key=str):
        h.update(Path(p).read_bytes())
    return h.hexdigest()[:12]


def load_condition_prompts(run: str, conditions) -> dict:
    """Load one system-prompt file per named condition from prompts/<run>/<condition>.txt
    (the generalized N-condition path, e.g. the factorial run's P_L_TRIZ_ON etc.)."""
    d = PROMPTS / run
    return {c: (d / f"{c}.txt").read_text().strip() for c in conditions}


def api_key() -> str:
    # Search order: OpenRouter first, then Vercel gateway. Checked in env, then .env.
    names = ["AI_OPENROUTER_API_KEY", "OPENROUTER_API_KEY",
             "AI_GATEWAY_API_KEY", "VERCEL_AI_GATEWAY_API_KEY"]
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    envf = ROOT / ".env"
    if envf.exists():
        kv = {}
        for line in envf.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                kv[k.strip().upper()] = v.strip().strip('"').strip("'")
        for n in names:
            if kv.get(n):
                return kv[n]
    sys.exit(
        "ERROR: no API key found. Put AI_OPENROUTER_API_KEY=... (or AI_GATEWAY_API_KEY=...) "
        "in a .env file or the environment."
    )


def list_models(base_url: str):
    r = requests.get(f"{base_url}/models", headers={"Authorization": f"Bearer {api_key()}"}, timeout=60)
    r.raise_for_status()
    ids = sorted(m["id"] for m in r.json().get("data", []))
    print(f"{len(ids)} models available via gateway:\n")
    for i in ids:
        print(" ", i)


def cache_key(model, mode, case_id, sample_idx, pv, params) -> str:
    blob = json.dumps(
        {"model": model, "mode": mode, "case_id": case_id, "sample": sample_idx,
         "prompt_version": pv, "params": params},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def call_gateway(base_url, model, system, user, params):
    messages = []
    if system:  # control mode has an empty system prompt -> omit it
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    payload = {"model": model, "messages": messages,
               "temperature": params["temperature"], "max_tokens": params["max_tokens"]}
    last = None
    for attempt in range(4):
        try:
            r = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
                json=payload, timeout=180,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"], None
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            if r.status_code in (429, 500, 502, 503, 529):
                time.sleep(2 ** attempt)
                continue
            return None, last
        except requests.RequestException as e:
            last = str(e)
            time.sleep(2 ** attempt)
    return None, last


def run_one(base_url, case, model, mode, sample_idx, params, pv, sys_prompts, user_tpl):
    key = cache_key(model, mode, case["id"], sample_idx, pv, params)
    out_path = GEN_DIR / f"{key}.json"
    if out_path.exists():
        rec = json.loads(out_path.read_text())
        rec["_cached"] = True
        return rec

    system = sys_prompts[mode]
    user = user_tpl.format(problem_description=case["problem_description"])
    content, err = call_gateway(base_url, model, system, user, params)
    rec = {
        "hash": key, "case_id": case["id"], "mode": mode, "model": model,
        "sample_idx": sample_idx, "prompt_version": pv, "params": params,
        "system": system, "user": user, "output": content,
        "display": extract_solution(content),  # solution-only text for raters (both arms)
        "error": err,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    rec["_cached"] = False
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--models", nargs="*", help="override config model list")
    ap.add_argument("--limit", type=int, help="override: only first N cases")
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    base_url = cfg["gateway_base_url"].rstrip("/")

    if args.list_models:
        list_models(base_url)
        return

    # Per-run path isolation: data/<run>/generations, results/<run>, casebase from config.
    global GEN_DIR, RESULTS, CASEBASE
    run = cfg.get("run", "main")
    GEN_DIR = ROOT / "data" / run / "generations"
    RESULTS = ROOT / "results" / run
    CASEBASE = ROOT / cfg.get("casebase", "casebase.json")
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    print(f"run='{run}'  casebase={CASEBASE.name}  -> {GEN_DIR}")

    models = args.models or cfg["models"]
    k = cfg.get("k", 1)
    limit = args.limit if args.limit is not None else cfg.get("limit")
    params = {
        "temperature": args.temperature if args.temperature is not None else cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }
    user_tpl = load_text("user_template.txt")

    # Generalized N-named-condition path (e.g. factorial: P_L_TRIZ_ON/OFF, P_S_TRIZ_ON/OFF)
    # vs. the legacy 2-mode path (triz/control) used by main and us_patents.
    conditions = cfg.get("conditions")
    if conditions:
        # The prompt template SET (e.g. "factorial") is independent of which specific
        # run/casebase is active (e.g. "factorial_pilot12", a 12-case subset) — default
        # to the run name for convenience, but let config.yaml override with `prompt_dir:`.
        prompt_dir = cfg.get("prompt_dir", run)
        modes = conditions
        sys_prompts = load_condition_prompts(prompt_dir, conditions)
        prompt_paths = [PROMPTS / prompt_dir / f"{c}.txt" for c in conditions] + [PROMPTS / "user_template.txt"]
    else:
        modes = cfg["modes"]
        sys_prompts = {
            "triz": load_text("triz_system.txt").strip(),
            "control": load_text("control_system.txt").strip(),
        }
        prompt_paths = [PROMPTS / "triz_system.txt", PROMPTS / "control_system.txt", PROMPTS / "user_template.txt"]
    pv = prompt_version(prompt_paths)

    cases = json.loads(CASEBASE.read_text())["cases"]
    if limit:
        cases = cases[:limit]

    jobs = [(c, m, mode, s)
            for c in cases for m in models for mode in modes for s in range(k)]
    print(f"{len(jobs)} generations: {len(cases)} cases x {len(models)} models "
          f"x {len(modes)} modes x k={k}  (prompt_version={pv})")

    records = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, base_url, c, m, mode, s, params, pv,
                          sys_prompts, user_tpl): (c["id"], m, mode, s)
                for (c, m, mode, s) in jobs}
        for fut in cf.as_completed(futs):
            cid, m, mode, _ = futs[fut]
            rec = fut.result()
            records.append(rec)
            tag = "cache" if rec.get("_cached") else ("ERR " if rec.get("error") else "new ")
            print(f"  [{tag}] case {cid}  {mode:7s}  {m}" + (f"  !! {rec['error']}" if rec.get("error") else ""))

    write_outputs(records)
    try:
        import report
        html = report.build()
    except Exception as e:  # report is best-effort; never fail the run
        html = f"(skipped: {e})"
    n_err = sum(1 for r in records if r.get("error"))
    print(f"\nDone. {len(records)} records, {n_err} errors.")
    print(f"  report  -> {html}   <-- open this in a browser")
    print(f"  csv     -> {RESULTS/'generations.csv'}")
    print(f"  md      -> {RESULTS/'summary_table.md'}, {RESULTS/'solutions.md'}")


def write_outputs(records):
    import csv
    RESULTS.mkdir(parents=True, exist_ok=True)
    records = sorted(records, key=lambda r: (r["case_id"], r["model"], r["mode"], r["sample_idx"]))

    def wc(t):
        return len((t or "").split())

    # CSV (full)
    with (RESULTS / "generations.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "model", "mode", "sample_idx", "words", "error", "solution"])
        for r in records:
            w.writerow([r["case_id"], r["model"], r["mode"], r["sample_idx"],
                        wc(r["output"]), r.get("error") or "", (r["output"] or "").replace("\n", " ")])

    # Markdown summary table (truncated)
    lines = ["# Generation summary", "",
             f"{len(records)} solutions. Cols: case / model / mode / word count / preview.", "",
             "| case | model | mode | words | solution (preview) |",
             "|---|---|---|---:|---|"]
    for r in records:
        prev = (r["output"] or r.get("error") or "").replace("\n", " ").replace("|", "\\|")
        if len(prev) > 160:
            prev = prev[:160] + "…"
        lines.append(f"| {r['case_id']} | {r['model']} | {r['mode']} | {wc(r['output'])} | {prev} |")
    (RESULTS / "summary_table.md").write_text("\n".join(lines))

    # Full solutions, grouped by case with triz/control side by side per model
    out = ["# Full solutions", ""]
    by_case = {}
    for r in records:
        by_case.setdefault(r["case_id"], []).append(r)
    cases = {c["id"]: c for c in json.loads(CASEBASE.read_text())["cases"]}
    for cid in sorted(by_case):
        out.append(f"## Case {cid}")
        out.append(f"> {cases[cid]['problem_description']}")
        out.append("")
        for r in sorted(by_case[cid], key=lambda x: (x["model"], x["mode"])):
            out.append(f"### {r['model']} — `{r['mode']}`")
            out.append(r["output"] or f"_ERROR: {r.get('error')}_")
            out.append("")
    (RESULTS / "solutions.md").write_text("\n".join(out))


if __name__ == "__main__":
    main()
