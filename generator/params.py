"""Generator settings. Only the generator and the benchmark scripts may read
this file. Code under src/clientprofit must never import it (D-08)."""

START_MONTH = "2024-10"      # first month of data
N_MONTHS = 24                # last month is 2026-09
AS_OF = "2026-09-30"         # truth is computed as of this date

N_CLIENTS_DEFAULT = 50       # allowed range 40-60
N_STAFF = 12
STAFF_COST_RANGE = (35, 110)  # hourly cost, dollars

# Used only to set fees and to compute the planted truth.
OVERHEAD = 1.3
PAYMENT_TERMS_DAYS = 30
LATE_RATE = 0.08
MIN_MONTHS = 3

# Share of clients per primary type. "new" and "no_invoices" are fixed counts.
TYPE_SHARES = {
    "healthy": 0.42,
    "big_loss": 0.10,
    "slow_payer": 0.15,
    "scope_creep": 0.15,
    "decline": 0.10,
}
N_NEW = 2           # under 3 months of data
N_NO_INVOICES = 1   # hours logged, never invoiced
N_OVERLAP = 2       # scope_creep clients that are also slow payers

HEALTHY_MARGIN = (0.25, 0.45)
CREEP_MONTHLY_GROWTH = (0.03, 0.06)
DECLINE_MONTHLY_DROP = (0.02, 0.04)
SLOW_PAY_DAYS = (60, 120)
NORMAL_PAY_DAYS = (10, 35)
HOUR_NOISE = 0.15
DECEMBER_FACTOR = 0.75

# Planted data problems (counts).
N_NEGATIVE_HOURS = 3
N_DUP_TIME_ROWS = 5
N_DUP_INVOICE_ROWS = 2
N_NAME_VARIANT_CLIENTS = 4
N_SKIPPED_INVOICES = 3
N_BLANK_TASK_TYPE = 3
N_BLANK_CHANNEL = 2
ALT_DATE_FORMAT_SHARE = 0.10
