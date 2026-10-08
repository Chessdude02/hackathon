"""Plain-language explanation per client, and the number check (D-07, D-26).

Code builds a list of facts with every number already formatted. The LLM only
writes sentences around them. `check_numbers` pulls every number out of the
text; if any number is not among the facts, the text is thrown away and a fixed
template made from the same facts is shown instead. The LLM never computes.
"""
import re

from clientprofit.llm import complete
from clientprofit.scope.store import LabelStore, label_key

PROMPT_VERSION = "explain-v2"  # v2: contribution and overhead facts (D-36)
SYSTEM = (
    "You explain one client's numbers to the owner of a small agency, in two or three short, plain "
    "sentences. Use ONLY the facts given. Copy every number exactly as written, including $ and %. "
    "Do not calculate, round, combine or invent any number, and do not add numbers that are not in "
    "the facts. Say what the suggested action is and why. No greeting, no bullet points."
)
NUMBER = re.compile(r"[-−]?\$?\d[\d,]*(?:\.\d+)?%?")


def escape_markdown(text):
    """Show text from uploads or the LLM as plain text on the screen (D-35): escape the characters
    that make links, images, HTML or formatting, and $ (Streamlit reads $...$ as a maths formula)."""
    text = str(text)
    for ch in "\\`*_[]<>!#|~$":
        text = text.replace(ch, "\\" + ch)
    return text


def money(v):
    return f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"


def pct(v):
    return f"{v:.0%}"


def facts_for(rec, totals):
    """The facts an explanation may use, as {label: formatted text}. `rec` is a recommend_actions row,
    `totals` the client's compute_client_totals row."""
    f = {
        "Client": rec["client"],
        "Suggested action": rec["action"],
        "Profit over the last 12 months, after its share of shared overhead": money(totals["profit_last_12m"]),
        "Contribution over the last 12 months, before shared overhead": money(totals["contribution_last_12m"]),
        "Revenue over the last 12 months": money(totals["revenue_last_12m"]),
        **({"Direct costs over the last 12 months (not staff time)": money(totals["direct_cost_last_12m"])}
           if totals.get("direct_cost_last_12m") else {}),
        "Profit over the last 3 months": money(rec["profit_3m"]),
        "Contribution over the last 3 months": money(rec["contribution_3m"]),
        "Target margin": pct(rec["target_margin"]),
    }
    if rec.get("margin_3m") is not None and rec["margin_3m"] == rec["margin_3m"]:
        f["Margin over the last 3 months"] = pct(rec["margin_3m"])
    if rec["action"] != "keep as is":
        f["Effect of the action per year"] = money(rec["dollar_effect_per_year"])
    if rec["action"] in ("raise price", "end the contract") and rec.get("price_rise_needed") is not None \
            and rec["price_rise_needed"] == rec["price_rise_needed"]:
        f["Price rise needed to reach the target"] = pct(rec["price_rise_needed"])
    if rec.get("unbilled_share_3m"):
        f["Share of hours not billed, last 3 months"] = pct(rec["unbilled_share_3m"])
        f["Cost of unbilled work per year"] = money(rec["unbilled_cost_per_year"])
    if rec.get("extra_request_share_3m") is not None and rec["extra_request_share_3m"] == rec["extra_request_share_3m"]:
        f["Share of recent requests that look like extra unpaid work"] = pct(rec["extra_request_share_3m"])
    if totals["profit_if_overdue_unpaid"] != totals["profit_last_12m"]:
        f["Profit over 12 months if overdue invoices are never paid"] = money(totals["profit_if_overdue_unpaid"])
    if rec.get("heading_to_loss"):
        f["Warning"] = "heading toward a loss"
    f["Reason"] = rec["why"]
    if isinstance(rec.get("alternative"), str) and rec["alternative"]:
        f["Alternative"] = rec["alternative"]
    return f


def _value(token):
    t = token.replace("−", "-").replace("$", "").replace(",", "").replace("%", "")
    try:
        return abs(float(t))
    except ValueError:
        return None


def allowed_numbers(facts):
    """Every number that appears in the facts, plus the periods the facts talk about (3 and 12 months)."""
    out = {3.0, 12.0}
    for text in facts.values():
        out |= {v for v in (_value(m) for m in NUMBER.findall(str(text))) if v is not None}
    return out


def check_numbers(text, facts):
    """Return the numbers in `text` that are not in `facts` (an empty list means the text passes)."""
    allowed = allowed_numbers(facts)
    bad = []
    for token in NUMBER.findall(text):
        v = _value(token)
        if v is not None and v not in allowed:
            bad.append(token)
    return bad


def template_text(rec):
    """Fixed wording from the recommendation's own reason (all numbers from code)."""
    text = f"Suggested action for {rec['client']}: {rec['action']}. {rec['why']}"
    if isinstance(rec.get("alternative"), str) and rec["alternative"]:
        text += f" {rec['alternative']}"
    return text


def prompt_for(facts):
    return "Facts:\n" + "\n".join(f"- {k}: {v}" for k, v in facts.items()) + "\n\nExplanation:"


def write_explanation(rec, totals, model, provider="featherless", store=None, allow_llm=True):
    """Return {text, source, invented}: source is "saved", "llm" or "template".
    With `allow_llm=False` a saved text is still used, but no new LLM call is made (D-35)."""
    facts = facts_for(rec, totals)
    store = store if store is not None else LabelStore(EXPLANATIONS_PATH)
    key = label_key(prompt_for(facts), "", model, PROMPT_VERSION)
    saved = store.get(key)
    if saved:
        return {"text": saved, "source": "saved", "invented": []}
    if not allow_llm:
        return {"text": template_text(rec), "source": "template", "invented": [], "capped": True}
    try:
        text = complete(prompt_for(facts), model, provider, system=SYSTEM, max_tokens=180).strip()
    except Exception:  # provider down or anything else: never block the screen
        return {"text": template_text(rec), "source": "template", "invented": [], "error": True}
    invented = check_numbers(text, facts)
    if invented or not text:
        return {"text": template_text(rec), "source": "template", "invented": invented, "rejected": text}
    store.put(key, text)
    store.save()
    return {"text": text, "source": "llm", "invented": []}


EXPLANATIONS_PATH = LabelStore().path.parent / "saved_explanations.json"
