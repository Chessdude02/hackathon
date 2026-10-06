"""Column mapping, client-name cleaning and validation."""
import json

import pandas as pd
import pytest

from clientprofit import ingest, validate
from clientprofit.schema import SRC_ROW
from generator.generate import generate


def typed(table, rows, columns):
    return ingest.coerce_types(pd.DataFrame(rows, columns=columns).astype(str).replace("None", ""), table, "x.csv")


INV_COLS = ["client", "invoice_date", "amount", "due_date", "paid_date"]
TE_COLS = ["client", "staff", "work_date", "hours", "billable"]


# ---- Mapping ----

def test_mapping_handles_units_case_and_punctuation():
    m = ingest.propose_mapping(["Invoice Date (YYYY-MM-DD)", "AMT", "Customer:Job", "Paid at"], "invoices")
    assert m == {"Invoice Date (YYYY-MM-DD)": "invoice_date", "AMT": "amount",
                 "Customer:Job": "client", "Paid at": "paid_date"}


def test_unknown_header_is_left_for_the_owner():
    assert ingest.propose_mapping(["Colour"], "invoices") == {"Colour": None}


def test_each_schema_column_is_used_once():
    m = ingest.propose_mapping(["Client", "Customer"], "invoices")
    assert sorted(v for v in m.values() if v) == ["client"]


def test_missing_required_columns_are_listed():
    m = ingest.propose_mapping(["Client", "Amount"], "invoices")
    assert ingest.missing_required(m, "invoices") == ["invoice_date", "paid_date"]


def test_blank_text_counts_as_empty():
    te = typed("time_entries", [("A", "Ana", "2026-01-01", "1", "TRUE")], TE_COLS)
    assert te.loc[0, "task_type"] is None


def test_billable_words_are_read():
    rows = [("A", "Ana", "2026-01-01", "1", v) for v in ("Y", "no", "Billable", "Not Billable", "maybe")]
    assert typed("time_entries", rows, TE_COLS)["billable"].tolist() == [True, False, True, False, None]


# ---- Client names ----

@pytest.mark.parametrize("a,b", [("Acme Ltd", "ACME"), ("Acme  Co", "acme"), ("Acme Inc.", "Acme "),
                                 ("Acme LLC", "Acme Limited")])
def test_client_key_matches_common_variants(a, b):
    assert ingest.client_key(a) == ingest.client_key(b)


def test_different_clients_stay_apart():
    assert ingest.client_key("Acme Foods") != ingest.client_key("Acme Fitness")


def test_unify_uses_most_common_spelling_and_keeps_original():
    inv = typed("invoices", [("Acme Ltd", "2026-01-01", "1", None, None)] * 2 +
                [("ACME LTD", "2026-02-01", "1", None, None)], INV_COLS)
    tables, merged = ingest.unify_client_names({"invoices": inv})
    assert set(tables["invoices"]["client"]) == {"Acme Ltd"}
    assert tables["invoices"]["client_original"].tolist()[-1] == "ACME LTD"
    assert merged == {"Acme Ltd": ["ACME LTD", "Acme Ltd"]}


# ---- Validation ----

def checks(problems):
    return {p["check"]: p for p in problems}


def test_unpaid_invoice_is_not_an_error():
    inv = typed("invoices", [("A", "2026-01-01", "100", None, None)], INV_COLS)
    assert not validate.has_errors(validate.validate_inputs({"invoices": inv}))


def test_unreadable_amount_is_an_error_with_row():
    inv = typed("invoices", [("A", "2026-01-01", "abc", None, None)], INV_COLS)
    p = checks(validate.validate_inputs({"invoices": inv}))["empty_or_unreadable"]
    assert p["severity"] == "error" and p["rows"] == [2]


def test_negative_hours_are_a_warning_and_kept():
    te = typed("time_entries", [("A", "Ana", "2026-01-01", "-2", "TRUE")], TE_COLS)
    tables = {"time_entries": te}
    p = checks(validate.validate_inputs(tables))["negative_or_zero_hours"]
    assert p["severity"] == "warning" and p["rows"] == [2] and len(tables["time_entries"]) == 1


def test_duplicate_invoice_suggests_exclusion_but_duplicate_time_does_not():
    inv = typed("invoices", [("A", "2026-01-01", "100", None, None)] * 2, INV_COLS)
    te = typed("time_entries", [("A", "Ana", "2026-01-01", "1", "TRUE")] * 2, TE_COLS)
    dups = [p for p in validate.validate_inputs({"invoices": inv, "time_entries": te})
            if p["check"] == "duplicate_rows"]
    by_table = {p["table"]: p for p in dups}
    assert by_table["invoices"]["suggest_exclude"] and by_table["invoices"]["rows"] == [3]
    assert not by_table["time_entries"]["suggest_exclude"]


def test_hours_without_invoices_and_month_gap_are_reported():
    inv = typed("invoices", [("A", "2026-01-01", "1", None, None), ("A", "2026-03-01", "1", None, None)], INV_COLS)
    te = typed("time_entries", [("A", "Ana", "2026-02-05", "1", "TRUE"), ("B", "Ana", "2026-02-05", "1", "TRUE")],
               TE_COLS)
    found = checks(validate.validate_inputs({"invoices": inv, "time_entries": te}))
    assert "'B'" in found["hours_but_no_invoices"]["message"]
    assert "2026-02" in found["month_without_invoice"]["message"]


def test_staff_without_cost_is_an_error():
    te = typed("time_entries", [("A", "Zed", "2026-01-01", "1", "TRUE")], TE_COLS)
    p = checks(validate.validate_inputs({"time_entries": te}, {"staff_costs": {"Ana": 50}}))["staff_without_cost"]
    assert p["severity"] == "error"


def test_exclude_rows_removes_only_chosen_rows():
    te = typed("time_entries", [("A", "Ana", "2026-01-01", h, "TRUE") for h in ("1", "2", "3")], TE_COLS)
    out = validate.exclude_rows({"time_entries": te}, {"time_entries": [3]})
    assert out["time_entries"][SRC_ROW].tolist() == [2, 4] and len(te) == 3


# ---- On generated data: are the planted problems found? ----

def test_planted_problems_are_found(tmp_path):
    truth = json.loads(generate(7, 45, tmp_path / "d", tmp_path / "t").read_text())
    tables = {}
    for t in ("invoices", "time_entries", "requests"):
        raw = ingest.read_raw(tmp_path / "d" / f"{t}.csv")
        tables[t] = ingest.apply_mapping(raw, ingest.propose_mapping(raw.columns, t), t, f"{t}.csv")
    tables, merged = ingest.unify_client_names(tables)
    problems = validate.validate_inputs(tables, None, merged)
    found = {}
    for p in problems:
        found.setdefault((p["check"], p["table"]), []).append(p)
    planted = pd.DataFrame(truth["defects"])
    assert len(found[("negative_or_zero_hours", "time_entries")][0]["rows"]) == (planted.type == "negative_hours").sum()
    assert len(found[("duplicate_rows", "invoices")][0]["rows"]) >= ((planted.type == "duplicate_row") &
                                                                     (planted.table == "invoices")).sum()
    # Every planted spelling ends up as one client name (a trailing space is
    # already trimmed on load, so it needs no merge).
    for v in planted[planted.type == "name_variant"].itertuples():
        names = set()
        for df in tables.values():
            names |= set(df.loc[df["client_original"].isin([v.client, v.variant.strip()]), "client"])
        assert len(names) == 1, (v.client, v.variant, names)
    assert ("hours_but_no_invoices", "time_entries") in found


def test_pipeline_runs_without_requests(tmp_path):
    """Requests are optional: invoices and time entries alone give a ranked list."""
    from clientprofit import pipeline
    generate(7, 45, tmp_path / "d", tmp_path / "t")
    paths = pipeline.find_files(tmp_path / "d")
    paths.pop("requests")
    paths.pop("clients")
    tables = pipeline.apply_mappings(pipeline.load_files(paths))
    costs = pd.read_csv(tmp_path / "d" / "staff_costs.csv")
    settings = {"staff_costs": dict(zip(costs.staff, costs.hourly_cost)), "overhead_multiplier": 1.3,
                "late_payment_annual_rate": 0.08, "payment_terms_days": 30, "unpaid_warning_days": 90,
                "min_months_for_ranking": 3}
    result = pipeline.run_pipeline(tables, settings)
    assert result["stopped"] is None and len(result["ranked"]) > 30
