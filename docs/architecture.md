# Architecture

GitHub shows this diagram as a picture. For the Devpost upload, take a
screenshot of it on GitHub, or paste the code block into https://mermaid.live
and export a PNG.

```mermaid
flowchart TD
    subgraph IN["Owner's files (CSV)"]
        INV[invoices]
        TE[time entries]
        RQ["client requests (optional)"]
        SV["services covered (optional)"]
        SC["staff hourly costs (or typed in)"]
    end

    subgraph CORE["Plain code, no AI (src/clientprofit)"]
        MAP["ingest.py: suggest column mapping,<br/>unify client names"]
        OK{{"Owner confirms mapping"}}
        VAL["validate.py: list every problem,<br/>drop nothing on its own"]
        EXC{{"Owner ticks rows to exclude"}}
        CE["cost_engine.py: profit per client per month<br/>= revenue − hours × cost × overhead − late cost"]
        RANK["Rank by 12-month profit<br/>(under 3 months: listed apart)"]
        FC["forecast/: next quarter's margin<br/>baseline ships (LightGBM lost, D-06)"]
        REC["recommend.py: keep / raise price /<br/>cut scope / end, with $ effect and alternative"]
    end

    subgraph AI["LLM via one wrapper (llm.py → Featherless, Qwen 2.5 14B)"]
        LAB["scope/: label each request<br/>in scope / extra unpaid / unclear"]
        EXP["explain.py: 2-3 sentences from<br/>facts formatted by code"]
        CHK{"Number check:<br/>any number not in the facts?"}
    end

    STORE[("Saved labels and explanations<br/>labels/*.json")]
    UI["Streamlit screen (app.py)<br/>ranked list, warnings, client detail"]

    INV & TE & RQ & SV --> MAP --> OK --> VAL --> EXC --> CE
    SC --> CE
    CE --> RANK --> UI
    CE --> FC
    RQ --> LAB
    SV --> LAB
    LAB <--> STORE
    LAB -. "extra-work share<br/>(optional signal)" .-> REC
    RANK --> REC --> UI
    REC --> EXP
    EXP <--> STORE
    EXP --> CHK
    CHK -- "no: show AI text" --> UI
    CHK -- "yes: show fixed wording" --> UI

    GEN["generator/ (test data only)<br/>never imported by src/clientprofit"]
    TRUTH[("planted truth file")]
    BENCH["scripts/run_benchmarks.py"]
    GEN -. "CSV files" .-> INV
    GEN -.-> TRUTH -.-> BENCH
```

## Rules the diagram encodes

- **The ranked list never waits for the LLM.** It is shown as soon as the cost
  engine finishes (about 1 second for 50 clients). Labels and explanations fill
  in afterwards.
- **The LLM never does arithmetic.** Every number is computed and formatted by
  code. The LLM only chooses a label or writes words around given numbers.
- **One wrapper for the provider** (`src/clientprofit/llm.py`). Changing the
  provider is a config change.
- **If the LLM is down,** labels fall back to a keyword rule and explanations
  to fixed wording. After 5 failed calls in a row the app stops calling.
- **The generator is test equipment.** Product code never imports it. Only the
  benchmark script reads the planted truth. The app uses the generator only to
  build demo files when they are missing (D-28).
