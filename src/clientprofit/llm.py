"""The only file that calls an LLM API (D-07, D-14).

Providers are reached through their OpenAI-style chat completions endpoint
using the Python standard library, so no extra package is needed. The API
key is read from an environment variable and never stored in code or config.
"""
import json
import os
import time
import urllib.error
import urllib.request

PROVIDERS = {
    "featherless": {"base_url": "https://api.featherless.ai/v1", "key_env": "FEATHERLESS_API_KEY"},
}
BASE_URL_ENV = "LLM_BASE_URL"  # optional override, used by tests
RETRY_STATUS = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when the LLM call cannot be completed. Callers fall back to non-LLM paths."""


def _settings(provider):
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown llm.provider '{provider}'. Known: {', '.join(PROVIDERS)}")
    p = PROVIDERS[provider]
    key = os.environ.get(p["key_env"])
    if not key:
        raise LLMError(f"Environment variable {p['key_env']} is not set")
    return os.environ.get(BASE_URL_ENV, p["base_url"]).rstrip("/"), key


def _request(url, key, body=None, timeout=120, retries=3):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUS and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise LLMError(f"HTTP {e.code}: {e.read()[:300]!r}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise LLMError(f"Connection failed: {e}") from e


def complete(prompt, model, provider="featherless", system=None, max_tokens=256, temperature=0.0):
    """Send one prompt and return the reply text."""
    base_url, key = _settings(provider)
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    out = _request(f"{base_url}/chat/completions", key, body)
    try:
        return out["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response shape: {str(out)[:300]}") from e


def list_models(provider="featherless"):
    """Return the model ids the provider offers."""
    base_url, key = _settings(provider)
    out = _request(f"{base_url}/models", key)
    return sorted(m["id"] for m in out.get("data", []))
