"""Streamlit entry point: upload, confirm mapping, settings, ranked list, client detail.

Run with: streamlit run app.py
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
from clientprofit.forecast.outlook import client_outlook  # noqa: E402
from clientprofit.scope.registry import get_detector, services_by_client  # noqa: E402
from clientprofit.scope.store import LabelStore  # noqa: E402

ASK_BEFORE_LABELLING = 200   # more new messages than this: show the time and ask first (D-15)
# D-35: the public app spends the team's AI credits, so each browser session has a ceiling.
MAX_LIVE_LABELS = 500        # more new messages than this: keyword rule only, no AI calls
MAX_LIVE_EXPLANATIONS = 25   # new AI explanations per session; saved ones do not count
SECONDS_PER_MESSAGE = 0.8    # measured 2026-10-06, 2 calls at a time (D-15)
ACTION_ICON = {recommend.KEEP: "✅", recommend.RAISE: "💲", recommend.CUT: "✂️", recommend.END: "🛑"}
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
        with st.expander(f"{item['src_file']} → {table}" + (f"  (missing: {', '.join(missing)})" if missing else ""),
                         expanded=bool(missing)):
            cols = st.columns(3)
            for i, header in enumerate(item["raw"].columns):
                current = item["mapping"].get(header) or IGNORE
                choice = cols[i % 3].selectbox(header, options, index=options.index(current),
                                               key=f"map_{table}_{header}")
                item["mapping"][header] = None if choice == IGNORE else choice
            missing = ingest.missing_required(item["mapping"], table)
            if missing:
                st.error(f"Map a column to: {', '.join(missing)}")
                ok = False
    return ok


def settings_editor(cfg, staff_names, costs):
    s = dict(cfg)
    c1, c2, c3 = st.columns(3)
    s["overhead_multiplier"] = c1.number_input("Overhead multiplier", 1.0, 5.0, float(cfg["overhead_multiplier"]), 0.05)
    s["target_margin"] = c2.number_input("Target margin", 0.0, 0.95, float(cfg["target_margin"]), 0.05)
    s["late_payment_annual_rate"] = c3.number_input("Late payment cost per year", 0.0, 0.5,
                                                    float(cfg["late_payment_annual_rate"]), 0.01)
    s["payment_terms_days"] = int(c1.number_input("Payment terms (days)", 0, 365, cfg["payment_terms_days"]))
    s["unpaid_warning_days"] = int(c2.number_input("Warn when unpaid after (days past due)", 0, 365,
                                                   cfg["unpaid_warning_days"]))
    s["min_months_for_ranking"] = int(c3.number_input("Months of data needed to rank", 1, 24,
                                                      cfg["min_months_for_ranking"]))
    known = {**cfg["staff_costs"], **costs}
    table = pd.DataFrame({"staff": staff_names, "hourly_cost": [known.get(n) for n in staff_names]})
    st.caption("Hourly cost per staff member (what each hour costs you, before overhead)")
    edited = st.data_editor(table, disabled=["staff"], hide_index=True, key="staff_costs",
                            width="stretch")
    s["staff_costs"] = {r.staff: float(r.hourly_cost) for r in edited.itertuples() if pd.notna(r.hourly_cost)}
    return s


def problems_panel(problems):
    """Show problems; return the rows the owner chose to exclude."""
    exclusions = {}
    icons = {"error": "🛑", "warning": "⚠️", "info": "ℹ️"}
    counts = {sev: sum(p["severity"] == sev for p in problems) for sev in icons}
    title = f"Problems found: {counts['error']} errors, {counts['warning']} warnings, {counts['info']} notes"
    with st.expander(title, expanded=counts["error"] > 0):
        for i, p in enumerate(problems):
            st.markdown(f"{icons[p['severity']]} **{p['check'].replace('_', ' ')}** ({p['table']}): {p['message']}")
            if p["rows"]:
                st.caption(f"Rows: {', '.join(map(str, p['rows'][:30]))}{' …' if len(p['rows']) > 30 else ''}")
            if p["rows"] and p["severity"] != "info":
                if st.checkbox(f"Exclude these {len(p['rows'])} row(s)", value=p["suggest_exclude"], key=f"ex_{i}"):
                    exclusions.setdefault(p["table"], []).extend(p["rows"])
    return exclusions


def has_direct_costs(result):
    return bool((result["client_month"]["direct_cost"] != 0).any())


def ranked_table(result, recs):
    r = result["ranked"].merge(recs, on="client", how="left")
    direct = {"Direct costs (12 mo)": r["direct_cost_last_12m"].map(money)} if has_direct_costs(result) else {}
    return pd.DataFrame({
        "Rank": r["rank"], "Client": r["client"],
        "Profit (12 mo)": r["profit_last_12m"].map(money),
        "Revenue (12 mo)": r["revenue_last_12m"].map(money),
        **direct,
        "Margin": r["margin_last_12m"].map(lambda v: "" if pd.isna(v) else f"{v:.0%}"),
        "Profit (last 3 mo)": r["profit_3m"].map(money),
        "Losing money": r["loss_making"].map({True: "Yes", False: ""}),
        "Heading to a loss": r["heading_to_loss"].map({True: "⚠️ Yes", False: ""}),
        "Suggested action": [f"{ACTION_ICON.get(a, '')} {a}" for a in r["action"]],
        "Effect per year": [money(v) if a != recommend.KEEP else "" for a, v in zip(r["action"],
                                                                                   r["dollar_effect_per_year"])],
        "Profit if overdue never paid": r["profit_if_overdue_unpaid"].map(money),
    })


def ranked_view(result, recs):
    """Heading, notes and the ranked table. Returns the table's slot so it can be refreshed."""
    st.subheader(f"Clients ranked by profit, last 12 months to {result['as_of']:%d %b %Y}")
    st.caption(f"Ranked in {result['seconds_to_ranked']:.2f} s. Suggested actions use the last 3 months and "
               "assume the same workload and that the client accepts the change. You decide; nothing is "
               "sent to clients.")
    st.warning("These figures assume your time logs are complete. If staff log fewer hours than they "
               "really work, every client looks more profitable than it is.", icon="⏱️")
    slot = st.empty()
    slot.dataframe(ranked_table(result, recs), hide_index=True, width="stretch")
    return slot


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
    bar = st.progress(0.0, text=f"Labelling {new} new messages…")
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


def md(text):
    return explain.escape_markdown(text)


EFFECT_WORDS = {recommend.RAISE: "+{} profit a year", recommend.CUT: "saves {} a year",
                recommend.END: "stops a {}-a-year loss"}


def recommendation_box(rec):
    icon = ACTION_ICON.get(rec["action"], "")
    words = EFFECT_WORDS.get(rec["action"])
    effect = f" ({words.format(money(rec['dollar_effect_per_year']))})" if words else ""
    st.markdown(f"#### {icon} " + md(f"Suggested action: {rec['action']}{effect}"))
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
        with st.spinner("Writing a plain-language explanation…"):
            st.session_state[key] = explain.write_explanation(
                rec, totals, cfg["llm"]["model"], cfg["llm"]["provider"], store=session_store("explanations"),
                allow_llm=used < MAX_LIVE_EXPLANATIONS)
        if st.session_state[key]["source"] == "llm" or st.session_state[key].get("error"):
            st.session_state.live_explanations = used + 1
    out = st.session_state[key]
    st.info(md(out["text"]), icon="💬")
    if out["source"] == "template":
        reason = ("the AI was unavailable" if out.get("error")
                  else f"this session reached its limit of {MAX_LIVE_EXPLANATIONS} AI explanations"
                  if out.get("capped")
                  else f"the AI's text used numbers not in the figures ({', '.join(out['invented'])})")
        st.caption(f"Standard wording shown because {reason}.")
    else:
        st.caption("Written by AI from the figures above; every number in it was checked against them.")


MONEY_COLUMNS = {"Amount", "Direct cost", "Late payment cost", "Hourly cost", "Labour cost (with overhead)"}
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


def outlook_box(result, client, settings):
    """3-month margin over time, the target, and next quarter's forecast with its typical error (D-34)."""
    if st.session_state.get("outlook_for") is not id(result):
        st.session_state.outlook = client_outlook(result, settings)
        st.session_state.outlook_for = id(result)
    features, out = st.session_state.outlook
    hist = features[(features["client"] == client) & features["margin_3m"].notna()]
    o = out.get(client, {})
    if hist.empty or o.get("forecast") is None:
        return
    st.markdown("**Margin trend and next quarter**")
    rows = [{"date": m.end_time.strftime("%Y-%m-01"), "margin": v, "series": "Margin, last 3 months"}
            for m, v in zip(hist["month"], hist["margin_3m"])]
    nxt = (hist["month"].max() + 2).end_time.strftime("%Y-%m-01")  # middle of next quarter
    err, f = o["typical_error"], o["forecast"]
    point = {"date": nxt, "margin": f, "series": "Next quarter (forecast)",
             "low": f - err if err is not None else f, "high": f + err if err is not None else f}
    target = settings["target_margin"]
    names = ["Margin, last 3 months", "Next quarter (forecast)"]
    color = {"field": "series", "type": "nominal", "title": None,
             "scale": {"domain": names, "range": ["#1f77b4", "#e4572e"]}}
    link = [rows[-1] | {"series": names[1]}, point]
    x = {"field": "date", "type": "temporal", "title": None, "axis": {"format": "%b %Y"}}
    st.vega_lite_chart({
        "height": 260,
        "layer": [
            {"data": {"values": rows}, "mark": {"type": "line", "point": True},
             "encoding": {"x": x,
                          "y": {"field": "margin", "type": "quantitative", "axis": {"format": "%"}, "title": "Margin"},
                          "color": color}},
            {"data": {"values": link}, "mark": {"type": "line", "strokeDash": [3, 3]},
             "encoding": {"x": x, "y": {"field": "margin", "type": "quantitative"}, "color": color}},
            {"data": {"values": [point]}, "mark": {"type": "rule", "strokeWidth": 8, "opacity": 0.3},
             "encoding": {"x": x, "y": {"field": "low", "type": "quantitative"},
                          "y2": {"field": "high"}, "color": color}},
            {"data": {"values": [point]}, "mark": {"type": "point", "filled": True, "size": 120},
             "encoding": {"x": x, "y": {"field": "margin", "type": "quantitative"}, "color": color}},
            {"data": {"values": [{"t": target}]}, "mark": {"type": "rule", "strokeDash": [4, 4], "color": "gray"},
             "encoding": {"y": {"field": "t", "type": "quantitative"}}},
        ]}, width="stretch")
    range_text = (f" On your data, this simple rule was off by {err:.0%} points on average over the last "
                  f"{settings['forecast']['test_months']} months, so read it as {f - err:.0%} to {f + err:.0%}."
                  if err is not None else " There is not enough history yet to say how far off it usually is.")
    st.caption(f"Grey dashed line: your {target:.0%} target. Next quarter, if nothing changes: about {f:.0%} "
               f"margin (the last 3 months carried forward; margin here leaves out late-payment cost)."
               + range_text + " A machine-learning forecast was tested and was less accurate (D-06), so this "
               "simple rule is used.")


def client_detail(result, recs, labels, cfg):
    clients = list(result["ranked"]["client"]) + list(result["unranked"]["client"])
    client = st.selectbox("Client detail", clients, key="detail_client")
    rec = recs[recs["client"] == client]
    if len(rec):
        recommendation_box(rec.iloc[0].to_dict())
        totals = result["totals"].set_index("client").loc[client].to_dict()
        explanation_box(rec.iloc[0].to_dict(), totals, cfg)
        outlook_box(result, client, cfg)
    else:
        reason = result["unranked"].set_index("client").loc[client, "not_ranked_because"]
        st.info(f"Not ranked and no action suggested: {reason}.")
    cm = result["client_month"][result["client_month"]["client"] == client]
    direct = {"Direct costs": cm["direct_cost"].map(money)} if has_direct_costs(result) else {}
    st.dataframe(pd.DataFrame({
        "Month": cm["month"].astype(str), "Revenue": cm["revenue"].map(money), **direct,
        "Labour cost": cm["labour_cost"].map(money), "Late payment cost": cm["late_cost"].map(money),
        "Profit": cm["profit"].map(money), "Hours": cm["hours"].round(1),
        "Margin": cm["margin"].map(lambda v: "no revenue" if pd.isna(v) else f"{v:.0%}"),
    }), hide_index=True, width="stretch")
    month = st.selectbox("Show the rows behind a month", cm["month"].astype(str).tolist(), key="detail_month")
    row = cm[cm["month"].astype(str) == month].iloc[0]
    inv = result["invoices_costed"]
    te = result["time_costed"]
    inv_rows = inv[(inv["client"] == client) & inv[schema.SRC_ROW].isin(row["invoice_rows"])]
    te_rows = te[(te["client"] == client) & te[schema.SRC_ROW].isin(row["time_rows"])]
    st.markdown("Invoices")
    st.dataframe(readable(inv_rows, {
        schema.SRC_FILE: "File", schema.SRC_ROW: "Row", "invoice_date": "Invoice date", "amount": "Amount",
        "due": "Due", "paid_date": "Paid", "days_late": "Days late", "late_cost": "Late payment cost",
        **({"direct_cost": "Direct cost"} if has_direct_costs(result) else {})}),
        hide_index=True, width="stretch")
    st.markdown("Time entries")
    st.dataframe(readable(te_rows, {
        schema.SRC_FILE: "File", schema.SRC_ROW: "Row", "work_date": "Date", "staff": "Staff", "hours": "Hours",
        "hourly_cost": "Hourly cost", "labour_cost": "Labour cost (with overhead)", "billable": "Billable"}),
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
    cfg = config.load_config()

    st.caption("Demo only: please don't upload confidential client data. Uploaded files stay in this "
               "session, but request messages are sent to an outside AI service (Featherless) for labelling.")
    source = st.radio("Data", ["Upload my files", "Use demo data (generated)"], horizontal=True)
    if source.startswith("Use demo"):
        if not (DEMO / "invoices.csv").exists():
            with st.spinner("Building the demo data (first start only, about 10 seconds)..."):
                ensure_demo_data()
        if "loaded" not in st.session_state or st.session_state.get("source") != "demo":
            st.session_state.loaded, st.session_state.costs = load_demo()
            st.session_state.source = "demo"
    else:
        c = st.columns(5)
        files = {t: c[i].file_uploader(f"{t}.csv" + ("" if t in REQUIRED_FILES else " (optional)"), type="csv")
                 for i, t in enumerate(pipeline.TABLE_FILES)}
        staff_file = c[4].file_uploader("staff costs (optional)", type="csv")
        if not all(files[t] is not None for t in REQUIRED_FILES):
            st.info("Upload invoices and time entries to start. Client requests and services are optional: "
                    "they add scope-creep signals but the ranking works without them.")
            return
        if st.session_state.get("source") != "upload" or st.button("Reload files"):
            st.session_state.loaded, st.session_state.costs = load_uploads(files, staff_file)
            st.session_state.source = "upload"

    loaded = st.session_state.loaded
    st.header("1. Check the column mapping")
    st.caption("Open a file to check or change which column means what.")
    if not mapping_editor(loaded):
        return
    tables = pipeline.apply_mappings(loaded)

    st.header("2. Settings")
    staff_names = sorted(tables["time_entries"]["staff"].dropna().unique())
    known = {**cfg["staff_costs"], **st.session_state.costs}
    missing_costs = [n for n in staff_names if n not in known]
    with st.expander("Costs and rules" + (f" ({len(missing_costs)} staff without a cost)" if missing_costs else ""),
                     expanded=bool(missing_costs)):
        settings = settings_editor(cfg, staff_names, st.session_state.costs)

    st.header("3. Problems in the files")
    named, merged = ingest.unify_client_names(tables)
    problems = validate.validate_inputs(named, settings, merged)
    exclusions = problems_panel(problems)

    if st.button("Rank clients", type="primary"):
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
    st.header("4. Ranked clients")
    labels = st.session_state.get("labels")
    slot = ranked_view(result, recommend.recommend_actions(result, settings, labels))
    if len(result["unranked"]):
        st.markdown("**Not ranked** (too little to go on, so no rank and no suggested action)")
        u = result["unranked"]
        st.dataframe(pd.DataFrame({"Client": u["client"], "Why not ranked": u["not_ranked_because"],
                                   "Months of data": u["months_of_data"],
                                   "Profit, all data": u["profit_all_data"].map(money)}),
                     hide_index=True, width="stretch")
    new_labels = scope_section(result, cfg)
    if new_labels is not None:
        labels_summary(new_labels)
        if labels is None:  # labels just arrived: refresh the ranked table with them
            slot.dataframe(ranked_table(result, recommend.recommend_actions(result, settings, new_labels)),
                           hide_index=True, width="stretch")
    recs = recommend.recommend_actions(result, settings, new_labels)
    st.header("5. Client detail")
    client_detail(result, recs, new_labels, settings)


main()
