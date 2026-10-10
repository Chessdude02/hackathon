# Submission: Client Profit Finder

Everything needed for the ForgeHacks Online 2026 submission, ready to copy into Devpost.
Every number below comes from a run recorded in `docs/decisions.md`.

| Required item | Where it is |
|---|---|
| 1. Title and short description | Section 1 below |
| 2. Track | Section 2 below: **Business** |
| 3. Public demo video (2 to 4 minutes) | **Add the YouTube link here before submitting:** `VIDEO LINK` |
| 4. GitHub repository with README | https://github.com/Chessdude02/hackathon |
| 5. Written description | Section 5 below |
| 6. Screenshots, architecture diagram, deployment link | Section 6 below |

---

## 1. Project title and short description

**Title:** Client Profit Finder

**Short description (one paragraph):**
Small agencies know which clients pay them the most, but rarely which clients make them money.
Client Profit Finder reads the invoices and time logs an agency already has and shows the true
profit of every client: revenue minus staff time, direct costs, late payment and a fair share of
overhead. It ranks clients, flags the ones losing money, suggests one action for each (keep, raise
the price, cut the scope, or as a last resort end the contract) with its dollar effect per year, and
shows the exact invoice and time rows behind every number. AI only labels client requests and writes
short explanations; it never does the arithmetic.

## 2. Track

**Business**

## 3. Demo video

Public YouTube link: `VIDEO LINK` (2 to 4 minutes, shows the problem and how the app works).
Script: `docs/demo_script.md`.

## 4. Source code

Repository: https://github.com/Chessdude02/hackathon (public). The README explains what the tool does,
the results, how to run it, and its honest limits.

---

## 5. Written project description

### Problem statement and target users

**Who:** owners of small service agencies (5 to 30 staff): marketing, design, web, consulting.

**The problem:** these owners know which clients pay the most, not which make them money. A big client
can quietly lose money through:

- more staff hours than the fee covers,
- work that is never billed,
- a steady stream of "small" extra requests outside the agreed scope,
- late payment.

Large firms have finance teams to catch this. A small agency has the owner and a spreadsheet, so
decisions on which clients to keep, re-price or drop are made on gut feeling.

**What the owner gets:** a ranked list of clients by true profit, a clear action for each one with its
dollar effect, and the evidence behind every figure, down to the original invoice and time-entry rows.
The owner makes every decision; the tool never contacts a client.

### Technical approach and components

**Flow:** upload files, confirm columns, review problems, rank, act.

1. **Reading the files.** Messy column names from any tool ("Amt", "Customer:Job", "Date Paid") are
   matched to a fixed list of meanings, and the owner confirms the mapping. Client name variants
   ("ACME LTD", "Acme Ltd") are merged and reported.
2. **Validation.** Every problem is listed with its row numbers (duplicates, staff without a cost,
   negative hours, odd payment dates, months with work but no invoice). Nothing is dropped silently;
   the owner ticks what to exclude.
3. **Cost engine (plain arithmetic, no AI).** For every client and month:
   - contribution = revenue minus staff time (hours x hourly cost), direct costs and the cost of late
     payment: what the agency would lose without the client;
   - profit = contribution minus the client's share of shared overhead (rent, software, admin), split by
     logged hours from the owner's yearly overhead.
   It matches an independent hand calculation exactly, and every figure links back to its source rows.
4. **Suggested actions (fixed rules on the last 3 months).** Keep, raise the price (to reach the target
   margin), cut scope (stop or bill unbilled work), or end the contract (only if the client does not
   even cover its own costs, and always shown with an alternative). Savings never count shared overhead
   as saved, because rent does not go away when one client leaves.
5. **AI, behind one small wrapper (Featherless, Qwen 2.5 14B), two jobs only:**
   - label each client request as routine, extra unpaid work, or unclear, using the services that client
     pays for;
   - write two or three plain sentences per client from figures the code computed. Every number in the
     text is checked against those figures, and broken or invented text is replaced by fixed wording.
6. **Screen (Streamlit):** what we found, revenue versus profit, what to do, then one client in detail
   with a margin trend showing "if nothing changes" against "after the suggested action".

**Components:** Python, pandas, numpy, Streamlit, LightGBM (tested for forecasting), Featherless AI
(Qwen 2.5 14B), pytest (161 automated tests), deployed on Streamlit Community Cloud.

**What we measured (all on generated data unless noted; no real agency data was available):**

| Test | Result |
|---|---|
| Cost engine against a hand calculation | Exact match on 29 client-months and 10 client totals |
| Are the planted loss-making clients at the bottom? | 15 of 15 by profit, only 3 of 15 by revenue; on 5 unseen datasets, 55 of 56 by profit vs 18 of 56 by revenue |
| Forecasting | A LightGBM model lost to "next quarter looks like the last one" on all 8 datasets, so the app shows trends and the effect of each action instead of a forecast |
| Request labels against 150 human labels | AI 0.73 to 0.75 accuracy, keyword rule 0.76: shown as a suggestion to review, marked beta |
| Explanations | 0 invented numbers in 48 AI texts; a quality check catches garbage replies |
| Speed | About 1 second from upload to ranked list (50 clients) |
| Safety of suggestions on unseen data | Every losing client got an action (49 of 49); no healthy client was told to cut scope or end (66 of 66) |

We report where AI lost to simple rules instead of hiding it.

### Real-world impact

- **Money the owner can act on.** In the demo agency, 15 of 48 clients lose money, together $311,566 a
  year, which cancels out most of what the profitable clients earn. The number 2 client by revenue
  (Lakeshore Clinic, $187,650) is the biggest loss ($55,802). The tool shows that cutting its unbilled
  work saves about $52,000 a year, and that a price rise is still needed.
- **Fair, explainable decisions.** Every figure traces back to source rows, so the owner can check it and
  take it into a client conversation.
- **Better pricing.** Separating what a client contributes from its share of overhead stops owners from
  dropping clients to "save" costs that would not go away.
- **Small business reach.** It uses the exports agencies already have, needs no finance team, and runs
  in about a second.
- **Honest limits.** Profit is only as good as the time logs (the screen warns about this). It has not
  yet been tested on a real agency's data; an independent synthetic dataset from a university course was
  used as an outside check and exposed three weaknesses we fixed. Client messages are sent to the AI
  provider, so a real deployment needs a data agreement or a local model.

---

## 6. Screenshots, architecture diagram and deployment link

**Live app (for testing):** https://hackathon-qiv6graw7ewfv6lqndywtd.streamlit.app/
(it may take a minute to wake up; choose "Use demo data").

**Screenshots** (in `docs/screenshots/`, upload these to Devpost in this order):

1. `1_headline_and_chart.png`: what we found, in four numbers
2. `2_revenue_vs_profit.png`: big revenue is not big profit
3. `3_what_to_do.png`: clients that need a decision, worst first
4. `4_client_detail.png`: one client, the action, and the AI explanation
5. `5_margin_trend.png`: the trend, if nothing changes vs after the action
6. `6_architecture.png`: architecture diagram

**Built with (Devpost tags):** python, pandas, numpy, streamlit, lightgbm, featherless-ai, qwen, pytest

---

## Before you press submit

- [ ] YouTube video is **Public**, 2 to 4 minutes, link pasted in sections 3 above and on Devpost
- [ ] Track set to **Business**
- [ ] All six screenshots uploaded
- [ ] Live app opened in a private window and the demo loads
- [ ] Repository link opens without signing in
- [ ] All team members added to the Devpost project
- [ ] Submitted before **12:00 PM EDT, 10 October 2026**
