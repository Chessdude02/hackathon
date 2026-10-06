"""Recommendation rules (D-24): one test per rule, on small clients with round numbers."""
import pandas as pd
import pytest

from clientprofit import pipeline, recommend
from clientprofit.ingest import coerce_types

SETTINGS = {"staff_costs": {"Ana": 50}, "overhead_multiplier": 1.0, "late_payment_annual_rate": 0.0,
            "payment_terms_days": 30, "unpaid_warning_days": 90, "min_months_for_ranking": 3,
            "target_margin": 0.30}
MONTHS = [f"2026-0{m}" for m in range(1, 7)]


def client(name, revenue, billable_h, unbilled_h, months=MONTHS, revenue_by_month=None):
    """Monthly invoice of `revenue` (paid on issue) and hours for Ana at $50."""
    inv, te = [], []
    for i, m in enumerate(months):
        r = revenue_by_month[i] if revenue_by_month else revenue
        if r:
            inv.append((name, f"{m}-01", r, "", f"{m}-01"))
        if billable_h:
            te.append((name, "Ana", f"{m}-10", billable_h, "TRUE"))
        if unbilled_h:
            te.append((name, "Ana", f"{m}-11", unbilled_h, "FALSE"))
    return inv, te


def run(*clients, labels_extra=None):
    inv = sum((c[0] for c in clients), [])
    te = sum((c[1] for c in clients), [])
    tables = {
        "invoices": coerce_types(pd.DataFrame(inv, columns=["client", "invoice_date", "amount", "due_date",
                                                            "paid_date"]).astype(str), "invoices", "i"),
        "time_entries": coerce_types(pd.DataFrame(te, columns=["client", "staff", "work_date", "hours",
                                                               "billable"]).astype(str), "time_entries", "t"),
    }
    labels = None
    if labels_extra is not None:
        rows = [(c, "2026-06-15", f"msg {i}") for c, n_extra, n_total in labels_extra for i in range(n_total)]
        tables["requests"] = coerce_types(pd.DataFrame(rows, columns=["client", "request_date", "message"]),
                                          "requests", "r")
        labels = [{"label": "extra_unpaid" if i < n_extra else "in_scope"}
                  for _, n_extra, n_total in labels_extra for i in range(n_total)]
    result = pipeline.run_pipeline(tables, SETTINGS)
    return recommend.recommend_actions(result, SETTINGS, labels).set_index("client")


def test_price_rise_formula():
    assert recommend.price_rise_needed(1000, 900, 0.30) == pytest.approx(900 / 0.7 / 1000 - 1)
    assert recommend.price_rise_needed(1000, 500, 0.30) == 0.0
    assert recommend.price_rise_needed(0, 500, 0.30) is None


def test_keep_when_at_target():
    r = run(client("A", 1000, 12, 0))  # cost 600, margin 40%
    assert r.loc["A", "action"] == recommend.KEEP and r.loc["A", "dollar_effect_per_year"] == 0


def test_raise_price_with_dollar_effect():
    r = run(client("A", 1000, 16, 0))  # cost 800 a month, margin 20%
    assert r.loc["A", "action"] == recommend.RAISE
    assert r.loc["A", "price_rise_needed"] == pytest.approx(800 / 0.7 / 1000 - 1)
    assert r.loc["A", "dollar_effect_per_year"] == pytest.approx((800 / 0.7 - 1000) * 12, abs=0.01)


def test_cut_scope_when_unbilled_work_alone_reaches_target():
    r = run(client("A", 1000, 10, 6))  # cost 800 (300 unbilled), cutting it gives 50% margin
    assert r.loc["A", "action"] == recommend.CUT
    assert r.loc["A", "dollar_effect_per_year"] == pytest.approx(300 * 12)


def test_cut_scope_preferred_over_ending_when_cutting_breaks_even():
    r = run(client("A", 1000, 14, 8))  # cost 1100, losing; cutting 400 unbilled gives +300
    assert r.loc["A", "action"] == recommend.CUT


def test_end_contract_only_as_last_resort_and_always_with_alternative():
    r = run(client("A", 1000, 30, 0))  # cost 1500, losing all along, no unbilled work, needs 114% rise
    row = r.loc["A"]
    assert row["action"] == recommend.END
    assert row["dollar_effect_per_year"] == pytest.approx(500 * 12)
    assert row["alternative"] and "raise the price" in row["alternative"]


def test_never_end_a_client_profitable_over_12_months():
    rev = [3000, 3000, 3000, 600, 600, 600]  # good first quarter, bad last quarter
    r = run(client("A", 0, 30, 0, revenue_by_month=rev))
    assert r.loc["A", "action"] != recommend.END


def test_warning_when_profitable_over_year_but_losing_now():
    rev = [3000, 3000, 3000, 1000, 1000, 1000]
    r = run(client("A", 0, 24, 0, revenue_by_month=rev))  # cost 1200 a month
    assert bool(r.loc["A", "heading_to_loss"])


def test_hours_without_invoices_recently_means_bill_or_stop():
    rev = [1000, 1000, 1000, 0, 0, 0]
    r = run(client("A", 0, 10, 0, revenue_by_month=rev))
    assert r.loc["A", "action"] == recommend.CUT and "nothing was invoiced" in r.loc["A", "why"]


def test_no_recent_activity_means_keep():
    a = client("A", 1000, 10, 0, months=MONTHS[:3])
    b = client("B", 1000, 10, 0)
    r = run(a, b)
    assert r.loc["A", "action"] == recommend.KEEP and "No invoices or hours" in r.loc["A", "why"]


def test_labels_are_optional_and_add_the_extra_request_share():
    without = run(client("A", 1000, 10, 6))
    with_labels = run(client("A", 1000, 10, 6), labels_extra=[("A", 3, 4)])
    assert not without.loc["A", "scope_signals_available"]
    assert with_labels.loc["A", "extra_request_share_3m"] == pytest.approx(0.75)
    assert "75% of requests" in with_labels.loc["A", "why"]
