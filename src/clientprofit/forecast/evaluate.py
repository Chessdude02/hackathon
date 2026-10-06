"""Benchmark 3: time-based split and mean absolute error (never a random split)."""
import numpy as np

MIN_REVENUE = 1000.0   # both windows need at least this revenue, so margin is meaningful
MIN_MONTHS = 6         # months of history before a client-month is used


def time_split(features, test_months=6, horizon=3):
    """Test: origins whose target months all fall in the last `test_months`.
    Train: origins whose target months all end before the test period starts."""
    last = features["month"].max()
    usable = features[(features["months_seen"] >= MIN_MONTHS) & features["target_margin"].notna()
                      & (features["revenue_3m"] >= MIN_REVENUE) & (features["target_revenue"] >= MIN_REVENUE)]
    first_test = last - (test_months - 1)
    test = usable[(usable["month"] + 1 >= first_test) & (usable["month"] + horizon <= last)]
    train = usable[usable["month"] + horizon < first_test]
    return train, test


def mae(pred, actual):
    return float(np.mean(np.abs(np.asarray(pred) - np.asarray(actual))))


def evaluate(features, forecasters, test_months=6, horizon=3):
    train, test = time_split(features, test_months, horizon)
    out = {"train_rows": len(train), "test_rows": len(test),
           "train_months": [str(train["month"].min()), str(train["month"].max())],
           "test_origin_months": [str(test["month"].min()), str(test["month"].max())]}
    for f in forecasters:
        f.fit(train)
        out[f.name] = {"mae": round(mae(f.predict(test), test["target_margin"]), 4)}
    return out
