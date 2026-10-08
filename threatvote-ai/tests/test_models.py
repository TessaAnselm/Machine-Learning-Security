import data
import models


def test_build_models_returns_all_four():
    built = models.build_models()
    assert set(built.keys()) == set(models.MODEL_NAMES)


def test_train_and_evaluate_produces_metrics_in_range():
    df = data.load_sample()
    X_train, X_test, y_train, y_test, *_ = data.split(df)
    results = models.train_and_evaluate(models.build_models(n_trees=20, boost_iters=20),
                                        X_train, y_train, X_test, y_test)
    for name in models.MODEL_NAMES:
        r = results[name]
        for metric in ["accuracy", "precision", "recall", "f1"]:
            assert 0.0 <= r[metric] <= 1.0
        assert r["confusion"].sum() == len(y_test)


def test_outcome_labels_cover_every_test_row():
    df = data.load_sample()
    X_train, X_test, y_train, y_test, *_ = data.split(df)
    built = models.build_models(n_trees=20, boost_iters=20)
    results = models.train_and_evaluate(built, X_train, y_train, X_test, y_test)
    outcomes = models.outcome_labels(y_test, results["Random Forest"]["y_pred"])
    assert len(outcomes) == len(y_test)
    assert set(outcomes.unique()) <= {"True Positive", "False Positive", "False Negative", "True Negative"}


def test_hyperparameters_change_model_behavior():
    df = data.load_sample()
    X_train, X_test, y_train, y_test, *_ = data.split(df)
    shallow = models.build_models(tree_depth=1)["Decision Tree"]
    deep = models.build_models(tree_depth=15)["Decision Tree"]
    shallow.fit(X_train, y_train)
    deep.fit(X_train, y_train)
    assert shallow.get_depth() < deep.get_depth()
