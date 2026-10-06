"""Scores for benchmark 4: precision, recall and F1 against hand labels."""
LABELS = ("in_scope", "extra_unpaid", "unclear")


def scores(predicted, actual, positive="extra_unpaid"):
    """Accuracy, per-label precision/recall/F1, macro F1, and the headline for `positive`."""
    pairs = list(zip(predicted, actual))
    out = {"n": len(pairs), "accuracy": round(sum(p == a for p, a in pairs) / len(pairs), 3), "per_label": {}}
    f1s = []
    for label in LABELS:
        tp = sum(p == label and a == label for p, a in pairs)
        fp = sum(p == label and a != label for p, a in pairs)
        fn = sum(p != label and a == label for p, a in pairs)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out["per_label"][label] = {"precision": round(precision, 3), "recall": round(recall, 3),
                                   "f1": round(f1, 3), "support": tp + fn}
        f1s.append(f1)
    out["macro_f1"] = round(sum(f1s) / len(f1s), 3)
    out["headline"] = {"label": positive, **out["per_label"][positive]}
    return out
