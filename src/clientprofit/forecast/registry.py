"""Name -> forecaster (config key forecast.model)."""
from clientprofit.forecast.baseline import BaselineForecaster


def get_forecaster(name, seed=42):
    if name == "baseline":
        return BaselineForecaster()
    if name == "lightgbm":
        from clientprofit.forecast.lightgbm_model import LightGBMForecaster
        return LightGBMForecaster(seed)
    raise ValueError(f"Unknown forecast.model '{name}'. Known: baseline, lightgbm")
