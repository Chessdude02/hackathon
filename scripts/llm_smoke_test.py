#!/usr/bin/env python3
"""Time one LLM model on 20 request messages before building on it (D-14).

Usage:
    python scripts/llm_smoke_test.py --list-models
    python scripts/llm_smoke_test.py --model <model id>

Reads messages from data/generated/label_sheet.csv (no labels in that file),
so this script never sees the generator's truth. Writes timings and the
model's labels to out/llm_smoke_<model>.json for a person to check by eye.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from clientprofit.llm import LLMError, complete, list_models  # noqa: E402

LABELS = ("in_scope", "extra_unpaid", "unclear")
SYSTEM = (
    "You label messages that clients send to a marketing agency. Reply with exactly one word:\n"
    "in_scope - routine work the client already pays for (approvals, edits to agreed work, scheduling)\n"
    "extra_unpaid - a new deliverable or work beyond the agreed plan\n"
    "unclear - cannot tell without more detail"
)
EXAMPLES = (
    "Message: Please schedule the newsletter for Friday as planned.\nLabel: in_scope\n\n"
    "Message: Can you also design a flyer for our charity event? Should be quick.\nLabel: extra_unpaid\n\n"
    "Message: Can we make the homepage pop more?\nLabel: unclear\n\n"
)


def parse_label(text):
    t = text.strip().lower()
    hits = [lbl for lbl in LABELS if lbl in t]
    return hits[0] if len(hits) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="featherless")
    ap.add_argument("--model")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--sheet", default="data/generated/label_sheet.csv")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.list_models:
        print("\n".join(list_models(args.provider)))
        return
    if not args.model:
        sys.exit("Give --model, or run with --list-models first")

    sheet = pd.read_csv(REPO / args.sheet)
    sample = sheet.sample(n=args.n, random_state=args.seed)
    rows = []
    for row in sample.itertuples():
        start = time.perf_counter()
        try:
            reply = complete(EXAMPLES + f"Message: {row.message}\nLabel:", args.model,
                             args.provider, system=SYSTEM, max_tokens=10)
            error = None
        except LLMError as e:
            reply, error = None, str(e)
        seconds = time.perf_counter() - start
        rows.append({"row": int(row.row), "message": row.message, "reply": reply,
                     "label": parse_label(reply) if reply else None,
                     "seconds": round(seconds, 2), "error": error})
        print(f"{seconds:6.2f}s  {rows[-1]['label'] or 'FAILED':13} {row.message[:70]}")

    ok = [r["seconds"] for r in rows if r["error"] is None]
    summary = {
        "provider": args.provider, "model": args.model, "calls": len(rows),
        "errors": sum(r["error"] is not None for r in rows),
        "unparsed_replies": sum(r["error"] is None and r["label"] is None for r in rows),
        "median_seconds": round(statistics.median(ok), 2) if ok else None,
        "max_seconds": round(max(ok), 2) if ok else None,
        "total_seconds": round(sum(r["seconds"] for r in rows), 1),
        "label_counts": {lbl: sum(r["label"] == lbl for r in rows) for lbl in LABELS},
    }
    if ok:
        summary["minutes_for_3000_one_by_one"] = round(statistics.median(ok) * 3000 / 60, 1)
    out = REPO / "out" / f"llm_smoke_{args.model.replace('/', '_')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "calls": rows}, indent=1))
    print(json.dumps(summary, indent=1))
    print(f"Wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
