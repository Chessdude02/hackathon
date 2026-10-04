"""Planted data problems and messy header styles."""
import pandas as pd

from generator import params as P

# style -> table -> canonical column -> header written to the file.
# Columns left out of a style are not written in that style.
HEADER_STYLES = {
    "snake": {
        "invoices": {"invoice_id": "invoice_id", "client": "client_name", "invoice_date": "invoice_date",
                     "amount": "amount", "due_date": "due_date", "paid_date": "date_paid"},
        "time_entries": {"client": "client_name", "staff": "staff_member", "work_date": "date",
                         "hours": "hours", "task_type": "task_type", "billable": "is_billable"},
        "requests": {"client": "client_name", "request_date": "date", "channel": "channel", "message": "message"},
    },
    "title": {
        "invoices": {"invoice_id": "Invoice ID", "client": "Client", "invoice_date": "Invoice Date",
                     "amount": "Amount", "due_date": "Due Date", "paid_date": "Date Paid"},
        "time_entries": {"client": "Client", "staff": "Staff Member", "work_date": "Date",
                         "hours": "Hours", "task_type": "Task Type", "billable": "Billable"},
        "requests": {"client": "Client", "request_date": "Date Received", "channel": "Channel", "message": "Message"},
    },
    "caps": {
        "invoices": {"invoice_id": "INV_NO", "client": "CUSTOMER", "invoice_date": "INV_DATE",
                     "amount": "TOTAL", "due_date": "DUE", "paid_date": "PAID_ON"},
        "time_entries": {"client": "CUSTOMER", "staff": "EMPLOYEE", "work_date": "WORK_DATE",
                         "hours": "HRS", "task_type": "ACTIVITY", "billable": "BILLABLE_YN"},
        "requests": {"client": "CUSTOMER", "request_date": "RECEIVED", "channel": "VIA", "message": "TEXT"},
    },
    "short": {
        "invoices": {"invoice_id": "Inv #", "client": "Cust", "invoice_date": "Inv Dt",
                     "amount": "Amt", "due_date": "Due Dt", "paid_date": "Pd Dt"},
        "time_entries": {"client": "Cust", "staff": "Emp", "work_date": "Dt",
                         "hours": "Hrs", "task_type": "Act", "billable": "Bill?"},
        "requests": {"client": "Cust", "request_date": "Dt", "channel": "Ch", "message": "Msg"},
    },
    "units": {
        "invoices": {"invoice_id": "Invoice Number", "client": "Client Name",
                     "invoice_date": "Invoice Date (YYYY-MM-DD)", "amount": "Amount (USD)",
                     "due_date": "Due Date (YYYY-MM-DD)", "paid_date": "Payment Date (YYYY-MM-DD)"},
        "time_entries": {"client": "Client Name", "staff": "Team Member", "work_date": "Date (YYYY-MM-DD)",
                         "hours": "Time (hours)", "task_type": "Work Type", "billable": "Billable (Y/N)"},
        "requests": {"client": "Client Name", "request_date": "Received (YYYY-MM-DD)",
                     "channel": "Channel", "message": "Message Text"},
    },
    "extra_cols": {
        "invoices": {"invoice_id": "invoice", "client": "client", "invoice_date": "issued",
                     "amount": "net_amount", "due_date": "due", "paid_date": "settled"},
        "time_entries": {"client": "client", "staff": "user", "work_date": "day",
                         "hours": "duration", "task_type": "category", "billable": "chargeable"},
        "requests": {"client": "client", "request_date": "created", "channel": "source", "message": "body"},
    },
    "shuffled": {
        "invoices": {"invoice_id": "Ref", "client": "Account", "invoice_date": "Billed On",
                     "amount": "Invoice Total", "paid_date": "Received On"},
        "time_entries": {"client": "Account", "staff": "Who", "work_date": "When",
                         "hours": "Time Spent", "task_type": "What", "billable": "Charge Client"},
        "requests": {"client": "Account", "request_date": "When", "channel": "How", "message": "Request"},
    },
    "harvest": {
        "invoices": {"invoice_id": "ID", "client": "Client", "invoice_date": "Issue Date",
                     "amount": "Amount", "due_date": "Due Date", "paid_date": "Paid Date"},
        "time_entries": {"client": "Client", "staff": "Person", "work_date": "Date",
                         "hours": "Hours", "task_type": "Task", "billable": "Billable?"},
        "requests": {"client": "Client", "request_date": "Date", "channel": "Source", "message": "Notes"},
    },
    "toggl": {
        "invoices": {"invoice_id": "Invoice", "client": "Customer", "invoice_date": "Created",
                     "amount": "Total", "due_date": "Due", "paid_date": "Paid at"},
        "time_entries": {"client": "Client", "staff": "User", "work_date": "Start date",
                         "hours": "Duration (h)", "task_type": "Tags", "billable": "Billable"},
        "requests": {"client": "Company", "request_date": "Timestamp", "channel": "Type", "message": "Content"},
    },
    "quickbooks": {
        "invoices": {"invoice_id": "Num", "client": "Name", "invoice_date": "Date",
                     "amount": "Amount", "due_date": "Due Date", "paid_date": "Date Paid"},
        "time_entries": {"client": "Customer:Job", "staff": "Employee", "work_date": "Date",
                         "hours": "Duration", "task_type": "Service Item", "billable": "Billable Status"},
        "requests": {"client": "Name", "request_date": "Date", "channel": "Method", "message": "Memo"},
    },
}
MAIN_STYLE = "title"

# Extra unused columns some styles add. Not part of the schema.
EXTRA_COLUMNS = {
    "extra_cols": {"invoices": ["currency", "tax", "notes"], "time_entries": ["project", "notes"],
                   "requests": ["priority"]},
    "shuffled": {"invoices": ["Terms"], "time_entries": ["Rate"], "requests": ["Status"]},
    "harvest": {"time_entries": ["Project", "Notes"]},
    "toggl": {"time_entries": ["Description", "Start time"]},
}
BILLABLE_TEXT = {"caps": ("Y", "N"), "short": ("y", "n"), "units": ("Y", "N"),
                 "quickbooks": ("Billable", "Not Billable"), "harvest": ("Yes", "No")}


def _variant(name, k):
    if k == 0:
        return name.upper()
    if k == 1:
        for suf in (" Ltd", " Inc", " LLC", " Co"):
            if name.endswith(suf):
                return name[: -len(suf)]
        return name + " Ltd"
    if k == 2:
        return name.replace(" ", "  ", 1)
    return name + " "


def plant_defects(rng, inv, te, rq, clients):
    """Add known data problems. Returns new tables and a list of what was planted."""
    defects = []
    inv, te, rq = inv.copy(), te.copy(), rq.copy()

    retainer_rows = inv.index[inv["client"].isin([c["client"] for c in clients if c["billing"] == "retainer"])]
    skip = rng.choice(retainer_rows, size=P.N_SKIPPED_INVOICES, replace=False)
    for i in skip:
        defects.append({"type": "skipped_invoice", "client": inv.loc[i, "client"],
                        "month": str(inv.loc[i, "invoice_date"].to_period("M"))})
    inv = inv.drop(index=skip).reset_index(drop=True)

    for i in rng.choice(len(te), size=P.N_NEGATIVE_HOURS, replace=False):
        te.loc[i, "hours"] = -te.loc[i, "hours"]
        defects.append({"type": "negative_hours", "table": "time_entries",
                        "client": te.loc[i, "client"], "hours": float(te.loc[i, "hours"])})

    for i in rng.choice(len(te), size=P.N_BLANK_TASK_TYPE, replace=False):
        te.loc[i, "task_type"] = None
        defects.append({"type": "blank_cell", "table": "time_entries", "column": "task_type",
                        "client": te.loc[i, "client"]})
    for i in rng.choice(len(rq), size=P.N_BLANK_CHANNEL, replace=False):
        rq.loc[i, "channel"] = None
        defects.append({"type": "blank_cell", "table": "requests", "column": "channel",
                        "client": rq.loc[i, "client"]})

    dup_te = te.iloc[rng.choice(len(te), size=P.N_DUP_TIME_ROWS, replace=False)]
    dup_inv = inv.iloc[rng.choice(len(inv), size=P.N_DUP_INVOICE_ROWS, replace=False)]
    for _, r in dup_te.iterrows():
        defects.append({"type": "duplicate_row", "table": "time_entries", "client": r["client"]})
    for _, r in dup_inv.iterrows():
        defects.append({"type": "duplicate_row", "table": "invoices", "client": r["client"],
                        "invoice_id": r["invoice_id"]})
    te = pd.concat([te, dup_te]).sort_values(["client", "work_date"], kind="stable").reset_index(drop=True)
    inv = pd.concat([inv, dup_inv]).sort_values(["client", "invoice_date"], kind="stable").reset_index(drop=True)

    invoiced = sorted(inv["client"].unique())
    picks = rng.choice(invoiced, size=P.N_NAME_VARIANT_CLIENTS, replace=False)
    for k, name in enumerate(picks):
        variant = _variant(name, k % 4)
        for table, df in (("invoices", inv), ("time_entries", te), ("requests", rq)):
            rows = df.index[df["client"] == name]
            chosen = rows[rng.random(len(rows)) < 0.25]
            df.loc[chosen, "client"] = variant
        defects.append({"type": "name_variant", "client": name, "variant": variant})

    return inv, te, rq, defects


def _fmt_date(series, rng, alt_share):
    out = []
    for v in series:
        if pd.isna(v):
            out.append("")
        elif rng.random() < alt_share:
            out.append(v.strftime("%d %b %Y"))
        else:
            out.append(v.strftime("%Y-%m-%d"))
    return out


def write_style(rng, tables, style, folder, alt_dates=False):
    """Write the three tables with one header style. Returns header -> canonical mapping."""
    folder.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for table, df in tables.items():
        cols = HEADER_STYLES[style][table]
        out = pd.DataFrame(index=df.index)
        for canon, header in cols.items():
            col = df[canon]
            if pd.api.types.is_datetime64_any_dtype(col):
                share = P.ALT_DATE_FORMAT_SHARE if (alt_dates and table == "invoices") else 0.0
                col = _fmt_date(col, rng, share)
            elif canon == "billable":
                yes, no = BILLABLE_TEXT.get(style, ("TRUE", "FALSE"))
                col = col.map({True: yes, False: no})
            out[header] = col
        for extra in EXTRA_COLUMNS.get(style, {}).get(table, []):
            out[extra] = ""
        if style == "shuffled":
            out = out[list(rng.permutation(out.columns))]
        out.to_csv(folder / f"{table}.csv", index=False)
        mapping[table] = {header: canon for canon, header in cols.items()}
    return mapping
