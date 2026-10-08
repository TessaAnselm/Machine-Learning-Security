"""ThreatVote AI - an interactive lab for ensemble-learning threat detection.

Run with: streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data
import models

# Reference palette (see dataviz skill): categorical slot 1 = blue, slot 8 = red.
COLOR_BENIGN = "#2a78d6"
COLOR_ATTACK = "#e34948"
COLOR_SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # one per model, fixed order
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"

st.set_page_config(page_title="ThreatVote AI", layout="wide")


@st.cache_data(show_spinner="Loading data...")
def get_dataset(source, raw_path_str, max_rows, seed):
    if source == "Sample (synthetic, bundled)":
        return data.load_sample()
    return data.load_raw(raw_path_str, max_rows=max_rows, seed=seed)


@st.cache_data(show_spinner=False)
def get_split(df_hash, df, test_size, seed):
    return data.split(df, test_size=test_size, seed=seed)


@st.cache_resource(show_spinner="Training models...")
def get_trained(df_hash, _X_train, _y_train, _X_test, _y_test, tree_depth, n_trees,
                boost_iters, learning_rate, seed):
    built = models.build_models(tree_depth=tree_depth, n_trees=n_trees,
                                boost_iters=boost_iters, learning_rate=learning_rate, seed=seed)
    return models.train_and_evaluate(built, _X_train, _y_train, _X_test, _y_test)


def confusion_figure(cm, title):
    labels = ["Benign", "Attack"]
    fig = px.imshow(cm, x=labels, y=labels, text_auto=True, color_continuous_scale="Blues",
                    labels=dict(x="Predicted", y="Actual", color="Count"))
    fig.update_layout(title=title, coloraxis_showscale=False, margin=dict(t=40, b=10, l=10, r=10))
    return fig


def metric_bar(results, metric):
    names = list(results.keys())
    vals = [results[n][metric] for n in names]
    fig = go.Figure(go.Bar(x=names, y=vals, marker_color=COLOR_SERIES,
                           text=[f"{v:.3f}" for v in vals], textposition="outside"))
    fig.update_layout(title=metric.capitalize(), yaxis_range=[0, 1.05],
                      margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
    return fig


# --- Sidebar: data + hyperparameters -----------------------------------------
st.sidebar.title("ThreatVote AI")
st.sidebar.caption("Ensemble learning for network-traffic threat detection")

st.sidebar.header("Dataset")
raw_files = data.list_raw_files()
source_options = ["Sample (synthetic, bundled)"] + [f.name for f in raw_files]
source = st.sidebar.selectbox("Source", source_options,
                              help="Drop real CIC-IDS2017 CSVs into data/raw/ to see them here.")
max_rows = st.sidebar.slider("Max rows (real data only)", 2_000, 100_000, 20_000, step=2_000) \
    if source != source_options[0] else 50_000
test_size = st.sidebar.slider("Test set size", 0.1, 0.4, 0.25, step=0.05)
seed = st.sidebar.number_input("Random seed", value=42, step=1)

st.sidebar.header("Model controls")
tree_depth = st.sidebar.slider("Decision Tree max depth", 2, 20, 8)
n_trees = st.sidebar.slider("Random Forest: number of trees", 10, 300, 100, step=10)
boost_iters = st.sidebar.slider("AdaBoost: boosting iterations", 10, 300, 100, step=10)
learning_rate = st.sidebar.slider("AdaBoost: learning rate", 0.01, 2.0, 0.5, step=0.01)

raw_path = str([f for f in raw_files if f.name == source][0]) if source != source_options[0] else ""
df = get_dataset(source, raw_path, max_rows, seed)
df_hash = f"{source}-{len(df)}-{test_size}-{seed}"
X_train, X_test, y_train, y_test, attack_train, attack_test = get_split(df_hash, df, test_size, seed)
results = get_trained(df_hash + f"-{tree_depth}-{n_trees}-{boost_iters}-{learning_rate}",
                      X_train, y_train, X_test, y_test, tree_depth, n_trees,
                      boost_iters, learning_rate, seed)

st.sidebar.metric("Train rows", len(X_train))
st.sidebar.metric("Test rows", len(X_test))

tab_dashboard, tab_battle, tab_failures = st.tabs(
    ["Threat Detection Dashboard", "Model Battle", "Detection Failure Lab"])

# --- Tab 1: Threat Detection Dashboard ---------------------------------------
with tab_dashboard:
    st.header("Threat Detection Dashboard")
    st.caption("Labeled network traffic, split once into train/test before any model sees it.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total flows", len(df))
    c2.metric("Benign", int((df[data.LABEL_COL] == data.BENIGN).sum()))
    c3.metric("Attack flows", int((df[data.LABEL_COL] != data.BENIGN).sum()))

    left, right = st.columns(2)
    with left:
        counts = df[data.LABEL_COL].value_counts().reset_index()
        counts.columns = ["label", "count"]
        colors = [COLOR_BENIGN if l == data.BENIGN else COLOR_ATTACK for l in counts["label"]]
        fig = go.Figure(go.Bar(x=counts["label"], y=counts["count"], marker_color=colors))
        fig.update_layout(title="Traffic by label", margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        best = max(results, key=lambda n: results[n]["f1"])
        fig = confusion_figure(results[best]["confusion"], f"Confusion matrix — {best} (test set)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sample of labeled traffic")
    st.dataframe(df.head(20), use_container_width=True)

# --- Tab 2: Model Battle ------------------------------------------------------
with tab_battle:
    st.header("Model Battle")
    st.caption("All four models trained on the same split, scored on the held-out test set only.")

    metric_cols = st.columns(4)
    for col, metric in zip(metric_cols, ["accuracy", "precision", "recall", "f1"]):
        col.plotly_chart(metric_bar(results, metric), use_container_width=True)

    st.subheader("Full metrics table")
    table = pd.DataFrame({name: {m: round(results[name][m], 4)
                                 for m in ["accuracy", "precision", "recall", "f1"]}
                          for name in results}).T
    table["train_seconds"] = [round(results[n]["train_seconds"], 3) for n in table.index]
    st.dataframe(table, use_container_width=True)

    st.subheader("Confusion matrices")
    cols = st.columns(4)
    for col, name in zip(cols, results):
        col.plotly_chart(confusion_figure(results[name]["confusion"], name), use_container_width=True)

# --- Tab 3: Detection Failure Lab --------------------------------------------
with tab_failures:
    st.header("Detection Failure Lab")
    st.caption("Where each model's mistakes land, and which attack families cause them.")

    model_choice = st.selectbox("Model to inspect", list(results.keys()), key="fail_model")
    y_pred = results[model_choice]["y_pred"]
    outcomes = models.outcome_labels(y_test, y_pred)

    c1, c2, c3, c4 = st.columns(4)
    for col, name, color in [(c1, "True Positive", STATUS_GOOD), (c2, "True Negative", STATUS_GOOD),
                             (c3, "False Positive", STATUS_CRITICAL), (c4, "False Negative", STATUS_CRITICAL)]:
        col.metric(name, int((outcomes == name).sum()))

    left, right = st.columns(2)
    with left:
        st.subheader("False Positives — flagged, actually benign")
        fp_mask = outcomes == "False Positive"
        if fp_mask.any():
            st.dataframe(X_test[fp_mask].assign(**{"True label": attack_test[fp_mask]}),
                        use_container_width=True)
        else:
            st.info("No false positives for this model on this split.")
    with right:
        st.subheader("False Negatives — missed, actually an attack")
        fn_mask = outcomes == "False Negative"
        if fn_mask.any():
            fn_by_family = attack_test[fn_mask].value_counts().reset_index()
            fn_by_family.columns = ["attack_family", "missed_count"]
            fig = go.Figure(go.Bar(x=fn_by_family["attack_family"], y=fn_by_family["missed_count"],
                                   marker_color=COLOR_ATTACK))
            fig.update_layout(title="Missed attacks by family", margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(X_test[fn_mask].assign(**{"True label": attack_test[fn_mask]}),
                        use_container_width=True)
        else:
            st.info("No false negatives for this model on this split.")

    st.caption("A missed Bot or Web-Attack flow usually means its traffic pattern overlaps "
              "benign browsing closely enough that the model's decision boundary lets it through — "
              "try increasing tree depth or boosting iterations in the sidebar and compare.")
