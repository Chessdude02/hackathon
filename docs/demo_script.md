# 2-minute demo script

For the lead (voice-over) and B (recording). Record from the **deployed app**,
not a laptop. Wake the app first and click through once before recording so
the demo data is already built.

Client names and figures below are from the seed-42 demo data, checked on
2026-10-06 with `scripts/run_pipeline.py`. **Before recording, open each named
client on the deployed app and copy the numbers from the screen into this
script**; the screen uses request labels, which can change one client's action.

Total: about 2 minutes. Times are targets, not limits.

---

### 0:00-0:15 The problem (talking over the app's start page)

> "Small agencies know which clients pay the most. They rarely know which
> clients make them money. A client paying fifteen thousand a month can lose
> money through unbilled hours, extra requests and late payment. Big firms have
> finance teams for this. A ten-person agency has the owner and a spreadsheet."

### 0:15-0:35 Upload and checks

On screen: choose **Use demo data**. Open one file in **1. Check the column
mapping** to show a messy header mapped; scroll past **2. Settings**; open
**3. Problems in the files** for a second.

> "The owner uploads the invoices and time logs they already have. The tool
> reads messy column names and asks the owner to confirm. It lists every
> problem in the files, like duplicate invoices, and never drops a row on its
> own."

### 0:35-1:05 The ranked list (the key moment)

On screen: click **Rank clients**. Point at the bottom of the list.

> "In under a second, every client is ranked by true profit over twelve
> months. Look at Lakeshore Clinic. It's our second-biggest client by revenue,
> about one hundred and eighty-eight thousand dollars a year, and it's the
> biggest loss on the list, about fifty-six thousand dollars."

> "In our test data, all fifteen loss-making clients are the fifteen lowest
> on this list. Ranking by revenue, which is what most owners look at,
> puts only three of them at the bottom."

### 1:05-1:35 Action and explanation

On screen: in **5. Client detail**, choose Lakeshore Clinic. Show the action
box, then the explanation.

> "For each client the tool suggests one action with its dollar effect. Here:
> cut scope. Almost a third of the hours on this client are never billed.
> The AI writes a short explanation, but it never does the maths. Our code
> computes every number, and a check throws out any sentence with a number
> that isn't in our figures."

Optional, if time allows: show Riverbend Cycles or Tidewater Academy, where
the suggestion is "end the contract" and the screen also shows the alternative.

> "We only suggest ending a contract as a last resort, and always with an
> alternative."

### 1:35-1:50 Scope creep

On screen: scroll to **Scope-creep signals (beta)**.

> "The AI also reads client requests and flags ones that look like extra
> unpaid work, using the list of services each client pays for. It's marked
> beta: on our tests it tied a simple keyword rule, and we say so."

### 1:50-2:00 Close

> "The owner gets the numbers, the reason, and the choice. The tool never acts
> on its own. Every result is in our repo, including the parts where AI lost
> to a simple rule."

---

## Things to avoid saying

- Don't say it was tested on real agencies. It wasn't (unless D's agency call
  happens; then quote them by permission only).
- Don't say "AI predicts which clients will lose money". The forecast that
  ships is a simple baseline, because the AI model lost.
- Don't say "100% accurate". The 15 of 15 result is on generated data, and the
  test is nearly circular.
