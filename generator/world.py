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
    """Staff list, including the new hire who replaces the leaver (D-13)."""
    rows = []
    for name, role in STAFF[:P.N_STAFF] + [P.STAFF_HIRE]:
        lo, hi = (80, P.STAFF_COST_RANGE[1]) if role in SENIOR_ROLES else (P.STAFF_COST_RANGE[0], 75)
        rows.append({"staff": name, "role": role, "senior": role in SENIOR_ROLES,
                     "hourly_cost": float(rng.integers(lo, hi + 1))})
    return pd.DataFrame(rows)


def make_holidays(rng, staff):
    """Set of (staff name, month index) when that person is on holiday."""
    out = set()
    for name in staff["staff"]:
        for year_start in range(0, P.N_MONTHS, 12):
            for m in rng.choice(12, size=P.HOLIDAY_MONTHS_PER_YEAR, replace=False):
                out.add((name, year_start + int(m)))
    return out


def _staff_at(name, m):
    """The leaver's work goes to the new hire from the change month on."""
    if name == P.STAFF_LEAVER and m >= P.STAFF_CHANGE_MONTH:
        return P.STAFF_HIRE[0]
    return name


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


def _rint(rng, lo, hi):
    """Random integer from lo to hi, both included."""
    return int(rng.integers(lo, hi + 1))


def make_clients(rng, n, staff):
    types = _type_list(n)
    rng.shuffle(types)
    names = _client_names(rng, n)
    pool_staff = staff[staff["staff"] != P.STAFF_HIRE[0]]
    seniors = pool_staff.index[pool_staff["senior"]].tolist()
    juniors = pool_staff.index[~pool_staff["senior"]].tolist()
    creep_idx = [i for i, t in enumerate(types) if t == "scope_creep"]
    overlap = set(rng.choice(creep_idx, size=min(P.N_OVERLAP, len(creep_idx)), replace=False).tolist())

    clients = []
    for i, (name, ctype) in enumerate(zip(names, types)):
        tags = [ctype] + (["slow_payer"] if i in overlap else [])
        c = {"client": name, "types": tags, "start": 0, "end": P.N_MONTHS - 1}

        # Joining and leaving.
        if ctype == "new":
            c["start"] = P.N_MONTHS - _rint(rng, 1, 2)
        elif ctype != "big_loss" and rng.random() < P.P_LATE_START:
            c["start"] = _rint(rng, *P.LATE_START_MONTHS)
        if ctype != "new" and rng.random() < P.P_CHURN:
            lo = max(c["start"] + 3, P.CHURN_MONTHS[0])
            if lo <= P.CHURN_MONTHS[1]:
                c["end"] = _rint(rng, lo, P.CHURN_MONTHS[1])
                tags.append("churned")

        if ctype == "big_loss":
            mix = list(rng.choice(seniors, size=min(3, len(seniors)), replace=False)) + [int(rng.choice(juniors))]
            c["base_hours"] = float(rng.uniform(120, 200))
            c["nonbill"] = float(rng.uniform(0.30, 0.45))
        elif ctype == "no_invoices":
            mix = [int(rng.choice(juniors))]
            c["base_hours"] = float(rng.uniform(5, 15))
            c["nonbill"] = 1.0
        else:
            k = _rint(rng, 2, 4)
            pool = juniors + seniors[:1]
            mix = list(rng.choice(pool, size=min(k, len(pool)), replace=False))
            c["base_hours"] = float(rng.uniform(20, 80))
            c["nonbill"] = float(rng.uniform(0.05, 0.15))
        weights = rng.dirichlet(np.ones(len(mix)))
        c["staff_mix"] = [(staff.loc[s, "staff"], float(w)) for s, w in zip(mix, weights)]
        c["avg_cost"] = float(sum(staff.loc[s, "hourly_cost"] * w for s, w in zip(mix, weights)))
        monthly_cost = c["base_hours"] * c["avg_cost"] * P.OVERHEAD

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
            c["bill_rate"] = round(c["avg_cost"] * P.OVERHEAD / ((1 - margin) * (1 - c["nonbill"])), 0)

        # Healthy clients that go wrong partway through.
        if ctype == "healthy":
            r = rng.random()
            switch = _rint(rng, *P.LATE_SWITCH_MONTHS)
            if switch < c["end"] - 2:
                if r < P.P_HEALTHY_TO_CREEP:
                    ctype_effect = "scope_creep"
                    tags.append("late_scope_creep")
                elif r < P.P_HEALTHY_TO_CREEP + P.P_HEALTHY_TO_DECLINE:
                    ctype_effect = "decline"
                    tags.append("late_decline")
                else:
                    ctype_effect = None
                if ctype_effect == "scope_creep":
                    c["creep_start"] = switch
                elif ctype_effect == "decline":
                    c["decline_start"] = switch
        if ctype == "scope_creep":
            c["creep_start"] = _rint(rng, 6, 10)
        if "creep_start" in c:
            c["creep_growth"] = float(rng.uniform(*P.CREEP_MONTHLY_GROWTH))
            c["creep_jump"] = float(rng.uniform(*P.CREEP_START_JUMP))
        if ctype == "decline":
            c["decline_start"] = _rint(rng, 4, 8)
        if "decline_start" in c:
            c["decline_drop"] = float(rng.uniform(*P.DECLINE_MONTHLY_DROP))

        # One-off repricing.
        if ctype != "no_invoices" and rng.random() < P.P_FEE_STEP and c["start"] + 2 < c["end"]:
            c["fee_step_month"] = _rint(rng, c["start"] + 2, c["end"])
            c["fee_step"] = float(rng.uniform(*P.FEE_STEP_RANGE))
            tags.append("repriced")

        slow = "slow_payer" in tags
        c["pay_days"] = float(rng.uniform(*(P.SLOW_PAY_DAYS if slow else P.NORMAL_PAY_DAYS)))
        if slow and rng.random() < P.P_SLOW_PAYER_RECOVERS:
            c["recover_month"] = _rint(rng, *P.RECOVER_MONTHS)
            c["pay_days_after"] = float(rng.uniform(*P.NORMAL_PAY_DAYS))
            tags.append("recovered_payer")
        c["unpaid_prob"] = 0.12 if slow else 0.01
        c["request_rate"] = float(rng.uniform(1, 4))
        clients.append(c)
    return clients


def _hours_factor(c, m):
    """Growth in hours from scope creep: a jump at the start, then steady growth."""
    if "creep_start" in c and m > c["creep_start"]:
        return c["creep_jump"] * (1 + c["creep_growth"]) ** (m - c["creep_start"])
    return 1.0


def _nonbill(c, m):
    if "creep_start" in c and m > c["creep_start"]:
        return min(0.6, c["nonbill"] + 0.015 * (m - c["creep_start"]))
    return c["nonbill"]


def _price_factor(c, m):
    f = 1.0
    if "decline_start" in c and m > c["decline_start"]:
        f *= (1 - c["decline_drop"]) ** (m - c["decline_start"])
    if "fee_step_month" in c and m >= c["fee_step_month"]:
        f *= c["fee_step"]
    return f


def _pay_days(c, m):
    if "recover_month" in c and m >= c["recover_month"]:
        return c["pay_days_after"]
    return c["pay_days"]


def _season(period):
    if period.month == 12:
        return P.DECEMBER_FACTOR
    if period.month in (7, 8):
        return P.SUMMER_FACTOR
    return 1.0


def _rand_day(rng, period):
    return period.start_time + pd.Timedelta(days=int(rng.integers(period.days_in_month)))


def _make_invoice(rng, c, m, amount, inv_date, as_of, inv_no):
    due = inv_date + pd.Timedelta(days=P.PAYMENT_TERMS_DAYS)
    paid = None
    if rng.random() >= c["unpaid_prob"]:
        delay = max(0.0, rng.normal(_pay_days(c, m), 8))
        paid = inv_date + pd.Timedelta(days=int(delay))
        if paid > as_of:
            paid = None
    return {"invoice_id": f"INV-{inv_no}", "client": c["client"], "invoice_date": inv_date,
            "amount": float(amount), "due_date": due, "paid_date": paid}


def simulate(rng, clients, holidays, staff):
    """Return clean invoices, time_entries and requests (with a hidden _label column)."""
    ms = months()
    as_of = pd.Timestamp(P.AS_OF)
    inv, te, rq = [], [], []
    inv_no = 1000
    all_staff = [s for s in staff["staff"] if s != P.STAFF_HIRE[0]]
    for c in clients:
        names = [s for s, _ in c["staff_mix"]]
        w = np.array([w for _, w in c["staff_mix"]])
        spell = 0.0
        c["one_off_months"] = []
        for m in range(c["start"], c["end"] + 1):
            per = ms[m]
            spell = P.SPELL_PERSISTENCE * spell + float(rng.normal(0, P.SPELL_SD))
            noise = float(np.exp(spell + rng.normal(0, P.MONTH_NOISE_SD)))
            hours = c["base_hours"] * _season(per) * _hours_factor(c, m) * noise
            k = max(1, int(round(hours / 3.5)))
            split = rng.dirichlet(np.ones(k)) * hours
            nb = _nonbill(c, m)
            billable_hours = 0.0
            for h in split:
                h = max(0.25, round(h * 4) / 4)
                billable = bool(rng.random() >= nb)
                billable_hours += h if billable else 0
                who = names[int(rng.choice(len(names), p=w))]
                if (who, m) in holidays and rng.random() < 0.5:
                    others = [s for s in names if s != who] or [s for s in all_staff if s != who]
                    who = others[int(rng.integers(len(others)))]
                te.append({"client": c["client"], "staff": _staff_at(who, m),
                           "work_date": _rand_day(rng, per), "hours": h,
                           "task_type": TASK_TYPES[int(rng.integers(len(TASK_TYPES)))],
                           "billable": billable})

            # Invoices: retainers billed on the 1st of the month; hourly work
            # billed early the next month (so work and invoice months differ).
            if "no_invoices" not in c["types"]:
                amount, inv_date = None, None
                if c["billing"] == "retainer":
                    amount, inv_date = round(c["fee"] * _price_factor(c, m), -1), per.start_time
                elif m + 1 < P.N_MONTHS:
                    amount = round(billable_hours * c["bill_rate"] * _price_factor(c, m), 2)
                    inv_date = ms[m + 1].start_time + pd.Timedelta(days=int(rng.integers(0, 5)))
                if amount:
                    inv_no += 1
                    inv.append(_make_invoice(rng, c, m, amount, inv_date, as_of, inv_no))

                # One-off project: extra billed work, invoiced at month end.
                if rng.random() < P.P_ONE_OFF_PROJECT:
                    value = round(float(rng.uniform(*P.ONE_OFF_VALUE)), -2)
                    p_margin = float(rng.uniform(0.1, 0.4))
                    p_hours = value * (1 - p_margin) / (c["avg_cost"] * P.OVERHEAD)
                    for h in rng.dirichlet(np.ones(max(1, int(p_hours // 6)))) * p_hours:
                        who = names[int(rng.choice(len(names), p=w))]
                        te.append({"client": c["client"], "staff": _staff_at(who, m),
                                   "work_date": _rand_day(rng, per), "hours": max(0.25, round(h * 4) / 4),
                                   "task_type": "one-off project", "billable": True})
                    inv_no += 1
                    inv.append(_make_invoice(rng, c, m, value, per.end_time.normalize(), as_of, inv_no))
                    c["one_off_months"].append(str(per))

            # Requests
            lam = c["request_rate"] * _hours_factor(c, m) * _season(per)
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


def client_events(c):
    """Planted changes for one client, as month strings, for the truth file."""
    ms = months()
    keys = {"creep_start": "scope_creep_from", "decline_start": "decline_from",
            "fee_step_month": "repriced_in", "recover_month": "pays_on_time_from"}
    out = {label: str(ms[c[k]]) for k, label in keys.items() if k in c}
    if "fee_step" in c:
        out["reprice_factor"] = round(c["fee_step"], 3)
    out["first_month"] = str(ms[c["start"]])
    out["last_month"] = str(ms[c["end"]])
    out["one_off_project_months"] = c.get("one_off_months", [])
    return out


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
