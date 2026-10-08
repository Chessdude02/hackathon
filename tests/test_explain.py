"""Explanations and the number check (benchmark 6). LLM calls go to a local fake server."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from clientprofit import explain, llm
from clientprofit.scope.store import LabelStore

REC = {"client": "Studio 54", "action": "raise price", "dollar_effect_per_year": 10006.14, "profit_3m": 2500.0, "contribution_3m": 4000.0,
       "margin_3m": 0.2, "target_margin": 0.3, "price_rise_needed": 0.1477, "unbilled_share_3m": 0.0,
       "unbilled_cost_per_year": 0.0, "extra_request_share_3m": None, "heading_to_loss": False,
       "alternative": None, "why": "Last 3 months' margin 20% is below the 30% target; a 15% price rise reaches it."}
TOTALS = {"profit_last_12m": 12000.0, "contribution_last_12m": 18000.0, "revenue_last_12m": 50000.0, "profit_if_overdue_unpaid": 12000.0}


def test_facts_are_formatted_by_code():
    f = explain.facts_for(REC, TOTALS)
    assert f["Price rise needed to reach the target"] == "15%" and f["Effect of the action per year"] == "$10,006"
    assert "Share of hours not billed, last 3 months" not in f


@pytest.mark.parametrize("text,bad", [
    ("Margin was 20%, below the 30% target; a 15% rise adds $10,006 a year.", []),
    ("Profit over 12 months was $12,000 on $50,000 of revenue.", []),
    ("A loss of $12,000 is shown without its sign.", []),           # sign may be dropped
    ("The client named Studio 54 is fine.", []),                     # numbers in the client name are allowed
    ("Over the last 3 months and 12 months.", []),                   # the periods themselves
    ("Raise the price by 16% to earn $10,500 more.", ["16%", "$10,500"]),
    ("That is about 1.5 times the target.", ["1.5"]),
])
def test_check_numbers(text, bad):
    assert explain.check_numbers(text, explain.facts_for(REC, TOTALS)) == bad


class Fake(BaseHTTPRequestHandler):
    reply = "fine"

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        body = {"choices": [{"message": {"content": Fake.reply}}]} if Fake.reply != "500" else {"error": "x"}
        self.send_response(200 if Fake.reply != "500" else 500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def fake(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv(llm.BASE_URL_ENV, f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    yield Fake
    server.shutdown()


def test_good_text_is_used_and_saved(fake, tmp_path):
    fake.reply = "Margin was 20%, below the 30% target. A 15% price rise adds $10,006 a year."
    store = LabelStore(tmp_path / "e.json")
    out = explain.write_explanation(REC, TOTALS, "m", store=store)
    assert out["source"] == "llm" and out["text"] == fake.reply
    assert explain.write_explanation(REC, TOTALS, "m", store=store)["source"] == "saved"


def test_invented_number_is_replaced_by_template(fake, tmp_path):
    fake.reply = "Studio 54 should raise the price by 18% to earn $12,345 more each year from this client."
    out = explain.write_explanation(REC, TOTALS, "m", store=LabelStore(tmp_path / "e.json"))
    assert out["source"] == "template" and out["invented"] == ["18%", "$12,345"]
    assert out["text"].startswith("Suggested action for Studio 54: raise price.")


def test_provider_down_gives_template(fake, tmp_path):
    fake.reply = "500"
    out = explain.write_explanation(REC, TOTALS, "m", store=LabelStore(tmp_path / "e.json"))
    assert out["source"] == "template" and out.get("error")


def test_template_contains_only_fact_numbers():
    assert explain.check_numbers(explain.template_text(REC), explain.facts_for(REC, TOTALS)) == []


def test_direct_cost_fact_only_when_present():
    """Clients without direct costs keep the same facts, so saved explanations still match (D-31)."""
    assert not any("Direct" in k for k in explain.facts_for(REC, TOTALS))
    f = explain.facts_for(REC, {**TOTALS, "direct_cost_last_12m": 8000.0})
    assert f["Direct costs over the last 12 months (not staff time)"] == "$8,000"


def test_escape_markdown_neutralises_links_images_and_html():
    """D-35: an uploaded client name or LLM reply cannot become a link, image or HTML on the screen."""
    out = explain.escape_markdown("![x](http://evil/p.png) [click](http://evil) <b>hi</b> costs $5")
    import re
    assert not re.search(r"(?<!\\)[\[\]<>!$]", out)  # every special character is escaped
    assert out.replace("\\", "") == "![x](http://evil/p.png) [click](http://evil) <b>hi</b> costs $5"


def test_no_new_llm_call_when_not_allowed(fake, tmp_path):
    """D-35: past the session's explanation limit, saved texts still show; nothing new is bought."""
    store = LabelStore(tmp_path / "e.json")
    out = explain.write_explanation(REC, TOTALS, "m", store=store, allow_llm=False)
    assert out["source"] == "template" and out["capped"]
    fake.reply = "Margin was 20%, below the 30% target, so the suggested action is to raise the price."
    explain.write_explanation(REC, TOTALS, "m", store=store)
    assert explain.write_explanation(REC, TOTALS, "m", store=store, allow_llm=False)["source"] == "saved"


def test_memory_store_never_writes_to_disk(tmp_path, monkeypatch):
    """D-35: labels and explanations for uploaded files stay in the browser session's memory."""
    monkeypatch.chdir(tmp_path)
    store = LabelStore(None)
    store.put("k", "text")
    store.save()
    assert store.get("k") == "text" and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("text,broken", [
    ("Green!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", True),       # seen from the LLM on 2026-10-08
    ("Z!!!!!!!!!", True),
    ("Profit was $12,000.", True),                                   # too short to explain anything
    ("Studio 54 earns $12,000 a year on $50,000 of revenue, a margin of 20% against the 30% target, "
     "so a 15% price rise is suggested.", False),
])
def test_looks_broken(text, broken):
    assert explain.looks_broken(text) is broken


def test_broken_reply_is_retried_then_replaced_and_never_saved(fake, tmp_path):
    """D-38: garbage with no numbers passes the number check, so it is caught separately."""
    fake.reply = "Studio!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    store = LabelStore(tmp_path / "e.json")
    out = explain.write_explanation(REC, TOTALS, "m", store=store)
    assert out["source"] == "template" and out["broken"] and len(store) == 0


def test_broken_text_already_saved_is_not_shown(tmp_path):
    store = LabelStore(tmp_path / "e.json")
    facts = explain.facts_for(REC, TOTALS)
    store.put(explain.label_key(explain.prompt_for(facts), "", "m", explain.PROMPT_VERSION), "Green!!!!!!!!!!!!!!")
    out = explain.write_explanation(REC, TOTALS, "m", store=store, allow_llm=False)
    assert out["source"] == "template"
