# Client Profit Finder: project overview

ForgeHacks Online 2026, Business track. This document explains what the
project does, what it ships today, how it works, what we measured, and what it
means for the people who would use it. It is written for teammates, judges and
anyone reading the repository for the first time.

State of this document: written on 6 October 2026 (day 4 of 7). Every
statement below is marked as **Built** (exists in the code and is tested) or
**Planned** (designed, not built yet). Numbers come from real runs recorded in
`docs/decisions.md`.

---

## 1. The problem in one paragraph

A small agency (5 to 30 staff) usually knows which clients pay the most. It
rarely knows which clients make it the most money. A client paying $9,000 a
month can quietly lose money if senior staff spend too many hours on it, if
much of the work is never billed, if the client asks for more and more extra
work, or if it pays months late. Large firms have finance teams that work
this out. Small agencies do not. The owner decides who to keep, re-price or
drop on gut feeling.

**Our tool answers one question for that owner: which clients actually make
money, which are heading toward a loss, and what should I do about each one?**

## 2. Who it is for and what they decide

- **User:** the owner of a small agency with no finance team.
- **Decision:** for each client, one of four actions:
  - keep as is,
  - raise the price,
  - cut the scope of work,
  - end the contract.
- **Who decides:** always the owner. The tool never acts on its own. It never
  emails a client, changes a price or ends anything. It shows numbers and a
  suggestion; a person makes the call.

## 3. What the owner does with it

1. Uploads three files the agency already has:
   - **invoices** (client, date, amount, date paid),
   - **time entries** (client, staff member, date, hours, task, billable or not),
   - **client requests** (client, date, channel, message text).
   - Optionally a fourth: **services covered** per client (what each client pays for).
2. Checks how the tool read the files (which column means what) and fixes it if needed.
3. Enters what each staff member's hour costs, plus a few rules (overhead, payment terms).
4. Reviews the problems the tool found in the files and chooses what to exclude.
5. Gets a **ranked list of clients by true profit** over the last 12 months.
6. Clicks a client to see the month-by-month detail, down to the exact invoice
   and time-entry rows behind each figure.

---

## 4. What ships today

### 4.1 Built and tested

| Part | What it does | Status |
|---|---|---|
| **File loading and column mapping** | Reads CSV files with messy headers ("Amt", "Customer:Job", "Paid at") and suggests which column means what. The owner confirms or corrects every suggestion. | Built |
| **Client name matching** | Treats "ACME LTD", "Acme Ltd" and "Acme" as one client, and reports every merge so the owner can catch a wrong one. | Built |
| **Problem report** | Finds unreadable values, staff without a cost, negative hours, duplicate invoices, clients with hours but no invoices, and months with work but no invoice. **Never drops a row on its own.** The owner ticks what to exclude. | Built |
| **Cost engine** | Works out, for every client and month: revenue, labour cost, cost of late payment, and profit. Plain arithmetic, no AI. Every figure lists the input rows behind it. | Built, matches a hand calculation exactly |
| **Ranking** | Ranks clients by profit over the last 12 months. Clients with under 3 months of data are listed apart as "not enough history" instead of being ranked. | Built |
| **Worst-case profit** | For each client, also shows profit if invoices more than 90 days overdue are never paid. | Built |
| **Request labeller** | Labels each client message as routine work, extra unpaid work, or unclear, using an AI model (Featherless, Qwen 2.5 14B) and the client's list of services. Saves every label so the same message is never sent twice. Shown as a suggestion to review. | Built |
| **Keyword baseline** | A simple word-rule labeller used as the comparison and as the fallback if the AI fails. | Built |
| **Forecast** | Predicts next quarter's margin per client. A LightGBM model was tested against "next quarter equals last quarter" and lost, so the simple rule ships. | Built, not yet shown on the screen |
| **Recommendations** | One action per client (keep, raise price, cut scope, end the contract) with its dollar effect a year, the reason, and for "end" always an alternative. Rules on the last 3 months; "end" only as a last resort. | Built |
| **Loss warnings** | Flags clients profitable over the year but heading toward a loss now. | Built |
| **Explanations** | Two or three plain sentences per client, written by the AI using only numbers our code computed. An automatic check rejects any text with a number not in the figures and shows standard wording instead. | Built: 0 invented numbers in 48 texts |
| **Screen** | Streamlit app: data source, column check, settings, problems, ranked list with actions and warnings, scope-creep signals with progress, client detail. Requests and services are optional. | Built (rough) |
| **Data generator** | Creates a realistic fake agency (50 clients, 24 months) with planted patterns, because no real data was available. | Built |
| **Benchmarks** | One script runs the benchmarks and writes the numbers to a file. | Built (all 7) |
| **Tests** | 128 automated tests, including one for every cost calculation. | Built, all passing |

### 4.2 Planned (days 4 to 6)

| Part | What it will do |
|---|---|
| **Forecast on the screen** | Trend lines per client next to the action. **Dropped on 2026-10-07** in favour of direct costs (D-31). |
| **Services table on the settings screen** | Type each client's services in the app instead of uploading a file. |
| **Deployment** | Done: https://hackathon-qiv6graw7ewfv6lqndywtd.streamlit.app/ (D-28). |
| **Direct costs** | Built on 2026-10-07: an optional cost column on invoices (freelancers, ad spend, materials), subtracted from profit (D-31). |

---

## 5. How it works

### 5.1 The flow

```
 upload 3 files ─► map columns ─► owner confirms ─► unify client names ─► problem report
                                                                              │
                                                    owner excludes rows ◄─────┘
                                                              │
                                                              ▼
                                cost engine (arithmetic only) ─► RANKED LIST  ◄── shown at once
                                                              │
               ┌──────────────────────────────────────────────┼──────────────────────────┐
               ▼                                              ▼                          ▼
     request labeller (AI, saved labels)          features ─► forecast (baseline)   (planned)
               │                                              │                    recommendations
               └──────────────────────────────┬───────────────┘                    explanations
                                              ▼
                                 fills in on the screen later
```

### 5.2 The profit formula

For each client and month:

- **Revenue** = sum of invoices dated in that month.
- **Labour cost** = for every hour logged: hours × that person's hourly cost × overhead multiplier.
  Non-billable hours count, because they still cost money.
- **Late-payment cost** = invoice amount × yearly cost of money × days late ÷ 365.
  An invoice not yet paid keeps building late cost up to the last date in the data.
- **Profit** = revenue − labour cost − late-payment cost.

Every rule is written down (decisions D-11, D-16, D-18) and checked against a
hand calculation done by a teammate who did not write or read the engine code.

### 5.3 Where AI is used, and where it is not

| Task | Who does it | Why |
|---|---|---|
| All money figures, ranking, worst case | **Code only** | Every number must be exact and traceable. An AI that invents one number in a "drop this client" recommendation would destroy trust. |
| Forecast | **Simple rule** (the AI model lost the test) | We ship what measured best, not what sounds most impressive. |
| Labelling client messages | **AI with the client's services** (keyword fallback), shown as a suggestion to review (D-23) | Reading "can we make it pop more?" is a language task. It tied a keyword rule on our data, so it is not claimed to be more accurate. |
| Column mapping | **Word rules now; AI planned**, owner always confirms | A wrong mapping silently corrupts every number, so a person checks it. |
| Explanations | **AI**, given only computed numbers, with an automatic check and a standard-wording fallback (D-26) | The AI writes words; code supplies every number. |

All AI calls go through one small file (`src/clientprofit/llm.py`), so the
provider can be swapped in about an hour. The API key is read from an
environment variable and is never in the code.

---

## 6. What we measured, and what it means

**Important:** benchmarks 2 to 5 run on data we generated, because no real
agency data was available. They show the code works. They do not show it is
accurate on real businesses.

| # | Benchmark | Result | What it really tells you |
|---|---|---|---|
| 1 | Cost engine vs a hand calculation (10 clients) | **Exact match** on all 29 client-months and 10 client totals | The arithmetic is right. This one is not circular. |
| 2 | Planted loss-making clients found at the bottom (bottom K, K = number of planted losers; D-27) | **All 15** planted loss-makers are the 15 lowest by profit; ranking by revenue puts only **3** there. Seeds 1 and 2: 12/12 vs 4/12, 15/15 vs 3/15. Bottom 10: 10/10 vs 2 to 4/10. | Ranking by revenue hides losing clients. But the test is nearly circular: "loss-making" in the test data is computed with the same rules as the engine, so the perfect profit score mostly shows the wiring is right. The revenue gap is the real point. |
| 3 | Forecast error, last 6 months, split by time | Baseline **0.143**, LightGBM **0.172** (baseline wins on all 3 datasets) | The AI model did not earn its place, so it was dropped. That is the honest result. |
| 4 | Message labeller vs 150 messages labelled by a teammate | Keyword + services **0.76** accuracy, AI **0.73 to 0.75** | The AI ties a keyword rule on our generated messages. It does not beat it. The keyword rule's lead is partly circular (its word list overlaps the generator's). |
| 5 | Column mapping on 10 header styles | **172 of 172** | Meaningless as it stands: the same person wrote the test headers and the word list. Needs real export headers. |
| 6 | No invented numbers in explanations | **0 of 48** AI texts contained an invented number; 0 reached the screen | The check proves numbers are not made up. It cannot prove each number is described correctly (we saw "48%, closer to the 30% target" when 48% is above it). |
| 8 | Suggested actions vs planted client types (5 unseen seeds, D-33) | "End" only on planted loss-makers **9 of 9**; active loss-makers given an action **49 of 49**; healthy clients never told to cut or end **66 of 66**; warnings on problem clients **18 of 18**, but late-trouble clients warned only **4 of 41** | The rules are safe (no wrong "end") but the warning is late: it fires once the margin is already near zero. Seed 42, used for tuning, looked perfect; new seeds showed the weakness. |
| 7 | Speed, upload to ranked list, 50 clients | **About 1 second** (target: under 60) | Fast enough. Labelling new messages is timed separately; all 2,601 demo messages took 33 minutes once, then 2.5 seconds when reused. |

**Two of our three AI components lost to simple baselines.** We kept the
evidence and reported it, instead of tuning until the AI looked better on our
own test data. A judge should read that as a strength: the product only claims
what was measured.

---

## 7. Implications

### 7.1 For the agency owner

- **Better decisions on real money.** The ranked list can show that the
  biggest-paying client is the one losing money. In our test data, the five
  clients that "looked biggest" by revenue were the top five by revenue and
  four of them lost money.
- **A clear, explainable reason.** Every figure can be traced to the invoice and
  time-entry rows behind it. The owner can check it and argue with it.
- **A starting point for a conversation, not a verdict.** "Raise the price by
  14%" is a number to take into a client meeting, not an order.
- **Time saved.** What would take a finance person days in a spreadsheet takes
  about a second once the files are loaded.

### 7.2 For staff and clients (the people affected by the decision)

- **Ending a contract affects people.** Staff who work on that client, and the
  client's own business. That is why the tool never recommends ending a
  contract without the numbers behind it and one alternative, and never acts on
  its own.
- **Profit is not the only reason to keep a client.** A loss-making client may
  bring referrals, a famous name for the portfolio, or a foothold in a new
  market. The tool cannot see any of that. The owner must weigh it.
- **Staff cost numbers are sensitive.** Hourly costs per person are close to
  salaries. Whoever runs the tool sees them. In a real deployment, access
  should be limited to the owner.
- **Scope-creep labels can sour relationships if used carelessly.** Telling a
  client "the system says you asked for 40 unpaid extras" is very different
  from the owner reviewing the messages and raising it politely.

### 7.3 Privacy and data handling

- **Client messages are sent to a third-party AI provider (Featherless).**
  Real messages may contain names, prices and business plans. A real agency
  would need its clients' consent or a contract covering this, and should check
  how long the provider keeps the data. We have not reviewed Featherless's data
  policy.
- **Money figures never leave the app.** Invoices, hours and costs are not sent
  to the AI. Only message text (and, when built, the already-computed numbers
  for each explanation) is sent.
- **Saved labels are stored in a file.** For the demo this is fine. For real
  use, that file holds client message fingerprints and labels and should be
  treated as confidential.

### 7.4 Limits and risks

- **No real data yet.** Every result after benchmark 1 comes from data we
  generated. Real agencies may record time differently, bill differently, or
  write messages that look nothing like ours.
- **Garbage in, garbage out.** If hourly costs or the overhead multiplier are
  wrong, every profit figure is wrong in the same direction. The tool shows the
  settings it used so the owner can check them.
- **"Unclear" is common and genuine.** Our human labeller agreed with the
  generator's own labels on only 73% of messages. Deciding what counts as
  "extra work" is hard even for people. The labels are a prompt for review, not
  a fact.
- **Small samples.** 150 hand-labelled messages and about 170 forecast test
  windows. Differences of a few points between methods are within noise.
- **Short history makes results unreliable.** Clients with under 3 months of
  data are not ranked at all, rather than being ranked on thin evidence.

### 7.5 Wider implications

- **Small firms get a tool that used to need a finance team.** Products like
  this exist for larger software companies; we found no self-serve tool for
  small service businesses (decision D-02, based on a quick search, not a full
  market study).
- **The same idea fits other service businesses.** Any business that bills
  clients and tracks hours (accountants, consultants, IT support, law firms)
  has the same blind spot.
- **A pattern for using AI responsibly with money.** Code does every
  calculation; AI only reads and writes language; every AI result is tested
  against a simple baseline and dropped if it does not win. That pattern is
  worth more than any single model.

---

## 8. How we built it

- **Seven days, one Python app**, no separate services. Streamlit for the screen,
  pandas for the numbers, LightGBM for the forecast test, Featherless for AI calls.
- **Every decision is written down** in `docs/decisions.md` (22 so far), with the
  options considered, why one was chosen, and the measured result when there is
  one. Nothing is deleted; changed decisions are marked "Superseded".
- **`docs/execution.md` describes exactly what the code does**, and a test fails
  if the function call graph in the docs drifts from the code.
- **Honesty rules we held to:**
  - A teammate who never saw the engine code did the hand calculation.
  - A teammate who never saw the generator did the message labelling.
  - The forecast and the labeller were compared to simple baselines, and the
    baseline shipped where it won.
  - When a prompt bug was found by a benchmark, it was fixed once and disclosed,
    not tuned repeatedly against the test labels.

## 9. Repository map

| Path | What it holds |
|---|---|
| `app.py` | The screen |
| `src/clientprofit/` | The product code: loading, validation, cost engine, labeller, forecast, AI wrapper |
| `generator/` | The fake-agency generator (never imported by product code) |
| `scripts/` | Command-line tools: generate data, run the pipeline, label requests, build the message bank, run benchmarks |
| `tests/` | 100 automated tests and the hand-calculation files |
| `labelling/` | The 150-message sheet, blank and hand-labelled |
| `labels/saved_labels.json` | Saved AI labels for the demo data |
| `docs/decisions.md` | Every decision and its evidence |
| `docs/execution.md` | How the code runs, function by function |
| `config.yaml` | All settings |

## 10. What would make it real

In order of value:

1. **One real agency's anonymised files.** It would turn every benchmark from
   "the code works" into "the tool works".
2. **One conversation with an agency owner** to confirm the four actions are the
   decisions they actually face, and that they can export these three files.
3. **Real export headers** from Toggl, Harvest and QuickBooks, to test column
   mapping honestly.
4. **A data-handling review** before any real client messages are sent to an
   AI provider.
