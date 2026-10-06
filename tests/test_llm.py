"""The LLM wrapper, checked against a local fake server (no real API calls)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from clientprofit import llm


class FakeAPI(BaseHTTPRequestHandler):
    fail_first = 0
    error_body_first = 0
    status = 200
    seen = []

    def _reply(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAPI.seen.append({"path": self.path, "auth": self.headers["Authorization"],
                            "agent": self.headers["User-Agent"], "body": body})
        if FakeAPI.status != 200:
            return self._reply(FakeAPI.status, {"error": "no"})
        if FakeAPI.error_body_first > 0:
            FakeAPI.error_body_first -= 1
            return self._reply(200, {"error": {"message": "No successful response", "type": "server_error"}})
        if FakeAPI.fail_first > 0:
            FakeAPI.fail_first -= 1
            return self._reply(429, {"error": "busy"})
        self._reply(200, {"choices": [{"message": {"content": "extra_unpaid"}}]})

    def do_GET(self):
        self._reply(200, {"data": [{"id": "b-model"}, {"id": "a-model"}]})

    def log_message(self, *args):
        pass


@pytest.fixture
def fake(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeAPI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv(llm.BASE_URL_ENV, f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    FakeAPI.seen, FakeAPI.fail_first, FakeAPI.status, FakeAPI.error_body_first = [], 0, 200, 0
    yield FakeAPI
    server.shutdown()


def test_complete_sends_key_and_returns_text(fake):
    assert llm.complete("hi", "m", system="sys") == "extra_unpaid"
    call = fake.seen[0]
    assert call["path"] == "/chat/completions"
    assert call["auth"] == "Bearer test-key"
    assert call["agent"] == llm.USER_AGENT  # Cloudflare blocks the urllib default
    assert call["body"]["messages"][0] == {"role": "system", "content": "sys"}


def test_busy_server_is_retried(fake):
    fake.fail_first = 2
    assert llm.complete("hi", "m") == "extra_unpaid"
    assert len(fake.seen) == 3


def test_error_body_with_http_200_is_retried(fake):
    fake.error_body_first = 1
    assert llm.complete("hi", "m") == "extra_unpaid"
    assert len(fake.seen) == 2


def test_error_body_every_time_raises(fake):
    fake.error_body_first = 10
    with pytest.raises(llm.LLMError, match="Provider error"):
        llm.complete("hi", "m")


def test_list_models(fake):
    assert llm.list_models() == ["a-model", "b-model"]


def test_missing_key_sends_placeholder(fake, monkeypatch):
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    llm.complete("hi", "m")
    assert fake.seen[0]["auth"] == f"Bearer {llm.PLACEHOLDER_KEY}"


def test_refused_key_names_the_variable(fake):
    fake.status = 401
    with pytest.raises(llm.LLMError, match="FEATHERLESS_API_KEY"):
        llm.complete("hi", "m")


def test_unknown_provider_raises():
    with pytest.raises(llm.LLMError, match="Unknown"):
        llm.complete("hi", "m", provider="nope")
