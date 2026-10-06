"""Keyword baseline for request labels (benchmark 4 baseline, LLM fallback).

Counts words that suggest routine work or extra work. With a client's
services text (D-17), a deliverable named in the message counts towards
in-scope if the services mention it, and towards extra work if not.
"""
import re

EXTRA_WORDS = ["also", "as well", "another", "extra", "additional", "each of", "every ", "for each",
               "redo", "from scratch", "entire", "whole", "launch", "build us", "set up", "translate",
               "spanish", "version of", "versions", "brand refresh", "business cards", "signage",
               "online shop", "investor", "new location", "new product", "new office", "branches"]
IN_SCOPE_WORDS = ["approv", "schedule", "as planned", "monthly", "report", "typo", "round of edits",
                  "check-in", "login", "invoice", "on track", "when is the next", "confirm", "swap",
                  "replace", "agreed", "draft", "publish", "go ahead", "shared folder"]
# Common deliverables an agency makes; used only to tell "named and covered"
# from "named and not covered".
DELIVERABLES = ["banner", "newsletter", "post", "landing page", "logo", "photo", "blog", "menu",
                "brochure", "ads", "contact form", "booking page", "flyer", "deck", "website", "video",
                "poster", "email"]


def _named(text):
    return [d for d in DELIVERABLES if re.search(rf"\b{re.escape(d)}", text)]


def label_one(message, services=None):
    text = f" {str(message).lower()} "
    extra = sum(w in text for w in EXTRA_WORDS)
    in_scope = sum(w in text for w in IN_SCOPE_WORDS)
    if services:
        covered = str(services).lower()
        for d in _named(text):
            if re.search(rf"\b{re.escape(d)}", covered):
                in_scope += 1
            else:
                extra += 1
    if extra > in_scope:
        return "extra_unpaid"
    if in_scope > extra:
        return "in_scope"
    return "unclear"


class KeywordDetector:
    name = "keyword"

    def label_requests(self, requests, services_by_client=None, progress=None):
        """Return a list of {label, source} in the order of `requests`."""
        services_by_client = services_by_client or {}
        out = [{"label": label_one(m, services_by_client.get(c)), "source": "keyword"}
               for m, c in zip(requests["message"], requests["client"])]
        if progress:
            progress(len(out), len(out))
        return out
