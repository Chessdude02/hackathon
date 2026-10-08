# Devpost draft (for C to edit)

First draft. C owns the final text. Every number here is in
`docs/decisions.md` or `out/benchmarks.json`; keep them unchanged unless the
benchmarks are re-run. Fill the placeholders in square brackets.

---

## Inspiration

Small agencies (5 to 30 staff) usually know which clients pay the most, not
which ones make them money. A big client can quietly lose money through
unbilled hours, a steady stream of "small" extra requests, and late payment.
Large firms have finance teams to catch this; a small agency has the owner and
a spreadsheet. [D: add the agency owner's quote here if the call happens, with
permission. If it doesn't, delete this line.]

## What it does

The owner uploads the invoices and time logs they already have (client
requests and a list of services per client are optional). Client Profit
Finder:

- reads messy column names and asks the owner to confirm the mapping,
- lists every problem in the files and never drops a row on its own,
- works out two figures per client per month: contribution (revenue minus
  staff hours at their real cost, direct costs and the cost of late payment)
  and profit after the client's share of shared overhead (rent, software,
  admin), using the owner's real yearly overhead,
- ranks clients by 12-month profit, and keeps clients with under 3 months of
  data apart instead of ranking them on too little evidence,
- warns about clients that are profitable over the year but heading toward a
  loss now,
- suggests one action per client (keep, raise price, cut scope, end the
  contract) with its dollar effect per year; "end the contract" is a last
  resort for clients that don't even cover their own costs, always comes with
  an alternative, and never counts shared overhead as saved,
- uses an LLM to flag client requests that look like extra unpaid work, and to
  write a short explanation per client.

The owner makes every decision. The tool never acts on its own.

## How we built it

- **Python, pandas, Streamlit.** The cost engine is plain arithmetic with one
  automated test per calculation, checked against a hand calculation done by
  a teammate (exact match on 29 client-months).
- **LLM:** Featherless AI (Qwen 2.5 14B) behind a single wrapper, for two jobs
  only: labelling requests and writing explanation sentences. **The LLM never
  does arithmetic.** Code formats every number; an automatic check rejects
  any text containing a number that is not in our figures and shows fixed
  wording instead (0 invented numbers in 48 explanations).
- **Forecast:** we trained LightGBM to predict next quarter's margin and
  compared it to a simple "next quarter looks like the last one" baseline. The
  baseline won (error 0.143 vs 0.172, and on all 3 datasets), so the baseline
  ships.
- **Data:** no real agency data was available, so we built a generator that
  creates a realistic agency (50 clients, 24 months) with planted patterns:
  clients that look big but lose money, slow payers, growing scope creep,
  holidays and noise. The product code never sees the planted answers; only
  the benchmark script does.
- **Process:** every design decision is recorded with the options considered
  and its measured effect (`docs/decisions.md`).

## Results

All on generated data except where noted. These show the code works, not that
it is accurate on real businesses.

- **Finding losing clients:** all 15 planted loss-making clients are the 15
  lowest by profit; ranking by revenue puts only 3 of them at the bottom
  (same pattern on 2 more datasets). This is nearly circular, because the
  planted label uses the same profit rule, but it shows how much a
  revenue view hides.
- **Request labeller:** against 150 messages labelled by a teammate, the LLM
  scored 0.73 to 0.75 accuracy and a keyword rule 0.76. It ships as a
  reviewed suggestion, marked beta.
- **Speed:** upload to ranked list in about 1 second for 50 clients.

## Challenges we ran into

- Two of our three AI parts lost to, or only tied, simple rules. We reported
  that instead of tuning on our own test data.
- The first version of the recommendation rules suggested ending 14 of 48
  clients. We tightened "end the contract" to a last resort (6 of 48), then
  realised even those counted rent and software as "saved". Once we separated
  a client's own costs from shared overhead, none of the 48 needed ending:
  every losing client could be fixed by cutting unbilled work or repricing.
- Labelling all 2,601 demo requests took 33 minutes, so labels are saved and
  reused, and the ranked list never waits for the AI.
- [Add any team or deployment challenge.]

## Accomplishments that we're proud of

- An exact match between the cost engine and an independent hand calculation.
- Zero invented numbers reaching the screen, with a check that is tested to
  fire.
- Honest benchmarks, including the ones the AI lost.

## What we learned

[Team to fill in. Suggestion: on a small, structured problem, plain rules and
a careful profit definition did more than the AI models; the AI was most
useful for reading text.]

## What's next

- Test on real agency exports (Toggl, Harvest, QuickBooks, Xero). [If D
  collected real headers: "Column mapping matched X of Y real headers before
  any changes."]
- Check the time log is complete; profit is only as good as the hours logged.
- A locally run model, so client messages never leave the agency.
- Track whether suggested actions were taken and what happened, to tune the
  rules on real outcomes.

## Built with

python, pandas, numpy, streamlit, lightgbm, featherless-ai, qwen, pytest

## Links

- Demo: https://hackathon-qiv6graw7ewfv6lqndywtd.streamlit.app/
- Repo: https://github.com/Chessdude02/hackathon
- Video: [link]
