"""LLM request labeller (D-14, D-15, D-17). Labels only; never does arithmetic (D-07)."""
from concurrent.futures import ThreadPoolExecutor

from clientprofit.llm import complete
from clientprofit.scope.keyword import label_one
from clientprofit.scope.store import LabelStore, label_key

PROMPT_VERSION = "v1"
SAVE_EVERY = 50
MAX_FAILURES_IN_A_ROW = 5  # then stop calling the LLM and use keyword labels for the rest
LABELS = ("in_scope", "extra_unpaid", "unclear")
SYSTEM = (
    "You label messages that clients send to their marketing agency. Reply with exactly one word.\n"
    "in_scope - routine work the client already pays for: approvals, edits or fixes to agreed work, "
    "scheduling, reports, admin, or work on a service listed as covered\n"
    "extra_unpaid - a new deliverable, a deliverable not in the covered services, or clearly more than "
    "agreed (redo, versions for each branch, extra volume, new channels)\n"
    "unclear - cannot tell without asking the client"
)
EXAMPLES = (
    "Services covered: newsletter, flyer\nMessage: Please schedule the newsletter for Friday as planned.\n"
    "Label: in_scope\n\n"
    "Services covered: newsletter, flyer\nMessage: Can you also design a brochure for our open day?\n"
    "Label: extra_unpaid\n\n"
    "Services covered: newsletter, flyer\nMessage: Can we make the flyer pop more?\nLabel: unclear\n\n"
)


def parse_label(text):
    t = str(text).strip().lower().replace("-", "_").replace("extra unpaid", "extra_unpaid") \
        .replace("in scope", "in_scope")
    hits = [lbl for lbl in LABELS if lbl in t]
    return hits[0] if len(hits) == 1 else None


# Used when a client's services are unknown. Telling the model "services: not known"
# made it answer "unclear" to everything (benchmark 4, 2026-10-06), so the services
# line is left out and the label is judged from the wording alone.
PROMPT_VERSION_NO_SERVICES = "v1-noservices"
SYSTEM_NO_SERVICES = (
    "You label messages that clients send to their marketing agency. Reply with exactly one word.\n"
    "in_scope - routine work on something already agreed: approvals, edits or fixes, scheduling, reports, admin\n"
    "extra_unpaid - a new deliverable or clearly more than agreed (also make X, redo, versions for each branch, "
    "extra volume, new channels)\n"
    "unclear - cannot tell without asking the client"
)
EXAMPLES_NO_SERVICES = (
    "Message: Please schedule the newsletter for Friday as planned.\nLabel: in_scope\n\n"
    "Message: Can you also design a brochure for our open day?\nLabel: extra_unpaid\n\n"
    "Message: Can we make the flyer pop more?\nLabel: unclear\n\n"
)


def prompt_for(message, services):
    """Prompt text and system message; without services the services line is left out."""
    if services:
        return EXAMPLES + f"Services covered: {services}\nMessage: {message}\nLabel:", SYSTEM
    return EXAMPLES_NO_SERVICES + f"Message: {message}\nLabel:", SYSTEM_NO_SERVICES


class LLMDetector:
    name = "llm"

    def __init__(self, model, provider="featherless", store=None, workers=2, use_services=True):
        self.model, self.provider = model, provider
        self.store = store if store is not None else LabelStore()
        self.workers, self.use_services = workers, use_services
        self.failures_in_a_row, self.gave_up = 0, False

    def _label_live(self, message, services, tries=2):
        """Ask the model; an unreadable reply gets one more try, then the keyword label.
        After MAX_FAILURES_IN_A_ROW failed calls the provider is treated as down."""
        if self.gave_up:
            return {"label": label_one(message, services), "source": "keyword_fallback_provider_down"}
        try:
            prompt, system = prompt_for(message, services)
            for _ in range(tries):
                reply = complete(prompt, self.model, self.provider, system=system, max_tokens=8)
                self.failures_in_a_row = 0
                label = parse_label(reply)
                if label:
                    return {"label": label, "source": "live"}
            return {"label": label_one(message, services), "source": "keyword_fallback_unparsed"}
        except Exception:  # LLMError or anything unexpected: one message must not stop a long run
            self.failures_in_a_row += 1
            if self.failures_in_a_row >= MAX_FAILURES_IN_A_ROW:
                self.gave_up = True
            return {"label": label_one(message, services), "source": "keyword_fallback_error"}

    def _keys(self, requests, services_by_client):
        services_by_client = (services_by_client if self.use_services else {}) or {}
        items = [(m, services_by_client.get(c)) for m, c in zip(requests["message"], requests["client"])]
        keys = [label_key(m, s, self.model, PROMPT_VERSION if s else PROMPT_VERSION_NO_SERVICES)
                for m, s in items]
        return items, keys

    def count_new(self, requests, services_by_client=None):
        """How many distinct messages are not saved yet (each needs a live call)."""
        _, keys = self._keys(requests, services_by_client)
        return len({k for k in keys if not self.store.get(k)})

    def label_requests(self, requests, services_by_client=None, progress=None):
        """Return a list of {label, source} in the order of `requests`.

        Saved labels are reused; the rest are labelled live in parallel and saved.
        progress(done, total) is called as live labels finish.
        """
        items, keys = self._keys(requests, services_by_client)
        out = [None] * len(items)
        todo = {}
        for i, k in enumerate(keys):
            saved = self.store.get(k)
            if saved:
                out[i] = {"label": saved, "source": "saved"}
            else:
                todo.setdefault(k, []).append(i)
        done = 0
        if progress:
            progress(0, len(todo))
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {k: pool.submit(self._label_live, *items[idx[0]]) for k, idx in todo.items()}
            for k, fut in futures.items():
                result = fut.result()
                if result["source"] == "live":
                    self.store.put(k, result["label"])
                for i in todo[k]:
                    out[i] = result
                done += 1
                if done % SAVE_EVERY == 0:
                    self.store.save()  # long runs keep their work if stopped
                if progress and (done % 10 == 0 or done == len(todo)):
                    progress(done, len(todo))
        if todo:
            self.store.save()
        return out
