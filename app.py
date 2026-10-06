"""Streamlit entry point: upload, confirm mapping, settings, ranked list, client detail.

Run with: streamlit run app.py
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from clientprofit import config, ingest, pipeline, recommend, schema, validate  # noqa: E402
from clientprofit.scope.registry import get_detector, services_by_client  # noqa: E402

ASK_BEFORE_LABELLING = 200   # more new messages than this: show the time and ask first (D-15)
SECONDS_PER_MESSAGE = 0.8    # measured 2026-10-06, 2 calls at a time (D-15)
ACTION_ICON = {recommend.KEEP: "✅", recommend.RAISE: "💲", recommend.CUT: "✂️", recommend.END: "🛑"}
DEMO = Path(os.environ.get("CLIENTPROFIT_DEMO_DIR", Path(__file__).resolve().parent / "data" / "generated"))
IGNORE = "(ignore)"
REQUIRED_FILES = ("invoices", "time_entries")  # requests and clients are optional


def money(v):
    if pd.isna(v):
        return ""
    return f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"


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


def ranked_table(result, recs):
    r = result["ranked"].merge(recs, on="client", how="left")
    return pd.DataFrame({
        "Rank": r["rank"], "Client": r["client"],
        "Profit (12 mo)": r["profit_last_12m"].map(money),
        "Revenue (12 mo)": r["revenue_last_12m"].map(money),
        "Margin": r["margin_last_12m"].map(lambda v: "" if pd.isna(v) else f"{v:.0%}"),
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
    detector = get_detector(cfg["scope"]["detector"], cfg)
    services = services_by_client(result["tables"])
    new = detector.count_new(req, services) if hasattr(detector, "count_new") else 0
    if new > ASK_BEFORE_LABELLING and not st.session_state.get("label_go"):
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
    """Escape $ so Streamlit markdown does not read money as a maths formula."""
    return str(text).replace("$", "\\$")


EFFECT_WORDS = {recommend.RAISE: "+{} profit a year", recommend.CUT: "saves {} a year",
                recommend.END: "stops a {}-a-year loss"}


def recommendation_box(rec):
    icon = ACTION_ICON.get(rec["action"], "")
    words = EFFECT_WORDS.get(rec["action"])
    effect = f" ({words.format(money(rec['dollar_effect_per_year']))})" if words else ""
    st.markdown(md(f"#### {icon} Suggested action: {rec['action']}{effect}"))
    st.markdown(md(rec["why"]))
    if isinstance(rec.get("alternative"), str) and rec["alternative"]:
        st.markdown(md(f"**{rec['alternative']}**"))
    if rec["heading_to_loss"]:
        st.warning("Heading toward a loss: profitable over 12 months, but the last 3 months are below zero "
                   "or close to zero and falling.")
    st.caption("Based on the last 3 months, scaled to a year. Assumes the same workload and that the client "
               "accepts the change. You make the final call.")


def client_detail(result, recs, labels):
    clients = list(result["ranked"]["client"]) + list(result["unranked"]["client"])
    client = st.selectbox("Client detail", clients, key="detail_client")
    rec = recs[recs["client"] == client]
    if len(rec):
        recommendation_box(rec.iloc[0].to_dict())
    else:
        st.info("Not enough history to rank or recommend an action (under 3 months of data).")
    cm = result["client_month"][result["client_month"]["client"] == client]
    st.dataframe(pd.DataFrame({
        "Month": cm["month"].astype(str), "Revenue": cm["revenue"].map(money),
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
    st.dataframe(inv_rows[[schema.SRC_FILE, schema.SRC_ROW, "invoice_date", "amount", "due", "paid_date",
                           "days_late", "late_cost"]], hide_index=True, width="stretch")
    st.markdown("Time entries")
    st.dataframe(te_rows[[schema.SRC_FILE, schema.SRC_ROW, "work_date", "staff", "hours", "hourly_cost",
                          "labour_cost", "billable"]], hide_index=True, width="stretch")
    req = result["tables"].get("requests")
    if labels is not None and req is not None:
        mine = req.assign(label=[x["label"] for x in labels])
        mine = mine[mine["client"] == client].sort_values("request_date", ascending=False)
        st.markdown(f"Client requests with AI labels (beta, review before acting): {len(mine)}")
        st.dataframe(mine[["request_date", "channel", "message", "label"]], hide_index=True, width="stretch")


def main():
    st.set_page_config(page_title="Client profit finder", layout="wide")
    st.title("Client profit finder")
    cfg = config.load_config()

    source = st.radio("Data", ["Upload my files", "Use demo data (generated)"], horizontal=True)
    if source.startswith("Use demo"):
        if not (DEMO / "invoices.csv").exists():
            st.error("No demo data. Run: python scripts/generate_data.py --out data/generated --seed 42")
            return
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
        st.markdown("**Not enough history to rank** (results unreliable)")
        u = result["unranked"]
        st.dataframe(pd.DataFrame({"Client": u["client"], "Months of data": u["months_of_data"],
                                   "Profit so far": u["profit_last_12m"].map(money)}),
                     hide_index=True, width="stretch")
    new_labels = scope_section(result, cfg)
    if new_labels is not None:
        labels_summary(new_labels)
        if labels is None:  # labels just arrived: refresh the ranked table with them
            slot.dataframe(ranked_table(result, recommend.recommend_actions(result, settings, new_labels)),
                           hide_index=True, width="stretch")
    recs = recommend.recommend_actions(result, settings, new_labels)
    st.header("5. Client detail")
    client_detail(result, recs, new_labels)


main()
