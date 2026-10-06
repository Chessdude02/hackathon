"""Saved request labels (D-15, D-17).

A label is saved under a key made from the message text, the client's services
text, the model and the prompt version, so a change to any of them means the
message is labelled again.
"""
import hashlib
import json
import threading
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "labels" / "saved_labels.json"


def label_key(message, services, model, prompt_version):
    raw = "\x1f".join([prompt_version, model, str(services or ""), str(message)])
    return hashlib.sha1(raw.encode()).hexdigest()


class LabelStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, label):
        with self._lock:
            self._data[key] = label

    def save(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=0, sort_keys=True) + "\n")

    def __len__(self):
        return len(self._data)
