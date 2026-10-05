#!/usr/bin/env python3
"""Run the pipeline with no screen.

Usage:
    python scripts/run_pipeline.py --data data/generated --out out/

Uses the suggested column mapping as is. Staff costs come from
<data>/staff_costs.csv if present, else from config.yaml. With
--exclude-suggested, rows the validation step suggests excluding are excluded.
"""
import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from clientprofit import config, pipeline, validate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/generated")
    ap.add_argument("--out", default="out")
    ap.add_argument("--config", default=str(config.DEFAULT_PATH))
    ap.add_argument("--exclude-suggested", action="store_true")
    args = ap.parse_args()

    t0 = time.perf_counter()
    settings = config.load_config(args.config)
    costs_file = Path(args.data) / "staff_costs.csv"
    if costs_file.exists():
        settings["staff_costs"] = {**settings["staff_costs"], **config.read_staff_costs(costs_file)}
    loaded = pipeline.load_files(pipeline.find_files(args.data))
    tables = pipeline.apply_mappings(loaded)
    problems = validate.validate_inputs(tables, settings)
    exclusions = pipeline.suggested_exclusions(problems) if args.exclude_suggested else {}
    result = pipeline.run_pipeline(tables, settings, exclusions)
    total = time.perf_counter() - t0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    validate.summary(result["problems"]).to_csv(out / "problems.csv", index=False)
    if result["stopped"]:
        for p in result["stopped"]:
            print("ERROR:", p["message"], "rows", p["rows"][:10])
        sys.exit("Stopped: fix or exclude the errors above")
    result["client_month"].to_csv(out / "client_month.csv", index=False)
    result["ranked"].to_csv(out / "ranked.csv", index=False)
    result["unranked"].to_csv(out / "unranked.csv", index=False)
    print(f"As of {result['as_of'].date()}: {len(result['ranked'])} ranked, "
          f"{len(result['unranked'])} not enough history, {len(result['problems'])} problems reported, "
          f"rows excluded: {result['excluded'] or 'none'}")
    print(f"Upload to ranked list: {total:.2f} s (pipeline only {result['seconds_to_ranked']:.2f} s)")
    print(result["ranked"][["rank", "client", "profit_last_12m", "revenue_last_12m", "loss_making"]]
          .head(10).to_string(index=False))


if __name__ == "__main__":
    main()
