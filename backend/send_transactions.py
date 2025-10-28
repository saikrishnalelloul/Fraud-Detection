"""
send_transactions.py
Simulate streaming fake transactions into the local /predict endpoint.

Run:
    python send_transactions.py

Adjust:
    - N_TXNS: number of transactions to send
    - DELAY_SECS: delay between sends (0 for burst)
"""

import time
import json
import requests
import traceback

# import your generator from fraud_model
from fraud_model import generate_fake_transactions

# CONFIG
API_URL = "http://127.0.0.1:5000/predict"
N_TXNS = 100        # how many txns to send (change as needed)
DELAY_SECS = 0.5    # seconds between sends, simulate rate. 0 -> as fast as possible
RETRY_DELAY = 1.0   # if request fails, wait then retry (simple)
MAX_RETRIES = 3

def make_payload(row):
    """
    Turn one row (pandas Series or dict) into the JSON payload expected by /predict.
    Adapt the keys here to match the fields your API expects.
    """
    # if pandas Series, convert to dict
    try:
        tx = dict(row)
    except Exception:
        tx = row

    # normalize field names / formats - match your API's expected input
    payload = {
        "amount": float(tx.get("amount", 0)),
        "location": tx.get("location", "Unknown"),
        "device": tx.get("device", "Unknown"),
        "time": tx.get("time", None),               # keep the timestamp string from generator
        # optional engineered fields if your model expects them
        "prev_txns_24h": int(tx.get("prev_txns_24h", 0)),
        "avg_amount_24h": float(tx.get("avg_amount_24h", 0.0))
    }
    return payload

def send_one(payload):
    """POST payload to the /predict endpoint with simple retries."""
    headers = {"Content-Type": "application/json"}
    for attempt in range(1, MAX_RETRIES+1):
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=5)
            # HTTP-level OK
            if resp.status_code == 200:
                return resp.json()
            else:
                # server sent an error but responded: show and break/retry
                print(f"[WARN] HTTP {resp.status_code} - {resp.text}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print("[ERROR] Max retries reached, skipping this transaction.")
                return {"error": str(e)}
    return {"error": "unknown"}

def main():
    print(f"[INFO] Generating {N_TXNS} fake transactions...")
    # generate_fake_transactions should return a pandas DataFrame (as in your day1)
    df = generate_fake_transactions(n=N_TXNS)
    sent = 0

    for idx, row in df.iterrows():
        payload = make_payload(row)
        # optional: inject a client-side transaction_id if you want it stored as-is
        # payload["transaction_id"] = f"SIM_{int(time.time()*1000)}_{idx}"

        result = send_one(payload)

        # print brief status
        if "prediction" in result:
            print(f"[{sent+1}/{N_TXNS}] -> {result['prediction']} | payload amount={payload['amount']} | id:{payload.get('transaction_id','-')}")
        else:
            print(f"[{sent+1}/{N_TXNS}] -> error: {result}")

        sent += 1
        if DELAY_SECS > 0:
            time.sleep(DELAY_SECS)

    print(f"[INFO] Done. Sent {sent} transactions.")

if __name__ == "__main__":
    main()
