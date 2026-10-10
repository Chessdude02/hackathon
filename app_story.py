"""Story-first version of the screen: the finding, the picture, what to do, then the proof.

Same calculations as app.py (it calls the same pipeline and rules); only the order and the views differ.
Run with: streamlit run app_story.py
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT))  # for generator/, used only to build missing demo data (D-28)

from clientprofit import config, explain, ingest, pipeline, recommend, schema, validate  # noqa: E402
from clientprofit.scope.registry import get_detector, services_by_client  # noqa: E402
from clientprofit.scope.store import LabelStore  # noqa: E402

ASK_BEFORE_LABELLING = 200   # more new messages than this: show the time and ask first (D-15)
# D-35: the public app spends the team's AI credits, so each browser session has a ceiling.
MAX_LIVE_LABELS = 500        # more new messages than this: keyword rule only, no AI calls
MAX_LIVE_EXPLANATIONS = 25   # new AI explanations per session; saved ones do not count
SECONDS_PER_MESSAGE = 0.8    # measured 2026-10-06, 2 calls at a time (D-15)
TABLE_NAMES = {"invoices": "Invoices", "time_entries": "Time entries", "requests": "Client requests",
               "clients": "Clients and services", "all": "all files"}
IGNORE_LABEL = "(not used)"


def nice(name):
    """Plain words for an internal table or column name: no underscores on the screen."""
    return TABLE_NAMES.get(name, str(name).replace("_", " "))
DEMO = Path(os.environ.get("CLIENTPROFIT_DEMO_DIR", ROOT / "data" / "generated"))
DEMO_SEED = 42           # the saved labels and explanations were made from seed 42 (D-15, D-26)
DEMO_CLIENTS = 50
IGNORE = "(ignore)"
REQUIRED_FILES = ("invoices", "time_entries")  # requests and clients are optional
# Raise when the shape of a pipeline result changes. A browser tab kept open across an
# update still holds a result made by the old code; it is dropped and ranked again.
RESULT_VERSION = 2  # 2: direct costs and reasons for not ranking (D-30, D-31)


def money(v):
    if pd.isna(v):
        return ""
    return f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"


# Tables keep real numbers so sorting works; these only change how they look.
DOLLARS = st.column_config.NumberColumn(format="dollar", step=1)  # step=1: whole dollars
PERCENT = st.column_config.NumberColumn(format="%.0f%%")


def number_formats(df):
    """Column formats for a table: money columns as dollars, Margin as a percent."""
    money_words = ("Profit", "Contribution", "Revenue", "Direct cost", "Effect", "cost", "Overhead")
    cfg = {c: DOLLARS for c in df.columns if any(w in c for w in money_words)}
    if "Margin" in df.columns:
        cfg["Margin"] = PERCENT
    return cfg


@st.cache_resource(show_spinner=False)
def ensure_demo_data(folder=DEMO):
    """Build the demo files once per server if they are missing, e.g. on a fresh deploy (D-28).
    Same seed as the saved labels, so the labels and explanations are reused, not re-bought."""
    folder = Path(folder)
    if not (folder / "invoices.csv").exists():
        from generator.generate import generate  # app only; src/clientprofit never imports the generator
        generate(DEMO_SEED, DEMO_CLIENTS, folder, folder.parent / "truth")
    return str(folder)


def load_demo():
    loaded = pipeline.load_files(pipeline.find_files(DEMO))
    costs = config.read_staff_costs(DEMO / "staff_costs.csv") if (DEMO / "staff_costs.csv").exists() else {}
    return loaded, costs


def load_uploads(files, staff_file):
    loaded = {}
    for table, f in files.items():
        if f is not None:
            raw = pd.read_csv(f, dtype=str, keep_default_na=False)
            loaded[table] = {"raw": raw, "src_file": f.name, "mapping": ingest.propose_mapping(raw.columns, table)}
    costs = {}
    if staff_file is not None:
        df = pd.read_csv(staff_file)
        costs = {str(s): float(c) for s, c in zip(df.iloc[:, 0], df.iloc[:, 1])}
    return loaded, costs


def mapping_editor(loaded):
    """One select box per header, defaulting to the suggestion. Returns False if anything required is unmapped."""
    ok = True
    for table, item in loaded.items():
        columns = {**schema.TABLES, **schema.OPTIONAL_TABLES}[table]
        options = [IGNORE] + list(columns)
        missing = ingest.missing_required(item["mapping"], table)
        with st.expander(nice(table) + (f" (missing: {', '.join(nice(m) for m in missing)})" if missing else ""),
                         expanded=bool(missing)):
            cols = st.columns(3)
            for i, header in enumerate(item["raw"].columns):
                current = item["mapping"].get(header) or IGNORE
                choice = cols[i % 3].selectbox(header, options, index=options.index(current),
                                               key=f"map_{table}_{header}",
                                               format_func=lambda o: IGNORE_LABEL if o == IGNORE else nice(o))
                item["mapping"][header] = None if choice == IGNORE else choice
            missing = ingest.missing_required(item["mapping"], table)
            if missing:
                st.error(f"Map a column to: {', '.join(nice(m) for m in missing)}")
                ok = False
    return ok


def settings_editor(cfg, staff_names, costs):
    s = dict(cfg)
    c1, c2, c3 = st.columns(3)
    s["overhead_per_year"] = c1.number_input(
        "Shared overhead per year ($)", 0.0, 1e8, float(cfg.get("overhead_per_year", 0)), 1000.0,
        help="Rent, software, admin salaries, insurance: costs no single client causes. Split by logged hours. "
             "Leave at 0 to use the overhead multiplier instead.")
    s["overhead_multiplier"] = c1.number_input("Overhead multiplier (used when overhead per year is 0)", 1.0, 5.0,
                                               float(cfg["overhead_multiplier"]), 0.05)
    s["target_margin"] = c2.number_input("Target margin", 0.0, 0.95, float(cfg["target_margin"]), 0.05)
    s["late_payment_annual_rate"] = c3.number_input("Late payment cost per year", 0.0, 0.5,
                                                    float(cfg["late_payment_annual_rate"]), 0.01)
    s["payment_terms_days"] = int(c1.number_input("Payment terms (days)", 0, 365, cfg["payment_terms_days"]))
    s["unpaid_warning_days"] = int(c2.number_input("Warn when unpaid after (days past due)", 0, 365,
                                                   cfg["unpaid_warning_days"]))
    s["min_months_for_ranking"] = int(c3.number_input("Months of data needed to rank", 1, 24,
                                                      cfg["min_months_for_ranking"]))
    known = {**cfg["staff_costs"], **costs}
    table = pd.DataFrame({"Staff": staff_names, "Hourly cost": [known.get(n) for n in staff_names]})
    st.caption("Hourly cost per staff member (what each hour costs you, before overhead)")
    edited = st.data_editor(table, disabled=["Staff"], hide_index=True, key="staff_costs",
                            width="stretch")
    s["staff_costs"] = {name: float(cost) for name, cost in zip(edited["Staff"], edited["Hourly cost"])
                        if pd.notna(cost)}
    return s


def problems_panel(problems):
    """Show problems; return the rows the owner chose to exclude."""
    exclusions = {}
    icons = {"error": "Error:", "warning": "Warning:", "info": "Note:"}
    counts = {sev: sum(p["severity"] == sev for p in problems) for sev in icons}
    title = f"Problems found: {counts['error']} errors, {counts['warning']} warnings, {counts['info']} notes"
    with st.expander(title, expanded=counts["error"] > 0):
        for i, p in enumerate(problems):
            st.markdown(f"{icons[p['severity']]} **{p['check'].replace('_', ' ')}** ({nice(p['table']).lower()}): "
                        + md(p["message"]))
            if p["rows"]:
                st.caption(f"Rows: {', '.join(map(str, p['rows'][:30]))}{' and more' if len(p['rows']) > 30 else ''}")
            if p["rows"] and p["severity"] != "info":
                if st.checkbox(f"Exclude these {len(p['rows'])} row(s)", value=p["suggest_exclude"], key=f"ex_{i}"):
                    exclusions.setdefault(p["table"], []).extend(p["rows"])
    return exclusions


def has_direct_costs(result):
    return bool((result["client_month"]["direct_cost"] != 0).any())


def ranked_table(result, recs):
    r = result["ranked"].merge(recs, on="client", how="left")
    direct = {"Direct costs (12 mo)": r["direct_cost_last_12m"].round(0)} if has_direct_costs(result) else {}
    return pd.DataFrame({
        "Rank": r["rank"], "Client": r["client"],
        "Profit (12 mo)": r["profit_last_12m"].round(0),
        "Contribution (12 mo)": r["contribution_last_12m"].round(0),
        "Revenue (12 mo)": r["revenue_last_12m"].round(0),
        **direct,
        "Margin": (r["margin_last_12m"] * 100).round(0) + 0.0,  # + 0.0 shows -0% as 0%
        "Profit (last 3 mo)": r["profit_3m"].round(0),
        "Losing money": r["loss_making"].map({True: "Yes", False: ""}),
        "Heading to a loss": r["heading_to_loss"].map({True: "Yes", False: ""}),
        "Suggested action": r["action"],
        "Effect per year": [round(v) if a != recommend.KEEP and pd.notna(v) else None for a, v in zip(r["action"],
                                                                                   r["dollar_effect_per_year"])],
        "Profit if overdue never paid": r["profit_if_overdue_unpaid"].round(0),
    })


def headline(result, recs):
    """The story in four numbers, from figures already computed. No new calculation rules."""
    r = result["ranked"].merge(recs, on="client", how="left")
    losers = r[r["profit_last_12m"] < 0]
    act = r[r["action"] != recommend.KEEP]
    c = st.columns(4)
    c[0].metric("Clients losing money (12 mo)", f"{len(losers)} of {len(r)}")
    c[1].metric("What they cost you (12 mo)", money(-losers["profit_last_12m"].sum()))
    c[2].metric("Clients that need a decision", f"{len(act)}")
    c[3].metric("Profit from all ranked clients (12 mo)", money(r["profit_last_12m"].sum()))
    top = r.sort_values("revenue_last_12m", ascending=False).head(10).dropna(subset=["margin_last_12m"])
    if len(top):
        b = top.loc[top["margin_last_12m"].idxmin()]
        n = int((r["revenue_last_12m"] > b["revenue_last_12m"]).sum()) + 1
        if b["profit_last_12m"] < 0:
            text = (f"**Big revenue is not big profit.** {b['client']} is your number {n} client by revenue "
                    f"({money(b['revenue_last_12m'])} in 12 months), yet it lost you "
                    f"{money(-b['profit_last_12m'])} over the same period.")
        else:
            text = (f"**Big revenue is not big profit.** {b['client']} is your number {n} client by revenue "
                    f"({money(b['revenue_last_12m'])} in 12 months), yet only {b['margin_last_12m']:.0%} "
                    f"of it is left as profit.")
        st.markdown(text.replace("$", "\\$"))


def attention_table(result, recs):
    """Clients whose suggested action is not 'keep as is', biggest loss first."""
    t = ranked_table(result, recs)
    t = t[t["Suggested action"] != recommend.KEEP].sort_values("Profit (12 mo)")
    cols = ["Client", "Revenue (12 mo)", "Profit (12 mo)", "Margin", "Profit (last 3 mo)",
            "Heading to a loss", "Suggested action", "Effect per year"]
    return t[cols]


def draw_ranking(slot, result, recs):
    """Headline, the clients that need a decision, then every client ranked. Redrawn when labels arrive."""
    with slot.container():
        headline(result, recs)
        need = attention_table(result, recs)
        st.subheader(f"Needs your attention ({len(need)})")
        if len(need):
            st.caption("Worst first. Pick one in section 5 to see why and the rows behind it.")
            st.dataframe(need, hide_index=True, width="stretch", column_config=number_formats(need))
        else:
            st.caption("Every ranked client is at or near your target margin.")
        st.subheader("All clients, ranked by profit")
        table = ranked_table(result, recs)
        st.dataframe(table, hide_index=True, width="stretch", column_config=number_formats(table))


ACTION_COLOURS = {recommend.KEEP: "#2ca02c", recommend.RAISE: "#ff7f0e", recommend.CUT: "#d62728",
                  recommend.END: "#7f0000"}


def revenue_vs_profit(result, recs):
    """One dot per ranked client: 12-month revenue across, 12-month profit up. Figures already computed."""
    r = result["ranked"].merge(recs, on="client", how="left")
    rows = [{"client": c, "revenue": float(v), "profit": float(p), "action": a}
            for c, v, p, a in zip(r["client"], r["revenue_last_12m"], r["profit_last_12m"], r["action"])]
    shown = [a for a in ACTION_COLOURS if a in set(r["action"])]
    st.vega_lite_chart({
        "height": 340,
        "layer": [
            {"data": {"values": rows}, "mark": {"type": "circle", "size": 120, "opacity": 0.85},
             "encoding": {
                 "x": {"field": "revenue", "type": "quantitative", "title": "Revenue, last 12 months",
                       "axis": {"format": "$,.0f"}},
                 "y": {"field": "profit", "type": "quantitative", "title": "Profit, last 12 months",
                       "axis": {"format": "$,.0f"}},
                 "color": {"field": "action", "type": "nominal", "title": "Suggested action",
                           "scale": {"domain": shown, "range": [ACTION_COLOURS[a] for a in shown]},
                           "legend": {"orient": "bottom"}},
                 "tooltip": [{"field": "client", "title": "Client"},
                             {"field": "revenue", "title": "Revenue", "format": "$,.0f"},
                             {"field": "profit", "title": "Profit", "format": "$,.0f"},
                             {"field": "action", "title": "Suggested action"}]}},
            {"data": {"values": [{"y": 0}]}, "mark": {"type": "rule", "strokeDash": [4, 4], "color": "gray"},
             "encoding": {"y": {"field": "y", "type": "quantitative"}}},
        ]}, width="stretch")
    st.caption("Each dot is a client. Dots below the dashed line lost money over the last 12 months. "
               "If revenue meant profit, the dots would climb from left to right; many of the biggest "
               "clients sit near or below the line. Hover over a dot for the name.")


def overdue_note(result, client, settings):
    """Invoices for this client already flagged overdue and unpaid by the pipeline."""
    inv = result["invoices_costed"]
    od = inv[(inv["client"] == client) & inv["overdue_unpaid"]]
    if len(od):
        st.warning(f"Also: {len(od)} invoice(s) worth {money(od['amount'].sum())} are unpaid more than "
                   f"{settings['unpaid_warning_days']} days past due. Chase payment before deciding on price "
                   "or scope.".replace("$", "\\$"))


def ranked_view(result, recs):
    """Heading, notes and the ranking. Returns the ranking's slot so it can be refreshed."""
    st.subheader(f"Last 12 months to {result['as_of']:%d %b %Y}")
    st.caption(f"Ranked in {result['seconds_to_ranked']:.2f} s. Suggested actions use the last 3 months and "
               "assume the same workload and that the client accepts the change. You decide; nothing is "
               "sent to clients.")
    st.warning("These figures assume your time logs are complete. If staff log fewer hours than they "
               "really work, every client looks more profitable than it is.")
    slot = st.empty()
    draw_ranking(slot, result, recs)
    st.caption(overhead_note(result).replace("$", "\\$"))  # else Streamlit reads $...$ as maths
    return slot


def overhead_note(result):
    """D-36: what the two profit columns mean, how overhead was split, and how the clients add up."""
    o, rk = result.get("overhead", {}), result["ranked"]
    how = (f"your {money(o['per_year'])} a year of shared overhead, split by logged hours "
           f"(${o['rate_per_hour']:,.2f} an hour)" if o.get("rate_per_hour") is not None
           else f"staff cost times {o.get('multiplier', 1):.2f} as an estimate of shared overhead (enter your real "
                "yearly overhead in Settings to replace it)")
    contribution, overhead = rk["contribution_last_12m"].sum(), rk["overhead_last_12m"].sum()
    other = result["unranked"]["overhead_last_12m"].sum() if len(result["unranked"]) else 0.0
    return (f"Contribution = revenue minus the client's own costs (staff time, direct costs, late payment): "
            f"what you would lose without it. Profit also takes off its share of overhead, using {how}. "
            f"'End the contract' and 'cut scope' use contribution, because shared overhead stays when "
            f"a client or its work goes; 'raise price' uses profit. Ranked clients, last 12 months: "
            f"contribution {money(contribution)} minus overhead {money(overhead)} equals profit "
            f"{money(contribution - overhead)}."
            + (f" Clients not ranked carry the other {money(other)} of overhead." if round(other) else ""))


def scope_section(result, cfg):
    """Label client requests (D-15, D-23). Returns labels in request order, or None."""
    req = result["tables"].get("requests")
    if req is None or not len(req):
        st.info("No client requests uploaded, so scope-creep signals are off. The ranking and suggested "
                "actions still work.")
        return None
    st.subheader("Scope-creep signals (beta)")
    st.caption("An AI model labels each client message as routine, extra unpaid work, or unclear, using the "
               "client's services if given. On our test data it did no better than a simple keyword rule, "
               "so treat labels as prompts to review, not facts. Message text is sent to the AI provider.")
    if st.session_state.get("labels") is not None:
        return st.session_state.labels
    name = cfg["scope"]["detector"]
    detector = get_detector(name, cfg, store=session_store("labels")) if name == "llm" else get_detector(name, cfg)
    services = services_by_client(result["tables"])
    new = detector.count_new(req, services) if hasattr(detector, "count_new") else 0
    if new > MAX_LIVE_LABELS:
        st.warning(f"{new} messages have not been labelled before. This public demo labels at most "
                   f"{MAX_LIVE_LABELS} new messages with AI per session, so the simple keyword rule labels "
                   "them instead. Run the app yourself with your own key to use AI labels.")
        detector, new = get_detector("keyword"), 0
    elif new > ASK_BEFORE_LABELLING and not st.session_state.get("label_go"):
        st.warning(f"{new} messages have not been labelled before. That takes about "
                   f"{new * SECONDS_PER_MESSAGE / 60:.0f} minutes. The ranking above does not wait for it.")
        if st.button("Label them now"):
            st.session_state.label_go = True
            st.rerun()
        return None
    bar = st.progress(0.0, text=f"Labelling {new} new messages...")
    labels = detector.label_requests(
        req, services, progress=lambda d, n: bar.progress(d / n if n else 1.0, text=f"Labelled {d} of {n} new messages"))
    bar.empty()
    st.session_state.labels = labels
    return labels


def labels_summary(labels):
    counts = pd.Series([x["label"] for x in labels]).value_counts().to_dict()
    sources = pd.Series([x["source"] for x in labels]).value_counts().to_dict()
    fallback = sum(v for k, v in sources.items() if k.startswith("keyword"))
    st.caption(f"{len(labels)} messages: {counts.get('extra_unpaid', 0)} look like extra unpaid work, "
               f"{counts.get('in_scope', 0)} routine, {counts.get('unclear', 0)} unclear. "
               f"{sources.get('saved', 0)} reused from saved labels"
               + (f"; {fallback} used the keyword rule because the AI was unavailable." if fallback else "."))


def plain(text):
    """Text from the AI, without the dashes and typographic symbols that make it read as machine-written."""
    for a, b in ((" — ", ", "), ("—", ", "), (" – ", ", "), ("–", "-"), ("−", "-"), ("’", "'"), ("‘", "'"),
                 ("“", '"'), ("”", '"'), ("…", "...")):
        text = str(text).replace(a, b)
    return text


def md(text):
    return explain.escape_markdown(text)


EFFECT_WORDS = {recommend.RAISE: "+{} profit a year", recommend.CUT: "saves {} a year",
                recommend.END: "stops a {}-a-year loss"}


def recommendation_box(rec):
    words = EFFECT_WORDS.get(rec["action"])
    effect = f" ({words.format(money(rec['dollar_effect_per_year']))})" if words else ""
    st.markdown("#### " + md(f"Suggested action: {rec['action']}{effect}"))
    st.markdown(md(rec["why"]))
    if isinstance(rec.get("alternative"), str) and rec["alternative"]:
        st.markdown("**" + md(rec["alternative"]) + "**")
    if rec["heading_to_loss"]:
        st.warning("Heading toward a loss: profitable over 12 months, but the last 3 months are below zero "
                   "or close to zero and falling.")
    st.caption("Based on the last 3 months, scaled to a year. Assumes the same workload and that the client "
               "accepts the change. You make the final call.")


def explanation_box(rec, totals, cfg):
    """Two or three sentences from the LLM using only computed numbers (D-26)."""
    key = ("explanation", rec["client"], rec["action"], round(rec["dollar_effect_per_year"], 2))
    if key not in st.session_state:
        used = st.session_state.get("live_explanations", 0)
        with st.spinner("Writing a plain-language explanation..."):
            st.session_state[key] = explain.write_explanation(
                rec, totals, cfg["llm"]["model"], cfg["llm"]["provider"], store=session_store("explanations"),
                allow_llm=used < MAX_LIVE_EXPLANATIONS)
        if st.session_state[key]["source"] == "llm" or st.session_state[key].get("error"):
            st.session_state.live_explanations = used + 1
    out = st.session_state[key]
    st.info(md(plain(out["text"])))
    if out["source"] == "template":
        reason = ("the AI was unavailable" if out.get("error")
                  else f"this session reached its limit of {MAX_LIVE_EXPLANATIONS} AI explanations"
                  if out.get("capped")
                  else "the AI's reply was unreadable" if out.get("broken")
                  else f"the AI's text used numbers not in the figures ({', '.join(out['invented'])})")
        st.caption(f"Standard wording shown because {reason}.")
    else:
        st.caption("Written by AI from the figures above; every number in it was checked against them.")


MONEY_COLUMNS = {"Amount", "Direct cost", "Late payment cost", "Hourly cost", "Staff cost",
                 "Labour cost (with overhead)"}
LABEL_WORDS = {"in_scope": "routine", "extra_unpaid": "extra unpaid work", "unclear": "unclear"}


def readable(rows, names):
    """Rows behind a figure, for people: plain column names, dates without times, money rounded."""
    out = rows[list(names)].rename(columns=names).copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d").fillna("")
        elif col in MONEY_COLUMNS:
            out[col] = out[col].map(lambda v: "" if pd.isna(v) else f"${v:,.2f}")
    if "AI label" in out.columns:
        out["AI label"] = out["AI label"].map(lambda v: LABEL_WORDS.get(v, v))
    return out


def session_store(kind):
    """Where AI labels and explanations are kept (D-35). Demo data: the saved files shipped with the
    repo, so nothing is paid for twice. Uploads: this browser session's memory only, so nothing from
    a visitor's files is written to the server's disk."""
    if st.session_state.get("source") == "demo":
        return LabelStore() if kind == "labels" else LabelStore(explain.EXPLANATIONS_PATH)
    key = f"memory_store_{kind}"
    if key not in st.session_state:
        st.session_state[key] = LabelStore(None)
    return st.session_state[key]


def trend_box(result, rec, settings):
    """D-37: the client's 3-month margin over time, the target, and next quarter two ways: if nothing
    changes, and after the suggested action. Both come from computed figures; nothing is predicted."""
    hist = recommend.margin_history(result, rec["client"])
    if hist.empty:
        return
    st.markdown("**Margin trend and the effect of the suggested action**")
    target = settings["target_margin"]
    names = ["Margin, last 3 months", "If nothing changes", "After the suggested action"]
    rows = [{"date": m.end_time.strftime("%Y-%m-01"), "margin": v, "series": names[0]}
            for m, v in zip(hist["month"], hist["margin"])]
    nxt = (hist["month"].max() + 2).end_time.strftime("%Y-%m-01")  # middle of next quarter
    now, after = rec.get("margin_3m"), rec.get("margin_after_action")
    points = []
    if now is not None and now == now:
        points.append({"date": nxt, "margin": now, "series": names[1]})
    if after is not None and after == after and rec["action"] != recommend.KEEP:
        points.append({"date": nxt, "margin": after, "series": names[2]})
    # the legend lists only what is drawn: a client to keep has no "after" point
    shown = [n for n, c in zip(names, ["#1f77b4", "#9e9e9e", "#2ca02c"])
             if n == names[0] or any(p["series"] == n for p in points)]
    palette = dict(zip(names, ["#1f77b4", "#9e9e9e", "#2ca02c"]))
    color = {"field": "series", "type": "nominal", "title": None,
             "legend": {"orient": "bottom", "labelLimit": 400},
             "scale": {"domain": shown, "range": [palette[n] for n in shown]}}
    x = {"field": "date", "type": "temporal", "title": None, "axis": {"format": "%b %Y"}}
    y = {"field": "margin", "type": "quantitative", "axis": {"format": "%"}, "title": "Margin"}
    st.vega_lite_chart({
        "height": 260,
        "layer": [
            {"data": {"values": rows}, "mark": {"type": "line", "point": True},
             "encoding": {"x": x, "y": y, "color": color}},
            {"data": {"values": points}, "mark": {"type": "point", "filled": True, "size": 140},
             "encoding": {"x": x, "y": y, "color": color}},
            {"data": {"values": [{"t": target}]}, "mark": {"type": "rule", "strokeDash": [4, 4], "color": "gray"},
             "encoding": {"y": {"field": "t", "type": "quantitative"}}},
        ]}, width="stretch")
    if rec["action"] == recommend.KEEP:
        effect = "No change suggested, so the margin stays where it is."
    elif rec["action"] == recommend.END:
        effect = ("If the contract ends there is no next quarter for this client; the money saved is the "
                  "effect per year shown above.")
    elif after is not None and after == after:
        effect = f"After the suggested action ({rec['action']}): about {after:.0%}."
    else:
        effect = ""
    st.caption(f"Grey dashed line: your {target:.0%} target. Next quarter if nothing changes: "
               + (f"{now:.0%} (the last 3 months). " if now is not None and now == now else "no revenue to compare. ")
               + effect + " These are not predictions: we tested forecasting models and none beat "
               "'the next quarter looks like the last one', so the chart shows the trend and what "
               "the suggested action would change, at the current workload.")


def client_detail(result, recs, labels, cfg):
    clients = list(result["ranked"]["client"]) + list(result["unranked"]["client"])
    act = recs[recs["action"] != recommend.KEEP].merge(result["ranked"][["client", "profit_last_12m"]], on="client")
    first = act.sort_values("profit_last_12m")["client"].iloc[0] if len(act) else clients[0]
    client = st.selectbox("Client detail", clients, index=clients.index(first), key="detail_client",
                          help="Opens on the client that needs a decision most (largest 12-month loss).")
    rec = recs[recs["client"] == client]
    if len(rec):
        recommendation_box(rec.iloc[0].to_dict())
        overdue_note(result, client, cfg)
        totals = result["totals"].set_index("client").loc[client].to_dict()
        explanation_box(rec.iloc[0].to_dict(), totals, cfg)
        trend_box(result, rec.iloc[0].to_dict(), cfg)
    else:
        reason = result["unranked"].set_index("client").loc[client, "not_ranked_because"]
        st.info(f"Not ranked and no action suggested: {reason}.")
    cm = result["client_month"][result["client_month"]["client"] == client]
    direct = {"Direct costs": cm["direct_cost"].round(0)} if has_direct_costs(result) else {}  # numbers, formatted below
    month_table = pd.DataFrame({
        "Month": cm["month"].astype(str), "Revenue": cm["revenue"].round(0), **direct,
        "Staff cost": cm["staff_cost"].round(0), "Late payment cost": cm["late_cost"].round(0),
        "Contribution": cm["contribution"].round(0), "Overhead share": cm["overhead_cost"].round(0),
        "Profit": cm["profit"].round(0), "Hours": cm["hours"].round(1),
        "Margin": (cm["margin"] * 100).round(0) + 0.0,
    })
    st.dataframe(month_table, hide_index=True, width="stretch", column_config=number_formats(month_table))
    month = st.selectbox("Show the rows behind a month", cm["month"].astype(str).tolist(), key="detail_month")
    row = cm[cm["month"].astype(str) == month].iloc[0]
    inv = result["invoices_costed"]
    te = result["time_costed"]
    inv_rows = inv[(inv["client"] == client) & inv[schema.SRC_ROW].isin(row["invoice_rows"])]
    te_rows = te[(te["client"] == client) & te[schema.SRC_ROW].isin(row["time_rows"])]
    st.markdown("Invoices")
    st.dataframe(readable(inv_rows, {
        schema.SRC_ROW: "Row in file", "invoice_date": "Invoice date", "amount": "Amount",
        "due": "Due", "paid_date": "Paid", "days_late": "Days late", "late_cost": "Late payment cost",
        **({"direct_cost": "Direct cost"} if has_direct_costs(result) else {})}),
        hide_index=True, width="stretch")
    st.markdown("Time entries (staff cost = hours x hourly cost; overhead is added per month above)")
    st.dataframe(readable(te_rows, {
        schema.SRC_ROW: "Row in file", "work_date": "Date", "staff": "Staff", "hours": "Hours",
        "hourly_cost": "Hourly cost", "staff_cost": "Staff cost", "billable": "Billable"}),
        hide_index=True, width="stretch")
    req = result["tables"].get("requests")
    if labels is not None and req is not None:
        mine = req.assign(label=[x["label"] for x in labels])
        mine = mine[mine["client"] == client].sort_values("request_date", ascending=False)
        st.markdown(f"Client requests with AI labels (beta, review before acting): {len(mine)}")
        st.dataframe(readable(mine, {"request_date": "Date", "channel": "Channel", "message": "Message",
                                     "label": "AI label"}), hide_index=True, width="stretch")


def main():
    st.set_page_config(page_title="Client profit finder", layout="wide")
    st.title("Client profit finder")
    st.markdown("**Your biggest clients are not always your most profitable.** See which clients really make "
                "you money, and what to do about the ones that don't.")
    cfg = config.load_config()

    st.caption("Demo only: please don't upload confidential client data. Uploaded files stay in this "
               "session, but request messages are sent to an outside AI service (Featherless) for labelling.")
    source = st.radio("Data", ["Use demo data (generated)", "Upload my files"], horizontal=True)
    if source.startswith("Use demo"):
        if not (DEMO / "invoices.csv").exists():
            with st.spinner("Building the demo data (first start only, about 10 seconds)..."):
                ensure_demo_data()
        if "loaded" not in st.session_state or st.session_state.get("source") != "demo":
            st.session_state.loaded, st.session_state.costs = load_demo()
            st.session_state.source = "demo"
    else:
        c = st.columns(5)
        files = {t: c[i].file_uploader(nice(t) + (" (CSV)" if t in REQUIRED_FILES else " (CSV, optional)"), type="csv")
                 for i, t in enumerate(pipeline.TABLE_FILES)}
        staff_file = c[4].file_uploader("Staff costs (CSV, optional)", type="csv")
        if not all(files[t] is not None for t in REQUIRED_FILES):
            st.info("Upload invoices and time entries to start. Client requests and services are optional: "
                    "they add scope-creep signals but the ranking works without them.")
            return
        # Read the files again whenever the set of uploads changes, so a file added after the first
        # two (staff costs, requests, clients) is never silently ignored.
        uploads = tuple((t, getattr(f, "file_id", None) or (f.name, f.size)) if f is not None else (t, None)
                        for t, f in [*files.items(), ("staff_costs", staff_file)])
        if (st.session_state.get("source") != "upload" or st.session_state.get("uploads") != uploads
                or st.button("Reload files")):
            st.session_state.loaded, st.session_state.costs = load_uploads(files, staff_file)
            st.session_state.source, st.session_state.uploads = "upload", uploads
            st.session_state.result = st.session_state.labels = None  # results were for the old files

    loaded = st.session_state.loaded
    demo = st.session_state.get("source") == "demo"
    with st.expander("Data and settings: column mapping, costs and rules, problems in the files",
                     expanded=not demo):
        st.subheader("Check the column mapping")
        st.caption("Open a file to check or change which column means what.")
        if not mapping_editor(loaded):
            return
        tables = pipeline.apply_mappings(loaded)
        st.subheader("Costs and rules")
        staff_names = sorted(tables["time_entries"]["staff"].dropna().unique())
        known = {**cfg["staff_costs"], **st.session_state.costs}
        missing_costs = [n for n in staff_names if n not in known]
        if missing_costs:
            st.error(f"{len(missing_costs)} staff without an hourly cost: fill them in below.")
        settings = settings_editor(cfg, staff_names, st.session_state.costs)
        st.subheader("Problems in the files")
        named, merged = ingest.unify_client_names(tables)
        problems = validate.validate_inputs(named, settings, merged)
        exclusions = problems_panel(problems)

    clicked = st.button("Rank again with these settings" if demo or st.session_state.get("result") is not None
                        else "Rank clients",
                        type="primary")
    first_demo_run = demo and st.session_state.get("result") is None
    if clicked or first_demo_run:  # the demo ranks itself, so the story is the first thing on screen
        start = time.perf_counter()
        st.session_state.result = pipeline.run_pipeline(tables, settings, exclusions)
        st.session_state.result["seconds_to_ranked"] = time.perf_counter() - start
        st.session_state.labels, st.session_state.label_go = None, False
        st.session_state.result_version = RESULT_VERSION
    if st.session_state.get("result") is not None and st.session_state.get("result_version") != RESULT_VERSION:
        st.session_state.result = None
        st.info("The app was updated since you last ranked. Click \"Rank clients\" again.")
    result = st.session_state.get("result")
    if result is None:
        return
    if result["stopped"]:
        st.error("Cannot rank yet. Fix or exclude these errors: " +
                 "; ".join(p["message"] for p in result["stopped"]))
        return

    # The story is drawn into these containers after the request labels are known (they live at the
    # bottom of the page but feed the suggested actions), so it reads top to bottom.
    story = st.container()
    st.divider()
    with st.expander("Scope-creep signals (beta): how client requests were labelled"):
        labels = scope_section(result, cfg)
        if labels is not None:
            labels_summary(labels)
    recs = recommend.recommend_actions(result, settings, labels)

    with story:
        st.header("1. What we found")
        st.caption(f"Last 12 months to {result['as_of']:%d %b %Y}. Ranked in {result['seconds_to_ranked']:.2f} s.")
        headline(result, recs)

        st.header("2. Revenue is not profit")
        revenue_vs_profit(result, recs)

        st.header("3. What to do")
        need = attention_table(result, recs)
        st.subheader(f"Clients that need a decision ({len(need)}), worst first")
        if len(need):
            st.dataframe(need, hide_index=True, width="stretch", column_config=number_formats(need))
        st.caption("Suggested actions use the last 3 months and assume the same workload and that the client "
                   "accepts the change. You decide; nothing is sent to clients.")
        st.warning("These figures assume your time logs are complete. If staff log fewer hours than they "
                   "really work, every client looks more profitable than it is.")
        with st.expander("All clients, ranked by profit, and how profit is calculated"):
            table = ranked_table(result, recs)
            st.dataframe(table, hide_index=True, width="stretch", column_config=number_formats(table))
            st.caption(overhead_note(result).replace("$", "\\$"))
            if len(result["unranked"]):
                st.markdown("**Not ranked** (too little to go on, so no rank and no suggested action)")
                u = result["unranked"]
                st.dataframe(pd.DataFrame({"Client": u["client"], "Why not ranked": u["not_ranked_because"],
                                           "Months of data": u["months_of_data"],
                                           "Profit, all data": u["profit_all_data"].map(money)}),
                             hide_index=True, width="stretch")

        st.header("4. Why: one client, down to the source rows")
        st.caption("Pick any client. Opens on the one that needs a decision most.")
        client_detail(result, recs, labels, settings)

main()
