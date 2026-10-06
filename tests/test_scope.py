"""Request labelling: keyword baseline, saved labels, LLM detector (fake server)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pandas as pd
import pytest

from clientprofit import llm
from clientprofit.scope import keyword
from clientprofit.scope.llm_detector import LLMDetector, parse_label, prompt_for
from clientprofit.scope.registry import get_detector, services_by_client
from clientprofit.scope.store import LabelStore, label_key


# ---- Keyword baseline ----

def test_keyword_routine_and_extra_words():
    assert keyword.label_one("Please schedule the newsletter as planned") == "in_scope"
    assert keyword.label_one("Could you also build us an online shop?") == "extra_unpaid"
    assert keyword.label_one("Thoughts?") == "unclear"


def test_keyword_uses_services():
    msg = "Can you send over this month's flyer?"
    assert keyword.label_one(msg, "flyer, newsletter") == "in_scope"
    assert keyword.label_one("Can you send over this month's brochure", "flyer, newsletter") == "extra_unpaid"


# ---- Saved labels ----

def test_label_key_changes_with_services_model_and_prompt():
    base = label_key("hi", "flyer", "m", "v1")
    assert base == label_key("hi", "flyer", "m", "v1")
    assert len({base, label_key("hi", "logo", "m", "v1"), label_key("hi", "flyer", "m2", "v1"),
                label_key("hi", "flyer", "m", "v2"), label_key("hi!", "flyer", "m", "v1")}) == 5


def test_store_round_trip(tmp_path):
    s = LabelStore(tmp_path / "s.json")
    s.put("k", "in_scope")
    s.save()
    assert LabelStore(tmp_path / "s.json").get("k") == "in_scope"


# ---- LLM detector against a fake server ----

class Fake(BaseHTTPRequestHandler):
    reply = "extra_unpaid"
    calls = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.calls.append(body["messages"][-1]["content"])
        out = {"choices": [{"message": {"content": Fake.reply}}]} if Fake.reply != "500" else None
        self.send_response(200 if out else 500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(out or {"error": "x"}).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def fake(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv(llm.BASE_URL_ENV, f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    Fake.reply, Fake.calls = "extra_unpaid", []
    yield Fake
    server.shutdown()


REQ = pd.DataFrame({"client": ["A", "A", "B"], "message": ["one", "one", "two"]})


def test_llm_labels_once_per_unique_message_and_saves(fake, tmp_path):
    store = LabelStore(tmp_path / "s.json")
    d = LLMDetector("m", store=store)
    out = d.label_requests(REQ, {"A": "flyer"})
    assert [o["label"] for o in out] == ["extra_unpaid"] * 3 and len(fake.calls) == 2
    again = LLMDetector("m", store=LabelStore(tmp_path / "s.json")).label_requests(REQ, {"A": "flyer"})
    assert [o["source"] for o in again] == ["saved"] * 3 and len(fake.calls) == 2


def test_services_are_in_the_prompt(fake, tmp_path):
    LLMDetector("m", store=LabelStore(tmp_path / "s.json")).label_requests(REQ.head(1), {"A": "flyer, logo"})
    assert "Services covered: flyer, logo" in fake.calls[0]


def test_unreadable_reply_retries_then_uses_keyword(fake, tmp_path):
    fake.reply = "maybe?"
    out = LLMDetector("m", store=LabelStore(tmp_path / "s.json")).label_requests(REQ.head(1))
    assert out[0]["source"] == "keyword_fallback_unparsed" and len(fake.calls) == 2


def test_failed_call_uses_keyword_and_is_not_saved(fake, tmp_path):
    fake.reply = "500"
    store = LabelStore(tmp_path / "s.json")
    out = LLMDetector("m", store=store).label_requests(REQ.head(1))
    assert out[0]["source"] == "keyword_fallback_error" and len(store) == 0


def test_progress_is_reported(fake, tmp_path):
    seen = []
    LLMDetector("m", store=LabelStore(tmp_path / "s.json")).label_requests(REQ, progress=lambda d, n: seen.append((d, n)))
    assert seen[0] == (0, 2) and seen[-1] == (2, 2)


@pytest.mark.parametrize("reply,label", [("in_scope", "in_scope"), ("Extra unpaid", "extra_unpaid"),
                                         ("extra-unpaid.", "extra_unpaid"), ("UNCLEAR", "unclear"),
                                         ("in_scope or unclear", None), ("", None)])
def test_parse_label(reply, label):
    assert parse_label(reply) == label


def test_prompt_without_services_says_not_known():
    assert "Services covered: not known" in prompt_for("hi", None)


def test_registry_and_services_lookup():
    assert get_detector("keyword").name == "keyword"
    with pytest.raises(ValueError):
        get_detector("nope")
    clients = pd.DataFrame({"client": ["A", "B"], "services_covered": ["flyer", None]})
    assert services_by_client({"clients": clients}) == {"A": "flyer"}
