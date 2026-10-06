"""The only file that calls an LLM API (D-07, D-14).

Providers are reached through their OpenAI-style chat completions endpoint
using the Python standard library, so no extra package is needed. The API
key is read from an environment variable and never stored in code or config.
If the variable is not set, a placeholder is sent: in the build environment a
proxy replaces it with the real key. Teammates and the deployed app set the
variable.
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
PLACEHOLDER_KEY = "placeholder"
# Featherless sits behind Cloudflare, which blocks Python's default
# "Python-urllib" user agent (error 1010), so send our own.
USER_AGENT = "clientprofit/0.1"
RETRY_STATUS = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """Raised when the LLM call cannot be completed. Callers fall back to non-LLM paths."""


def _settings(provider):
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown llm.provider '{provider}'. Known: {', '.join(PROVIDERS)}")
    p = PROVIDERS[provider]
    key = os.environ.get(p["key_env"]) or PLACEHOLDER_KEY
    return os.environ.get(BASE_URL_ENV, p["base_url"]).rstrip("/"), key, p["key_env"]


def _request(url, key, key_env, body=None, timeout=120, retries=3):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json",
                                          "User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                out = json.loads(resp.read())
            # Featherless can answer HTTP 200 with an error body when busy; retry those too.
            if isinstance(out, dict) and "error" in out and "choices" not in out and "data" not in out:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMError(f"Provider error after {retries + 1} tries: {str(out['error'])[:300]}")
            return out
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUS and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            if e.code in (401, 403):
                raise LLMError(f"HTTP {e.code} (is {key_env} set to a valid key?): "
                               f"{e.read()[:300]!r}") from e
            raise LLMError(f"HTTP {e.code}: {e.read()[:300]!r}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise LLMError(f"Connection failed: {e}") from e


def complete(prompt, model, provider="featherless", system=None, max_tokens=256, temperature=0.0):
    """Send one prompt and return the reply text."""
    base_url, key, key_env = _settings(provider)
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    out = _request(f"{base_url}/chat/completions", key, key_env, body)
    try:
        return out["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response shape: {str(out)[:300]}") from e


def list_models(provider="featherless"):
    """Return the model ids the provider offers."""
    base_url, key, key_env = _settings(provider)
    out = _request(f"{base_url}/models", key, key_env)
    return sorted(m["id"] for m in out.get("data", []))
