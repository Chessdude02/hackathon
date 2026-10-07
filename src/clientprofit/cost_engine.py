"""Profit per client per month (D-05, D-11, D-16). Arithmetic only.

Every figure can be traced to input rows: each client-month row lists the
`_src_row` numbers of the invoices and time entries behind it.
"""
import pandas as pd

from clientprofit.schema import SRC_ROW


class CostEngineError(Exception):
    """Inputs the engine cannot compute from. The message says what to fix."""


def as_of_date(invoices, time_entries, requests=None):
    """Latest activity date in the inputs: invoice, work or request date (D-29).

    Due dates and payment dates are left out: one late or mistyped payment date
    must not move the 12-month window past the last real work.
    """
    dates = [invoices["invoice_date"], time_entries["work_date"]]
    if requests is not None and len(requests):
        dates.append(requests["request_date"])
    return max(d.max() for d in dates if d.notna().any())


def _check(df, columns, table):
    for col in columns:
        bad = df.loc[df[col].isna(), SRC_ROW].tolist()
        if bad:
            raise CostEngineError(f"{table}: '{col}' is empty or unreadable in rows {bad}. "
                                  "Fix or exclude them in the validation step.")


def invoice_costs(invoices, settings, as_of):
    """Add due date, days late and late cost to each invoice."""
    _check(invoices, ["client", "invoice_date", "amount"], "invoices")
    inv = invoices.copy()
    default_due = inv["invoice_date"] + pd.Timedelta(days=settings["payment_terms_days"])
    inv["due"] = inv["due_date"].fillna(default_due)
    end = inv["paid_date"].fillna(as_of)
    inv["days_late"] = (end - inv["due"]).dt.days.clip(lower=0)
    inv["late_cost"] = inv["amount"] * settings["late_payment_annual_rate"] * inv["days_late"] / 365
    direct = inv["direct_cost"] if "direct_cost" in inv.columns else pd.Series(0.0, index=inv.index)
    inv["direct_cost"] = direct.fillna(0.0)  # D-31: empty or not mapped counts as 0
    inv["month"] = inv["invoice_date"].dt.to_period("M")
    inv["overdue_unpaid"] = inv["paid_date"].isna() & \
        ((as_of - inv["due"]).dt.days > settings["unpaid_warning_days"])
    return inv


def labour_costs(time_entries, settings):
    """Add the cost of each time entry: hours x hourly cost x overhead multiplier."""
    _check(time_entries, ["client", "staff", "work_date", "hours"], "time_entries")
    costs = settings["staff_costs"]
    missing = sorted(set(time_entries["staff"]) - set(costs))
    if missing:
        raise CostEngineError(f"No hourly cost for staff: {', '.join(missing)}. "
                              "Add them under staff_costs in the settings.")
    te = time_entries.copy()
    te["hourly_cost"] = te["staff"].map(costs).astype(float)
    te["labour_cost"] = te["hours"] * te["hourly_cost"] * settings["overhead_multiplier"]
    te["month"] = te["work_date"].dt.to_period("M")
    return te


def compute_client_month_profit(invoices, time_entries, settings, requests=None):
    """Return (client_month table, invoices with costs, time entries with costs, as-of date)."""
    as_of = as_of_date(invoices, time_entries, requests)
    inv = invoice_costs(invoices, settings, as_of)
    te = labour_costs(time_entries, settings)

    rev = inv.groupby(["client", "month"]).agg(
        revenue=("amount", "sum"), direct_cost=("direct_cost", "sum"), late_cost=("late_cost", "sum"),
        invoice_rows=(SRC_ROW, list))
    lab = te.groupby(["client", "month"]).agg(
        labour_cost=("labour_cost", "sum"), hours=("hours", "sum"),
        time_rows=(SRC_ROW, list))
    cm = rev.join(lab, how="outer").reset_index()
    for col in ("revenue", "direct_cost", "late_cost", "labour_cost", "hours"):
        cm[col] = cm[col].fillna(0.0)
    for col in ("invoice_rows", "time_rows"):
        cm[col] = cm[col].apply(lambda v: v if isinstance(v, list) else [])
    cm["profit"] = cm["revenue"] - cm["direct_cost"] - cm["labour_cost"] - cm["late_cost"]
    # D-11: margin is left empty when there is no revenue, never shown as 0.
    cm["margin"] = (cm["profit"] / cm["revenue"]).where(cm["revenue"] != 0)
    cm = cm.sort_values(["client", "month"]).reset_index(drop=True)
    return cm, inv, te, as_of


def compute_client_totals(client_month, invoices_with_costs, settings, as_of):
    """One row per client: months of data, 12-month profit, worst case, ranking flags."""
    end = pd.Period(as_of, "M")
    window = client_month[(client_month["month"] > end - 12) & (client_month["month"] <= end)]
    inv12 = invoices_with_costs[(invoices_with_costs["month"] > end - 12) &
                                (invoices_with_costs["month"] <= end)]
    rows = []
    for client, g in client_month.groupby("client"):
        months_of_data = (g["month"].max() - g["month"].min()).n + 1
        w = window[window["client"] == client]
        p12 = w["profit"].sum()
        revenue12 = w["revenue"].sum()
        # D-30: a client with no invoices and no hours in the window has nothing to rank on.
        active = bool(revenue12 != 0 or w["hours"].sum() > 0 or w["direct_cost"].sum() != 0)
        overdue = inv12[(inv12["client"] == client) & inv12["overdue_unpaid"]]
        # D-16: an overdue invoice is removed completely: its revenue and its late cost.
        # Its direct cost stays (D-31): that money was spent whether or not the client pays.
        worst = p12 - overdue["amount"].sum() + overdue["late_cost"].sum()
        enough = bool(months_of_data >= settings["min_months_for_ranking"])
        ranked = enough and active
        rows.append({
            "client": client,
            "months_of_data": months_of_data,
            "revenue_last_12m": revenue12,
            "direct_cost_last_12m": w["direct_cost"].sum(),
            "profit_last_12m": p12,
            "profit_all_data": g["profit"].sum(),
            "margin_last_12m": p12 / revenue12 if revenue12 else None,
            "profit_if_overdue_unpaid": worst,
            "overdue_invoice_rows": overdue[SRC_ROW].tolist(),
            "ranked": ranked,
            "not_ranked_because": None if ranked else (
                f"under {settings['min_months_for_ranking']} months of data" if not enough
                else "no invoices or hours in the last 12 months"),
            "loss_making": bool(p12 < 0) if ranked else None,
        })
    return pd.DataFrame(rows)


def rank_clients(totals):
    """Ranked clients, highest 12-month profit first. Unranked clients are returned apart."""
    ranked = totals[totals["ranked"]].sort_values("profit_last_12m", ascending=False)
    ranked = ranked.reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked, totals[~totals["ranked"]].reset_index(drop=True)
