# Client profit finder

A tool for small agencies (5-30 staff). The owner uploads the invoices and
time entries the agency already has (client requests and services covered are
optional) and gets:

- every client ranked by **true profit** over the last 12 months,
- a warning for clients that are profitable over the year but **heading toward a loss** now,
- **one suggested action** per client (keep, raise price, cut scope, end the
  contract) with its dollar effect per year, the reason, and for "end" always
  an alternative,
- a short plain-English explanation per client that is **checked for invented numbers**.

The owner makes every decision. The tool never acts on its own.

Built for ForgeHacks Online 2026, Business track.

**Live demo:** https://hackathon-qiv6graw7ewfv6lqndywtd.streamlit.app/ (Streamlit Community Cloud; it may take a minute to wake up).
Demo only: please don't upload confidential client data.

## Headline results

No benchmark uses real agency data. Benchmark 1 uses a small hand-made set
checked by a person; benchmark 4 uses human labels on generated messages; the
rest run on **generated data** (see "About the data"). They show the code
works, not that it is accurate on real businesses.

| # | What we measured | Result |
|---|---|---|
| 1 | Cost engine vs a hand calculation done by a teammate (10 clients) | Exact match on all 29 client-months and 10 totals |
| 2 | Are the planted loss-making clients at the bottom? | All 15 planted loss-makers are the 15 lowest by profit; ranking by revenue finds only 3. Same on 2 more datasets (12/12 vs 4/12, 15/15 vs 3/15). Nearly circular: the planted "loss-making" label uses the same profit rule as the engine. |
| 3 | Forecast error, next quarter's margin | Simple baseline 0.143 vs LightGBM 0.172. LightGBM lost on all 3 datasets, so **the baseline ships**. |
| 4 | Request labeller vs 150 messages labelled by a teammate | Keyword rule 0.76 accuracy, LLM 0.73 to 0.75. The LLM ties a keyword rule; it ships as a reviewed suggestion. |
| 5 | Column mapping on 10 header styles | 172 of 172, but circular (same author wrote headers and word list). Real export headers pending. |
| 6 | Explanations with an invented number | 0 of 48 |
| 7 | Upload to ranked list, 50 clients | About 1 second (target under 60) |
| 8 | Suggested actions against planted client types | Every active loss-maker got an action (49 of 49 on new seeds); no healthy client told to cut or end (66 of 66). Since overhead is separated (D-36), "end the contract" fires almost never (once in 8 datasets, on a planted loss-maker): losing clients still cover their own costs or would after cutting unbilled work. Warnings: all 18 on planted problem clients, but only 4 of 41 late-trouble clients warned. |

**Unseen data.** Benchmarks 2, 3, 7 and 8 were re-run on 5 new generated
datasets (seeds 101 to 105) never used while building or tuning: bottom K
55 of 56 by profit vs 18 of 56 by revenue; LightGBM lost to the baseline on
all 5; about 0.6 s each. Seed 42, which the rules were tuned on, scored
perfectly on benchmark 8; the new seeds did not (see the warning recall above
and D-33). Same generator, so "unseen" means new random clients, not a new kind of data.

Two of our three AI parts lost to, or only tied, simple rules. We report that
instead of tuning on our own test data. Details: `docs/project_overview.md`
section 6 and `docs/decisions.md`.

## How it works

Diagram: `docs/architecture.md`. In short:

1. **Load and map:** reads messy CSV headers ("Amt", "Customer:Job") and
   suggests which column means what; the owner confirms.
2. **Validate:** lists every problem (bad values, duplicates, staff without a
   cost). No row is ever dropped silently; the owner ticks what to exclude.
3. **Cost engine (plain arithmetic, no AI):** per client per month,
   **contribution** = revenue − direct costs (optional: freelancers, ad spend,
   materials) − staff hours × hourly cost − cost of late payment: what the agency
   would lose without the client. **Profit** = contribution − the client's share
   of shared overhead (rent, software, admin), from the owner's yearly overhead
   split by logged hours, or ×1.3 on staff cost if not given. Every figure links
   back to its input rows.
4. **Rank:** by 12-month profit. Clients with under 3 months of data, or with
   nothing in the last 12 months, are listed apart with the reason and not ranked.
5. **Recommend:** fixed rules on the last 3 months. "End the contract" only
   when the client does not cover even its own costs (negative contribution)
   over 12 months and 3 months, cutting unbilled work would not fix it, and the
   price rise needed is over 50%. "End" and "cut scope" savings never count
   shared overhead, because it stays when a client goes; "raise price" aims to
   cover it.
6. **Forecast:** each client's margin trend with next quarter's margin, shown
   as a range: the typical error is measured on the owner's own data. The
   forecast is "last 3 months carried forward", because a LightGBM model was
   less accurate in every test.
7. **LLM (Featherless, Qwen 2.5 14B), two jobs only:** label client requests
   (in scope / extra unpaid / unclear) and write the explanation sentences.
   The LLM never does arithmetic. Code formats every number; a check rejects
   any text with a number that is not in the facts and shows fixed wording instead.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

Choose "Use demo data". If `data/generated` is missing, the app builds it on
first use (seed 42, about 10 seconds). For the LLM parts set
`FEATHERLESS_API_KEY` (never commit it; `.env` is in `.gitignore`). Without a
key, labels fall back to the keyword rule and explanations to fixed wording;
the ranked list never needs the LLM.

Other commands:

```
python scripts/generate_data.py --out data/generated --seed 42   # demo data
python scripts/run_pipeline.py --data data/generated --out out/   # no screen
python scripts/run_benchmarks.py                                  # out/benchmarks.json
pytest                                                            # 128 tests
```

Full list with options: `docs/execution.md` section 1.

## About the data

No real client data is used. All data is generated by `generator/` with
planted patterns (clients that look large but lose money, slow payers, growing
scope creep, noise). Benchmarks 2, 3 and 5 run on this generated data: they
show that the code works. They do not show that it is accurate on real
businesses. The generator is a separate module; the product code in
`src/clientprofit` never imports it, and the planted truth is read only by
the benchmark script.

## Demo data was labelled ahead of time

Each client request in the demo data is labelled (in scope, extra unpaid
work, or unclear) by an LLM. Labelling all 2,601 demo requests took about 33
minutes, so it was done once before the demo and the labels were saved in
`labels/saved_labels.json` (D-15). In the demo, saved labels are reused and
only new messages are sent to the LLM. The ranked client list never waits
for labels. Explanations are saved the same way (`labels/saved_explanations.json`).

## Honest limits

- **Not tested on a real agency.** Every benchmark uses generated or hand-made data.
  We also ran it on an independent synthetic dataset built for a university
  course (an HVAC contractor): column matching found 7 of 10 of its headers on
  the first try, and it exposed three weaknesses we then fixed (D-29 to D-32).
  That data is not in this repo.
- **Costs not tied to an invoice** (rent, software for the whole agency) are not
  split across clients; only staff time and per-invoice direct costs are.
- **Profit is only as good as the time log.** If staff under-log hours,
  clients look more profitable than they are. The screen warns about this.
- **Thresholds are judgement.** The recommendation rules (for example, "end"
  needs a price rise over 50%) were not fitted to real outcomes.
- **The "heading to a loss" warning is late, not early.** It fires only when a
  client's recent margin is already near zero; on new data it caught 4 of 41
  clients planted with late trouble.
- **Dollar effects assume the client accepts the change** and the workload stays the same.
- **The number check proves no number was invented,** not that each number is
  described correctly.
- **Privacy:** request messages are sent to Featherless for labelling. A real
  deployment needs a data agreement or a locally run model.

## Security

The app is public and has no login: it is a demo, not for confidential data.
AI use is capped per session, uploaded data is never written to the server's
disk, uploads are limited to 20 MB, and no key is stored in the repository.
Full list, including what is not protected: `SECURITY.md`.

## Docs

- `docs/project_overview.md`: what it does, results, implications, limits.
- `docs/architecture.md`: diagram of the parts.
- `docs/decisions.md`: every decision, options considered, measured effect.
- `docs/execution.md`: every command, function and failure path, kept in step with the code.
- `docs/deploy.md`: how to deploy the app.

## What was built during the event

The hackathon ran from 3 October 2026 12:00 PM to 10 October 2026 12:00 PM EDT.
This repository was created on 4 October 2026, and all code and documents in it
were written during the event. Nothing was brought in from before the start.
