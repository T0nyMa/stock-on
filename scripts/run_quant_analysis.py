#!/usr/bin/env python3
"""Generate deterministic Quantitative Analysis V2 artifacts from local JSON."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.quant.pipeline import run_repository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", dest="as_of")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(run_repository(args.root, args.as_of), ensure_ascii=False))


if __name__ == "__main__":
    main()
