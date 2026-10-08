"""Features, forecasters and the time split (benchmark 3). No future data may leak."""
import numpy as np
import pandas as pd
import pytest

from clientprofit.features import FEATURES, build_features
from clientprofit.forecast.baseline import BaselineForecaster
from clientprofit.forecast.evaluate import time_split
from clientprofit.forecast.registry import get_forecaster


def fake_result(months=12, revenue=1000.0, labour=600.0, clients=("A",)):
    per = pd.period_range("2025-01", periods=months, freq="M")
    cm = pd.DataFrame([{"client": c, "month": m, "revenue": revenue, "labour_cost": labour, "hours": 10.0}
                       for c in clients for m in per])
    te = pd.DataFrame([{"client": c, "month": m, "hours": 2.0, "billable": False} for c in clients for m in per])
    inv = pd.DataFrame([{"client": c, "month": m, "invoice_date": m.start_time, "paid_date": m.start_time
                         + pd.Timedelta(days=20)} for c in clients for m in per])
    rq = pd.DataFrame([{"client": c, "request_date": m.start_time} for c in clients for m in per])
    return {"client_month": cm, "time_costed": te, "invoices_costed": inv, "tables": {"requests": rq}}


def test_rolling_margin_is_sum_profit_over_sum_revenue():
    r = fake_result()
    r["client_month"].loc[0:2, "revenue"] = [1000, 0, 2000]
    f = build_features(r)
    row = f.iloc[2]
    assert row["margin_3m"] == pytest.approx((3000 - 1800) / 3000)


def test_target_is_next_three_months_margin():
    r = fake_result()
    r["client_month"].loc[3:5, "labour_cost"] = [900, 900, 900]
    f = build_features(r)
    assert f.iloc[2]["target_margin"] == pytest.approx(0.1)


def test_features_do_not_change_when_the_future_changes():
    a = build_features(fake_result())
    r = fake_result()
    r["client_month"].loc[8:, "labour_cost"] = 5000
    b = build_features(r)
    assert np.allclose(a.loc[:6, FEATURES].fillna(-9).to_numpy(), b.loc[:6, FEATURES].fillna(-9).to_numpy())


def test_days_to_pay_ignores_payments_after_the_month():
    r = fake_result()
    r["invoices_costed"].loc[5, "paid_date"] = pd.Timestamp("2026-12-31")
    f = build_features(r)
    assert f.iloc[5]["days_to_pay"] == pytest.approx(20)


def test_time_split_never_overlaps():
    f = build_features(fake_result(months=24, clients=("A", "B")))
    train, test = time_split(f, test_months=6, horizon=3)
    first_test = f["month"].max() - 5
    assert len(train) and len(test)
    assert (train["month"] + 3 < first_test).all()
    assert (test["month"] + 1 >= first_test).all() and (test["month"] + 3 <= f["month"].max()).all()


def test_baseline_predicts_last_quarter():
    f = build_features(fake_result())
    assert np.allclose(BaselineForecaster().fit(f).predict(f.iloc[5:6]), f.iloc[5]["margin_3m"])


def test_lightgbm_fits_and_predicts():
    f = build_features(fake_result(months=24, clients=tuple("ABCDEFGH"))).dropna(subset=["target_margin"])
    model = get_forecaster("lightgbm").fit(f)
    assert len(model.predict(f)) == len(f) and set(model.importance()) == set(FEATURES)


def test_unknown_forecaster():
    with pytest.raises(ValueError):
        get_forecaster("nope")


def test_direct_cost_lowers_feature_margin():
    """D-31 carried into the features: margin = (revenue - direct - labour) / revenue."""
    r = fake_result()
    r["client_month"]["direct_cost"] = 100.0
    f = build_features(r)
    assert f.iloc[2]["margin_3m"] == pytest.approx((3000 - 1800 - 300) / 3000)


def test_outlook_gives_baseline_forecast_and_measured_error():
    from clientprofit.forecast.outlook import client_outlook
    settings = {"forecast": {"model": "baseline", "horizon_months": 3, "test_months": 6}}
    _, out = client_outlook(fake_result(months=24, clients=tuple("ABCDEFGH")), settings)
    assert out["A"]["forecast"] == pytest.approx(0.4)          # last 3 months' margin carried forward
    assert out["A"]["typical_error"] == pytest.approx(0.0)     # flat data: the rule is never wrong
    _, short = client_outlook(fake_result(months=8), settings)
    assert short["A"]["typical_error"] is None                 # too few past forecasts to measure
