# kafka_producer.py
import json
import time
from kafka import KafkaProducer
from uuid import uuid4
import random
from datetime import datetime
import os
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    linger_ms=5
)

# Probability of creating an anomalous/fraud-like transaction
FRAUD_PROB = 0.1  # 10% — change to 0.05 or 0.2 to tune sensitivity

def fake_transaction():
    # normal fields
    tx_time = datetime.utcnow().isoformat()
    normal_tx = {
        "transaction_id": str(uuid4()),
        "user_id": random.randint(1000, 2000),
        "amount": round(random.expovariate(1/50), 2),  # typical amounts
        "timestamp": tx_time,
        "time": tx_time,  # also include 'time' key in case consumer expects it
        "location": random.choice(["IN", "US", "GB", "FR", "CN"]),
        "device": random.choice(["mobile", "desktop", "tablet"]),
        "card_present": random.choice([True, False]),
        "merchant": random.choice(["m1", "m2", "m3", "m4"])
    }

    # Occasionally create a suspicious/fraud-like transaction
    if random.random() < FRAUD_PROB:
        fraud_tx = {
            "transaction_id": normal_tx["transaction_id"],
            "user_id": normal_tx["user_id"],
            # unusually high amount
            "amount": round(random.uniform(3000, 20000), 2),
            "timestamp": tx_time,
            "time": tx_time,
            # rare / unknown location and device
            "location": random.choice(["Unknown", "Offshore", "Fraud-Land"]),
            "device": random.choice(["skimmer", "rooted_mobile", "unknown_browser"]),
            "card_present": False,
            # suspicious merchant ids
            "merchant": random.choice(["suspicious_1", "suspicious_2", "suspicious_3"])
        }
        return fraud_tx

    return normal_tx

if __name__ == "__main__":
    # send 1 message per 0.5s - adjust as needed
    try:
        while True:
            tx = fake_transaction()
            producer.send('transactions', value=tx)
            producer.flush()  # optional; useful when debugging
            print("sent", tx["transaction_id"], tx["amount"])
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("stopped")
    finally:
        producer.close()
