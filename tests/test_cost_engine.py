"""Cost engine: benchmark 1 (hand-calculated answers) and one test per calculation."""
from pathlib import Path

import pandas as pd
import pytest
import yaml

from clientprofit import cost_engine as ce
from clientprofit.ingest import coerce_types, load_canonical

HAND = Path(__file__).parent / "fixtures" / "hand_calc"
SETTINGS = {"staff_costs": {"Ana": 50, "Ben": 80}, "overhead_multiplier": 1.5,
            "late_payment_annual_rate": 0.073, "payment_terms_days": 30,
            "unpaid_warning_days": 90, "min_months_for_ranking": 3}


def tables(invoices=(), times=(), requests=()):
    inv = pd.DataFrame(list(invoices), columns=["client", "invoice_date", "amount", "due_date", "paid_date"])
    te = pd.DataFrame(list(times), columns=["client", "staff", "work_date", "hours", "billable"])
    rq = pd.DataFrame(list(requests), columns=["client", "request_date", "message"])
    return (coerce_types(inv.astype(str).replace("None", ""), "invoices", "i.csv"),
            coerce_types(te.astype(str), "time_entries", "t.csv"),
            coerce_types(rq.astype(str), "requests", "r.csv"))


def run(invoices=(), times=(), requests=(), settings=SETTINGS):
    inv, te, rq = tables(invoices, times, requests)
    cm, inv_c, te_c, as_of = ce.compute_client_month_profit(inv, te, settings, rq)
    return cm, inv_c, te_c, as_of, ce.compute_client_totals(cm, inv_c, settings, as_of)


# ---- Benchmark 1: exact match with the hand calculation ----

@pytest.fixture(scope="module")
def hand():
    t = load_canonical(HAND)
    settings = yaml.safe_load((HAND / "config.yaml").read_text())
    cm, inv, te, as_of = ce.compute_client_month_profit(t["invoices"], t["time_entries"], settings, t["requests"])
    return cm, ce.compute_client_totals(cm, inv, settings, as_of), as_of


def test_benchmark1_client_month_matches_hand_calculation(hand):
    cm, _, _ = hand
    expected = pd.read_csv(HAND / "expected_client_month.csv", dtype={"month": str})
    got = cm.assign(month=cm["month"].astype(str))
    merged = expected.merge(got, on=["client", "month"], how="outer", suffixes=("_hand", "_engine"),
                            indicator=True)
    assert (merged["_merge"] == "both").all(), merged[merged["_merge"] != "both"][["client", "month", "_merge"]]
    for col in ("revenue", "labour_cost", "late_cost", "profit"):
        diff = (merged[f"{col}_hand"] - merged[f"{col}_engine"].round(2)).abs()
        assert (diff < 0.005).all(), merged.loc[diff >= 0.005, ["client", "month", f"{col}_hand", f"{col}_engine"]]


def test_benchmark1_client_totals_match_hand_calculation(hand):
    _, totals, _ = hand
    expected = pd.read_csv(HAND / "expected_client_totals.csv", keep_default_na=False,
                           dtype={"ranked": str, "loss_making": str})
    got = totals.set_index("client")
    assert sorted(expected["client"]) == sorted(got.index)
    for row in expected.itertuples():
        g = got.loc[row.client]
        assert g["months_of_data"] == row.months_of_data, row.client
        assert round(g["profit_last_12m"], 2) == pytest.approx(row.profit_last_12m, abs=0.005), row.client
        assert round(g["profit_if_overdue_unpaid"], 2) == pytest.approx(row.profit_if_overdue_unpaid, abs=0.005), row.client
        assert g["ranked"] == (row.ranked == "TRUE"), row.client
        expected_loss = {"TRUE": True, "FALSE": False, "": None}[row.loss_making]
        assert g["loss_making"] == expected_loss, row.client


def test_benchmark1_as_of_date(hand):
    assert hand[2] == pd.Timestamp("2026-03-31")


# ---- One test per calculation ----

def test_revenue_is_booked_in_invoice_month_not_payment_month():
    cm, *_ = run(invoices=[("A", "2026-01-31", 100, None, "2026-02-05")])
    assert cm.loc[0, "month"] == pd.Period("2026-01", "M") and cm.loc[0, "revenue"] == 100


def test_labour_cost_is_hours_times_cost_times_overhead_including_non_billable():
    cm, *_ = run(times=[("A", "Ana", "2026-01-05", 2, "TRUE"), ("A", "Ben", "2026-01-06", 1, "FALSE")])
    assert cm.loc[0, "labour_cost"] == pytest.approx(2 * 50 * 1.5 + 1 * 80 * 1.5)


def test_negative_hours_reduce_cost_as_written():
    cm, *_ = run(times=[("A", "Ben", "2026-01-05", 10, "TRUE"), ("A", "Ben", "2026-01-06", -2, "TRUE")])
    assert cm.loc[0, "labour_cost"] == pytest.approx(8 * 80 * 1.5)


def test_due_date_defaults_to_invoice_date_plus_terms():
    _, inv, *_ = run(invoices=[("A", "2026-01-01", 100, None, "2026-01-01")])
    assert inv.loc[0, "due"] == pd.Timestamp("2026-01-31")


def test_explicit_due_date_is_used():
    _, inv, *_ = run(invoices=[("A", "2026-01-01", 100, "2026-01-10", "2026-01-15")])
    assert inv.loc[0, "days_late"] == 5


def test_early_payment_has_zero_days_late():
    _, inv, *_ = run(invoices=[("A", "2026-01-01", 100, None, "2026-01-05")])
    assert inv.loc[0, "days_late"] == 0 and inv.loc[0, "late_cost"] == 0


def test_late_cost_formula():
    _, inv, *_ = run(invoices=[("A", "2026-01-01", 4000, None, "2026-03-02")])  # due 01-31, 30 days late
    assert inv.loc[0, "late_cost"] == pytest.approx(4000 * 0.073 * 30 / 365)


def test_unpaid_invoice_runs_late_to_as_of_date():
    _, inv, _, as_of, _ = run(invoices=[("A", "2026-01-01", 1000, None, None)],
                              requests=[("A", "2026-03-02", "hi")])
    assert as_of == pd.Timestamp("2026-03-02") and inv.loc[0, "days_late"] == 30


def test_as_of_ignores_due_dates():
    _, _, _, as_of, _ = run(invoices=[("A", "2026-01-01", 100, "2026-06-30", "2026-01-10")],
                            times=[("A", "Ana", "2026-01-05", 1, "TRUE")])
    assert as_of == pd.Timestamp("2026-01-05")


def test_as_of_ignores_payment_dates():
    """D-29 (replaces D-18's use of payment dates): a late payment must not move the 12-month window."""
    _, _, _, as_of, _ = run(invoices=[("A", "2026-01-01", 100, None, "2026-11-30")],
                            times=[("A", "Ana", "2026-01-20", 1, "TRUE")])
    assert as_of == pd.Timestamp("2026-01-20")


def _with_direct(rows):
    inv = pd.DataFrame(rows, columns=["client", "invoice_date", "amount", "due_date", "paid_date", "direct_cost"])
    te = pd.DataFrame([("A", "Ana", "2026-01-10", "2", "TRUE")],
                      columns=["client", "staff", "work_date", "hours", "billable"])
    inv_t = coerce_types(inv.astype(str).replace("None", ""), "invoices", "i.csv")
    te_t = coerce_types(te, "time_entries", "t.csv")
    cm, inv_c, te_c, as_of = ce.compute_client_month_profit(inv_t, te_t, SETTINGS)
    return cm, inv_c, ce.compute_client_totals(cm, inv_c, SETTINGS, as_of)


def test_direct_cost_is_subtracted_in_invoice_month():
    """D-31: profit = revenue - direct cost - labour - late cost. 2 h x 50 x 1.5 = 150 labour."""
    cm, _, totals = _with_direct([("A", "2026-01-15", 1000, None, "2026-01-20", 300),
                                  ("A", "2026-01-25", 500, None, "2026-01-30", None)])
    assert cm.loc[0, "direct_cost"] == 300 and cm.loc[0, "profit"] == pytest.approx(1500 - 300 - 150)
    assert totals.loc[0, "direct_cost_last_12m"] == 300


def test_missing_direct_cost_counts_as_zero():
    cm, *_ = run(invoices=[("A", "2026-01-15", 1000, None, "2026-01-20")])
    assert cm.loc[0, "direct_cost"] == 0 and cm.loc[0, "profit"] == 1000


def test_worst_case_keeps_direct_cost_of_overdue_invoice():
    """D-31 with D-16: an unpaid invoice's revenue goes, the money already spent on it stays."""
    _, inv, totals = _with_direct([("A", "2026-01-01", 1000, None, None, 400),
                                   ("A", "2026-06-01", 10, None, "2026-06-01", None)])
    late = inv.loc[0, "late_cost"]
    assert inv.loc[0, "overdue_unpaid"]
    assert totals.loc[0, "profit_if_overdue_unpaid"] == pytest.approx(totals.loc[0, "profit_last_12m"] - 1000 + late)


def test_client_with_no_activity_in_window_is_not_ranked():
    """D-30: old activity only, nothing in the last 12 months: listed apart with the reason."""
    _, _, _, _, totals = run(invoices=[("Old", "2024-01-15", 100, None, "2024-01-20"),
                                       ("Old", "2024-02-15", 100, None, "2024-02-20"),
                                       ("Old", "2024-03-15", 100, None, "2024-03-20"),
                                       ("New", "2026-01-15", 100, None, "2026-01-20"),
                                       ("New", "2026-02-15", 100, None, "2026-02-20"),
                                       ("New", "2026-03-15", 100, None, "2026-03-20")])
    t = totals.set_index("client")
    assert not t.loc["Old", "ranked"] and t.loc["Old", "not_ranked_because"].startswith("no invoices or hours")
    assert t.loc["Old", "profit_all_data"] == 300 and t.loc["New", "ranked"]


def test_profit_and_zero_revenue_month_margin_is_empty():
    cm, *_ = run(invoices=[("A", "2026-01-01", 1000, None, "2026-01-02")],
                 times=[("A", "Ana", "2026-01-05", 4, "TRUE"), ("A", "Ana", "2026-02-05", 4, "TRUE")])
    jan, feb = cm.iloc[0], cm.iloc[1]
    assert jan["profit"] == pytest.approx(1000 - 300) and jan["margin"] == pytest.approx(0.7)
    assert feb["revenue"] == 0 and feb["profit"] == pytest.approx(-300) and pd.isna(feb["margin"])


def test_months_of_data_counts_first_to_last_month_including_gaps():
    *_, totals = run(times=[("A", "Ana", "2026-01-05", 1, "TRUE"), ("A", "Ana", "2026-04-05", 1, "TRUE")])
    assert totals.loc[0, "months_of_data"] == 4


def test_short_history_is_not_ranked_and_has_no_loss_label():
    *_, totals = run(times=[("A", "Ana", "2026-01-05", 1, "TRUE"), ("A", "Ana", "2026-02-05", 1, "TRUE")])
    assert not totals.loc[0, "ranked"] and totals.loc[0, "loss_making"] is None


def test_loss_making_when_ranked_and_12_month_profit_below_zero():
    times = [("A", "Ana", f"2026-0{m}-05", 1, "TRUE") for m in (1, 2, 3)]
    *_, totals = run(times=times)
    flag = totals.loc[0, "loss_making"]
    assert totals.loc[0, "ranked"] and flag is not None and bool(flag)


def test_12_month_window_ends_in_as_of_month():
    times = [("A", "Ana", "2025-01-05", 10, "TRUE"), ("A", "Ana", "2026-03-05", 1, "TRUE")]
    *_, totals = run(times=times)
    assert totals.loc[0, "profit_last_12m"] == pytest.approx(-1 * 50 * 1.5)  # Jan 2025 is outside


def test_exactly_90_days_overdue_does_not_count():
    _, inv, *_ = run(invoices=[("A", "2025-12-01", 100, None, None)], requests=[("A", "2026-03-31", "x")])
    assert inv.loc[0, "days_late"] == 90 and not inv.loc[0, "overdue_unpaid"]


def test_worst_case_removes_overdue_invoice_revenue_and_late_cost():
    invs = [("A", "2025-11-15", 3000, None, None), ("A", "2025-12-15", 3000, None, "2026-01-10"),
            ("A", "2026-01-15", 3000, None, "2026-02-10")]
    _, inv, _, _, totals = run(invoices=invs, requests=[("A", "2026-03-31", "x")])
    late = inv.loc[0, "late_cost"]
    assert inv.loc[0, "overdue_unpaid"]
    assert totals.loc[0, "profit_if_overdue_unpaid"] == pytest.approx(totals.loc[0, "profit_last_12m"] - 3000 + late)


def test_missing_staff_cost_stops_with_the_name():
    with pytest.raises(ce.CostEngineError, match="Zed"):
        run(times=[("A", "Zed", "2026-01-05", 1, "TRUE")])


def test_unreadable_hours_stop_with_the_row_number():
    with pytest.raises(ce.CostEngineError, match=r"hours.*\[2\]"):
        run(times=[("A", "Ana", "2026-01-05", "abc", "TRUE")])


def test_rows_behind_each_figure_are_listed():
    cm, *_ = run(invoices=[("A", "2026-01-01", 100, None, "2026-01-02")],
                 times=[("A", "Ana", "2026-01-05", 1, "TRUE"), ("A", "Ana", "2026-01-06", 1, "TRUE")])
    assert cm.loc[0, "invoice_rows"] == [2] and cm.loc[0, "time_rows"] == [2, 3]


def test_ranking_orders_by_profit_and_keeps_unranked_apart():
    times = [(c, "Ana", f"2026-0{m}-05", h, "TRUE") for c, h in (("Low", 5), ("High", 1)) for m in (1, 2, 3)]
    times.append(("New", "Ana", "2026-03-05", 1, "TRUE"))
    *_, totals = run(times=times)
    ranked, unranked = ce.rank_clients(totals)
    assert list(ranked["client"]) == ["High", "Low"] and list(unranked["client"]) == ["New"]


def test_yearly_overhead_becomes_a_rate_per_logged_hour():
    """D-36: $12,000 a year over 120 hours logged in the last 12 months = $100 an hour. A client with
    10 h of Ana ($50) in a month gets $500 staff cost + $1,000 overhead; contribution is before overhead."""
    settings = {**SETTINGS, "overhead_per_year": 12000}
    times = [("A", "Ana", "2026-01-10", 10, "TRUE"), ("B", "Ana", "2026-02-10", 110, "TRUE")]
    cm, *_ , totals = run(invoices=[("A", "2026-01-15", 3000, None, "2026-01-20")], times=times,
                          settings=settings)
    a = cm[cm["client"] == "A"].iloc[0]
    assert a["staff_cost"] == 500 and a["overhead_cost"] == pytest.approx(1000)
    assert a["contribution"] == pytest.approx(2500) and a["profit"] == pytest.approx(1500)
    t = totals.set_index("client")
    assert t.loc["A", "contribution_last_12m"] == pytest.approx(2500)
    assert t.loc["A", "overhead_last_12m"] == pytest.approx(1000)


def test_multiplier_used_when_no_yearly_overhead():
    """D-36: without a yearly figure, overhead = staff cost x (multiplier - 1), as before (1.5 here)."""
    cm, *_ = run(invoices=[("A", "2026-01-15", 3000, None, "2026-01-20")],
                 times=[("A", "Ana", "2026-01-10", 10, "TRUE")])
    a = cm.iloc[0]
    assert a["staff_cost"] == 500 and a["overhead_cost"] == pytest.approx(250) and a["labour_cost"] == 750
    assert a["contribution"] == pytest.approx(2500) and a["profit"] == pytest.approx(2250)
