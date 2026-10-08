import numpy as np
import pandas as pd

import data


def test_generate_sample_reproducible():
    a = data.generate_sample(seed=7)
    b = data.generate_sample(seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_clean_drops_identifier_columns():
    df = data.generate_sample(n_rows=200, seed=1)
    df["Flow ID"] = "x"
    df["Source IP"] = "1.2.3.4"
    cleaned = data.clean(df)
    for col in data.IDENTIFIER_COLS:
        assert col not in cleaned.columns


def test_clean_drops_duplicates_and_bad_values():
    df = data.generate_sample(n_rows=50, seed=1)
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    dup.loc[1, "Flow Bytes/s"] = np.inf
    cleaned = data.clean(dup)
    assert len(cleaned) == len(df) - 1  # the inf row and the duplicate are both gone
    assert not cleaned.isin([np.inf, -np.inf]).any().any()


def test_split_no_row_overlap_between_train_and_test():
    df = data.load_sample()
    X_train, X_test, y_train, y_test, a_train, a_test = data.split(df)
    assert set(X_train.index).isdisjoint(set(X_test.index))
    assert len(X_train) + len(X_test) == len(df)


def test_split_every_attack_family_in_both_splits():
    df = data.load_sample()
    _, _, _, _, a_train, a_test = data.split(df)
    assert set(a_train.unique()) == set(a_test.unique()) == set(df[data.LABEL_COL].unique())


def test_attack_family_not_a_feature():
    df = data.load_sample()
    X_train, X_test, *_ = data.split(df)
    assert data.LABEL_COL not in X_train.columns
    assert data.LABEL_COL not in X_test.columns
