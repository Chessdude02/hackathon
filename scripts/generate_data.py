#!/usr/bin/env python3
"""Create generated data.

Usage:
    python scripts/generate_data.py --out data/generated --seed 42
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from generator.generate import generate  # noqa: E402
from generator.params import N_CLIENTS_DEFAULT  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/generated")
    ap.add_argument("--truth", default="data/truth")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clients", type=int, default=N_CLIENTS_DEFAULT)
    args = ap.parse_args()
    path = generate(args.seed, args.clients, args.out, args.truth)
    print(f"Wrote {args.out}/ and {path}")


if __name__ == "__main__":
    main()
