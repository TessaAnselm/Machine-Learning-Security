"""The four competing detectors and how they are scored."""

import time

import pandas as pd
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.tree import DecisionTreeClassifier

MODEL_NAMES = ["Decision Tree", "Random Forest", "AdaBoost", "Voting Ensemble"]


def build_models(tree_depth=8, n_trees=100, forest_depth=None, boost_iters=100,
                 learning_rate=0.5, voting="soft", seed=42):
    """Fresh, unfitted estimators. Tree-based models need no feature scaling,
    so there is no preprocessing step that could leak test statistics."""
    def tree():
        return DecisionTreeClassifier(max_depth=tree_depth, random_state=seed)

    def forest():
        return RandomForestClassifier(n_estimators=n_trees, max_depth=forest_depth,
                                      random_state=seed, n_jobs=-1)

    def boost():
        return AdaBoostClassifier(n_estimators=boost_iters, learning_rate=learning_rate,
                                  random_state=seed)

    return {
        "Decision Tree": tree(),
        "Random Forest": forest(),
        "AdaBoost": boost(),
        # The vote combines independent copies of the three models above.
        "Voting Ensemble": VotingClassifier(
            estimators=[("tree", tree()), ("forest", forest()), ("boost", boost())],
            voting=voting, n_jobs=-1),
    }


def evaluate(model, X_test, y_test):
    y_pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        # Rows = actual [benign, attack], columns = predicted [benign, attack].
        "confusion": confusion_matrix(y_test, y_pred, labels=[0, 1]),
        "y_pred": pd.Series(y_pred, index=X_test.index),
        "proba": None if proba is None else pd.Series(proba, index=X_test.index),
    }


def train_and_evaluate(models, X_train, y_train, X_test, y_test):
    """Fit on the training split only; score on the held-out test split only."""
    results = {}
    for name, model in models.items():
        start = time.perf_counter()
        model.fit(X_train, y_train)
        train_seconds = time.perf_counter() - start
        results[name] = {"model": model, "train_seconds": train_seconds,
                         **evaluate(model, X_test, y_test)}
    return results


def outcome_labels(y_true, y_pred):
    """Name each prediction TP / FP / FN / TN (positive class = attack)."""
    names = {(1, 1): "True Positive", (0, 1): "False Positive",
             (1, 0): "False Negative", (0, 0): "True Negative"}
    return pd.Series([names[(t, p)] for t, p in zip(y_true, y_pred)], index=y_true.index)
