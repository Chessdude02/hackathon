"""Loads and checks config.yaml. A missing key or wrong type stops the app at start-up."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PATH = REPO / "config.yaml"

# key -> (type, check, description of a valid value)
NUMBER = (int, float)
RULES = {
    "staff_costs": (dict, lambda v: all(isinstance(c, NUMBER) and c >= 0 for c in v.values()),
                    "a mapping of staff name to an hourly cost of 0 or more"),
    "overhead_multiplier": (NUMBER, lambda v: v >= 1, "a number of 1 or more"),
    "target_margin": (NUMBER, lambda v: 0 <= v < 1, "a fraction from 0 to below 1"),
    "late_payment_annual_rate": (NUMBER, lambda v: 0 <= v < 1, "a fraction from 0 to below 1"),
    "payment_terms_days": (int, lambda v: v >= 0, "a whole number of days, 0 or more"),
    "unpaid_warning_days": (int, lambda v: v >= 0, "a whole number of days, 0 or more"),
    "min_months_for_ranking": (int, lambda v: v >= 1, "a whole number, 1 or more"),
    "forecast.model": (str, bool, "a forecaster name"),
    "forecast.horizon_months": (int, lambda v: v >= 1, "a whole number, 1 or more"),
    "forecast.test_months": (int, lambda v: v >= 1, "a whole number, 1 or more"),
    "scope.detector": (str, bool, "a detector name"),
    "llm.provider": (str, bool, "a provider name"),
    "llm.model": (str, bool, "a model name"),
    "dataset": (str, bool, "a dataset name"),
    "random_seed": (int, lambda v: True, "a whole number"),
}


class ConfigError(Exception):
    """A config key is missing or has the wrong type."""


def _get(cfg, dotted):
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"Missing config key '{dotted}'")
        node = node[part]
    return node


def check_config(cfg):
    for key, (kind, ok, expected) in RULES.items():
        value = _get(cfg, key)
        if isinstance(value, bool) or not isinstance(value, kind) or not ok(value):
            raise ConfigError(f"Config key '{key}' must be {expected}; got {value!r}")
    return cfg


def load_config(path=DEFAULT_PATH):
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    cfg["staff_costs"] = {str(k): v for k, v in (cfg.get("staff_costs") or {}).items()}
    return check_config(cfg)


def read_staff_costs(path):
    """Read a staff cost CSV with columns staff, hourly_cost into a dict."""
    import pandas as pd
    df = pd.read_csv(path)
    return {str(s): float(c) for s, c in zip(df["staff"], df["hourly_cost"])}
