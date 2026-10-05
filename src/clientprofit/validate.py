"""Finds problems in the loaded tables and reports them. Never drops rows.

Each problem lists the `_src_row` numbers behind it. Rows leave the data only
through `exclude_rows`, which the owner triggers by choosing them.
"""
import pandas as pd

from clientprofit import schema
from clientprofit.schema import SRC_ROW

ERROR, WARNING, INFO = "error", "warning", "info"


def _problem(check, severity, table, rows, message, suggest_exclude=False):
    return {"check": check, "severity": severity, "table": table, "rows": [int(r) for r in rows],
            "message": message, "suggest_exclude": suggest_exclude}


def _unreadable(tables):
    out = []
    for table, df in tables.items():
        for col in schema.VALUE_REQUIRED.get(table, ()):
            rows = df.loc[df[col].isna(), SRC_ROW].tolist()
            if rows:
                out.append(_problem("empty_or_unreadable", ERROR, table, rows,
                                    f"'{col}' is empty or could not be read in {len(rows)} row(s)",
                                    suggest_exclude=True))
        for col in schema.TABLES.get(table, {}):
            if col in schema.VALUE_REQUIRED.get(table, ()) or col in ("paid_date", "due_date", "billable"):
                continue
            rows = df.loc[df[col].isna(), SRC_ROW].tolist() if col in df.columns else []
            if rows:
                out.append(_problem("optional_value_empty", INFO, table, rows,
                                    f"'{col}' is empty in {len(rows)} row(s); not needed for profit"))
    te = tables.get("time_entries")
    if te is not None:
        rows = te.loc[te["billable"].isna() & te["hours"].notna(), SRC_ROW].tolist()
        if rows:
            out.append(_problem("billable_unreadable", WARNING, "time_entries", rows,
                                f"'billable' could not be read in {len(rows)} row(s); cost is still counted"))
    return out


def _bad_values(tables):
    out = []
    te = tables.get("time_entries")
    if te is not None:
        rows = te.loc[te["hours"] <= 0, SRC_ROW].tolist()
        if rows:
            out.append(_problem("negative_or_zero_hours", WARNING, "time_entries", rows,
                                f"{len(rows)} time entr(ies) with zero or negative hours. They are "
                                "counted as written unless you exclude them", suggest_exclude=True))
    inv = tables.get("invoices")
    if inv is not None:
        rows = inv.loc[inv["paid_date"] < inv["invoice_date"], SRC_ROW].tolist()
        if rows:
            out.append(_problem("paid_before_invoice", WARNING, "invoices", rows,
                                f"{len(rows)} invoice(s) paid before the invoice date"))
        rows = inv.loc[inv["amount"] < 0, SRC_ROW].tolist()
        if rows:
            out.append(_problem("negative_amount", WARNING, "invoices", rows,
                                f"{len(rows)} invoice(s) with a negative amount (credit notes?)"))
    return out


def _duplicates(tables):
    """Invoices: a repeated invoice is an error to exclude. Time entries and requests:
    identical rows can be genuine (two 1-hour entries on one day), so only flag them."""
    out = []
    for table, df in tables.items():
        cols = [c for c in schema.TABLES.get(table, {}) if c in df.columns]
        if not cols:
            continue
        dup = df.duplicated(subset=cols, keep="first")
        if dup.any():
            rows = df.loc[dup, SRC_ROW].tolist()
            if table == "invoices":
                msg = (f"{len(rows)} invoice(s) repeat an earlier invoice exactly and would be "
                       "counted twice. Exclude unless they are genuinely separate invoices")
            else:
                msg = (f"{len(rows)} row(s) are identical to an earlier row. This can be genuine "
                       "(two equal entries on one day) or a double entry; check them")
            out.append(_problem("duplicate_rows", WARNING, table, rows, msg,
                                suggest_exclude=(table == "invoices")))
    return out


def _client_coverage(tables):
    out = []
    inv, te, rq = (tables.get(t) for t in ("invoices", "time_entries", "requests"))
    billed = set(inv["client"].dropna()) if inv is not None else set()
    worked = set(te["client"].dropna()) if te is not None else set()
    for client in sorted(worked - billed):
        rows = te.loc[te["client"] == client, SRC_ROW].tolist()
        out.append(_problem("hours_but_no_invoices", WARNING, "time_entries", rows,
                            f"'{client}' has hours but no invoices; shown as all cost"))
    for client in sorted(billed - worked):
        rows = inv.loc[inv["client"] == client, SRC_ROW].tolist()
        out.append(_problem("invoices_but_no_hours", INFO, "invoices", rows,
                            f"'{client}' has invoices but no hours logged"))
    if rq is not None:
        for client in sorted(set(rq["client"].dropna()) - billed - worked):
            rows = rq.loc[rq["client"] == client, SRC_ROW].tolist()
            out.append(_problem("requests_unknown_client", WARNING, "requests", rows,
                                f"'{client}' sends requests but has no invoices or hours"))
    return out


def _invoice_gaps(tables):
    """Months inside a client's active span with hours but no invoice."""
    inv, te = tables.get("invoices"), tables.get("time_entries")
    if inv is None or te is None:
        return []
    out = []
    inv_m = inv.dropna(subset=["invoice_date"]).assign(m=lambda d: d["invoice_date"].dt.to_period("M"))
    te_m = te.dropna(subset=["work_date"]).assign(m=lambda d: d["work_date"].dt.to_period("M"))
    for client, g in inv_m.groupby("client"):
        billed = set(g["m"])
        worked = set(te_m.loc[te_m["client"] == client, "m"])
        lo, hi = min(billed), max(billed)
        gaps = sorted(m for m in worked if lo <= m <= hi and m not in billed)
        if gaps:
            rows = te_m.loc[(te_m["client"] == client) & te_m["m"].isin(gaps), SRC_ROW].tolist()
            out.append(_problem("month_without_invoice", WARNING, "time_entries", rows,
                                f"'{client}' has hours but no invoice in {', '.join(map(str, gaps))}"))
    return out


def _staff_costs(tables, settings):
    te = tables.get("time_entries")
    if te is None or settings is None:
        return []
    costs = settings.get("staff_costs") or {}
    out = []
    for staff in sorted(set(te["staff"].dropna()) - set(costs)):
        rows = te.loc[te["staff"] == staff, SRC_ROW].tolist()
        out.append(_problem("staff_without_cost", ERROR, "time_entries", rows,
                            f"No hourly cost set for '{staff}'"))
    return out


def validate_inputs(tables, settings=None, merged_names=None):
    """Return a list of problems, errors first. Nothing is changed or dropped."""
    problems = (_unreadable(tables) + _staff_costs(tables, settings) + _bad_values(tables) +
                _duplicates(tables) + _client_coverage(tables) + _invoice_gaps(tables))
    for display, spellings in (merged_names or {}).items():
        problems.append(_problem("name_variants_merged", INFO, "all", [],
                                 f"Treated as one client '{display}': {', '.join(repr(s) for s in spellings)}"))
    order = {ERROR: 0, WARNING: 1, INFO: 2}
    return sorted(problems, key=lambda p: order[p["severity"]])


def exclude_rows(tables, exclusions):
    """Remove only the rows the owner chose: {table: [_src_row, ...]}. Returns new tables."""
    out = dict(tables)
    for table, rows in exclusions.items():
        if rows and table in out:
            out[table] = out[table][~out[table][SRC_ROW].isin(rows)].reset_index(drop=True)
    return out


def has_errors(problems):
    return any(p["severity"] == ERROR for p in problems)


def summary(problems):
    return pd.DataFrame([{k: (len(v) if k == "rows" else v) for k, v in p.items()} for p in problems])
