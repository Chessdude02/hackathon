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
| D-06 | 2026-10-04 | Forecast with LightGBM, baseline and drop gate | Assumed | Yes (gate failed: baseline ships) |
| D-07 | 2026-10-04 | The LLM never does arithmetic | Assumed | No |
| D-08 | 2026-10-04 | Generated data, kept separate from model code | Assumed | No |
| D-09 | 2026-10-04 | Fixed out-of-scope list | Assumed | No |
| D-10 | 2026-10-04 | Call graph generated with pyan3 as a text edge list | Assumed | Yes (toy code only) |
| D-11 | 2026-10-04 | Fixed input schema and profit definitions | Assumed | No |
| D-12 | 2026-10-04 | Data generator design | Superseded by D-13 | Yes (seed 42 run) |
| D-13 | 2026-10-04 | Make generated trends less clean | Assumed | Yes (seed 42 run) |
| D-14 | 2026-10-05 | LLM provider: Featherless AI behind one wrapper | Assumed | Yes (20-message smoke test) |
| D-15 | 2026-10-05 | Label requests once, save labels, ranked list never waits for labels | Assumed | No |
| D-16 | 2026-10-05 | Worst-case profit removes an overdue invoice completely | Assumed | No |
| D-17 | 2026-10-05 | Optional "services covered" per client, given to the request labeller | Assumed | No |
| D-18 | 2026-10-05 | As-of date uses activity dates only, not due dates | Assumed | Yes (benchmark 1) |
| D-19 | 2026-10-05 | Rule-based column mapping, name cleaning and validation rules | Assumed | Yes (seed 42, circular) |
| D-20 | 2026-10-06 | PyYAML for config and a demo-folder setting for tests | Assumed | No |
| D-21 | 2026-10-06 | Forecast set-up: operating margin, time split, baseline ships | Assumed | Yes (benchmark 3) |
| D-22 | 2026-10-06 | Benchmark 4 result; prompt for clients without services fixed | Assumed | Yes (benchmark 4) |
| D-23 | 2026-10-06 | Ship the LLM labeller with services, as a reviewed suggestion | Assumed | Yes (benchmark 4) |
| D-24 | 2026-10-06 | Recommendation rules: one action per client, last 3 months, end only as last resort | Assumed | Yes (seed 42) |
| D-25 | 2026-10-06 | Requests optional; time-log warning; stop calling a down provider | Assumed | No |
| D-26 | 2026-10-06 | Explanations: facts from code, LLM writes words, number check with template fallback | Assumed | Yes (benchmark 6) |
| D-27 | 2026-10-06 | Benchmark 2 headline is bottom K, bottom 10 second | Assumed | Yes (benchmark 2, 3 seeds) |
| D-28 | 2026-10-06 | Deploy on Streamlit Community Cloud; app builds missing demo data; "demo only" line | Assumed | Yes (live app, 2026-10-07) |

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
- **Actual measured effect:** LightGBM did not beat the baseline on any of 3 generated datasets. Mean absolute error of next-quarter operating margin, last 6 months, time split: seed 42 baseline 0.143, LightGBM 0.172; seed 1 baseline 0.132, LightGBM 0.134; seed 2 baseline 0.147, LightGBM 0.181. The gate applies: LightGBM is dropped, the baseline ships with trend lines.
- **Evidence:** `python scripts/run_benchmarks.py` on 2026-10-06 (`out/benchmarks.json`), set-up in D-21.
- **Related decisions:** D-05, D-08, D-21

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
- **Related decisions:** D-05, D-07, D-12, D-16, D-18

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
- **Related decisions:** D-07, D-12, D-15

## D-15: Label requests once, save labels, ranked list never waits for labels
- **ID:** D-15
- **Date:** 2026-10-05
- **Status:** Assumed
- **Context:** D-14 measured 1.24 s per labelling call. Labelling all 3,029 generated requests one at a time would take about 62 minutes, far over the 60-second target in benchmark 7.
- **Options considered:**
  1. Label each message once, save the label, and reuse it. Only new messages are labelled live.
  2. Send 20 to 30 messages per call.
  3. Run calls in parallel up to the plan's concurrency limit.
- **Decision:** Option 1, approved by the team lead with these conditions:
  - Saved labels are keyed by message text. Messages not in the saved set are labelled live, in parallel, with a progress indicator.
  - The ranked list must not depend on labels. It is shown first; labels and anything built on them fill in afterwards.
  - Benchmark 7 measures upload to ranked list only. Labelling N new messages is timed and reported separately.
  - The README states that the demo data was labelled ahead of time. This is added when the demo labels are actually made, not before.

  Options 2 and 3 are set aside for now. Parallel calls are still used for new messages, as the first condition requires.
- **Factors that led to it:** No risk to label accuracy. Most messages an owner uploads again were already labelled.
- **Trade-offs accepted:** A first upload of a new agency's history is still slow to label; the ranked list does not wait, but scope-creep figures and the "cut scope" recommendation appear only when labelling finishes. Keying by message text alone means the same text gets the same label for every client; this holds only while the model sees no client-specific context (see the open "services covered" question). Saving labels means the saved file must be treated as data that can go stale if the prompt or model changes; the key must then include the model and prompt version, or the file is rebuilt.
- **Expected effect:** Upload to ranked list under 60 seconds regardless of how many requests there are. Re-uploading already-labelled data needs no LLM calls.
- **Actual measured effect:** Upload to ranked list, with no labelling in the path: 0.88 s for 50 clients (load, map, validate, rank) from the command line; 0.53 s from "Rank clients" to the ranked list on the screen. Labelling ahead of time: 2,599 new messages (2,601 requests) took 2,003 s with 2 calls in parallel (0.77 s per message), 1 fell back to the keyword label; a second run reused every saved label and took 2.5 s. A first attempt crashed at 590 messages on a dropped connection and saved nothing; fixed by retrying dropped connections and saving every 50 labels.
- **Evidence:** `python scripts/run_pipeline.py --data data/generated --out out/` on seed 42 data, and the screen driven with Playwright, both on 2026-10-05; `python scripts/label_requests.py --data data/generated`, run twice on 2026-10-06. The 62-minute figure comes from D-14's smoke test.
- **Related decisions:** D-14, D-07, D-17

## D-16: Worst-case profit removes an overdue invoice completely
- **ID:** D-16
- **Date:** 2026-10-05
- **Status:** Assumed
- **Context:** D-11 defines `profit_if_overdue_unpaid` as profit with each overdue-unpaid invoice "removed completely, both its revenue and its late cost", and notes the late-cost part was the assistant's proposal, not yet agreed. The hand-calculation README worded it as "take away its revenue and its late cost". The hand calculation for Delta Foods read that as subtracting both from profit (1,372.80), not as removing both (1,500.00).
- **Options considered:**
  1. Subtract both: profit − amount − late cost. Delta Foods: 4,436.40 − 3,000 − 63.60 = 1,372.80.
  2. Remove the invoice completely: profit − amount + late cost. Delta Foods: 4,436.40 − 3,000 + 63.60 = 1,500.00.
- **Decision:** Option 2, chosen by the team lead on 2026-10-05.
- **Factors that led to it:** The figure answers "what if this invoice is never paid?". An invoice that is never paid brings no revenue, and the late cost (the cost of waiting for that money) no longer applies. Option 1 counts the late cost twice.
- **Trade-offs accepted:** The worst-case figure is slightly less harsh than option 1. The hand-calculation answer for Delta Foods was changed from 1,372.80 to 1,500.00 after the hand calculation was done; the change follows from this rule, not from re-checking the arithmetic. The README rule was reworded so it can only be read one way.
- **Expected effect:** The cost engine and the hand calculation use the same rule; benchmark 1 can pass.
- **Actual measured effect:** Not measured yet.
- **Evidence:** `tests/fixtures/hand_calc/hand_calc_workbook_answered.xlsx` (original hand answer 1,372.80) and `tests/fixtures/hand_calc/expected_client_totals.csv` (1,500.00 under this rule).
- **Related decisions:** D-11

## D-17: Optional "services covered" per client, given to the request labeller
- **ID:** D-17
- **Date:** 2026-10-05
- **Status:** Assumed
- **Context:** The request labeller decides "in scope" from wording alone, without knowing what each client pays for. The same message can be routine for one client and extra work for another.
- **Options considered:**
  1. Keep labelling from wording alone.
  2. Add an optional free-text `services_covered` per client and pass it to the model with each message.
- **Decision:** Option 2, approved by the team lead on 2026-10-05.
  - Schema: a fourth, optional input `clients` with `client` (str) and `services_covered` (str, free text). Given as `clients.csv` or typed into an editable table on the settings screen (the table is built on Thursday; `clients.csv` first).
  - Clients without an entry are labelled from wording alone and marked "scope unknown".
  - Saved labels (D-15) are keyed by message text plus that client's `services_covered` text, not by message text alone. Editing a client's services re-labels that client's messages.
  - Generator: each client gets 3 to 5 covered items. In-scope messages name covered items; extra-work messages name items not covered. `clients.csv` is written; the label sheet gets a `services_covered` column so the human labeller sees what the model sees.
  - The message bank must keep the `{item}` slot when paraphrasing; a check rejects paraphrases that drop it.
  - The keyword baseline also gets the services text, so benchmark 4 compares like with like.
- **Factors that led to it:** Labels become about scope, not tone. Running the detector with and without services on the 150 hand-labelled messages gives a measured result for the "AI use" judging criterion.
- **Trade-offs accepted:** About 6 hours of work (5 before Wednesday). Part of any measured gain is circular, because the generator sets labels from the same services list the model sees; the README must say so. Owners must type services for each client, which is why the field is optional.
- **Expected effect:** Higher agreement with the human labels on benchmark 4 than labelling from wording alone.
- **Actual measured effect:** Not measured yet.
- **Evidence:** None yet.
- **Related decisions:** D-15, D-14, D-12

## D-18: As-of date uses activity dates only, not due dates
- **ID:** D-18
- **Date:** 2026-10-05
- **Status:** Assumed
- **Context:** D-11 defines the as-of date as "the latest date in any of the three files". The invoices file can carry explicit due dates, which may lie in the future.
- **Options considered:**
  1. Latest of every date column, due dates included (D-11 as written).
  2. Latest activity date: invoice date, paid date, work date or request date.
- **Decision:** Option 2.
- **Factors that led to it:** A future due date would move the as-of date past the last real activity, so unpaid invoices would be charged late cost for days that have not happened yet.
- **Trade-offs accepted:** Narrows D-11's wording. Identical result on the hand-calculation files.
- **Expected effect:** As-of date is never later than the last real activity.
- **Actual measured effect:** Benchmark 1: as-of date 2026-03-31, and the cost engine matches the hand calculation on all 29 client-month rows (revenue, labour cost, late cost, profit) and all 10 client totals (months of data, 12-month profit, worst-case profit, ranked, loss-making).
- **Evidence:** `pytest tests/test_cost_engine.py`, run on 2026-10-05: 23 passed (`test_benchmark1_*` and one test per calculation, including `test_as_of_ignores_due_dates`).
- **Related decisions:** D-11, D-16

## D-19: Rule-based column mapping, name cleaning and validation rules
- **ID:** D-19
- **Date:** 2026-10-05
- **Status:** Assumed
- **Context:** Uploaded files have messy headers, client spellings that differ between files, and errors. D-11 asked for confirmed mapping, simple name cleaning and a report that never drops rows silently.
- **Options considered:**
  1. Rule-based: a hand-written list of header words per schema column, exact match after cleaning; the LLM mapping (planned) is added on top, and this list stays as the fallback and the benchmark 5 baseline.
  2. LLM mapping only.
- **Decision:** Option 1 now, LLM later. Details:
  - Headers are lower-cased, text in brackets and punctuation removed, then matched exactly against `ingest.SYNONYMS`. Unmatched headers are left for the owner. Each schema column is used once.
  - Client names: trimmed, case and punctuation ignored, and one trailing suffix from Ltd, Limited, Inc, Incorporated, LLC, Co, Corp, Corporation dropped. This adds Co, Corp and Limited to D-11's list. Each client is shown under its most common spelling; the original is kept in `client_original`. Every merge is reported to the owner.
  - "Required" splits in two: a column that must exist (`schema.*_REQUIRED`) and a value every row needs (`schema.VALUE_REQUIRED`). An empty paid date is allowed (unpaid).
  - Duplicate invoices are suggested for exclusion. Identical time entries are only flagged, because two equal entries on one day can be genuine.
  - Blank text cells count as empty.
  - Rows leave the data only through `validate.exclude_rows`, with rows the owner picks.
- **Factors that led to it:** Works without the LLM, is explainable, and gives benchmark 5 a non-LLM baseline.
- **Trade-offs accepted:** The header list and the generator's 10 header styles were written by the same person (the assistant), so the 172 of 172 score below is circular and says nothing about real files. Benchmark 5 needs headers the assistant did not write (for example real Toggl, Harvest or QuickBooks export columns). Two different clients named, for example, "Acme Co" and "Acme Inc" would be merged; the report shows every merge so the owner can catch it.
- **Expected effect:** Planted data problems are reported; real exports map with few manual fixes.
- **Actual measured effect:** Seed 42: 172 of 172 headers across the 10 generated styles mapped correctly (circular, see above). On the main files: all 3 negative-hours rows, both duplicate invoices, the client with hours but no invoices, 2 of 3 skipped invoices (the third falls at the edge of the client's months), and all 5 blank optional cells were reported. All 4 planted name variants end up as one name each (one was only a trailing space, trimmed on load). 14 identical time-entry rows were flagged against 5 planted: the other 9 are identical entries the generator made by chance, which is why time-entry duplicates are not suggested for exclusion. Empty paid dates (54, unpaid invoices) are no longer reported as errors.
- **Evidence:** Runs on `data/generated` from `python scripts/generate_data.py --out data/generated --seed 42` on 2026-10-05; `tests/test_ingest_validate.py` (seed 7 check of planted problems).
- **Related decisions:** D-11, D-12, D-17

## D-20: PyYAML for config and a demo-folder setting for tests
- **ID:** D-20
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** Both were added on 2026-10-05 before approval and flagged afterwards. The team rule is to ask before adding a library or feature.
- **Options considered:**
  1. Keep `pyyaml` (reads `config.yaml`, the format in the team's planned design) and the `CLIENTPROFIT_DEMO_DIR` environment variable (lets `tests/test_app.py` point the screen at its own generated data).
  2. Switch the config to JSON and hard-wire the demo folder.
- **Decision:** Option 1, approved by the team lead on 2026-10-06.
- **Factors that led to it:** `config.yaml` was already the planned format; PyYAML was already installed. The demo-folder variable keeps the app test independent of local data.
- **Trade-offs accepted:** One more dependency.
- **Expected effect:** None on behaviour.
- **Actual measured effect:** Not applicable.
- **Evidence:** Team lead approval in chat, 2026-10-06.
- **Related decisions:** D-19

## D-21: Forecast set-up: operating margin, time split, baseline ships
- **ID:** D-21
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** D-06 needs a fair test of LightGBM against "next quarter equals last quarter", with no future data in the features.
- **Options considered:**
  1. Forecast margin including late-payment cost.
  2. Forecast operating margin, (revenue - labour cost) / revenue, and keep late payment as a separate days-to-pay feature.
- **Decision:** Option 2, with this set-up:
  - Target: operating margin over the next 3 months (sum of profit / sum of revenue, D2c).
  - Features at each month, from that month and earlier only: 3-month margin, the 3 months before it, their difference, unbilled share of hours, growth in hours, request count and its change (no labels, so the forecast never waits for labelling, D-15), revenue and its growth, days to pay (only payments made by that month), months of history.
  - LightGBM (LightGBM's own API, no scikit-learn) predicts the change from last quarter's margin and adds it back. Settings were fixed before seeing test results and not tuned afterwards.
  - Split by time: test origins whose 3 target months fall in the last 6 months; training origins whose targets end before the test period starts. Rows need 6 months of history and at least $1,000 revenue in both windows.
  - Checked on 3 generated datasets (seeds 42, 1, 2), not one.
- **Factors that led to it:** A month's late cost depends on payments made later, so using it would leak the future. Three seeds guard against a lucky draw.
- **Trade-offs accepted:** The forecast ignores late-payment cost; that cost still counts in the ranking. About 360 to 410 training rows only. Clients with under $1,000 a quarter are not scored.
- **Expected effect:** A fair verdict on D-06's gate.
- **Actual measured effect:** Baseline wins on all three seeds (MAE 0.143 / 0.132 / 0.147 against LightGBM 0.172 / 0.134 / 0.181). `forecast.model` stays `baseline`. LightGBM code is kept so the comparison can be re-run and reported.
- **Evidence:** `python scripts/run_benchmarks.py` on 2026-10-06, `out/benchmarks.json`; `tests/test_forecast.py` checks the split and that features ignore future months.
- **Related decisions:** D-06, D-11, D-15

## D-22: Benchmark 4 result; prompt for clients without services fixed
- **ID:** D-22
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** A teammate labelled the 150-message sheet by hand. Benchmark 4 compares the LLM detector with the keyword baseline against those labels, each with and without the client's services (D-17). The first run showed the LLM without services answering "unclear" to almost everything (accuracy 0.14): the prompt said "Services covered: not known", which the model read as "cannot tell". In the app, every client without a `clients.csv` entry would have been labelled "unclear".
- **Options considered:**
  1. Report the broken result as it stood.
  2. Fix the prompt for unknown services (leave the services line out, use examples without services, its own prompt version so saved labels stay apart), re-run once, and report both the bug and the fixed result.
- **Decision:** Option 2. The prompt used when services are known was not changed, so the 2,598 saved demo labels stay valid. This was one fix of a broken case, not repeated tuning against the hand labels.
- **Factors that led to it:** The broken prompt was a product bug, not a fair "without services" condition.
- **Trade-offs accepted:** The prompt was changed after seeing test results; that is disclosed here and the change was limited to the broken case.
- **Expected effect:** The LLM beats the keyword baseline, and services help.
- **Actual measured effect:** Against 150 hand labels (73 extra unpaid, 58 in scope, 19 unclear). Accuracy; precision / recall / F1 for "extra unpaid":
  - Keyword without services: 0.56; 0.90 / 0.49 / 0.64.
  - Keyword with services: 0.76; 0.90 / 0.75 / 0.82.
  - LLM without services (fixed prompt): 0.75; 0.93 / 0.69 / 0.79.
  - LLM with services: 0.73; 0.88 / 0.69 / 0.77.
  - Before the fix, LLM without services: 0.14; 1.00 / 0.01 / 0.03.

  The expected effect did not happen. The LLM did not beat the keyword baseline. Services helped the keyword baseline a lot (F1 0.64 to 0.82) but not the LLM (0.79 to 0.77). With 150 messages, differences of a few points are within noise (about plus or minus 0.07 on accuracy). The human agreed with the generator's own labels on only 73% of messages, so the "right" label is often debatable. The keyword baseline's lead is partly circular: its list of deliverable words overlaps the generator's item list, both written by the assistant. The LLM has no such advantage, and real client wording would not match a fixed word list.
- **Evidence:** `python scripts/run_benchmarks.py` on 2026-10-06, `out/benchmarks.json`; hand labels in `labelling/label_sheet_seed42_labeled.csv`.
- **Related decisions:** D-14, D-15, D-17, D-23

## D-23: Ship the LLM labeller with services, as a reviewed suggestion
- **ID:** D-23
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** Benchmark 4 (D-22) found the LLM labeller with services (accuracy 0.73) within noise of the keyword baseline with services (0.76) and the LLM without services (0.75). A detector has to be chosen for `scope.detector`.
- **Options considered:**
  1. Keyword rules with services: best measured score, instant and free, but its lead is partly circular (its word list overlaps the generator's items).
  2. LLM with services: within noise of the best, not tied to a fixed word list, uses the services owners enter (D-17).
  3. LLM without services: slightly higher score, but makes the services field pointless for labels.
- **Decision:** Option 2, chosen by the team lead on 2026-10-06. `scope.detector` is set to `llm`. The keyword rules stay as the fallback when an LLM call fails.
- **Factors that led to it:** Real client wording will not match a fixed word list, so the keyword score is unlikely to hold on real messages. The LLM's score is not proven on real messages either; the choice rests on that judgement, not on a measured win.
- **Trade-offs accepted:** Not the best measured score on generated data. No claim may be made that the LLM labeller is more accurate than the keyword rules. Labels are shown as suggestions for the owner to review, not as facts. Message text goes to a third-party provider (privacy, see `docs/project_overview.md` section 7.3).
- **Expected effect:** Labels that hold up better than keyword rules on real client wording. Untested until real messages are available.
- **Actual measured effect:** On generated data, same as D-22: accuracy 0.73; precision / recall / F1 for "extra unpaid" 0.88 / 0.69 / 0.77.
- **Evidence:** `out/benchmarks.json` from `python scripts/run_benchmarks.py`, 2026-10-06.
- **Related decisions:** D-14, D-17, D-22

## D-24: Recommendation rules: one action per client, last 3 months, end only as last resort
- **ID:** D-24
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** The product promises one action per ranked client (keep, raise price, cut scope, end the contract) with its dollar effect, computed by rules, never ending a contract without numbers and one alternative.
- **Options considered:**
  1. Rules on the last 12 months.
  2. Rules on the last 3 months, scaled to a year, with 12-month figures shown beside them.
- **Decision:** Option 2. In order, for each ranked client (`src/clientprofit/recommend.py`):
  - No invoices or hours in the last 3 months: keep as is.
  - 3-month margin within 2 points of the target or above: keep as is.
  - Hours but no revenue in the last 3 months: cut scope ("bill this work or stop it").
  - Scope signals (20% or more of hours unbilled, or 30% or more of recent requests labelled extra unpaid with at least 3 of them) and cutting the unbilled work reaches the target, or turns a loss into a profit: cut scope; effect = unbilled labour cost × 4.
  - Losing over 12 months and in the last 3 months, cutting unbilled work would not break even, and the price rise needed is above 50%: end the contract; effect = loss stopped per year; the alternative (price rise and cut-scope saving) is always shown.
  - Otherwise: raise price by the amount that reaches the target: new revenue = cost ÷ (1 − target margin); effect = (new revenue − revenue) × 4.
  - Warning "heading to a loss": profitable over 12 months, but the last 3 months' margin is below 0, or below 5% and down 10 points or more on the quarter before.
- **Factors that led to it:** The last quarter shows where a client is now, so a client that recently turned bad is caught. A first version ended 14 of 48 clients, including ones that cutting unbilled work would make profitable; the "end" rule was tightened to a true last resort.
- **Trade-offs accepted:** Every dollar effect assumes the same workload and that the client accepts the change; the screen says so. A quarter is noisy (hourly clients are invoiced the month after the work). The thresholds are judgement, not fitted to data.
- **Expected effect:** Few "end" suggestions, each with numbers and an alternative; healthy clients mostly "keep".
- **Actual measured effect:** Seed 42, 48 ranked clients, with request labels: 19 keep, 15 cut scope, 8 raise price, 6 end the contract, 4 heading to a loss. All 6 "end" clients were planted as scope creep or decline and lose money; 17 of 23 planted healthy clients get "keep"; all 4 warnings are clients planted with late scope creep. Without labels, one client moves from cut scope to raise price (14 / 9). This is generated data; it shows the rules behave as designed, not that they are right for real agencies.
- **Evidence:** Runs on `data/generated` (seed 42) on 2026-10-06; `tests/test_recommend.py` (one test per rule).
- **Related decisions:** D-07, D-11, D-21, D-23

## D-25: Requests optional; time-log warning; stop calling a down provider
- **ID:** D-25
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** Most agencies keep client requests in email, chat and calls, not one file. Profit is overstated when staff under-log hours. If the AI provider is down, each failed call costs about 7 seconds of retries, which for thousands of messages would take hours.
- **Options considered:**
  1. Keep requests required; no warning; retry every message.
  2. Make requests (and services) optional; show a time-log warning by the ranked list; after 5 failed calls in a row, stop calling the provider and use keyword labels for the rest.
- **Decision:** Option 2, approved by the team lead on 2026-10-06. Also: when more than 200 messages are new, the screen shows the expected labelling time and asks before starting (D-15).
- **Factors that led to it:** The ranking and the recommendations work without requests; scope-creep signals are extra. The time-log risk is bigger than any model's accuracy and the owner should see it.
- **Trade-offs accepted:** Without requests, cut-scope suggestions rest on unbilled hours only. Keyword labels used after a provider failure are marked as such.
- **Expected effect:** Agencies without a requests export can still use the tool; a provider outage cannot stall the screen.
- **Actual measured effect:** Not measured beyond tests (`tests/test_ingest_validate.py::test_pipeline_runs_without_requests`, `tests/test_scope.py::test_provider_down_stops_calling_after_five_failures`).
- **Evidence:** Tests above, 2026-10-06.
- **Related decisions:** D-15, D-23, D-24

## D-26: Explanations: facts from code, LLM writes words, number check with template fallback
- **ID:** D-26
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** The brief asks for 2 to 3 plain sentences per client written by an LLM using only numbers from the cost engine, forecast and recommendations, with an automatic check that every number in the text exists in the computed figures (benchmark 6, target zero).
- **Options considered:**
  1. Give the LLM the raw tables and let it pick numbers.
  2. Code builds a list of facts with every number already formatted (including the recommendation's reason and alternative); the LLM only writes sentences; a check extracts every number from the text and rejects the text if any number is not among the facts; a rejected text is replaced by a fixed template from the same facts.
- **Decision:** Option 2 (`src/clientprofit/explain.py`). Explanations are written when the owner opens a client and saved (`labels/saved_explanations.json`), so they are never on the path to the ranked list.
- **Factors that led to it:** The LLM never computes (D-07). A failed check or a provider failure falls back to text made by code, so an invented number cannot reach the screen.
- **Trade-offs accepted:** The check proves no number was invented; it cannot tell whether a correct number is described correctly (seen on the screen: "48%, closer to the target of 30%", where 48% is above the target), and it does not catch numbers written as words. The check allows 3 and 12 (the periods the facts refer to) and drops the sign of a number (so "a loss of $1,175" passes). The screen says the numbers were checked, not the wording.
- **Expected effect:** Zero invented numbers in shown texts.
- **Actual measured effect:** 48 ranked clients on seed 42: 48 texts written by the LLM, 0 contained an invented number, 0 provider errors, 0 shown texts with an invented number; 107.1 s for all 48 (about 2.2 s each). The unit tests show the check does catch invented numbers (`tests/test_explain.py`), so zero is not a sign of a check that never fires.
- **Evidence:** `python scripts/run_benchmarks.py` on 2026-10-06, `out/benchmarks.json` section 6.
- **Related decisions:** D-07, D-14, D-24

## D-27: Benchmark 2 headline is bottom K, bottom 10 second
- **ID:** D-27
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** Benchmark 2 was written as "planted loss-making clients found in the bottom 10". Each dataset has 12 to 15 planted loss-makers (K), so a bottom 10 can never hold all of them and its share (at most 10 of K) understates the result.
- **Options considered:**
  1. Keep bottom 10 as the headline.
  2. Headline the bottom K (K = number of planted loss-making clients): how many of the K lowest clients by profit are planted loss-makers, against ranking by revenue. Report bottom 10 as a second line.
- **Decision:** Option 2, approved by the team lead on 2026-10-06. Every place that shows the result also says the test is nearly circular.
- **Factors that led to it:** Bottom K asks the right question ("are all the losing clients at the bottom?") and has a clean maximum (K of K).
- **Trade-offs accepted:** Nearly circular: "loss-making" in the generated data is computed with the same profit rule as the engine (D-11), so a perfect profit score mainly shows the engine is wired correctly. The real finding is the revenue comparison: ranking by revenue hides most losing clients, because the planted "looks big" clients are among the largest by revenue.
- **Expected effect:** A clearer, honest headline.
- **Actual measured effect:** Bottom K by profit vs by revenue: seed 42: 15/15 vs 3/15; seed 1: 12/12 vs 4/12; seed 2: 15/15 vs 3/15. Bottom 10: seed 42: 10/10 vs 2/10; seed 1: 10/10 vs 4/10; seed 2: 10/10 vs 3/10.
- **Evidence:** `python scripts/run_benchmarks.py` on 2026-10-06 (`out/benchmarks.json`, seed 42); seeds 1 and 2 from `bench2` in `scripts/run_benchmarks.py` on freshly generated data, 2026-10-06.
- **Related decisions:** D-11, D-13

## D-28: Deploy on Streamlit Community Cloud; app builds missing demo data; "demo only" line
- **ID:** D-28
- **Date:** 2026-10-06
- **Status:** Assumed
- **Context:** Judges need a working link. `data/` is never committed (.gitignore), so a fresh deploy has no demo files and the demo button failed with "No demo data". A public app also invites people to upload real client data.
- **Options considered:**
  1. Commit the generated demo data to the repo.
  2. Host elsewhere (a paid server or container).
  3. Streamlit Community Cloud (free, deploys from the public repo's main branch, key kept in its secrets); the app builds the demo data itself (seed 42) the first time the demo is chosen; a line on the screen says the app is a demo and not for confidential data.
- **Decision:** Option 3, approved by the team lead on 2026-10-06. The repo owner deploys (repo, branch main, file app.py, secret `FEATHERLESS_API_KEY`).
- **Factors that led to it:** Seed 42 rebuilds byte-identical files, so the saved labels and explanations are reused and no LLM credits are spent on the demo. Building takes about 7 seconds once per server start. Committing ~2 MB of generated CSVs would duplicate what the generator already makes.
- **Trade-offs accepted:** The first demo click after a restart waits about 7 to 10 seconds. A free app sleeps when unused, so it must be woken before judging. The app imports `generator/` (only to build demo files); `src/clientprofit` still never does (D-08). Uploaded request messages still go to Featherless; the screen says so. Whether Streamlit Cloud passes top-level secrets as environment variables must be checked on the first deploy.
- **Expected effect:** The deployed demo works from a clean checkout.
- **Actual measured effect:** On a clean folder, generating seed 42 took 7.0 s and the invoices, time entries, requests and clients files were byte-identical to the ones the saved labels were made from. `tests/test_app.py::test_missing_demo_data_is_built_on_first_start` passes. Deployed on 2026-10-07 at https://hackathon-qiv6graw7ewfv6lqndywtd.streamlit.app/ ; the team lead's check on the live app: 48 clients ranked in 1.34 s, all 2,601 request labels reused from the saved file (no "Label them now" button), explanations shown from the saved file.
- **Evidence:** Check run on 2026-10-06 (scratch script comparing a fresh seed-42 build with `data/generated`); the test above; team lead's screenshots of the live app, 2026-10-07.
- **Related decisions:** D-08, D-14, D-15, D-20, D-26

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
