# kafka_consumer_worker.py
import json
import pickle
import numpy as np
from kafka import KafkaConsumer
import pandas as pd
from datetime import datetime, timezone
import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

import warnings
from database import insert_transaction
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# ---------- Load artifacts ----------
with open("isolation_forest_artifacts.pkl", "rb") as f:
    artifacts = pickle.load(f)

model = artifacts["model"]
le_loc = artifacts["le_loc"]
le_dev = artifacts["le_dev"]
scaler = artifacts["scaler"]

# Ensure table exists — see SQL below if you want to create manually
# ---------- Kafka consumer ----------
consumer = KafkaConsumer(
    'transactions',
    bootstrap_servers=[KAFKA_BROKER],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='fraud-detector-group'
)

# Reuse featurize implementation (copy from previous code)
def _safe_label_transform(le, values):
    out = []
    classes = set(le.classes_.tolist())
    for v in values:
        if v in classes:
            out.append(int(le.transform([v])[0]))
        else:
            out.append(-1)
    return out

def featurize_single_tx(tx, le_loc, le_dev, scaler):
    amount = float(tx.get("amount", 0.0))
    prev = float(tx.get("prev_txns_24h", 0.0))
    avg_amt = float(tx.get("avg_amount_24h", 0.0))
    t_raw = tx.get("time")
    try:
        t = pd.to_datetime(t_raw)
        hour = float(t.hour + t.minute / 60.0)
    except Exception:
        hour = 0.0
    loc = str(tx.get("location", ""))
    dev = str(tx.get("device", ""))
    loc_enc = _safe_label_transform(le_loc, [loc])[0]
    dev_enc = _safe_label_transform(le_dev, [dev])[0]
    feat = np.array([[amount, prev, avg_amt, hour, loc_enc, dev_enc]], dtype=float)
    X_scaled = scaler.transform(feat)
    return X_scaled

print("Consumer ready — waiting for messages...")

for msg in consumer:
    tx = msg.value
    try:
        X = featurize_single_tx(tx, le_loc, le_dev, scaler)
        pred = model.predict(X)[0]            # -1 (fraud) or +1 (normal)
        score = model.decision_function(X)[0] # higher = more normal

        # Keep the actual score instead of inverting it
        risk_score = float(score)

        # Calculate a 5th percentile cutoff from training scores
        try:
            threshold = np.percentile(model.decision_function(model.X_fit_), 25)
        except AttributeError:
            # Fallback in case .X_fit_ isn’t available
            threshold = np.percentile(score, 5)

        # Mark fraud if score is below that threshold
        is_fraud = 1 if score < threshold else 0

        # pred = model.predict(X)[0]            # 1 or -1
        # score = model.decision_function(X)[0] # higher -> more normal
        # is_fraud = 1 if pred == -1 else 0
        # risk_score = float(-score)           # invert so larger = higher risk



        tx_record = {
            "transaction_id": tx.get("transaction_id"),
            "user_id": tx.get("user_id"),
            "amount": tx.get("amount"),
            "location": tx.get("location"),
            "device": tx.get("device"),
            "time": tx.get("time", datetime.now(timezone.utc).isoformat()),
            "timestamp": tx.get("time", datetime.now(timezone.utc).isoformat()),
            "is_fraud": is_fraud,
            "risk_score": risk_score,
        }

        insert_transaction(tx_record, "fraud" if is_fraud else "normal")

        print("Processed", tx_record["transaction_id"], "fraud?", is_fraud, "risk", risk_score)
    except Exception as e:
        print("Error processing message:", e)
        # optional: log the message to a dead-letter table or file
