# test_fraud.py
from kafka import KafkaProducer
import json, time
from uuid import uuid4
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

tx = {
    "transaction_id": str(uuid4()),
    "user_id": 1234,
   "amount": 10000.0,
"location": "Nowhere,XX",
"device": "TorBrowser",
"avg_amount_24h": 5.0,
"prev_txns_24h": 0,

    "avg_amount_24h": 10.0
}

producer.send("transactions", value=tx)
producer.flush()
print("sent test fraud tx")
