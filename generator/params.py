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

# --- Realism additions (D-13) ---
# Clients that change type partway through.
P_HEALTHY_TO_CREEP = 0.25       # healthy client develops scope creep
P_HEALTHY_TO_DECLINE = 0.15     # healthy client starts to decline
LATE_SWITCH_MONTHS = (12, 20)   # month index where the change starts
P_SLOW_PAYER_RECOVERS = 0.3
RECOVER_MONTHS = (10, 18)
CREEP_START_JUMP = (1.0, 1.25)  # one-off jump in hours when creep starts

# One-off fee change (repricing) for some clients.
P_FEE_STEP = 0.3
FEE_STEP_RANGE = (0.85, 1.20)

# Clients joining and leaving.
P_LATE_START = 0.3
LATE_START_MONTHS = (1, 16)
P_CHURN = 0.12
CHURN_MONTHS = (10, 21)

# Agency-wide events.
SUMMER_FACTOR = 0.85            # July and August hours
STAFF_LEAVER = "Tom Becker"     # leaves at STAFF_CHANGE_MONTH
STAFF_HIRE = ("Kai Moreno", "developer")
STAFF_CHANGE_MONTH = 12
HOLIDAY_MONTHS_PER_YEAR = 2     # per staff member; half their work moves to a colleague

# Busy and quiet spells: noise that carries over from month to month.
SPELL_PERSISTENCE = 0.6
SPELL_SD = 0.12
MONTH_NOISE_SD = 0.08

# One-off projects.
P_ONE_OFF_PROJECT = 0.03        # per client per month
ONE_OFF_VALUE = (2000, 10000)

# Services covered per client (D-17).
SERVICES_PER_CLIENT = (3, 5)
