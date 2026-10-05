"""Runs every stage in order. The only function app.py and the scripts call.

Built so far: load and map files, unify client names, validate, exclude the
rows the owner chose, cost engine, ranking. The ranked list never waits for
request labels (D-15). Later stages (scope, features, forecast, recommend,
explain) are added here as they are built.
"""
import time
from pathlib import Path

from clientprofit import cost_engine, ingest, validate

TABLE_FILES = ("invoices", "time_entries", "requests", "clients")


def load_files(paths):
    """Read raw files and propose a mapping for each. paths: {table: path}."""
    out = {}
    for table, path in paths.items():
        raw = ingest.read_raw(path)
        out[table] = {"raw": raw, "src_file": Path(path).name,
                      "mapping": ingest.propose_mapping(raw.columns, table)}
    return out


def find_files(folder):
    """{table: path} for the input files present in a folder."""
    folder = Path(folder)
    return {t: folder / f"{t}.csv" for t in TABLE_FILES if (folder / f"{t}.csv").exists()}


def apply_mappings(loaded):
    """Type each file with its (confirmed) mapping. Raises if a required column is unmapped."""
    tables = {}
    for table, item in loaded.items():
        missing = ingest.missing_required(item["mapping"], table)
        if missing:
            raise ValueError(f"{item['src_file']}: map a column to {', '.join(missing)}")
        tables[table] = ingest.apply_mapping(item["raw"], item["mapping"], table, item["src_file"])
    return tables


def run_pipeline(tables, settings, exclusions=None):
    """Return a results dict. If errors remain after exclusions, stop before the cost engine."""
    t0 = time.perf_counter()
    tables, merged = ingest.unify_client_names(tables)
    problems = validate.validate_inputs(tables, settings, merged)
    tables = validate.exclude_rows(tables, exclusions or {})
    remaining = validate.validate_inputs(tables, settings, merged)
    result = {"tables": tables, "problems": problems, "merged_names": merged,
              "excluded": {t: len(r) for t, r in (exclusions or {}).items() if r}}
    if validate.has_errors(remaining):
        result["stopped"] = [p for p in remaining if p["severity"] == validate.ERROR]
        result["seconds_to_ranked"] = time.perf_counter() - t0
        return result
    cm, inv, te, as_of = cost_engine.compute_client_month_profit(
        tables["invoices"], tables["time_entries"], settings, tables.get("requests"))
    totals = cost_engine.compute_client_totals(cm, inv, settings, as_of)
    ranked, unranked = cost_engine.rank_clients(totals)
    result.update({"client_month": cm, "invoices_costed": inv, "time_costed": te, "as_of": as_of,
                   "totals": totals, "ranked": ranked, "unranked": unranked, "stopped": None,
                   "seconds_to_ranked": time.perf_counter() - t0})
    return result


def suggested_exclusions(problems):
    """{table: rows} for every problem marked suggest_exclude."""
    out = {}
    for p in problems:
        if p["suggest_exclude"] and p["rows"]:
            out.setdefault(p["table"], []).extend(p["rows"])
    return out
