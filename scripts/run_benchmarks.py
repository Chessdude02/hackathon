#!/usr/bin/env python3
"""Run the benchmarks and write the numbers to a JSON file.

Usage:
    python scripts/run_benchmarks.py --data data/generated --truth data/truth/truth_seed42.json \
        --out out/benchmarks.json [--seeds 1 2]

The only script that reads the generator's truth file (D-08). Benchmarks 2 to 5
run on generated data: they show the code works, not that it is accurate on
real businesses.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from clientprofit import config, ingest, pipeline, validate  # noqa: E402
from clientprofit.features import build_features  # noqa: E402
from clientprofit.forecast.evaluate import evaluate  # noqa: E402
from clientprofit.forecast.registry import get_forecaster  # noqa: E402


def run_on(data):
    """Pipeline with the suggested mapping and suggested exclusions, timed."""
    t0 = time.perf_counter()
    cfg = config.load_config()
    costs = Path(data) / "staff_costs.csv"
    if costs.exists():
        cfg["staff_costs"] = config.read_staff_costs(costs)
    tables = pipeline.apply_mappings(pipeline.load_files(pipeline.find_files(data)))
    result = pipeline.run_pipeline(tables, cfg, pipeline.suggested_exclusions(validate.validate_inputs(tables, cfg)))
    result["seconds_upload_to_ranked"] = time.perf_counter() - t0
    return result


def _demo_labels(result):
    from clientprofit.scope.registry import get_detector, services_by_client
    req = result["tables"].get("requests")
    if req is None:
        return None
    return get_detector("llm", config.load_config()).label_requests(req, services_by_client(result["tables"]))


def bench1():
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_cost_engine.py", "-k", "benchmark1"],
                         cwd=REPO, capture_output=True, text=True)
    return {"passed": run.returncode == 0, "detail": run.stdout.strip().splitlines()[-1]}


def bench2(result, truth):
    """Share of planted loss-making clients found in the bottom 10 (and bottom K) of the ranking,
    against ranking by revenue alone."""
    key = ingest.client_key
    planted = {key(n) for n, c in truth["clients"].items() if c["loss_making"]}
    ranked = result["ranked"]
    by_profit = [key(c) for c in ranked.sort_values("profit_last_12m")["client"]]
    by_revenue = [key(c) for c in ranked.sort_values("revenue_last_12m")["client"]]
    k = len(planted)
    found = lambda order, n: len(planted & set(order[:n]))  # noqa: E731
    return {"planted_loss_making": k, "ranked_clients": len(ranked),
            "bottom10_profit": f"{found(by_profit, 10)}/{min(10, k)}",
            "bottom10_revenue": f"{found(by_revenue, 10)}/{min(10, k)}",
            "bottom10_share_profit": round(found(by_profit, 10) / k, 3),
            "bottom10_share_revenue": round(found(by_revenue, 10) / k, 3),
            "bottomK_profit": f"{found(by_profit, k)}/{k}", "bottomK_revenue": f"{found(by_revenue, k)}/{k}",
            "note": "Bottom 10 can hold at most 10 of K planted clients; bottom K shows the full picture."}


def bench3(result, cfg):
    f = build_features(result, cfg["forecast"]["horizon_months"])
    return evaluate(f, [get_forecaster("baseline"), get_forecaster("lightgbm")],
                    cfg["forecast"]["test_months"], cfg["forecast"]["horizon_months"])


def bench4(result, truth, hand_path):
    """Detectors against the human labels, each with and without the client's services (D-17)."""
    from clientprofit.scope.keyword import KeywordDetector
    from clientprofit.scope.llm_detector import LLMDetector
    from clientprofit.scope.metrics import scores
    from clientprofit.scope.registry import services_by_client

    hand = pd.read_csv(hand_path, keep_default_na=False)
    req = result["tables"]["requests"]
    by_row = req.set_index("_src_row")
    sample = by_row.loc[hand["row"] + 2].reset_index()  # sheet row = 0-based data row; _src_row = row + 2
    assert sample["message"].tolist() == hand["message"].tolist(), "label sheet does not match requests"
    services = services_by_client(result["tables"])
    actual = hand["label"].tolist()
    model = config.load_config()["llm"]["model"]
    out = {"hand_labelled": len(hand), "hand_label_counts": hand["label"].value_counts().to_dict()}
    runs = {"keyword_with_services": (KeywordDetector(), services),
            "keyword_without_services": (KeywordDetector(), {}),
            "llm_with_services": (LLMDetector(model), services),
            "llm_without_services": (LLMDetector(model, use_services=False), services)}
    for name, (detector, svc) in runs.items():
        t0 = time.perf_counter()
        labels = detector.label_requests(sample, svc)
        res = scores([x["label"] for x in labels], actual)
        res["sources"] = pd.Series([x["source"] for x in labels]).value_counts().to_dict()
        res["seconds"] = round(time.perf_counter() - t0, 1)
        out[name] = res
    gen = [truth["request_labels"][r] for r in hand["row"]]
    out["human_vs_generator_agreement"] = scores(gen, actual)["accuracy"]
    out["note"] = ("Sheet holds 50 messages per generator label, so precision is not at real-world shares. "
                   "Messages and services are generated; the generator set labels from the same services the "
                   "detectors see, so part of any gain from services is circular.")
    return out


def bench6(result, labels):
    """Explanations for every ranked client, written fresh (no saved texts), then checked for
    numbers that are not in the facts. Passing texts are saved for the demo."""
    import shutil
    from clientprofit import explain, recommend
    from clientprofit.scope.store import LabelStore

    cfg = config.load_config()
    recs = recommend.recommend_actions(result, cfg, labels)
    totals = result["totals"].set_index("client")
    tmp = Path(tempfile.mkdtemp()) / "explanations.json"
    store = LabelStore(tmp)
    t0 = time.perf_counter()
    rows = []
    for rec in recs.to_dict("records"):
        out = explain.write_explanation(rec, totals.loc[rec["client"]].to_dict(), cfg["llm"]["model"], store=store)
        shown_bad = explain.check_numbers(out["text"], explain.facts_for(rec, totals.loc[rec["client"]].to_dict()))
        rows.append({"source": out["source"], "invented": out["invented"], "error": bool(out.get("error")),
                     "shown_invented": shown_bad})
    seconds = time.perf_counter() - t0
    if tmp.exists():  # keep the passing texts so the demo does not wait for them
        saved = LabelStore(explain.EXPLANATIONS_PATH)
        for k, v in LabelStore(tmp)._data.items():
            saved.put(k, v)
        saved.save()
        shutil.rmtree(tmp.parent, ignore_errors=True)
    llm_texts = [r for r in rows if not r["error"]]
    return {"clients": len(rows),
            "llm_texts_written": len(llm_texts),
            "llm_texts_with_invented_numbers": sum(bool(r["invented"]) for r in llm_texts),
            "invented_numbers_caught": sum(len(r["invented"]) for r in llm_texts),
            "examples_caught": [r["invented"] for r in llm_texts if r["invented"]][:5],
            "provider_errors": sum(r["error"] for r in rows),
            "shown_texts_with_invented_numbers": sum(bool(r["shown_invented"]) for r in rows),
            "seconds": round(seconds, 1),
            "note": ("Target: zero invented numbers in shown texts. A text with an invented number is replaced by "
                     "a template built from the same facts. The check cannot tell whether a correct number is "
                     "described correctly, and does not catch numbers written as words.")}


def bench5(data, truth):
    total = correct = 0
    for style, maps in truth["header_mappings"].items():
        if "main" in style:
            continue
        for table, expected in maps.items():
            headers = list(pd.read_csv(Path(data) / "header_variants" / style / f"{table}.csv", nrows=0).columns)
            got = ingest.propose_mapping(headers, table)
            total += len(headers)
            correct += sum(got[h] == expected.get(h) for h in headers)
    return {"files": 10, "headers": total, "correct": correct, "accuracy": round(correct / total, 3),
            "mapper": "rule-based (ingest.propose_mapping)",
            "note": "Circular: the header styles and the word list were written by the same person."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/generated")
    ap.add_argument("--truth", default="data/truth/truth_seed42.json")
    ap.add_argument("--out", default="out/benchmarks.json")
    ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2], help="extra generated seeds for benchmarks 2-3")
    ap.add_argument("--hand-labels", default="labelling/label_sheet_seed42_labeled.csv")
    args = ap.parse_args()

    cfg = config.load_config()
    truth = json.loads(Path(args.truth).read_text())
    result = run_on(args.data)
    out = {"generated_data_note": "Benchmarks 2, 3 and 5 run on generated data: they show the code works, "
                                  "not that it is accurate on real businesses.",
           "1_cost_engine_vs_hand_calculation": bench1(),
           "2_ranking": {f"seed {truth['seed']}": bench2(result, truth)},
           "3_forecast_mae": {f"seed {truth['seed']}": bench3(result, cfg)},
           "4_scope_detector": (bench4(result, truth, args.hand_labels) if Path(args.hand_labels).exists()
                                else "Pending: needs the 150 hand labels."),
           "5_column_mapping": bench5(args.data, truth),
           "6_invented_numbers": bench6(result, _demo_labels(result)),
           "7_speed": {"clients": len(result["totals"]),
                       "seconds_upload_to_ranked": round(result["seconds_upload_to_ranked"], 2),
                       "note": "Command-line load, map, validate, rank. Request labelling is timed separately (D-15)."}}
    if args.seeds:
        from generator.generate import generate
        for seed in args.seeds:
            d = Path(tempfile.mkdtemp())
            t = json.loads(generate(seed, 50, d / "data", d / "truth").read_text())
            r = run_on(d / "data")
            out["2_ranking"][f"seed {seed}"] = bench2(r, t)
            out["3_forecast_mae"][f"seed {seed}"] = bench3(r, cfg)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
