#!/usr/bin/env python3
"""Label request messages and save the labels (D-15). Also times labelling N new messages.

Usage:
    python scripts/label_requests.py --data data/generated [--limit N] [--detector llm|keyword]
        [--no-services] [--store labels/saved_labels.json] [--out out/request_labels.csv]
"""
import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from clientprofit import config, ingest, pipeline  # noqa: E402
from clientprofit.scope.registry import get_detector, services_by_client  # noqa: E402
from clientprofit.scope.store import DEFAULT_PATH, LabelStore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/generated")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--detector", default="llm")
    ap.add_argument("--no-services", action="store_true")
    ap.add_argument("--store", default=str(DEFAULT_PATH))
    ap.add_argument("--out", default="out/request_labels.csv")
    args = ap.parse_args()

    cfg = config.load_config()
    tables, _ = ingest.unify_client_names(pipeline.apply_mappings(pipeline.load_files(pipeline.find_files(args.data))))
    requests = tables["requests"]
    if args.limit:
        requests = requests.head(args.limit)
    kwargs = {"store": LabelStore(args.store), "use_services": not args.no_services} if args.detector == "llm" else {}
    detector = get_detector(args.detector, cfg, **kwargs)
    t0 = time.perf_counter()
    labels = detector.label_requests(requests, services_by_client(tables),
                                     progress=lambda d, n: print(f"\r  labelled {d}/{n} new", end="", flush=True))
    seconds = time.perf_counter() - t0
    print()
    out = requests[["_src_row", "client", "message"]].copy()
    out["label"] = [x["label"] for x in labels]
    out["source"] = [x["source"] for x in labels]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(out["source"].value_counts().to_dict(), out["label"].value_counts().to_dict())
    print(f"{len(out)} requests in {seconds:.1f} s")


if __name__ == "__main__":
    main()
