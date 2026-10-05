"""Entry point for the data generator: writes the CSV files and the truth file."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from generator import params as P
from generator.messages import load_bank
from generator.messy import HEADER_STYLES, MAIN_STYLE, plant_defects, write_style
from generator.world import (add_messages, assign_services, client_events, make_clients, make_holidays,
                             make_staff, months, services_text, simulate, truth_profit)

LABEL_SHEET_SIZE = 150


def _label_sheet(rng, requests, folder):
    """150 messages for a teammate to label by hand, 50 per generator label so
    each class has enough examples. The generator label is not shown."""
    per = LABEL_SHEET_SIZE // 3
    idx = []
    for label in ("in_scope", "extra_unpaid", "unclear"):
        pool = np.flatnonzero(requests["_label"].values == label)
        idx += rng.choice(pool, size=min(per, len(pool)), replace=False).tolist()
    idx = sorted(idx)
    sheet = pd.DataFrame({"row": idx, "channel": requests.loc[idx, "channel"].values,
                          "services_covered": requests.loc[idx, "_services"].values,
                          "message": requests.loc[idx, "message"].values, "label": ""})
    sheet.to_csv(folder / "label_sheet.csv", index=False)


def generate(seed, n_clients, out_dir, truth_dir):
    if not 40 <= n_clients <= 60:
        raise ValueError("n_clients must be between 40 and 60")
    rng = np.random.default_rng(seed)
    out_dir, truth_dir = Path(out_dir), Path(truth_dir)

    staff = make_staff(rng)
    clients = make_clients(rng, n_clients, staff)
    holidays = make_holidays(rng, staff)
    inv, te, rq = simulate(rng, clients, holidays, staff)
    # Services and message wording use their own random stream, so adding them
    # (D-17) did not change the planted profits measured in D-12 and D-13.
    rng_text = np.random.default_rng([seed, 1])
    assign_services(rng_text, clients)
    bank, bank_source = load_bank()
    rq = add_messages(rng_text, rq, bank, clients)
    profit = truth_profit(inv, te, staff)
    inv_m, te_m, rq_m, defects = plant_defects(rng, inv, te, rq, clients)

    tables = {"invoices": inv_m, "time_entries": te_m, "requests": rq_m}
    mappings = {MAIN_STYLE + " (main files)": write_style(rng, tables, MAIN_STYLE, out_dir, alt_dates=True)}
    for style in HEADER_STYLES:
        mappings[style] = write_style(rng, tables, style, out_dir / "header_variants" / style)
    staff[["staff", "hourly_cost"]].to_csv(out_dir / "staff_costs.csv", index=False)
    pd.DataFrame({"Client": [c["client"] for c in clients],
                  "Services Covered": [services_text(c) for c in clients]}).to_csv(
        out_dir / "clients.csv", index=False)
    _label_sheet(rng, rq_m, out_dir)

    last12 = sorted(profit["month"].unique())[-12:]
    truth_clients = {}
    for c in clients:
        rows = profit[profit["client"] == c["client"]]
        # D-11: months from the first to the last month with any invoice or hours.
        n_months = (rows["month"].max() - rows["month"].min()).n + 1
        p12 = float(rows[rows["month"].isin(last12)]["profit"].sum())
        truth_clients[c["client"]] = {
            "types": c["types"],
            "billing": c["billing"],
            "months_of_data": n_months,
            "events": client_events(c),
            "services_covered": c["services"],
            "profit_last_12m": round(p12, 2),
            # D-11: clients under the minimum get no loss-making label.
            "loss_making": (p12 < 0) if n_months >= P.MIN_MONTHS else None,
            "profit_by_month": {str(r.month): round(float(r.profit), 2) for r in rows.itertuples()},
        }

    truth = {
        "seed": seed,
        "as_of": P.AS_OF,
        "months": [str(m) for m in pd.period_range(P.START_MONTH, periods=P.N_MONTHS, freq="M")],
        "generator_settings": {"overhead_multiplier": P.OVERHEAD, "late_payment_annual_rate": P.LATE_RATE,
                               "payment_terms_days": P.PAYMENT_TERMS_DAYS},
        "agency_events": {
            "staff_change": {"leaves": P.STAFF_LEAVER, "replaced_by": P.STAFF_HIRE[0],
                             "month": str(months()[P.STAFF_CHANGE_MONTH])},
            "holidays": sorted(f"{name} {months()[m]}" for name, m in holidays),
            "slow_months": "July and August hours x0.85, December x0.75",
        },
        "message_source": bank_source,
        "clients": truth_clients,
        "request_labels": rq_m["_label"].tolist(),
        "header_mappings": mappings,
        "defects": defects,
    }
    truth_dir.mkdir(parents=True, exist_ok=True)
    truth_path = truth_dir / f"truth_seed{seed}.json"
    truth_path.write_text(json.dumps(truth, indent=1, default=str))
    return truth_path
