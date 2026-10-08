"""Client-month features and forecast targets (D-21). Uses only data up to each month.

Margin here is operating margin: (revenue - direct cost - labour cost) / revenue
(direct cost per D-31; 0 when the data has none). Late-payment cost is left out because a month's late cost depends on payments made later,
which would leak the future into the features.
"""
import numpy as np
import pandas as pd

WINDOW = 3


def _monthly(result):
    """Complete month grid per client (first to last active month) with sums."""
    cm = result["client_month"]
    cm = cm.assign(direct_cost=cm["direct_cost"] if "direct_cost" in cm else 0.0)
    # D-31: direct costs count with labour, so "cost" below is everything except late payment.
    cm = cm.assign(labour_cost=cm["labour_cost"] + cm["direct_cost"].fillna(0.0))
    cm = cm[["client", "month", "revenue", "labour_cost", "hours"]]
    te = result["time_costed"]
    nb = te[te["billable"] == False].groupby(["client", "month"])["hours"].sum().rename("nonbill_hours")  # noqa: E712
    req = result["tables"].get("requests")
    rows = []
    for client, g in cm.groupby("client"):
        months = pd.period_range(g["month"].min(), g["month"].max(), freq="M")
        rows.append(pd.DataFrame({"client": client, "month": months}))
    grid = pd.concat(rows, ignore_index=True)
    df = grid.merge(cm, on=["client", "month"], how="left").fillna({"revenue": 0, "labour_cost": 0, "hours": 0})
    df = df.merge(nb.reset_index(), on=["client", "month"], how="left").fillna({"nonbill_hours": 0})
    if req is not None and len(req):
        rc = req.dropna(subset=["request_date"]).assign(month=lambda d: d["request_date"].dt.to_period("M"))
        df = df.merge(rc.groupby(["client", "month"]).size().rename("requests").reset_index(),
                      on=["client", "month"], how="left")
    else:
        df["requests"] = 0
    return df.fillna({"requests": 0}).sort_values(["client", "month"]).reset_index(drop=True)


def _days_to_pay(invoices, client, month):
    """Mean days from invoice to payment for invoices issued in the 6 months to `month`,
    counting only payments made by the end of `month` (no future knowledge)."""
    end = month.end_time
    g = invoices[(invoices["client"] == client) & (invoices["month"] <= month) & (invoices["month"] > month - 6)
                 & invoices["paid_date"].notna() & (invoices["paid_date"] <= end)]
    return float((g["paid_date"] - g["invoice_date"]).dt.days.mean()) if len(g) else np.nan


def build_features(result, horizon=3):
    """One row per client per month with features at that month and the next-`horizon`-month target."""
    df = _monthly(result)
    inv = result["invoices_costed"]
    out = []
    for client, g in df.groupby("client"):
        g = g.reset_index(drop=True)
        roll = lambda col, k=WINDOW: g[col].rolling(k, min_periods=k).sum()  # noqa: E731
        rev3, lab3 = roll("revenue"), roll("labour_cost")
        rev_prev, lab_prev = rev3.shift(WINDOW), lab3.shift(WINDOW)
        hrs3, nb3, req3 = roll("hours"), roll("nonbill_hours"), roll("requests")
        fwd_rev = sum(g["revenue"].shift(-k) for k in range(1, horizon + 1))
        fwd_lab = sum(g["labour_cost"].shift(-k) for k in range(1, horizon + 1))
        feat = pd.DataFrame({
            "client": client, "month": g["month"], "months_seen": np.arange(1, len(g) + 1),
            "revenue_3m": rev3,
            "margin_3m": (rev3 - lab3) / rev3.where(rev3 > 0),
            "margin_prev_3m": (rev_prev - lab_prev) / rev_prev.where(rev_prev > 0),
            "unbilled_share_3m": nb3 / hrs3.where(hrs3 > 0),
            "hours_growth": hrs3 / hrs3.shift(WINDOW).where(hrs3.shift(WINDOW) > 0) - 1,
            "requests_3m": req3,
            "requests_growth": req3 - req3.shift(WINDOW),
            "revenue_growth": rev3 / rev_prev.where(rev_prev > 0) - 1,
            "target_revenue": fwd_rev,
            "target_margin": (fwd_rev - fwd_lab) / fwd_rev.where(fwd_rev > 0),
        })
        feat["margin_trend"] = feat["margin_3m"] - feat["margin_prev_3m"]
        feat["days_to_pay"] = [_days_to_pay(inv, client, m) for m in g["month"]]
        out.append(feat)
    return pd.concat(out, ignore_index=True)


FEATURES = ["margin_3m", "margin_prev_3m", "margin_trend", "unbilled_share_3m", "hours_growth",
            "requests_3m", "requests_growth", "revenue_growth", "revenue_3m", "days_to_pay", "months_seen"]
