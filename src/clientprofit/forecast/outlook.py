"""Per-client margin history and next-quarter outlook for the screen (D-34).

The forecast is the configured model (`forecast.model`, the baseline since D-06:
next quarter's margin equals the last 3 months'). Its typical error is measured
on the owner's own data with the same time split as benchmark 3, so the screen
can show a range instead of a single number.
"""
from clientprofit.features import build_features
from clientprofit.forecast.evaluate import evaluate, time_split
from clientprofit.forecast.registry import get_forecaster

MIN_TEST_ROWS = 20  # fewer past forecasts than this: too few to say how wrong the rule usually is


def client_outlook(result, settings):
    """Return (features, outlook). `outlook` maps client -> {"forecast": margin or None,
    "typical_error": mean absolute error on this data or None, "test_rows": n}."""
    fc = settings["forecast"]
    features = build_features(result, fc["horizon_months"])
    model = get_forecaster(fc["model"])
    train, test = time_split(features, fc["test_months"], fc["horizon_months"])
    error = None
    if len(test) >= MIN_TEST_ROWS and (fc["model"] == "baseline" or len(train)):
        error = evaluate(features, [model], fc["test_months"], fc["horizon_months"])[model.name]["mae"]
    model.fit(train)
    latest = features.sort_values("month").groupby("client").tail(1)
    latest = latest[latest["margin_3m"].notna()]
    preds = dict(zip(latest["client"], model.predict(latest))) if len(latest) else {}
    out = {c: {"forecast": float(preds[c]) if c in preds else None, "typical_error": error,
               "test_rows": len(test)} for c in features["client"].unique()}
    return features, out
