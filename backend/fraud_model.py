"""
fraud_model.py
Day 1: generate fake transactions, train an IsolationForest, print & save predictions.

Run:
    python fraud_model.py

Outputs:
 - prints a small sample of transactions with predicted label
 - saves predictions.csv in the same folder
"""
import random
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler

# Optional: faker helps make realistic location/device strings
try:
    from faker import Faker
    faker = Faker()
except Exception:
    faker = None
    # If faker is not installed, we will use simple lists below.

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_fake_transactions(n=2000, fraud_ratio=0.02):
    """
    Generate a dataframe of fake transactions.
    Columns: transaction_id, amount, location, device, time, prev_txns_24h, avg_amount_24h
    """
    ids = []
    amounts = []
    locations = []
    devices = []
    times = []
    prev_counts = []
    avg_amounts = []
    labels = []  # ground-truth label we create for testing (not used by model)

    # Some sample locations/devices if faker not available
    sample_locations = [
        "Hyderabad,IN", "Bengaluru,IN", "Mumbai,IN", "New Delhi,IN", "Chennai,IN",
        "Pune,IN", "Kolkata,IN", "London,UK", "New York,US", "San Francisco,US"
    ]
    sample_devices = ["iPhone", "Android", "Windows PC", "Mac", "Unknown Device"]

    base_time = datetime.now()

    for i in range(n):
        txid = f"TX{100000 + i}"
        ids.append(txid)

        # Normal transactions: amounts mostly small-to-medium, with a long tail
        amount = float(np.round(np.random.exponential(scale=50.0) + 1.0, 2))  # skewed distribution
        amounts.append(amount)

        # location and device (with faker if available)
        if faker:
            loc = f"{faker.city()},{faker.country_code()}"
            dev = faker.user_agent()
        else:
            loc = random.choice(sample_locations)
            dev = random.choice(sample_devices)
        locations.append(loc)
        devices.append(dev)

        # timestamp spread over last 7 days
        time = base_time - timedelta(seconds=random.randint(0, 7 * 24 * 3600))
        times.append(time.isoformat())

        # short-term user behavior features (simulated)
        prev = np.random.poisson(2)  # previous transactions in last 24h
        prev_counts.append(prev)
        avg_a = float(np.round(max(1.0, np.random.normal(loc=30, scale=20)), 2))
        avg_amounts.append(avg_a)

        # create some injected frauds for evaluation (not used in training because IsolationForest is unsupervised)
        is_fraud = False
        # simple heuristics to create labeled frauds: very large amounts or odd locations/devices
        if random.random() < fraud_ratio:
            is_fraud = True
            # make fraud amounts larger
            amounts[-1] = float(np.round(np.random.uniform(200, 4000), 2))
            # set a rare location/device
            locations[-1] = "Unknown,ZZ"
            devices[-1] = "TorBrowser"
            prev_counts[-1] = np.random.poisson(0)
            avg_amounts[-1] = float(np.round(np.random.uniform(5, 30), 2))

        labels.append("fraud" if is_fraud else "normal")

    df = pd.DataFrame({
        "transaction_id": ids,
        "amount": amounts,
        "location": locations,
        "device": devices,
        "time": times,
        "prev_txns_24h": prev_counts,
        "avg_amount_24h": avg_amounts,
        "label": labels  # for your inspection only
    })
    return df


def prepare_features(df, le_loc=None, le_dev=None, scaler=None, fit=True):
    """
    Convert raw dataframe to numeric features suitable for IsolationForest.

    Args:
        df: input dataframe
        le_loc, le_dev, scaler: optional pre-fitted encoders/scaler
        fit: if True, fit new encoders; if False, reuse existing ones safely

    Returns:
        X_scaled: numeric feature matrix
        df2: transformed dataframe with extra columns
        (le_loc, le_dev, scaler): fitted objects for reuse
    """
    df2 = df.copy()

    # Derive hour feature
    df2["time"] = pd.to_datetime(df2["time"])
    df2["hour"] = df2["time"].dt.hour + df2["time"].dt.minute / 60.0

    # ===== Label Encoding =====
    if fit or le_loc is None:
        le_loc = LabelEncoder()
        df2["loc_enc"] = le_loc.fit_transform(df2["location"].astype(str))
    else:
        # handle unseen labels by assigning -1
        df2["loc_enc"] = [
            le_loc.transform([loc])[0] if loc in le_loc.classes_ else -1
            for loc in df2["location"].astype(str)
        ]

    if fit or le_dev is None:
        le_dev = LabelEncoder()
        df2["dev_enc"] = le_dev.fit_transform(df2["device"].astype(str))
    else:
        df2["dev_enc"] = [
            le_dev.transform([dev])[0] if dev in le_dev.classes_ else -1
            for dev in df2["device"].astype(str)
        ]

    # ===== Numeric feature preparation =====
    feature_cols = ["amount", "prev_txns_24h", "avg_amount_24h", "hour", "loc_enc", "dev_enc"]
    X = df2[feature_cols].astype(float)

    # ===== Scaling =====
    if fit or scaler is None:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = scaler.transform(X)

    return X_scaled, df2, (le_loc, le_dev, scaler)



def train_isolation_forest(X_train, contamination=0.02):
    """
    Train and return an IsolationForest model.
    contamination: expected proportion of outliers in the data
    """
    model = IsolationForest(
        n_estimators=100,
        max_samples="auto",
        contamination=contamination,
        random_state=RANDOM_SEED,
        # behaviour="deprecated" if False else "deprecated"  # this is for older sklearn compat; no effect here
    )
    model.fit(X_train)
    return model


def predict_and_save(model, X, df_original, output_csv="predictions.csv", save_sqlite=False):
    """
    Use model to predict anomalies and save results.
    model.predict returns 1 (normal) or -1 (anomaly).
    We'll map -1 -> 'fraud', 1 -> 'normal'
    """
    preds = model.predict(X)
    # Map predictions
    pred_labels = ["normal" if p == 1 else "fraud" for p in preds]

    results = df_original.copy()
    results["model_prediction"] = pred_labels
    # Score: decision_function gives anomaly score (lower -> more anomalous)
    try:
        scores = model.decision_function(X)
        results["anomaly_score"] = scores
    except Exception:
        results["anomaly_score"] = None

    # Print some stats
    print("=== Prediction summary ===")
    counts = results["model_prediction"].value_counts()
    print(counts.to_string())
    print("\nSample flagged as fraud (first 10):")
    print(results[results["model_prediction"] == "fraud"].head(10).to_string(index=False))

    # Save CSV
    results.to_csv(output_csv, index=False)
    print(f"\nSaved predictions to {output_csv}")

    # Optional: save to SQLite (quick demonstration)
    if save_sqlite:
        conn = sqlite3.connect("predictions.db")
        results.to_sql("transactions_with_predictions", conn, if_exists="replace", index=False)
        conn.close()
        print("Saved predictions to SQLite database predictions.db (table: transactions_with_predictions)")

    return results


def main():
    print("Generating fake transactions...")
    df = generate_fake_transactions(n=2000, fraud_ratio=0.02)

    print("Preparing features...")
    X, df_prepared, encoders = prepare_features(df)

    print("Training IsolationForest...")
    # The contamination param should reflect how many anomalies you expect.
    # If you set contamination too high, many normal txns will be misclassified as fraud.
    model = train_isolation_forest(X, contamination=0.02)

    print("Predicting...")
    results = predict_and_save(model, X, df_prepared, output_csv="predictions.csv", save_sqlite=False)

    # Print a small dataframe sample for quick viewing
    preview_cols = ["transaction_id", "amount", "location", "device", "time", "prev_txns_24h", "avg_amount_24h", "model_prediction", "anomaly_score", "label"]
    print("\n--- Preview (first 10 rows) ---")
    print(results[preview_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
