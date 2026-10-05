"""Request message text.

If generator/message_bank.json exists, messages are drawn from it. That file
is made once by paraphrasing these templates with an LLM (D-12) and then
committed, so every run uses the same text. Until it exists, the templates
below are used directly. The truth file records which source was used.
"""
import json
from pathlib import Path

BANK_PATH = Path(__file__).with_name("message_bank.json")

ITEMS = ["homepage banner", "Instagram posts", "newsletter", "landing page",
         "logo files", "product photos", "blog post", "menu PDF", "brochure",
         "Google ads", "contact form", "booking page", "flyer", "pitch deck"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "end of week",
        "tomorrow", "next week"]

TEMPLATES = {
    "in_scope": [
        "Can you send over this month's {item} for approval?",
        "Just checking the {item} is still on track for {day}.",
        "Approved the {item}, looks great. Go ahead and publish.",
        "Here are the photos for the {item} we discussed in the plan.",
        "Can we move our monthly check-in to {day}?",
        "Small typo on the {item}: 'recieve' should be 'receive'.",
        "Please share the monthly report when it's ready.",
        "Thanks for the draft {item}. One round of edits attached.",
        "When is the next {item} going out?",
        "Can you swap the photo on the {item} for the one in the shared folder?",
        "Confirming the {item} copy we agreed on last week is final.",
        "Login details for the CMS are in the vault as usual.",
        "Please schedule the {item} for {day} as planned.",
        "Got the invoice, thanks. All fine.",
    ],
    "extra_unpaid": [
        "Could you also put together a {item} for our new location? Need it by {day}.",
        "Quick one: can you redo the whole {item} in a different style?",
        "We're launching a new product, can you make a {item} for it too?",
        "Can you jump on a call with our investors {day} and walk them through the brand?",
        "Our nephew built a website, could you fix it up while you're at it?",
        "Need a {item} in Spanish as well, same deadline.",
        "Can you set up ads on TikTok too? Never done it before.",
        "Could you design a {item} for our charity event? Should be quick.",
        "Can you write 10 extra blog posts this month? Big push.",
        "Can you make a version of the {item} for each of our 6 branches?",
        "We need new business cards and signage, can you handle that?",
        "Can you also manage our Google reviews and reply to them?",
        "Board wants a full brand refresh deck by {day}.",
        "Could you build us a simple online shop? Just a few products.",
    ],
    "unclear": [
        "Can we make the {item} pop more?",
        "Can you take a look at the {item} when you get a sec?",
        "Not sure about the {item}. Thoughts?",
        "Can we chat {day} about some ideas?",
        "Is it possible to do something for the holidays?",
        "The {item} needs a few tweaks, will send notes.",
        "Can you help us with our socials a bit more?",
        "Our boss saw a competitor's {item} and wants something similar.",
        "Can we add a couple more things to the {item}?",
        "Something feels off with the website, can you check?",
        "Could you look into SEO stuff?",
        "We might need help with an event soon.",
        "Can you update the {item} with the new info?",
        "Let's revisit the plan, a few things have changed.",
    ],
}

GREETINGS = ["", "", "Hi, ", "Hey team, ", "Hello, ", "Morning! ", "hi "]
SIGNOFFS = ["", "", " Thanks!", " Cheers", " Thx", " Thanks so much.", " - sent from my phone"]


def _typo(text, rng):
    """Swap two neighbouring letters in one word."""
    words = text.split(" ")
    idx = [i for i, w in enumerate(words) if len(w) > 4 and w.isalpha()]
    if not idx:
        return text
    i = idx[int(rng.integers(len(idx)))]
    w = words[i]
    j = int(rng.integers(1, len(w) - 2))
    words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def load_bank():
    """Return (bank, source). bank maps label -> list of message strings."""
    if BANK_PATH.exists():
        return json.loads(BANK_PATH.read_text()), "message_bank.json"
    return TEMPLATES, "templates"


def _pick_item(label, rng, covered):
    """D-17: in-scope messages name a covered item, extra work an uncovered one."""
    if covered and label == "in_scope":
        pool = list(covered)
    elif covered and label == "extra_unpaid":
        pool = [i for i in ITEMS if i not in covered]
    else:
        pool = ITEMS
    return pool[int(rng.integers(len(pool)))]


def make_message(label, rng, bank, covered=None):
    """Build one message for a label, with a random tone."""
    options = bank[label]
    text = options[int(rng.integers(len(options)))]
    text = text.format(item=_pick_item(label, rng, covered),
                       day=DAYS[int(rng.integers(len(DAYS)))])
    text = GREETINGS[int(rng.integers(len(GREETINGS)))] + text
    text = text + SIGNOFFS[int(rng.integers(len(SIGNOFFS)))]
    roll = rng.random()
    if roll < 0.15:
        text = text.lower()
    elif roll < 0.25:
        text = _typo(text, rng)
    return text
