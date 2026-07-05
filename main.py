#!/usr/bin/env python3
"""
Run the whole TRIZ-on vs TRIZ-off pipeline end to end, using the current
config.yaml. Each stage caches to disk, so re-running is cheap and idempotent.

  generate  ->  build pairs  ->  judge  ->  report  ->  charts

Usage:
  python main.py                 # run every stage
  python main.py --from judge    # resume from a given stage
  python main.py --only generate # run a single stage
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

STAGES = [
    ("generate", [PY, "src/generate.py"]),
    ("pairs", [PY, "scripts/build_pairs.py"]),
    ("judge", [PY, "src/judge.py"]),
    ("report", [PY, "src/judge_report.py"]),
    ("charts", [PY, "src/judge_charts.py"]),
]


def main():
    names = [n for n, _ in STAGES]
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", choices=names, help="start at this stage")
    ap.add_argument("--only", choices=names, help="run only this stage")
    args = ap.parse_args()

    if args.only:
        todo = [s for s in STAGES if s[0] == args.only]
    elif args.start:
        i = names.index(args.start)
        todo = STAGES[i:]
    else:
        todo = STAGES

    for name, cmd in todo:
        print(f"\n=== {name} ===", flush=True)
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            sys.exit(f"stage '{name}' failed (exit {r.returncode})")


if __name__ == "__main__":
    main()
