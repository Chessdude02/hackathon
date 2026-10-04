import json

import pandas as pd
import pytest

from generator.generate import generate
from generator.messy import HEADER_STYLES

SEED, N = 7, 45


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    base = tmp_path_factory.mktemp("gen")
    truth_path = generate(SEED, N, base / "data", base / "truth")
    return base / "data", json.loads(truth_path.read_text()), truth_path


def test_same_seed_gives_same_files(run, tmp_path):
    data, _, truth_path = run
    truth2 = generate(SEED, N, tmp_path / "data", tmp_path / "truth")
    assert truth2.read_text() == truth_path.read_text()
    for name in ("invoices.csv", "time_entries.csv", "requests.csv"):
        assert (tmp_path / "data" / name).read_bytes() == (data / name).read_bytes()


def test_client_count_and_planted_types(run):
    _, truth, _ = run
    clients = truth["clients"]
    assert len(clients) == N
    types = [t for c in clients.values() for t in c["types"]]
    for t in ("healthy", "big_loss", "slow_payer", "scope_creep", "decline", "new", "no_invoices"):
        assert t in types


def test_short_history_clients_get_no_loss_label(run):
    _, truth, _ = run
    for c in truth["clients"].values():
        if c["months_of_data"] < 3:
            assert c["loss_making"] is None
        else:
            assert c["loss_making"] in (True, False)


def test_most_big_loss_clients_are_loss_making(run):
    """Not all: noise, repricing or one-off projects can lift a mildly
    loss-making client just above zero (D-13)."""
    _, truth, _ = run
    big = [c for c in truth["clients"].values() if "big_loss" in c["types"]]
    assert big and sum(bool(c["loss_making"]) for c in big) > len(big) / 2


def test_request_labels_line_up_with_rows(run):
    data, truth, _ = run
    requests = pd.read_csv(data / "requests.csv")
    assert len(truth["request_labels"]) == len(requests)


def test_ten_header_styles_with_true_mapping(run):
    data, truth, _ = run
    assert len(HEADER_STYLES) == 10
    for style in HEADER_STYLES:
        for table in ("invoices", "time_entries", "requests"):
            headers = set(pd.read_csv(data / "header_variants" / style / f"{table}.csv", nrows=1).columns)
            mapped = set(truth["header_mappings"][style][table])
            assert mapped <= headers


def test_planted_defects_are_recorded(run):
    _, truth, _ = run
    kinds = {d["type"] for d in truth["defects"]}
    assert kinds == {"skipped_invoice", "negative_hours", "blank_cell", "duplicate_row", "name_variant"}


def test_label_sheet_has_150_rows_and_no_labels(run):
    data, _, _ = run
    sheet = pd.read_csv(data / "label_sheet.csv", keep_default_na=False)
    assert len(sheet) == 150
    assert (sheet["label"] == "").all()


def test_client_count_outside_range_is_refused(tmp_path):
    with pytest.raises(ValueError):
        generate(SEED, 30, tmp_path / "d", tmp_path / "t")


def test_planted_changes_are_recorded_per_client(run):
    _, truth, _ = run
    clients = truth["clients"].values()
    for c in clients:
        ev = c["events"]
        assert ev["first_month"] <= ev["last_month"]
        if "late_scope_creep" in c["types"]:
            assert "scope_creep_from" in ev
        if "repriced" in c["types"]:
            assert "repriced_in" in ev and "reprice_factor" in ev
        if "recovered_payer" in c["types"]:
            assert "pays_on_time_from" in ev
    assert any(c["events"]["first_month"] > truth["months"][0] for c in clients)  # some join late


def test_staff_change_happens_at_the_planted_month(run):
    data, truth, _ = run
    change = truth["agency_events"]["staff_change"]
    te = pd.read_csv(data / "header_variants" / "snake" / "time_entries.csv")
    month = te["date"].str[:7]
    assert (te.loc[month >= change["month"], "staff_member"] != change["leaves"]).all()
    assert (te.loc[month < change["month"], "staff_member"] != change["replaced_by"]).all()


def test_staff_costs_include_the_new_hire(run):
    data, truth, _ = run
    costs = pd.read_csv(data / "staff_costs.csv")
    assert truth["agency_events"]["staff_change"]["replaced_by"] in set(costs["staff"])


def test_months_of_data_matches_profit_months(run):
    _, truth, _ = run
    for c in truth["clients"].values():
        months = sorted(c["profit_by_month"])
        first, last = pd.Period(months[0], "M"), pd.Period(months[-1], "M")
        assert c["months_of_data"] == (last - first).n + 1
