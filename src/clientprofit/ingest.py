"""Loads input files into the fixed schema (D-11).

Headers are mapped to the schema by `propose_mapping` (owner confirms) and
`apply_mapping`. Client spellings are unified by `unify_client_names`.
Values that cannot be read are left empty for validate to report; no row
is dropped here.
"""
import re
from pathlib import Path

import pandas as pd

from clientprofit import schema

TRUE_WORDS = {"true", "t", "yes", "y", "1", "billable"}
FALSE_WORDS = {"false", "f", "no", "n", "0", "not billable", "non-billable"}


def _to_bool(value):
    text = str(value).strip().lower()
    if text in TRUE_WORDS:
        return True
    if text in FALSE_WORDS:
        return False
    return None


def coerce_types(df, table, src_file):
    """Give each schema column its type and add the tracking columns."""
    out = pd.DataFrame(index=df.index)
    columns = {**schema.TABLES, **schema.OPTIONAL_TABLES}[table]
    for col, kind in columns.items():
        raw = df[col] if col in df.columns else pd.Series(None, index=df.index, dtype=object)
        if kind == "date":
            out[col] = pd.to_datetime(raw.replace("", None), errors="coerce", format="mixed")
        elif kind == "float":
            out[col] = pd.to_numeric(raw, errors="coerce")
        elif kind == "bool":
            out[col] = raw.map(_to_bool)
        else:
            text = raw.where(raw.notna(), None).map(lambda v: v.strip() if isinstance(v, str) else v)
            out[col] = text.where(text.astype(bool), None)  # blank text counts as empty
    out[schema.SRC_FILE] = src_file
    out[schema.SRC_ROW] = range(2, len(df) + 2)  # spreadsheet row number (header is row 1)
    return out


def load_canonical(folder):
    """Read invoices, time_entries and requests from a folder of schema-named CSV files."""
    folder = Path(folder)
    tables = {}
    for table in schema.TABLES:
        path = folder / f"{table}.csv"
        if path.exists():
            raw = pd.read_csv(path, dtype=str, keep_default_na=False)
            tables[table] = coerce_types(raw, table, path.name)
    return tables


# ---- Column mapping (manual fallback and non-LLM baseline for benchmark 5) ----

# Header words that commonly mean each schema column, per table. Written by
# hand from accounting and time-tracking vocabulary. Matching is exact on the
# cleaned header, so a header not listed is left for the owner to map.
SYNONYMS = {
    "invoices": {
        "invoice_id": ["invoice id", "invoice number", "invoice no", "invoice", "inv no", "inv", "ref",
                       "reference", "num", "number", "id", "doc id", "document number"],
        "client": ["client", "client name", "customer", "customer name", "account", "company", "name",
                   "cust", "customer job"],
        "invoice_date": ["invoice date", "date", "issue date", "issued", "date issued", "created",
                         "billed on", "inv date", "inv dt", "posting date"],
        "amount": ["amount", "total", "invoice total", "net amount", "amt", "value", "amount due"],
        # D-31, added 2026-10-07 after the Pemberton check: words for costs passed through to a client.
        "direct_cost": ["direct cost", "direct costs", "cost of sales", "cogs", "pass through",
                        "pass through cost", "expenses", "expense", "materials", "materials cost",
                        "parts cost", "third party cost", "freelancer cost", "media cost", "ad spend"],
        "due_date": ["due date", "due", "due dt", "payment due", "due on"],
        "paid_date": ["paid date", "date paid", "paid on", "paid at", "payment date", "settled",
                      "received on", "pd dt", "clear date", "paid"],
    },
    "time_entries": {
        "client": ["client", "client name", "customer", "customer name", "account", "company", "cust",
                   "customer job"],
        "staff": ["staff", "staff member", "employee", "user", "person", "team member", "who", "emp",
                  "member", "worker", "staff name"],
        "work_date": ["date", "work date", "day", "when", "start date", "dt", "entry date"],
        "hours": ["hours", "hrs", "duration", "time", "time spent", "qty", "quantity"],
        "task_type": ["task", "task type", "activity", "act", "category", "tags", "service item",
                      "work type", "what", "service"],
        "billable": ["billable", "is billable", "billable yn", "bill", "chargeable", "charge client",
                     "billable status"],
    },
    "requests": {
        "client": ["client", "client name", "customer", "customer name", "account", "company", "name",
                   "cust"],
        "request_date": ["date", "request date", "date received", "received", "created", "timestamp",
                         "dt", "when", "sent"],
        "channel": ["channel", "source", "via", "medium", "method", "type", "ch", "how"],
        "message": ["message", "message text", "text", "body", "request", "content", "memo", "notes",
                    "msg", "description"],
    },
    "clients": {
        "client": ["client", "client name", "customer", "customer name", "account", "company", "name"],
        "services_covered": ["services covered", "services", "scope", "covered", "plan", "package"],
    },
}


def clean_header(header):
    """Lower case, drop text in brackets and punctuation: 'Amount (USD)' -> 'amount'."""
    text = re.sub(r"\(.*?\)", " ", str(header)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def propose_mapping(headers, table):
    """Suggest {header: schema column or None}. The owner confirms or corrects it."""
    lookup = {}
    for col, words in SYNONYMS[table].items():
        for w in words:
            lookup.setdefault(w, col)
    mapping, used = {}, set()
    for h in headers:
        col = lookup.get(clean_header(h))
        mapping[h] = col if col and col not in used else None
        if mapping[h]:
            used.add(col)
    return mapping


def missing_required(mapping, table):
    """Required schema columns the mapping does not cover."""
    required = schema.REQUIRED.get(table, ("client",))
    return [c for c in required if c not in mapping.values()]


def apply_mapping(raw, mapping, table, src_file):
    """Rename confirmed columns to the schema and type them. Unmapped columns are ignored."""
    renamed = raw.rename(columns={h: c for h, c in mapping.items() if c})
    return coerce_types(renamed, table, src_file)


def read_raw(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


# ---- Client names (D-11) ----

NAME_SUFFIXES = {"ltd", "limited", "inc", "incorporated", "llc", "co", "corp", "corporation"}


def client_key(name):
    """Trim, ignore case and punctuation, drop a trailing company suffix."""
    words = re.sub(r"[^\w\s&]", " ", str(name)).casefold().split()
    while len(words) > 1 and words[-1] in NAME_SUFFIXES:
        words = words[:-1]
    return " ".join(words)


def unify_client_names(tables):
    """Give every spelling of a client the same display name (its most common spelling).

    Returns new tables and {display name: [spellings]} for clients with more than one spelling.
    The original spelling is kept in `client_original`.
    """
    counts = {}
    for df in tables.values():
        for name in df["client"].dropna():
            counts.setdefault(client_key(name), {}).setdefault(name, 0)
            counts[client_key(name)][name] += 1
    display = {k: max(v.items(), key=lambda kv: kv[1])[0] for k, v in counts.items()}
    out = {}
    for t, df in tables.items():
        df = df.copy()
        df["client_original"] = df["client"]
        df["client"] = df["client"].map(lambda n: display[client_key(n)] if pd.notna(n) else n)
        out[t] = df
    merged = {display[k]: sorted(v) for k, v in counts.items() if len(v) > 1}
    return out, merged
