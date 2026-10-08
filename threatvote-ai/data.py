"""Dataset loading, cleaning, and leakage-safe train/test splitting.

Two data sources share one cleaning path:
  * a small synthetic sample (data/sample/cicids2017_sample.csv) that mimics a
    subset of CIC-IDS2017's column names and attack families, generated with a
    fixed seed so every run is reproducible;
  * real CIC-IDS2017 CSVs dropped into data/raw/ (see README for download steps).

Run `python data.py` to (re)generate the sample CSV.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = PROJECT_DIR / "data" / "sample" / "cicids2017_sample.csv"
RAW_DIR = PROJECT_DIR / "data" / "raw"

LABEL_COL = "Label"
BENIGN = "BENIGN"

# Columns in the "GeneratedLabelledFlows" variant of CIC-IDS2017 that identify a
# specific host/session/time rather than describe traffic behaviour. A model
# trained on these memorises the lab's IP addresses and capture schedule
# instead of learning what an attack looks like, so they are always dropped.
IDENTIFIER_COLS = ["Flow ID", "Source IP", "Source Port", "Destination IP", "Timestamp"]

# Per-class generating parameters for the synthetic sample. Bot and web
# brute-force traffic deliberately overlap with benign web browsing so the
# models make realistic mistakes for the Detection Failure Lab to explore.
#   share: fraction of rows; ports: candidate destination ports
#   dur: lognormal (mean, sigma) of flow duration in microseconds
#   fwd/bwd: lognormal (mean, sigma) of forward/backward packet counts
#   fwd_len/bwd_len: lognormal (mean, sigma) of mean packet size in bytes
#   syn/psh/ack: probability that the flag appears in the flow
#   win: candidate initial TCP window sizes (forward direction)
CLASS_PROFILES = {
    BENIGN: dict(share=0.70, ports=[80, 443, 53, 22, 8080, 123], dur=(11.0, 2.5),
                 fwd=(1.8, 1.0), bwd=(1.8, 1.1), fwd_len=(4.0, 1.0), bwd_len=(5.0, 1.3),
                 syn=0.05, psh=0.35, ack=0.40, win=[8192, 29200, 65535, 256, -1]),
    "DoS Hulk": dict(share=0.10, ports=[80], dur=(11.5, 1.2),
                     fwd=(1.6, 0.4), bwd=(1.5, 0.5), fwd_len=(5.8, 0.5), bwd_len=(7.5, 0.6),
                     syn=0.02, psh=0.60, ack=0.20, win=[29200, 251]),
    "DDoS": dict(share=0.08, ports=[80], dur=(13.5, 1.5),
                 fwd=(1.3, 0.4), bwd=(1.4, 0.5), fwd_len=(2.0, 0.6), bwd_len=(8.0, 0.4),
                 syn=0.02, psh=0.10, ack=0.85, win=[256, 8192]),
    "PortScan": dict(share=0.07, ports=list(range(1, 1024)), dur=(3.8, 0.8),
                     fwd=(0.2, 0.3), bwd=(0.1, 0.3), fwd_len=(0.3, 0.5), bwd_len=(1.5, 0.8),
                     syn=0.60, psh=0.02, ack=0.05, win=[1024, 29200, 0]),
    "Bot": dict(share=0.03, ports=[8080, 80, 443], dur=(10.5, 2.5),
                fwd=(1.5, 0.8), bwd=(1.4, 0.9), fwd_len=(4.5, 0.8), bwd_len=(4.5, 1.0),
                syn=0.05, psh=0.40, ack=0.40, win=[8192, 65535, 256]),
    "Web Attack - Brute Force": dict(share=0.02, ports=[80], dur=(14.5, 1.0),
                                     fwd=(2.3, 0.5), bwd=(2.0, 0.6), fwd_len=(4.2, 0.6),
                                     bwd_len=(5.5, 0.8), syn=0.05, psh=0.50, ack=0.35,
                                     win=[29200, 8192]),
}


def generate_sample(n_rows=4000, seed=42):
    """Build a reproducible CIC-IDS2017-style flow table. Same seed -> same data."""
    rng = np.random.default_rng(seed)
    frames = []
    for label, p in CLASS_PROFILES.items():
        n = int(round(n_rows * p["share"]))
        duration = rng.lognormal(*p["dur"], n).round()
        fwd_pkts = np.maximum(1, rng.lognormal(*p["fwd"], n).round())
        bwd_pkts = rng.lognormal(*p["bwd"], n).round()
        fwd_len_mean = rng.lognormal(*p["fwd_len"], n)
        bwd_len_mean = np.where(bwd_pkts > 0, rng.lognormal(*p["bwd_len"], n), 0.0)
        seconds = np.maximum(duration, 1) / 1e6
        total_pkts = fwd_pkts + bwd_pkts
        total_bytes = fwd_pkts * fwd_len_mean + bwd_pkts * bwd_len_mean
        frames.append(pd.DataFrame({
            "Destination Port": rng.choice(p["ports"], n),
            "Flow Duration": duration,
            "Total Fwd Packets": fwd_pkts,
            "Total Backward Packets": bwd_pkts,
            "Total Length of Fwd Packets": (fwd_pkts * fwd_len_mean).round(),
            "Total Length of Bwd Packets": (bwd_pkts * bwd_len_mean).round(),
            "Fwd Packet Length Mean": fwd_len_mean.round(2),
            "Bwd Packet Length Mean": bwd_len_mean.round(2),
            "Flow Bytes/s": (total_bytes / seconds).round(2),
            "Flow Packets/s": (total_pkts / seconds).round(2),
            "Flow IAT Mean": (duration / np.maximum(total_pkts - 1, 1)).round(2),
            "SYN Flag Count": rng.binomial(1, p["syn"], n),
            "PSH Flag Count": rng.binomial(1, p["psh"], n),
            "ACK Flag Count": rng.binomial(1, p["ack"], n),
            "Init_Win_bytes_forward": rng.choice(p["win"], n),
            "Down/Up Ratio": (bwd_pkts / fwd_pkts).round(),
            LABEL_COL: label,
        }))
    # Shuffle so classes aren't in contiguous blocks.
    return pd.concat(frames, ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)


def clean(df, max_rows=None, seed=42):
    """Apply the same cleaning to the sample and to real CIC-IDS2017 files.

    Nothing here is *fitted* (no means, scalers, or encoders learned from the
    data), so it is safe to run before the train/test split.
    """
    df = df.copy()
    # Real CIC-IDS2017 headers carry leading spaces (" Destination Port").
    df.columns = df.columns.str.strip()
    df = df.drop(columns=[c for c in IDENTIFIER_COLS if c in df.columns])
    # The original files encode the en dash in "Web Attack – Brute Force" as a
    # cp1252 byte, which shows up as \x96 when read as latin-1.
    df[LABEL_COL] = df[LABEL_COL].astype(str).str.replace("\x96", "-").str.replace("–", "-").str.strip()

    features = [c for c in df.columns if c != LABEL_COL]
    df[features] = df[features].apply(pd.to_numeric, errors="coerce")
    # CIC-IDS2017 has inf/NaN in Flow Bytes/s and Flow Packets/s for zero-length flows.
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    # CIC-IDS2017 contains many exact duplicate flows. Left in, the same row can
    # land in both train and test, inflating test scores (a classic leak).
    df = df.drop_duplicates().reset_index(drop=True)

    if max_rows and len(df) > max_rows:
        df, _ = train_test_split(df, train_size=max_rows, random_state=seed,
                                 stratify=_stratify_key(df))
        df = df.reset_index(drop=True)
    return df


def load_sample():
    if not SAMPLE_PATH.exists():
        SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_sample().to_csv(SAMPLE_PATH, index=False)
    return clean(pd.read_csv(SAMPLE_PATH))


def list_raw_files():
    return sorted(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []


def load_raw(path, max_rows=50_000, seed=42):
    # latin-1 decodes every byte, so the cp1252 dash in the Thursday file can't crash the read.
    return clean(pd.read_csv(path, encoding="latin-1", low_memory=False), max_rows=max_rows, seed=seed)


def _stratify_key(df):
    """Stratify on attack family when possible so rare attacks appear in both splits."""
    counts = df[LABEL_COL].value_counts()
    if counts.min() >= 2:
        return df[LABEL_COL]
    return (df[LABEL_COL] != BENIGN)


def split(df, test_size=0.25, seed=42):
    """Split once, before any model sees the data.

    Returns X_train, X_test, y_train, y_test, attack_train, attack_test where y is
    binary (1 = attack) and attack_* keeps the original family name for analysis.
    The attack family is never used as a feature.
    """
    X = df.drop(columns=[LABEL_COL])
    y = (df[LABEL_COL] != BENIGN).astype(int)
    X_train, X_test, y_train, y_test, a_train, a_test = train_test_split(
        X, y, df[LABEL_COL], test_size=test_size, random_state=seed, stratify=_stratify_key(df))
    return X_train, X_test, y_train, y_test, a_train, a_test


if __name__ == "__main__":
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample = generate_sample()
    sample.to_csv(SAMPLE_PATH, index=False)
    print(f"Wrote {len(sample)} rows to {SAMPLE_PATH.relative_to(PROJECT_DIR)}")
    print(sample[LABEL_COL].value_counts().to_string())
