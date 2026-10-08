"""ThreatVote AI - an interactive lab for ensemble-learning threat detection.

Run with: streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data
import models
from monster_guide import show_guide

# Reference palette (see dataviz skill): categorical slot 1 = blue, slot 8 = red.
COLOR_BENIGN = "#2a78d6"
COLOR_ATTACK = "#e34948"
COLOR_SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # one per model, fixed order
METRIC_LABELS = {
    "accuracy": "Accuracy — correct predictions",
    "precision": "Precision — alerts that are correct",
    "recall": "Recall — attacks caught",
    "f1": "F1 — balance of precision and recall",
}

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
                           text=[f"{v:.1%}" for v in vals], textposition="outside"))
    fig.update_layout(title=METRIC_LABELS[metric], yaxis_range=[0, 1.05],
                      yaxis_tickformat=".0%",
                      margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
    return fig


# --- Sidebar: data + hyperparameters -----------------------------------------
st.sidebar.title("ThreatVote AI")
st.sidebar.caption("Ensemble learning for network-traffic threat detection")
MISSIONS = ["1 · Meet the traffic", "2 · Compare the detectors", "3 · Find the mistakes"]
mission = st.sidebar.radio("Your monster missions", MISSIONS, key="mission")
motion = st.sidebar.checkbox("Animate Monster", value=True)


def go_to_mission(index):
    st.session_state.mission = MISSIONS[index]


st.sidebar.header("Dataset")
raw_files = data.list_raw_files()
source_options = ["Sample (synthetic, bundled)"] + [f.name for f in raw_files]
source = st.sidebar.selectbox("Source", source_options,
                              help="Drop real CIC-IDS2017 CSVs into data/raw/ to see them here.")
max_rows = st.sidebar.slider("Max rows (real data only)", 2_000, 100_000, 20_000, step=2_000) \
    if source != source_options[0] else 50_000
with st.sidebar.expander("Advanced model settings", expanded=False):
    st.caption("Start with the defaults. Change one setting at a time to compare results.")
    test_size = st.slider("Test set size", 0.1, 0.4, 0.25, step=0.05,
                          help="Fraction of rows reserved for testing; models learn from the remaining rows.")
    seed = st.number_input("Random seed", value=42, step=1,
                           help="Keep this fixed to repeat the same split and model training.")
    tree_depth = st.slider("Decision Tree max depth", 2, 20, 8,
                           help="Maximum number of decision levels. Deeper trees can learn more complex rules.")
    n_trees = st.slider("Random Forest: number of trees", 10, 300, 100, step=10,
                        help="How many trees the forest combines. More trees take longer to train.")
    boost_iters = st.slider("AdaBoost: boosting iterations", 10, 300, 100, step=10,
                            help="Maximum number of learning rounds, each focusing on earlier mistakes.")
    learning_rate = st.slider("AdaBoost: learning rate", 0.01, 2.0, 0.5, step=0.01,
                              help="How much each boosting round contributes to the final prediction.")

st.title("ThreatVote AI")
st.caption("A monster-guided adventure in spotting suspicious network traffic")
guide_messages = [
    ("Hi! I'm Monster. Let's catch some attacks!",
     "A connection is a conversation between computers. Some are normal; some are attacks. "
     "Your first mission: pick the detector you think will catch the most attacks, then check your guess."),
    ("Mission 2: Which detector would you trust?",
     "Models are detectors that learn from examples. Pick two below. Compare missed attacks and false alarms, "
     "then choose your favorite. Fewer missed attacks is useful, but false alarms matter too!"),
    ("Mission 3: Even detectors make mistakes!",
     "Choose a detector below and inspect its mistakes. A false alarm flags a normal connection. "
     "A missed attack slips through. Can you explain the difference? Answer my question to finish!"),
]
show_guide(*guide_messages[MISSIONS.index(mission)], motion=motion)
if source == source_options[0]:
    st.info("Demo data: synthetic network traffic. These scores help you explore the app; "
            "they do not measure real-world detection performance.")
else:
    st.caption(f"Dataset: {source}. Results describe this file and test split.")

raw_path = str([f for f in raw_files if f.name == source][0]) if source != source_options[0] else ""
df = get_dataset(source, raw_path, max_rows, seed)
df_hash = f"{source}-{len(df)}-{test_size}-{seed}"
X_train, X_test, y_train, y_test, attack_train, attack_test = get_split(df_hash, df, test_size, seed)
results = get_trained(df_hash + f"-{tree_depth}-{n_trees}-{boost_iters}-{learning_rate}",
                      X_train, y_train, X_test, y_test, tree_depth, n_trees,
                      boost_iters, learning_rate, seed)

st.sidebar.metric("Rows used for learning", len(X_train))
st.sidebar.metric("Rows reserved for testing", len(X_test))

challenge_context = (source, max_rows, test_size, seed, tree_depth, n_trees, boost_iters, learning_rate)
if st.session_state.get("challenge_context") != challenge_context:
    st.session_state.challenge_context = challenge_context
    st.session_state.completed_missions = []
    st.session_state.guess_checked = False
completed = st.session_state.completed_missions
mission_progress = st.progress(len(completed) / 3, text=f"Monster missions completed: {len(completed)} of 3")


def complete_mission(index):
    if index not in completed:
        completed.append(index)
    mission_progress.progress(len(completed) / 3, text=f"Monster missions completed: {len(completed)} of 3")


# --- Tab 1: Threat Detection Dashboard ---------------------------------------
if mission == MISSIONS[0]:
    st.subheader("Your turn: guess the winner")
    guess = st.radio("Which detector will catch the most attacks?", list(results), key="winner_guess")
    if st.button("Monster, check my guess!", type="primary"):
        st.session_state.guess_checked = True
        complete_mission(0)
    if st.session_state.guess_checked:
        most_caught = max(int(r["confusion"][1, 1]) for r in results.values())
        winners = [name for name, r in results.items() if int(r["confusion"][1, 1]) == most_caught]
        caught = int(results[guess]["confusion"][1, 1])
        total_attacks = int((y_test == 1).sum())
        show_guide("Nice guess!" if guess in winners else "Now we've learned something!",
                   f"{guess} caught {caught:,} of {total_attacks:,} test attacks. "
                   f"Most attacks caught: {', '.join(winners)} ({most_caught:,}). "
                   "A tie is possible. Next, let's check false alarms too.",
                   motion=motion, celebrate=guess in winners)
        st.button("Next mission → Compare detectors", on_click=go_to_mission, args=(1,), type="primary")
    st.divider()
    st.header("Explore Traffic")
    st.caption("The labels tell us which connections are normal and which are attacks. "
               "Models learn from one group of rows and are tested on a separate group they have not seen.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total connections", len(df))
    c2.metric("Benign (normal) connections", int((df[data.LABEL_COL] == data.BENIGN).sum()))
    c3.metric("Attack connections", int((df[data.LABEL_COL] != data.BENIGN).sum()))

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
        st.caption("This grid counts correct predictions and mistakes. Rows are actual labels; "
                   "columns are predicted labels. The displayed model has the highest test-set F1 score.")

    st.subheader("Sample of labeled traffic")
    st.caption("Traffic features describe each connection, such as packet counts and duration. "
               "Label is the known answer; it is never given to a model as an input.")
    st.dataframe(df.head(20), use_container_width=True)

# --- Tab 2: Model Battle ------------------------------------------------------
if mission == MISSIONS[1]:
    st.subheader("Your turn: compare two detectors")
    a, b = st.columns(2)
    first = a.selectbox("First detector", list(results), key="compare_first")
    second = b.selectbox("Second detector", list(results), index=3, key="compare_second")
    for col, name in [(a, first), (b, second)]:
        tn, fp, fn, tp = (int(value) for value in results[name]["confusion"].ravel())
        col.metric("Attacks caught", f"{tp} of {tp + fn}")
        col.metric("Attacks missed", fn)
        col.metric("False alarms", fp)
    if first == second:
        st.info("Pick different detectors to explore their tradeoffs.")
    else:
        fn_delta = int(results[second]["confusion"][1, 0] - results[first]["confusion"][1, 0])
        fp_delta = int(results[second]["confusion"][0, 1] - results[first]["confusion"][0, 1])
        st.write(f"Compared with {first}, {second} misses {abs(fn_delta)} "
                 f"{'more' if fn_delta > 0 else 'fewer' if fn_delta < 0 else 'additional'} attacks "
                 f"and raises {abs(fp_delta)} "
                 f"{'more' if fp_delta > 0 else 'fewer' if fp_delta < 0 else 'additional'} false alarms.")
        favorite = st.radio("Which would you choose for this dataset?", [first, second], key="favorite")
        if st.button("Choose my detector", type="primary"):
            complete_mission(1)
            st.session_state.fail_model = favorite
            show_guide("Detector chosen!", f"You chose {favorite}. There is no single right choice: "
                       "catching attacks and avoiding false alarms are both important.", motion=motion, celebrate=True)
        if 1 in completed:
            st.button("Next mission → Find mistakes", on_click=go_to_mission, args=(2,), type="primary")
    st.divider()
    st.header("Compare Models")
    st.caption("All four models learn from the same training rows and predict the same unseen test rows.")
    with st.expander("How do the models work?"):
        st.markdown("- **Decision Tree:** learns a series of rules about traffic.\n"
                    "- **Random Forest:** combines many decision trees.\n"
                    "- **AdaBoost:** learns in rounds, focusing on earlier mistakes.\n"
                    "- **Voting Ensemble:** averages the three models' attack probabilities.")

    st.subheader("Results in counts")
    summaries = []
    for name, result in results.items():
        tn, fp, fn, tp = (int(value) for value in result["confusion"].ravel())
        summaries.append({
            "Model": name,
            "Attacks caught": f"{tp:,} of {tp + fn:,} attacks",
            "Attacks missed": fn,
            "False alarms": f"{fp:,} of {tn + fp:,} benign connections",
            "Correct alerts": f"{tp:,} of {tp + fp:,} alerts" if tp + fp else "No alerts raised",
        })
    st.dataframe(pd.DataFrame(summaries), hide_index=True, use_container_width=True)

    st.subheader("Scores explained")
    st.write("**Accuracy:** share of all predictions that are correct. "
             "**Precision:** share of attack alerts that are correct. "
             "**Recall:** share of actual attacks caught. "
             "**F1:** balances precision and recall.")
    st.caption("Higher scores are better. Accuracy can look high when most traffic is benign, "
               "so check missed attacks and false alarms too. Combining models does not always improve results.")

    metric_cols = st.columns(4)
    for col, metric in zip(metric_cols, ["accuracy", "precision", "recall", "f1"]):
        col.plotly_chart(metric_bar(results, metric), use_container_width=True)

    st.subheader("Full metrics table")
    table = pd.DataFrame({name: {m: f"{results[name][m]:.1%}"
                                 for m in ["accuracy", "precision", "recall", "f1"]}
                          for name in results}).T
    table["train_seconds"] = [round(results[n]["train_seconds"], 3) for n in table.index]
    table = table.rename(columns={**METRIC_LABELS, "train_seconds": "Training time (seconds)"})
    st.dataframe(table, use_container_width=True)

    st.subheader("Confusion matrices")
    st.caption("Rows show actual labels; columns show predictions. Off-diagonal cells are mistakes.")
    cols = st.columns(4)
    for col, name in zip(cols, results):
        col.plotly_chart(confusion_figure(results[name]["confusion"], name), use_container_width=True)

# --- Tab 3: Detection Failure Lab --------------------------------------------
if mission == MISSIONS[2]:
    st.subheader("Your turn: help Monster understand a mistake")
    answer = st.radio("A detector says 'normal', but the connection is actually an attack. What happened?",
                      ["A false alarm", "A missed attack"], index=None, key="mistake_answer")
    if st.button("Check my answer", type="primary"):
        if answer == "A missed attack":
            complete_mission(2)
            show_guide("You got it!", "The attack slipped through. This is a missed attack, also called a false negative.",
                       motion=motion, celebrate=True)
        elif answer is None:
            st.info("Choose an answer first.")
        else:
            st.info("Try again! A false alarm flags normal traffic as an attack. Here, an actual attack was missed.")
    if len(completed) == 3:
        st.success("All three missions complete! You guessed, compared detectors, and identified a missed attack.")
        st.caption("Ready for another experiment? Change one advanced setting and see how your results change.")
    elif 2 in completed:
        st.caption("You finished this mission. Use the sidebar to complete the other missions too.")
    st.divider()
    st.header("Inspect Mistakes")
    st.caption("A false alarm flags normal traffic as an attack. A missed attack is labeled normal. "
               "Choose a model to see both kinds of mistake.")

    model_choice = st.selectbox("Model to inspect", list(results.keys()), key="fail_model")
    y_pred = results[model_choice]["y_pred"]
    outcomes = models.outcome_labels(y_test, y_pred)

    c1, c2, c3, c4 = st.columns(4)
    for col, name, label in [(c1, "True Positive", "Attacks caught"),
                             (c2, "True Negative", "Benign correctly classified"),
                             (c3, "False Positive", "False alarms"),
                             (c4, "False Negative", "Attacks missed")]:
        col.metric(label, int((outcomes == name).sum()), help=name)

    left, right = st.columns(2)
    with left:
        st.subheader("False alarms — normal traffic flagged as an attack")
        fp_mask = outcomes == "False Positive"
        if fp_mask.any():
            st.dataframe(X_test[fp_mask].assign(**{"True label": attack_test[fp_mask]}),
                        use_container_width=True)
        else:
            st.info("No false alarms for this model on this test split.")
    with right:
        st.subheader("Missed attacks — attacks labeled as normal traffic")
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
            st.info("No missed attacks for this model on this test split.")

    st.caption("Attack-family names describe the known labels, not model predictions. "
               "For another experiment, open Advanced model settings and change tree depth. "
               "Does Decision Tree miss fewer attacks, and does it raise more false alarms?")
