"""Builds the clean simulated agency: staff, clients and the three tables.

Planted data problems and messy headers are added later, in messy.py.
"""
import numpy as np
import pandas as pd

from generator import params as P
from generator.messages import make_message
from generator.names import (CLIENT_FIRST, CLIENT_SECOND, CLIENT_SUFFIX,
                             SENIOR_ROLES, STAFF, TASK_TYPES)


def months():
    return list(pd.period_range(P.START_MONTH, periods=P.N_MONTHS, freq="M"))


def make_staff(rng):
    rows = []
    for name, role in STAFF[:P.N_STAFF]:
        lo, hi = (80, P.STAFF_COST_RANGE[1]) if role in SENIOR_ROLES else (P.STAFF_COST_RANGE[0], 75)
        rows.append({"staff": name, "role": role, "senior": role in SENIOR_ROLES,
                     "hourly_cost": float(rng.integers(lo, hi + 1))})
    return pd.DataFrame(rows)


def _client_names(rng, n):
    pairs = [(a, b) for a in CLIENT_FIRST for b in CLIENT_SECOND]
    picks = rng.choice(len(pairs), size=n, replace=False)
    names, used_first = [], set()
    for i in picks:
        first, second = pairs[i]
        if first in used_first:  # keep names easy to tell apart
            continue
        used_first.add(first)
        names.append(f"{first} {second}{CLIENT_SUFFIX[int(rng.integers(len(CLIENT_SUFFIX)))]}")
    while len(names) < n:  # fallback if too many first words clashed
        first, second = pairs[int(rng.integers(len(pairs)))]
        name = f"{first} {second} Group"
        if name not in names:
            names.append(name)
    return names[:n]


def _type_list(n):
    """Primary type per client, in a fixed order before shuffling."""
    fixed = ["new"] * P.N_NEW + ["no_invoices"] * P.N_NO_INVOICES
    rest = n - len(fixed)
    counts = {t: int(round(s * rest)) for t, s in P.TYPE_SHARES.items() if t != "healthy"}
    counts["healthy"] = rest - sum(counts.values())
    types = fixed[:]
    for t, c in counts.items():
        types += [t] * c
    return types


def make_clients(rng, n, staff):
    types = _type_list(n)
    rng.shuffle(types)
    names = _client_names(rng, n)
    seniors = staff.index[staff["senior"]].tolist()
    juniors = staff.index[~staff["senior"]].tolist()
    creep_idx = [i for i, t in enumerate(types) if t == "scope_creep"]
    overlap = set(rng.choice(creep_idx, size=min(P.N_OVERLAP, len(creep_idx)), replace=False).tolist())

    clients = []
    for i, (name, ctype) in enumerate(zip(names, types)):
        tags = [ctype] + (["slow_payer"] if i in overlap else [])
        c = {"client": name, "types": tags, "start": 0, "end": P.N_MONTHS - 1}
        if ctype == "new":
            c["start"] = P.N_MONTHS - int(rng.integers(1, 3))
        elif ctype not in ("big_loss",) and rng.random() < 0.2:
            c["start"] = int(rng.integers(1, 9))

        if ctype == "big_loss":
            mix = list(rng.choice(seniors, size=min(3, len(seniors)), replace=False)) + [int(rng.choice(juniors))]
            c["base_hours"] = float(rng.uniform(120, 200))
            c["nonbill"] = float(rng.uniform(0.30, 0.45))
        elif ctype == "no_invoices":
            mix = [int(rng.choice(juniors))]
            c["base_hours"] = float(rng.uniform(5, 15))
            c["nonbill"] = 1.0
        else:
            k = int(rng.integers(2, 5))
            pool = juniors + seniors[:1]
            mix = list(rng.choice(pool, size=min(k, len(pool)), replace=False))
            c["base_hours"] = float(rng.uniform(20, 80))
            c["nonbill"] = float(rng.uniform(0.05, 0.15))
        weights = rng.dirichlet(np.ones(len(mix)))
        c["staff_mix"] = [(staff.loc[s, "staff"], float(w)) for s, w in zip(mix, weights)]
        avg_cost = sum(staff.loc[s, "hourly_cost"] * w for s, w in zip(mix, weights))
        monthly_cost = c["base_hours"] * avg_cost * P.OVERHEAD

        if ctype in ("scope_creep", "decline", "big_loss") or rng.random() < 0.6:
            c["billing"] = "retainer"
        else:
            c["billing"] = "hourly"
        if ctype == "big_loss":
            margin = float(rng.uniform(-0.30, -0.08))
        elif ctype in ("scope_creep", "decline"):
            margin = float(rng.uniform(0.25, 0.35))
        elif ctype == "slow_payer":
            margin = float(rng.uniform(0.15, 0.30))
        else:
            margin = float(rng.uniform(*P.HEALTHY_MARGIN))
        c["planned_margin"] = margin
        c["fee"] = round(monthly_cost / (1 - margin), -1)
        if ctype != "no_invoices":
            c["bill_rate"] = round(avg_cost * P.OVERHEAD / ((1 - margin) * (1 - c["nonbill"])), 0)

        if ctype == "scope_creep":
            c["creep_start"] = int(rng.integers(6, 11))
            c["creep_growth"] = float(rng.uniform(*P.CREEP_MONTHLY_GROWTH))
        if ctype == "decline":
            c["decline_start"] = int(rng.integers(4, 9))
            c["decline_drop"] = float(rng.uniform(*P.DECLINE_MONTHLY_DROP))
        slow = "slow_payer" in tags
        c["pay_days"] = float(rng.uniform(*(P.SLOW_PAY_DAYS if slow else P.NORMAL_PAY_DAYS)))
        c["unpaid_prob"] = 0.12 if slow else 0.01
        c["request_rate"] = float(rng.uniform(1, 4))
        clients.append(c)
    return clients


def _hours_factor(c, m):
    if "creep_start" in c and m > c["creep_start"]:
        return (1 + c["creep_growth"]) ** (m - c["creep_start"])
    return 1.0


def _nonbill(c, m):
    if "creep_start" in c and m > c["creep_start"]:
        return min(0.6, c["nonbill"] + 0.015 * (m - c["creep_start"]))
    return c["nonbill"]


def _rand_day(rng, period):
    return period.start_time + pd.Timedelta(days=int(rng.integers(period.days_in_month)))


def simulate(rng, clients):
    """Return clean invoices, time_entries and requests, plus request labels."""
    ms = months()
    as_of = pd.Timestamp(P.AS_OF)
    inv, te, rq = [], [], []
    inv_no = 1000
    for c in clients:
        for m in range(c["start"], c["end"] + 1):
            per = ms[m]
            season = P.DECEMBER_FACTOR if per.month == 12 else 1.0
            hours = c["base_hours"] * season * _hours_factor(c, m) * float(rng.lognormal(0, P.HOUR_NOISE))
            k = max(1, int(round(hours / 3.5)))
            split = rng.dirichlet(np.ones(k)) * hours
            names = [s for s, _ in c["staff_mix"]]
            w = np.array([w for _, w in c["staff_mix"]])
            nb = _nonbill(c, m)
            billable_hours = 0.0
            for h in split:
                h = max(0.25, round(h * 4) / 4)
                billable = bool(rng.random() >= nb)
                billable_hours += h if billable else 0
                te.append({"client": c["client"], "staff": names[int(rng.choice(len(names), p=w))],
                           "work_date": _rand_day(rng, per), "hours": h,
                           "task_type": TASK_TYPES[int(rng.integers(len(TASK_TYPES)))],
                           "billable": billable})

            # Invoices: retainers billed on the 1st of the month; hourly work
            # billed early the next month (so work and invoice months differ).
            amount, inv_date = None, None
            if "no_invoices" in c["types"]:
                pass
            elif c["billing"] == "retainer":
                fee = c["fee"]
                if "decline_start" in c and m > c["decline_start"]:
                    fee = round(fee * (1 - c["decline_drop"]) ** (m - c["decline_start"]), -1)
                amount, inv_date = fee, per.start_time
            elif m + 1 < P.N_MONTHS:
                amount = round(billable_hours * c["bill_rate"], 2)
                inv_date = ms[m + 1].start_time + pd.Timedelta(days=int(rng.integers(0, 5)))
            if amount:
                inv_no += 1
                due = inv_date + pd.Timedelta(days=P.PAYMENT_TERMS_DAYS)
                paid = None
                if rng.random() >= c["unpaid_prob"]:
                    delay = max(0.0, rng.normal(c["pay_days"], 8))
                    paid = inv_date + pd.Timedelta(days=int(delay))
                    if paid > as_of:
                        paid = None
                inv.append({"invoice_id": f"INV-{inv_no}", "client": c["client"],
                            "invoice_date": inv_date, "amount": float(amount),
                            "due_date": due, "paid_date": paid})

            # Requests
            lam = c["request_rate"] * _hours_factor(c, m)
            for _ in range(int(rng.poisson(lam))):
                if "creep_start" in c and m > c["creep_start"]:
                    p_extra = min(0.6, 0.15 + 0.03 * (m - c["creep_start"]))
                else:
                    p_extra = 0.08
                r = rng.random()
                label = "extra_unpaid" if r < p_extra else ("unclear" if r < p_extra + 0.17 else "in_scope")
                rq.append({"client": c["client"], "request_date": _rand_day(rng, per),
                           "channel": ["email", "slack", "phone", "ticket", "other"][int(rng.choice(5, p=[.45, .25, .1, .15, .05]))],
                           "_label": label})
    return pd.DataFrame(inv), pd.DataFrame(te), pd.DataFrame(rq)


def add_messages(rng, requests, bank):
    requests = requests.copy()
    requests["message"] = [make_message(lbl, rng, bank) for lbl in requests["_label"]]
    return requests


def truth_profit(invoices, time_entries, staff):
    """Planted true profit per client per month, from the clean tables.

    Uses the same definitions as D-11 so it can serve as a cross-check.
    """
    as_of = pd.Timestamp(P.AS_OF)
    cost = staff.set_index("staff")["hourly_cost"]
    te = time_entries.assign(month=time_entries["work_date"].dt.to_period("M"))
    te["labour_cost"] = te["hours"] * te["staff"].map(cost) * P.OVERHEAD
    inv = invoices.assign(month=invoices["invoice_date"].dt.to_period("M"))
    end = inv["paid_date"].fillna(as_of)
    days_late = (end - inv["due_date"]).dt.days.clip(lower=0)
    inv["late_cost"] = inv["amount"] * P.LATE_RATE * days_late / 365
    rev = inv.groupby(["client", "month"])[["amount", "late_cost"]].sum()
    lab = te.groupby(["client", "month"])[["labour_cost"]].sum()
    out = rev.join(lab, how="outer").fillna(0.0)
    out["profit"] = out["amount"] - out["labour_cost"] - out["late_cost"]
    return out.rename(columns={"amount": "revenue"}).reset_index()
