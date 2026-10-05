"""The fixed column names and types for the three input tables (D-11).

Every loaded table also carries two tracking columns, `_src_file` and
`_src_row`, so each computed figure can be traced back to input rows.
"""

SRC_FILE = "_src_file"
SRC_ROW = "_src_row"
TRACKING_COLUMNS = (SRC_FILE, SRC_ROW)

# column name -> type name. Types: str, date, float, bool.
INVOICES = {
    "invoice_id": "str",
    "client": "str",
    "invoice_date": "date",
    "amount": "float",
    "due_date": "date",
    "paid_date": "date",
}
INVOICES_REQUIRED = ("client", "invoice_date", "amount", "paid_date")

TIME_ENTRIES = {
    "client": "str",
    "staff": "str",
    "work_date": "date",
    "hours": "float",
    "task_type": "str",
    "billable": "bool",
}
TIME_ENTRIES_REQUIRED = ("client", "staff", "work_date", "hours", "billable")

REQUESTS = {
    "client": "str",
    "request_date": "date",
    "channel": "str",
    "message": "str",
}
REQUESTS_REQUIRED = ("client", "request_date", "message")

TABLES = {
    "invoices": INVOICES,
    "time_entries": TIME_ENTRIES,
    "requests": REQUESTS,
}
REQUIRED = {
    "invoices": INVOICES_REQUIRED,
    "time_entries": TIME_ENTRIES_REQUIRED,
    "requests": REQUESTS_REQUIRED,
}

# Optional fourth input (D-17): what each client pays for, as free text.
CLIENTS = {
    "client": "str",
    "services_covered": "str",
}
OPTIONAL_TABLES = {"clients": CLIENTS}

CHANNELS = ("email", "slack", "phone", "ticket", "other")
REQUEST_LABELS = ("in_scope", "extra_unpaid", "unclear")
