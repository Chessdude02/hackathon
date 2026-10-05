# Hand-calculation check (benchmark 1)

**Who fills this in:** a teammate who does not write `src/clientprofit/cost_engine.py`
and has not read it. Work it out in a spreadsheet or on paper from the rules below.
The point is to catch mistakes in the code, so do not copy numbers from the code.

## What to fill in

1. `expected_client_month.csv`: one row per client per month that has any invoice
   or any hours. Months are written `2026-01`. Round money to 2 decimals.
2. `expected_client_totals.csv`: one row per client. `loss_making` and `ranked`
   are `TRUE` or `FALSE`. Leave `loss_making` blank for clients that are not ranked.

Commit both files. The test will then compare the cost engine against them.

## Inputs

`invoices.csv`, `time_entries.csv`, `requests.csv` and `config.yaml` in this folder.
Use every row as written, including the negative-hours row.

## Rules (D-11 in docs/decisions.md)

- **As-of date:** the latest invoice, payment, work or request date in the three files (due dates do not count, D-18). Here it is 2026-03-31.
- **Revenue month:** the month of the invoice date, not the payment date.
- **Labour cost** for a row = hours × that staff member's hourly cost × `overhead_multiplier`.
  Non-billable hours count. Booked in the month of the work date.
- **Due date:** the `due_date` column if filled in, otherwise invoice date + `payment_terms_days`.
- **Days late** = (paid date, or the as-of date if unpaid) − due date. If below 0, use 0.
- **Late cost** for an invoice = amount × `late_payment_annual_rate` × days late ÷ 365.
  Booked in the invoice's month.
- **Profit** for a client-month = revenue − labour cost − late cost.
  A month with hours but no invoice has revenue 0 and its cost still counts.
- **Months of data** = number of months from the client's first to last month with
  any invoice or hours, counting both ends.
- **Ranked** = months of data ≥ `min_months_for_ranking`.
- **Profit last 12m** = sum of profit for the 12 months ending in the as-of month.
- **Loss-making** = ranked and profit last 12m < 0.
- **Overdue-unpaid invoice** = still unpaid on the as-of date and more than
  `unpaid_warning_days` days past its due date (exactly 90 does not count).
- **profit_if_overdue_unpaid** = profit last 12m as if each overdue-unpaid invoice
  had never been issued: its revenue is gone, and so is its late cost. Because the
  late cost was a cost, removing it raises profit. In numbers:
  profit last 12m − invoice amount + that invoice's late cost (D-16).
