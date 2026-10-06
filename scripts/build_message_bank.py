#!/usr/bin/env python3
"""Paraphrase the request templates once with the LLM and save them (D-12, D-17).

Usage:
    python scripts/build_message_bank.py [--per-template 7] [--model ...]

Writes generator/message_bank.json. Run once; the file is committed so every
generator run uses the same text. A paraphrase is kept only if it has exactly
the same {item} / {day} slots as its template (D-17 needs {item} to work).
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from clientprofit.llm import LLMError, complete  # noqa: E402
from generator.messages import BANK_PATH, TEMPLATES  # noqa: E402

SYSTEM = (
    "You rewrite short messages that small-business clients send to their marketing agency. "
    "Write each rewrite the way a real, busy client would: vary the wording, length and tone "
    "(polite, curt, chatty, stressed). Keep exactly the same request and the same level of "
    "vagueness: do not make a vague message clearer, and do not add or remove any request. "
    "If the message contains {item} or {day}, keep those placeholders exactly as written, "
    "braces included. Do not add placeholders that are not in the message. "
    "Output one rewrite per line, with no numbering, quotes or extra text."
)
SLOT = re.compile(r"\{(item|day)\}")


def slots(text):
    return sorted(SLOT.findall(text))


def paraphrase(template, n, model):
    reply = complete(f"Message: {template}\n\nWrite {n} different rewrites.", model,
                     system=SYSTEM, max_tokens=60 * n, temperature=0.9)
    keep, dropped = [], []
    for line in reply.splitlines():
        line = re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", line).strip().strip('"').strip()
        if not line:
            continue
        if "{" in line.replace("{item}", "").replace("{day}", "") or slots(line) != slots(template):
            dropped.append(line)
        else:
            keep.append(line)
    return keep[:n], dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-template", type=int, default=7)
    ap.add_argument("--model", default="Qwen/Qwen2.5-14B-Instruct")
    args = ap.parse_args()

    jobs = [(label, t) for label, ts in TEMPLATES.items() for t in ts]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda j: (j, *paraphrase(j[1], args.per_template, args.model)), jobs))

    bank, report = {label: [] for label in TEMPLATES}, {"kept": 0, "dropped": 0, "templates": len(jobs)}
    for (label, template), keep, dropped in results:
        seen = {s.lower() for s in bank[label]}
        bank[label] += [k for k in keep if k.lower() not in seen]
        report["kept"] += len(keep)
        report["dropped"] += len(dropped)
    for label in bank:  # keep the originals too, so every template's meaning stays in the bank
        bank[label] = sorted(set(bank[label]) | set(TEMPLATES[label]))
    BANK_PATH.write_text(json.dumps(bank, indent=1, ensure_ascii=False) + "\n")
    report.update({label: len(v) for label, v in bank.items()})
    print(json.dumps(report, indent=1))
    print(f"Wrote {BANK_PATH.relative_to(REPO)}")


if __name__ == "__main__":
    try:
        main()
    except LLMError as e:
        sys.exit(f"LLM call failed: {e}")
