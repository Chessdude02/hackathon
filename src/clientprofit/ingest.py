"""Loads input files into the fixed schema (D-11).

So far this reads files whose headers already match the schema. Mapping
messy headers to the schema is added later (ingest.map_columns).
Values that cannot be read are left empty for validate to report; no row
is dropped here.
"""
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
    for col, kind in schema.TABLES[table].items():
        raw = df[col] if col in df.columns else pd.Series(None, index=df.index, dtype=object)
        if kind == "date":
            out[col] = pd.to_datetime(raw.replace("", None), errors="coerce", format="mixed")
        elif kind == "float":
            out[col] = pd.to_numeric(raw, errors="coerce")
        elif kind == "bool":
            out[col] = raw.map(_to_bool)
        else:
            out[col] = raw.where(raw.notna(), None)
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
