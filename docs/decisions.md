# Decisions

One entry per decision. Entries are never deleted or edited after the fact.
To change a decision, add a new entry and set the old one's status to
`Superseded by D-xx`. The only fields that may be updated later are
**Status**, **Actual measured effect**, **Evidence** and **Related decisions**.

Status values: `Confirmed` (the team agreed), `Assumed` (nobody has agreed yet),
`Superseded by D-xx`.

## Summary

| ID | Date | Decision | Status | Measured? |
|---|---|---|---|---|
| D-01 | 2026-10-04 | Enter the Business track | Confirmed | No |
| D-02 | 2026-10-04 | Build a client profit finder | Confirmed | No |
| D-03 | 2026-10-04 | Target user is a small agency (5-30 staff) | Assumed | No |
| D-04 | 2026-10-04 | One Python app with Streamlit | Assumed | No |
| D-05 | 2026-10-04 | Profit calculation uses no machine learning | Assumed | No |
| D-06 | 2026-10-04 | Forecast with LightGBM, baseline and drop gate | Assumed | No |
| D-07 | 2026-10-04 | The LLM never does arithmetic | Assumed | No |
| D-08 | 2026-10-04 | Generated data, kept separate from model code | Assumed | No |
| D-09 | 2026-10-04 | Fixed out-of-scope list | Assumed | No |
| D-10 | 2026-10-04 | Call graph generated with pyan3 as a text edge list | Assumed | Yes (toy code only) |
| D-11 | 2026-10-04 | Fixed input schema and profit definitions | Assumed | No |
| D-12 | 2026-10-04 | Data generator design | Superseded by D-13 | Yes (seed 42 run) |
| D-13 | 2026-10-04 | Make generated trends less clean | Assumed | Yes (seed 42 run) |
| D-14 | 2026-10-05 | LLM provider: Featherless AI behind one wrapper | Assumed | Yes (20-message smoke test) |

---

## D-01: Enter the Business track
- **ID:** D-01
- **Date:** 2026-10-04
- **Status:** Confirmed
- **Context:** The hackathon offers six tracks. One must be chosen before any idea work.
- **Options considered:**
  1. Business: turn business data into insights, predictions or recommendations.
  2. Cybersecurity: recognise, prevent, verify or respond to scams and fraud.
- **Decision:** Option 1, Business.
- **Factors that led to it:** Chosen by Vedant. Closest to the team lead's existing skills in prediction and data pipelines.
- **Trade-offs accepted:** Business is likely the more crowded track. The idea must be narrow to stand out.
- **Expected effect:** A project that doubles as a resume item for ML and data roles.
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-02

## D-02: Build a client profit finder
- **ID:** D-02
- **Date:** 2026-10-04
- **Status:** Confirmed
- **Context:** Common Business-track ideas (stock reorder, promo checker, sales dashboard with chatbot) are what most teams will build.
- **Options considered:**
  1. Client profit finder: rank clients by true profit and recommend one action each.
  2. Contract renewal finder.
  3. Quote price adviser.
  4. Broken-promise tracker.
  5. Decision scorecard.
- **Decision:** Option 1.
- **Factors that led to it:** A quick search found tools for software companies with finance teams (Cogs'z, Bruin) and a paid consulting build for small firms (Octavius), but no self-serve tool for small service businesses. The output is a decision with a dollar figure.
- **Trade-offs accepted:** The idea is not new. The pitch must rest on the unserved user, not originality. The search was quick, not a full market study.
- **Expected effect:** Judges can understand the result in under a minute: a ranked list with dollar figures and an action per client.
- **Actual measured effect:** Not measured yet.
- **Evidence:** Product pages for Cogs'z, Bruin and Octavius, read on 2026-10-04.
- **Related decisions:** D-01, D-03, D-05

## D-03: Target user is a small agency (5-30 staff)
- **ID:** D-03
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** The profit calculation needs hours spent per client. The user type decides which data exists.
- **Options considered:**
  1. Marketing or design agency.
  2. Clinic.
  3. Trades business.
- **Decision:** Option 1.
- **Factors that led to it:** Agencies already record hours per client.
- **Trade-offs accepted:** No teammate has confirmed knowing an agency from the inside, so the design rests on assumptions about how agencies work.
- **Expected effect:** Input files map cleanly to data an agency already has.
- **Actual measured effect:** Not measured yet.
- **Evidence:** None. Needs one conversation with a real agency owner.
- **Related decisions:** D-02, D-08

## D-04: One Python app with Streamlit
- **ID:** D-04
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** The build window is seven days. Team size and skills are not yet known.
- **Options considered:**
  1. Single Python app with Streamlit.
  2. React or Next.js front end with a Python API.
- **Decision:** Option 1.
- **Factors that led to it:** One code base, no time lost connecting two parts.
- **Trade-offs accepted:** The screen will look plainer than a custom front end.
- **Expected effect:** A working end-to-end flow by the end of Day 2.
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-09

## D-05: Profit calculation uses no machine learning
- **ID:** D-05
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** True profit per client is revenue minus the cost of hours and late payment. This is the core of the product.
- **Options considered:**
  1. Plain arithmetic in pandas or DuckDB, with a test for every calculation.
  2. A model that predicts profit directly.
- **Decision:** Option 1.
- **Factors that led to it:** Arithmetic is exact and every figure can be traced to rows. A model forced into arithmetic would be easy for judges to spot.
- **Trade-offs accepted:** The most important part of the product shows no ML skill.
- **Expected effect:** Exact match against 10 clients calculated by hand (benchmark 1).
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-06, D-07

## D-06: Forecast with LightGBM, baseline and drop gate
- **ID:** D-06
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** The product should warn about clients heading toward a loss. Data will be about 50 clients over 24 months, which is very little.
- **Options considered:**
  1. LightGBM on client-month rows, compared to "next quarter equals last quarter".
  2. Deep learning or a time-series library with many settings.
  3. No model: show trend lines only.
- **Decision:** Option 1, with a gate. If it does not beat the baseline by end of Day 3, fall back to option 3.
- **Factors that led to it:** Small tabular data suits gradient boosting. The gate protects the schedule.
- **Trade-offs accepted:** The project may ship with no trained model in it.
- **Expected effect:** Lower mean absolute error than the baseline on the last 6 months, using a split by time (benchmark 3).
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-05, D-08

## D-07: The LLM never does arithmetic
- **ID:** D-07
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** An LLM is useful for messy column names, labelling client requests and writing explanations, but can invent numbers.
- **Options considered:**
  1. LLM limited to column mapping, request labelling and explanations. All numbers come from code. An automatic check confirms every number in the text exists in the computed table.
  2. Let the LLM analyse the uploaded files directly.
- **Decision:** Option 1.
- **Factors that led to it:** One invented number in a "drop this client" recommendation would destroy trust.
- **Trade-offs accepted:** More code to write and test.
- **Expected effect:** Zero invented numbers in explanations (benchmark 6).
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-05

## D-08: Generated data, kept separate from model code
- **ID:** D-08
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** No real client data is available.
- **Options considered:**
  1. A generator with planted patterns, in a separate module whose parameters the model code cannot import. The README states which scores come from generated data.
  2. Wait for real data.
  3. Use generated data and present the scores as real-world accuracy.
- **Decision:** Option 1. If real anonymised data arrives, add it as a second test set.
- **Factors that led to it:** Work cannot wait for data. Option 3 is dishonest and a sharp judge would catch it.
- **Trade-offs accepted:** Ranking and forecast scores show the code works, not that it works on real businesses.
- **Expected effect:** Planted loss-making clients are found in the bottom 10 more often than when ranking by revenue (benchmark 2).
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-03, D-06

## D-09: Fixed out-of-scope list
- **ID:** D-09
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** A one-week build invites adding too much.
- **Options considered:**
  1. Exclude logins, live links to accounting or time-tracking tools, multiple companies, mobile layout, chat interface and automatic emails.
  2. Decide feature by feature during the week.
- **Decision:** Option 1.
- **Factors that led to it:** Each excluded item costs days and adds nothing to the core decision.
- **Trade-offs accepted:** The tool works from file uploads only.
- **Expected effect:** Feature freeze holds on Day 6.
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-04

## D-10: Call graph generated with pyan3 as a text edge list
- **ID:** D-10
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** `docs/execution.md` must include an auto-generated function call graph that always matches the code.
- **Options considered:**
  1. pyan3, with a script that writes a sorted "caller -> callee" list to `docs/callgraph.md`.
  2. code2flow.
  3. A picture rendered with Graphviz.
- **Decision:** Option 1.
- **Factors that led to it:** code2flow failed to install on Python 3.13. A text list holds no file paths, so it is the same on every machine and can be compared in CI with `--check`. Option 3 needs Graphviz installed and images cannot be compared line by line.
- **Trade-offs accepted:** A text list is harder to read than a picture. pyan3 reads the code without running it, so calls made through a registry or by name will be missing.
- **Expected effect:** `python scripts/gen_callgraph.py --check` fails whenever the code changes and the file was not regenerated.
- **Actual measured effect:** Works on a three-file toy package: correct edges, correct handling of `__init__`, and `--check` exits 1 after a code change. Not yet run on project code, because none exists.
- **Evidence:** `scripts/gen_callgraph.py`, tested with pyan3 2.8.1 on Python 3.13.16 on 2026-10-04.
- **Related decisions:** None.

## D-11: Fixed input schema and profit definitions
- **ID:** D-11
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** Column names in uploaded files will be messy. Every later stage needs one fixed set of columns, and the cost engine needs exact definitions so benchmark 1 can be checked by hand.
- **Options considered:**
  1. A small fixed schema of three tables, with two tracking columns (`_src_file`, `_src_row`) on every row, and written definitions for every figure.
  2. Keep the uploaded columns and map them at each stage as needed.
- **Decision:** Option 1. The schema is in `src/clientprofit/schema.py`:
  - invoices: `invoice_id`, `client`, `invoice_date`, `amount`, `due_date` (optional), `paid_date` (empty means unpaid)
  - time_entries: `client`, `staff`, `work_date`, `hours`, `task_type`, `billable`
  - requests: `client`, `request_date`, `channel`, `message`

  Definitions:
  - As-of date: the latest date in any of the three files.
  - Revenue month: month of the invoice date (D2c).
  - Labour cost: hours × staff hourly cost × `overhead_multiplier`. Non-billable hours count.
  - Due date: `due_date` if given, else invoice date + `payment_terms_days`.
  - Late cost: amount × `late_payment_annual_rate` × max(0, days late) ÷ 365, booked in the invoice month. Days late run to the paid date, or to the as-of date if unpaid.
  - Unpaid invoices still count as revenue. Invoices unpaid more than `unpaid_warning_days` past due get a warning (D2a).
  - `profit_if_overdue_unpaid`: profit with each such invoice removed completely, both its revenue and its late cost. Shown next to profit. Ranking does not use it (D2a addition).
  - Zero-revenue month: margin left empty and flagged. Its cost still counts in every total (D2d).
  - Months of data: months from the first to the last month with any invoice or hours, both ends included.
  - Clients with fewer than `min_months_for_ranking` months are not ranked and get no loss-making label (D2b).
  - Ranking: by profit over the 12 months ending in the as-of month. Loss-making: that figure is below 0 (D2b).
  - Forecast features use a 3-month rolling margin = sum of profit ÷ sum of revenue over the 3 months, not an average of monthly margins (D2c).
- **Factors that led to it:** Every figure must be traceable to rows. A hand check needs written rules. A $50,000 invoice that is never paid would otherwise make a client look profitable, so the worst-case figure is shown beside it.
- **Trade-offs accepted:** Monthly margin swings when work and invoice fall in different months; only the forecast features smooth this. Removing the late cost as well as the revenue in `profit_if_overdue_unpaid` was proposed by the assistant and not yet agreed by the team. Client names are matched by simple cleaning only (trim, ignore case, drop Ltd/Inc/LLC); anything else is shown to the owner to fix.
- **Expected effect:** The cost engine matches the hand-calculated file in `tests/fixtures/hand_calc/` exactly (benchmark 1).
- **Actual measured effect:** Not measured yet. The expected answers have not been filled in.
- **Evidence:** None yet.
- **Related decisions:** D-05, D-07, D-12

## D-12: Data generator design
- **ID:** D-12
- **Date:** 2026-10-04
- **Status:** Superseded by D-13
- **Context:** No real data (D-08). Benchmarks 2 to 5 need data with known answers.
- **Options considered:**
  1. A seeded generator in `generator/` with planted client types, planted data problems, 10 header styles and a truth file kept apart from the data.
  2. A few hand-made CSV files.
  3. A public dataset from another kind of business.
- **Decision:** Option 1.
  - 24 months (2024-10 to 2026-09), 40 to 60 clients (default 50), 12 staff.
  - Planted client types: healthy, looks big but loses money, slow payer, scope creep, steady decline, under 3 months of data, hours but no invoices, scope creep plus slow payer.
  - Retainer clients are invoiced on the 1st. Hourly clients are invoiced early the next month.
  - Planted problems: skipped invoices, negative hours, blank cells, duplicate rows, client name variants, a share of invoice dates written as "05 Mar 2025". All are listed in the truth file.
  - Main files use the "title" header style. All 10 styles are written to `header_variants/` with the true mapping in the truth file.
  - Request messages come from `generator/message_bank.json` if it exists (paraphrased once by an LLM, then committed), otherwise from templates. The truth file records which.
  - `label_sheet.csv`: 150 messages for hand labelling, 50 per generator label, with the label hidden.
  - Truth file: `data/truth/truth_seed<seed>.json`. Only the benchmark scripts may read it.
- **Factors that led to it:** Planted answers make benchmarks 2 to 5 scoreable. Splitting the label sheet 50/50/50 gives each class enough examples; a random 150 would hold only about 22 "extra work" messages. A test fails if `src/clientprofit` imports `generator`.
- **Trade-offs accepted:** Scores on generated data show the code works, not that it is accurate on real agencies. Dates use unambiguous formats only; DD/MM versus MM/DD confusion is not planted. Until the message bank exists, messages come from about 14 templates per label, so scope-creep scores on them would be too optimistic. The 50/50/50 split means precision on the label sheet is not the precision at real-world class shares.
- **Expected effect:** Planted loss-making clients rank near the bottom by profit and near the top by revenue.
- **Actual measured effect:** 50 clients, 14 loss-making by the D-11 rule (all 5 "looks big" clients, 6 of 7 scope creep, 2 of 5 decline, the no-invoice client), 2 unlabelled new clients. The 5 "looks big" clients are revenue ranks 1 to 5 of 49 invoiced clients. 3,029 requests (69% in-scope, 17% unclear, 15% extra). Run time 7.6 seconds. Because there are 14 loss-making clients, a bottom 10 can find at most 71% of them in benchmark 2.
- **Evidence:** `python scripts/generate_data.py --out data/generated --seed 42`, run on 2026-10-04. Label sheet from the same run: 150 rows, 50 per generator label.
- **Related decisions:** D-08, D-11, D-13

## D-13: Make generated trends less clean
- **ID:** D-13
- **Date:** 2026-10-04
- **Status:** Assumed
- **Context:** Under D-12, every client kept one type for all 24 months, every trend followed one smooth formula, no client left, and nothing affected all clients at once. Month-to-month noise was already large, but the shapes were too easy for a model to learn. Two items promised in D-12's design, one-off projects and staff holidays, had not been built.
- **Options considered:**
  1. Keep D-12 as it is.
  2. Add type changes partway through, step changes, clients joining and leaving, agency-wide events, noise that carries over from month to month, one-off projects and staff holidays.
  3. Option 2 plus a yearly staff pay rise.
- **Decision:** Option 2. Everything in D-12 stays except these additions (settings in `generator/params.py`):
  - 25% of healthy clients develop scope creep and 15% start to decline, starting in a random month from 12 to 20. 30% of slow payers start paying on time from month 10 to 18.
  - Scope creep starts with a jump of up to 25% in hours, then grows.
  - 30% of clients get one fee change of ×0.85 to ×1.20 (repricing).
  - 30% of clients start between month 1 and 16. 12% leave between month 10 and 21.
  - July and August hours ×0.85, as well as December ×0.75. One staff member leaves at month 12 and a new hire with a different cost takes over their work. Each staff member has 2 holiday months a year, in which half their work moves to a colleague.
  - Busy and quiet spells: each month's hours carry over 60% of the previous month's deviation.
  - One-off projects: a 3% chance per client per month of an extra invoice ($2,000 to $10,000) with matching extra hours.
  - The truth file records each client's planted changes by month (`events`) and the agency-wide events.
- **Factors that led to it:** A forecast that beats the baseline only on smooth trends proves nothing. Real clients change partway through, get repriced and leave.
- **Trade-offs accepted:** Benchmarks get harder, and the forecast will likely do worse against the baseline. The planted type no longer guarantees the outcome: the loss-making label comes from computed profit, as in D-11. Option 3 was rejected because the settings hold one hourly cost per staff member, so a pay rise would make the planted truth disagree with any cost engine by design. Every setting is still a guess, not taken from real agencies.
- **Expected effect:** Fewer clients follow a clean single-shape trend; benchmark 2 and 3 scores reflect noisier, more realistic data.
- **Actual measured effect:** Seed 42: 15 loss-making clients (D-12: 14). 4 of 5 "looks big" clients are loss-making; the fifth ended at +$933 over 12 months through noise and two one-off projects. These 5 are still revenue ranks 1 to 5. 12 of 23 healthy clients developed late scope creep. Over 300 seeds the rate is 23%, so seed 42 is high by chance; it was kept rather than choosing a seed. 2 clients left early, 15 were repriced, 3 slow payers recovered, 28 one-off projects. The typical month-to-month change in profit rose from 36% to 46% of the average for healthy clients, and the direction flipped 62% of the time (D-12: 68%), meaning more lasting swings.
- **Evidence:** `python scripts/generate_data.py --out data/generated --seed 42`, run on 2026-10-04, and a 300-seed count of `make_clients` on the same day.
- **Related decisions:** D-12, D-11, D-06

## D-14: LLM provider: Featherless AI behind one wrapper
- **ID:** D-14
- **Date:** 2026-10-05
- **Status:** Assumed
- **Context:** Column mapping, request labelling, the message bank and explanations need an LLM (D-07). The team has $25 of Featherless AI sponsor credit.
- **Options considered:**
  1. Featherless AI (open-weight models, sponsor credit).
  2. Anthropic Claude (pay per token, about $20 estimated for the week, no credit).
- **Decision:** Option 1, chosen by the team. All calls go through `src/clientprofit/llm.py`, which uses the provider's OpenAI-style chat completions endpoint through the Python standard library, so no extra package is added. The key is read from `FEATHERLESS_API_KEY` if set; otherwise a placeholder is sent, which the build environment's proxy replaces with the real key. Teammates and the deployed app set the variable. Before anything is built on it, one model is timed on 20 messages with `scripts/llm_smoke_test.py`. Model tested: `Qwen/Qwen2.5-14B-Instruct` (official release, concurrency cost 1, $0.108 / $0.28 per million input / output tokens, no thinking section in replies to strip).
- **Factors that led to it:** Free credit. Swapping providers later means adding one entry to `PROVIDERS` in `llm.py`.
- **Trade-offs accepted:** Open-weight models are likely weaker than frontier models at following a fixed output format, so replies are parsed strictly and unparseable replies are counted. Featherless limits how many calls run at once by plan, which may make labelling all requests slow (benchmark 7). The Featherless docs could not be read from the build environment; the endpoint, auth header and response shape were confirmed by real calls instead. Featherless sits behind Cloudflare, which blocks Python's default `Python-urllib` user agent (error 1010), so the wrapper sends `clientprofit/0.1`.
- **Expected effect:** Under 3 seconds per call; at least 19 of 20 replies parse to a label.
- **Actual measured effect:** `Qwen/Qwen2.5-14B-Instruct`, 20 label-sheet messages, one call at a time: 20 of 20 calls succeeded, 20 of 20 replies parsed to a valid label. Median 1.24 s per call, slowest 1.76 s, 25.4 s in total. Labels given: 9 in-scope, 6 extra unpaid, 5 unclear. At this rate, labelling all 3,029 generated requests one at a time would take about 62 minutes, which does not fit benchmark 7 (under 60 seconds from upload to ranked list) unless requests are labelled several per call, in parallel, or once and cached. Accuracy is not measured here; it needs the teammate's labels (benchmark 4). The messages are still template text, so accuracy on them will flatter the model.
- **Evidence:** `python scripts/llm_smoke_test.py --model Qwen/Qwen2.5-14B-Instruct`, run on 2026-10-05 with no `FEATHERLESS_API_KEY` set (proxy-supplied key), on data from `python scripts/generate_data.py --out data/generated --seed 42`. Before that, one curl call to `/v1/chat/completions` with a placeholder key returned HTTP 200 in 1.7 s. `tests/test_llm.py` passes against a local fake server.
- **Related decisions:** D-07, D-12

---

## Facts confirmed on 2026-10-04 (not decisions)

- Team size is 4, the maximum allowed.
- Hackathon: ForgeHacks Online 2026. Started 3 October 12:00 PM. Deadline 10 October 12:00 PM EDT.
- Rule on earlier work: "Projects must be substantially created during the hackathon period. Pre-existing projects are not eligible unless clearly stated what was added during the event."
- AI coding tools are allowed. Code must be publicly viewable.
- Judging criteria, no weights given: real-world impact and relevance, technical implementation and AI use, innovation and creativity, execution and completeness, presentation and communication.
- Submission: public demo video of 2 to 4 minutes, public repo with README, written description, and screenshots, an architecture diagram or a deployment link.

## Open questions (not decisions yet)

- Which teammate takes which role, and what is each one good at?
- Which LLM key or sponsor credits will the team use?
- Can any teammate get real, anonymised data from a business?
