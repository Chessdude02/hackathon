"""One recommended action per ranked client, with its dollar effect (D-24). Rules, not a model.

All figures come from the cost engine and features; nothing here is estimated by
an LLM (D-07). The basis is the last 3 months, scaled to a year, so the action
reflects where the client is now; 12-month figures are shown beside it.

Assumption behind every dollar effect: hours and volume stay as they are, and
the client accepts the change. Real clients may push back or leave.
"""
import pandas as pd

from clientprofit.features import build_features

KEEP, RAISE, CUT, END = "keep as is", "raise price", "cut scope", "end the contract"
MONTHS = 3
ANNUAL = 12 / MONTHS
# Rule thresholds (D-24)
END_IF_RISE_ABOVE = 0.50      # price rise needed above this, while losing money and not improving
NEAR_TARGET = 0.02            # within 2 points of the target margin counts as on target
EXTRA_SHARE_SIGNAL = 0.30     # share of recent requests labelled extra unpaid work
UNBILLED_SHARE_SIGNAL = 0.20  # share of recent hours not billed
FALLING_TREND = -0.10         # margin drop vs the quarter before that counts as falling


def _recent(result, months=MONTHS):
    """Per client: revenue, full cost (direct + labour + late), unbilled labour cost over the last `months`."""
    end = pd.Period(result["as_of"], "M")
    cm = result["client_month"]
    cm = cm[cm["month"] > end - months]
    te = result["time_costed"]
    te = te[te["month"] > end - months]
    rows = {}
    for client, g in cm.groupby("client"):
        rows[client] = {"revenue_3m": g["revenue"].sum(),
                        "cost_3m": g["direct_cost"].sum() + g["labour_cost"].sum() + g["late_cost"].sum(),
                        "overhead_3m": g["overhead_cost"].sum()}
    for client, g in te.groupby("client"):
        unbilled = g[g["billable"] == False]  # noqa: E712
        r = rows.setdefault(client, {"revenue_3m": 0.0, "cost_3m": 0.0})
        r["hours_3m"] = g["hours"].sum()
        r["unbilled_hours_3m"] = unbilled["hours"].sum()
        r["unbilled_cost_3m"] = unbilled["labour_cost"].sum()        # with its overhead share
        r["unbilled_staff_cost_3m"] = unbilled["staff_cost"].sum()  # what the agency actually stops paying
    return rows


def _scope_signals(result, labels, months=MONTHS):
    """Per client: requests and extra-unpaid requests over the last `months`, from labels."""
    req = result["tables"].get("requests")
    if req is None or labels is None or len(labels) != len(req):
        return {}
    end = pd.Period(result["as_of"], "M")
    df = req.assign(label=[x["label"] if isinstance(x, dict) else x for x in labels])
    df = df[df["request_date"].dt.to_period("M") > end - months]
    out = {}
    for client, g in df.groupby("client"):
        out[client] = {"requests_3m": len(g), "extra_requests_3m": int((g["label"] == "extra_unpaid").sum())}
    return out


def _latest_trend(result):
    f = build_features(result)
    last = f.sort_values("month").groupby("client").tail(1).set_index("client")
    return last[["margin_3m", "margin_trend"]].to_dict("index")


def margin_history(result, client, months=MONTHS):
    """D-37: the client's margin over each rolling `months`-month window up to the as-of month, with the
    same definition as the suggested actions: (revenue - direct - labour - late cost) / revenue.
    Windows without revenue are left out."""
    cm = result["client_month"]
    g = cm[cm["client"] == client].set_index("month")[["revenue", "profit"]]
    if g.empty:
        return pd.DataFrame(columns=["month", "margin"])
    grid = pd.period_range(g.index.min(), pd.Period(result["as_of"], "M"), freq="M")
    roll = g.reindex(grid, fill_value=0.0).rolling(months, min_periods=months).sum()
    roll = roll[roll["revenue"] > 0]
    return pd.DataFrame({"month": roll.index, "margin": (roll["profit"] / roll["revenue"]).to_numpy()})


def price_rise_needed(revenue, cost, target):
    """Fractional price rise so that (new revenue - cost) / new revenue = target. None if no revenue."""
    if revenue <= 0:
        return None
    return max(0.0, cost / (1 - target) / revenue - 1)


def recommend_actions(result, settings, labels=None):
    """One row per ranked client. `labels` (optional) are the request labels in request order."""
    target = settings["target_margin"]
    recent, signals, trend = _recent(result), _scope_signals(result, labels), _latest_trend(result)
    rows = []
    for r in result["ranked"].itertuples():
        c = r.client
        x = recent.get(c, {})
        rev, cost = x.get("revenue_3m", 0.0), x.get("cost_3m", 0.0)
        profit_3m = rev - cost
        # D-36: contribution leaves out shared overhead, which stays if the work or the client goes.
        contribution_3m = profit_3m + x.get("overhead_3m", 0.0)
        margin_3m = profit_3m / rev if rev > 0 else None
        unbilled_share = x.get("unbilled_hours_3m", 0) / x["hours_3m"] if x.get("hours_3m") else 0.0
        sig = signals.get(c)
        extra_share = sig["extra_requests_3m"] / sig["requests_3m"] if sig and sig["requests_3m"] else None
        t = trend.get(c, {})
        falling = t.get("margin_trend") is not None and pd.notna(t.get("margin_trend")) and \
            t["margin_trend"] <= FALLING_TREND
        rise = price_rise_needed(rev, cost, target)
        rise_dollars = (cost / (1 - target) - rev) * ANNUAL if rise is not None else None
        cut_saving = x.get("unbilled_staff_cost_3m", 0.0) * ANNUAL  # D-36: overhead does not go away
        cut_margin = (profit_3m + x.get("unbilled_cost_3m", 0.0)) / rev if rev > 0 else None
        scope_signal = unbilled_share >= UNBILLED_SHARE_SIGNAL or \
            (extra_share is not None and extra_share >= EXTRA_SHARE_SIGNAL and sig["extra_requests_3m"] >= 3)

        alternative = None
        cut_profit = profit_3m + x.get("unbilled_cost_3m", 0.0)                   # client's view, after overhead
        cut_contribution = contribution_3m + x.get("unbilled_staff_cost_3m", 0.0)  # agency's view (D-36)
        if rev <= 0 and not x.get("hours_3m"):
            action, effect = KEEP, 0.0
            why = "No invoices or hours in the last 3 months; nothing to change."
        elif margin_3m is not None and margin_3m >= target - NEAR_TARGET:
            action, effect = KEEP, 0.0
            why = f"Last 3 months' margin {margin_3m:.0%} is at or above the {target:.0%} target."
        elif rev <= 0:
            action, effect = CUT, cut_saving if cut_saving > 0 else (cost - x.get("overhead_3m", 0.0)) * ANNUAL
            why = ("Hours were logged in the last 3 months but nothing was invoiced: "
                   "bill this work or stop it.")
        elif scope_signal and ((cut_margin is not None and cut_margin >= target - NEAR_TARGET)
                               or (profit_3m < 0 <= cut_profit) or (contribution_3m < 0 <= cut_contribution)):
            action, effect = CUT, cut_saving
            why = (f"Unbilled work costs ${x.get('unbilled_staff_cost_3m', 0):,.0f} a quarter in staff time "
                   f"({unbilled_share:.0%} of hours unbilled"
                   + (f", {extra_share:.0%} of requests look like extra unpaid work" if extra_share is not None
                      else "") + f"). Stopping or billing it brings margin to {cut_margin:.0%}."
                   + (f" That is still below the {target:.0%} target, so a price rise is needed as well."
                      if cut_margin < target - NEAR_TARGET else ""))
        elif (r.contribution_last_12m < 0 and contribution_3m < 0 and cut_contribution < 0
              and rise is not None and rise > END_IF_RISE_ABOVE):
            # Last resort (D-24, D-36): the client does not even cover its own staff and direct costs,
            # over 12 months and now, cutting unbilled work would not fix that, and the price rise
            # needed is above END_IF_RISE_ABOVE. Shared overhead is left out: it stays if the client goes.
            action, effect = END, -contribution_3m * ANNUAL
            why = (f"Does not cover its own staff and direct costs: ending it saves "
                   f"${-contribution_3m * ANNUAL:,.0f} a year at the current rate (shared overhead stays); "
                   f"a price rise of {rise:.0%} would be needed to reach the {target:.0%} target.")
            alternative = (f"Alternative: raise the price by {rise:.0%} (${rise_dollars:,.0f} a year)"
                           + (f", or cut unbilled work worth ${cut_saving:,.0f} a year" if cut_saving > 0 else "")
                           + ".")
        else:
            action, effect = RAISE, rise_dollars
            why = (f"Last 3 months' margin {margin_3m:.0%} is below the {target:.0%} target; "
                   f"a {rise:.0%} price rise reaches it at the current workload.")
        warning = bool(r.profit_last_12m >= 0 and margin_3m is not None and
                       (margin_3m < 0 or (margin_3m < 0.05 and falling)))
        rows.append({
            "client": c, "action": action, "dollar_effect_per_year": round(effect or 0.0, 2), "why": why,
            "alternative": alternative, "heading_to_loss": warning,
            "revenue_3m": round(rev, 2), "cost_3m": round(cost, 2), "profit_3m": round(profit_3m, 2),
            "contribution_3m": round(contribution_3m, 2),
            "margin_3m": margin_3m, "target_margin": target,
            # D-37: the margin the action itself aims at (not a prediction): the target after a price
            # rise, the margin without the unbilled work after a cut, unchanged when kept, none when ended.
            "margin_after_action": (target if action == RAISE else cut_margin if action == CUT and rev > 0
                                    else margin_3m if action == KEEP else None),
            "price_rise_needed": rise, "price_rise_dollars_per_year": rise_dollars,
            "unbilled_share_3m": unbilled_share, "unbilled_cost_per_year": round(cut_saving, 2),
            "extra_request_share_3m": extra_share, "margin_trend": t.get("margin_trend"),
            "scope_signals_available": sig is not None,
        })
    return pd.DataFrame(rows)
