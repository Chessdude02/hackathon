"""LightGBM forecaster (D-06). Predicts the change from last quarter's margin,
then adds it back, so it starts from the baseline and learns corrections.
Uses LightGBM's own training API (no scikit-learn needed)."""
import lightgbm as lgb

from clientprofit.features import FEATURES

PARAMS = {"objective": "regression", "learning_rate": 0.03, "num_leaves": 15, "min_data_in_leaf": 20,
          "bagging_fraction": 0.8, "bagging_freq": 1, "feature_fraction": 0.8, "verbose": -1}
ROUNDS = 300


class LightGBMForecaster:
    name = "lightgbm"

    def __init__(self, seed=42):
        self.params = {**PARAMS, "seed": seed}
        self.booster = None

    def fit(self, features):
        y = features["target_margin"] - features["margin_3m"]
        self.booster = lgb.train(self.params, lgb.Dataset(features[FEATURES], y), num_boost_round=ROUNDS)
        return self

    def predict(self, features):
        return features["margin_3m"].to_numpy() + self.booster.predict(features[FEATURES])

    def importance(self):
        gains = self.booster.feature_importance("gain")
        return dict(sorted(zip(FEATURES, [round(float(g), 1) for g in gains]), key=lambda kv: -kv[1]))
