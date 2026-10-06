"""Baseline: next quarter's margin equals the last quarter's margin."""


class BaselineForecaster:
    name = "baseline"

    def fit(self, features):
        return self

    def predict(self, features):
        return features["margin_3m"].to_numpy()
