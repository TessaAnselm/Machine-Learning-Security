"""
Extends ML106 (samsclass.info data-poisoning project): label-flip 10/30/100
training samples ('1' -> '2'), then test whether a k-NN label-consistency
filter can catch the poisoned samples before training and recover accuracy.
"""

import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.svm import SVC
from sklearn.neighbors import NearestNeighbors
from sklearn.model_selection import train_test_split

RNG = np.random.RandomState(0)
N_TRAIN_PER_DIGIT = 200
N_TEST_PER_DIGIT = 100
POISON_LEVELS = [10, 30, 100]
K_NEIGHBORS = 5


def load_mnist_subset():
    mnist = fetch_openml("mnist_784", version=1, as_frame=False, parser="liac-arff")
    X, y = mnist.data, mnist.target.astype(int)

    train_idx, test_idx = [], []
    for digit in range(10):
        digit_idx = np.where(y == digit)[0]
        RNG.shuffle(digit_idx)
        train_idx.extend(digit_idx[:N_TRAIN_PER_DIGIT])
        test_idx.extend(digit_idx[N_TRAIN_PER_DIGIT : N_TRAIN_PER_DIGIT + N_TEST_PER_DIGIT])

    train_idx, test_idx = np.array(train_idx), np.array(test_idx)
    RNG.shuffle(train_idx)
    return X[train_idx], y[train_idx], X[test_idx], y[test_idx]


def poison(y_train, n_poison):
    """Flip the first n_poison labels of digit '1' to '2'. Returns poisoned
    labels and the indices that were flipped (ground truth for scoring the defense)."""
    y_poisoned = y_train.copy()
    ones_idx = np.where(y_train == 1)[0][:n_poison]
    y_poisoned[ones_idx] = 2
    return y_poisoned, ones_idx


def knn_label_filter(X_train, y_train, k=K_NEIGHBORS):
    """Flags samples whose label disagrees with the majority label of their
    k nearest neighbors (excluding themselves). Returns a boolean mask of
    samples to KEEP (True = keep, False = flagged as suspicious)."""
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X_train)
    _, neighbor_idx = nn.kneighbors(X_train)
    neighbor_idx = neighbor_idx[:, 1:]  # drop self

    keep_mask = np.ones(len(y_train), dtype=bool)
    for i in range(len(y_train)):
        neighbor_labels = y_train[neighbor_idx[i]]
        majority_label = np.bincount(neighbor_labels).argmax()
        if majority_label != y_train[i]:
            keep_mask[i] = False
    return keep_mask


def count_incorrect_twos(model, X_test, y_test):
    preds = model.predict(X_test)
    predicted_two = preds == 2
    return int(np.sum(predicted_two & (y_test != 2)))


def main():
    print("Loading MNIST subset (2000 train / 1000 test)...")
    X_train, y_train, X_test, y_test = load_mnist_subset()

    baseline_model = SVC(kernel="linear").fit(X_train, y_train)
    baseline_acc = baseline_model.score(X_test, y_test)
    baseline_incorrect_twos = count_incorrect_twos(baseline_model, X_test, y_test)
    print(f"\nBaseline (clean) test accuracy: {baseline_acc:.4f}")
    print(f"Baseline (clean) incorrect '2' predictions: {baseline_incorrect_twos}\n")

    print(f"{'Poisoned':>8} | {'No defense':>10} | {'Defense':>9} | {'Caught':>7} | {'False+':>7} | {'Acc (defended)':>15}")
    print("-" * 75)

    for n_poison in POISON_LEVELS:
        y_poisoned, poisoned_idx = poison(y_train, n_poison)

        # Attack with no defense
        undefended_model = SVC(kernel="linear").fit(X_train, y_poisoned)
        incorrect_twos_undefended = count_incorrect_twos(undefended_model, X_test, y_test)

        # Apply k-NN label-consistency defense, then retrain on cleaned data
        keep_mask = knn_label_filter(X_train, y_poisoned)
        caught = np.sum(~keep_mask[poisoned_idx])
        false_positives = np.sum(~keep_mask) - caught

        defended_model = SVC(kernel="linear").fit(X_train[keep_mask], y_poisoned[keep_mask])
        incorrect_twos_defended = count_incorrect_twos(defended_model, X_test, y_test)
        defended_acc = defended_model.score(X_test, y_test)

        print(
            f"{n_poison:>8} | {incorrect_twos_undefended:>10} | {incorrect_twos_defended:>9} | "
            f"{caught:>3}/{n_poison:<3} | {false_positives:>7} | {defended_acc:>15.4f}"
        )


if __name__ == "__main__":
    main()
