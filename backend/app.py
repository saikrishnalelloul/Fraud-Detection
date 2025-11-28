from flask import Flask, request, jsonify
import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import IsolationForest
from database import insert_transaction, get_connection
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 👈 allow React frontend access


# ========== 1. Load or create model ==========
# For now, reuse the same logic as Day1 (simple retrain on startup)
from fraud_model import generate_fake_transactions, prepare_features, train_isolation_forest

df = generate_fake_transactions(n=2000)
X, df_prepared, encoders = prepare_features(df)
model = train_isolation_forest(X, contamination=0.02)

# Optional: save encoders for later use
le_loc, le_dev, scaler = encoders


# ========== 2. API routes ==========

@app.route('/')
def home():
    return {"message": "Fraud Detection API is running 🚀"}

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True)

    try:
        # Convert to DataFrame
        df_input = pd.DataFrame([data])

        # Prepare features using pre-fitted encoders/scaler
        X_input, df_transformed, _ = prepare_features(
            df_input,
            le_loc=le_loc,
            le_dev=le_dev,
            scaler=scaler,
            fit=False
        )

        # Model prediction
        pred = model.predict(X_input)[0]
        result = "fraud" if pred == -1 else "normal"

        # ==== NEW: save to SQLite ====
        transaction = {
            'transaction_id': f"TXN_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S%f')}",
            'user_id': data.get('user_id') or data.get('userId'),
            'amount': data.get('amount'),
            'location': data.get('location'),
            'device': data.get('device'),
            'time': data.get('time')
        }

        insert_transaction(transaction, result)

        # Response to client
        return jsonify({
            "prediction": result,
            "transaction": transaction
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400



@app.route('/get-data', methods=['GET'])
def get_data():
    # Return last few generated transactions
    sample = df_prepared.sample(10).to_dict(orient='records')
    return jsonify(sample)

@app.route('/transactions', methods=['GET'])
def get_transactions():
    n = int(request.args.get('n', 10))  # default = last 10
    conn, cursor = get_connection()
    try:
        cursor.execute(
            "SELECT rowid AS sqlite_rowid, * FROM transactions ORDER BY rowid DESC LIMIT ?",
            (n,)
        )
        rows = cursor.fetchall()

        # Aggregate stats for entire table so the dashboard can show real totals
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_count_row = cursor.fetchone()
        total_count = total_count_row[0] if total_count_row else 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE (
                prediction IS NOT NULL AND LOWER(prediction) = 'fraud'
            )
            OR (
                is_fraud IS NOT NULL AND is_fraud != 0
            )
            """
        )
        fraud_count_row = cursor.fetchone()
        fraud_count = fraud_count_row[0] if fraud_count_row else 0
    finally:
        conn.close()

    transactions = []
    for row in rows:
        record = dict(row)
        prediction = record.get("prediction")
        if prediction is None and record.get("is_fraud") is not None:
            prediction = "fraud" if record["is_fraud"] else "normal"

        transaction_id = record.get("transaction_id")
        amount = record.get("amount")

        # ==== Normalize obvious data mismatches ====
        # Some historical rows stored the UUID under `amount` and a numeric code under
        # `transaction_id`. If we detect that pattern, swap them before returning to the UI.
        if isinstance(amount, str) and amount.count("-") >= 2 and isinstance(transaction_id, (int, float)):
            transaction_id, amount = amount, transaction_id

        # SQLite can return Decimal-like strings; convert safe numerics back to float
        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            amount_value = amount

        row_identifier = (
            record.get("id")
            or record.get("sqlite_rowid")
            or record.get("rowid")
        )

        transactions.append({
            "id": row_identifier,
            "transaction_id": transaction_id,
            "user_id": record.get("user_id"),
            "amount": amount_value,
            "time": record.get("time") or record.get("timestamp"),
            "prediction": prediction,
            "is_fraud": record.get("is_fraud"),
            "risk_score": record.get("risk_score"),
            "location": record.get("location"),
            "device": record.get("device"),
        })

    response = {
        "items": transactions,
        "meta": {
            "total": total_count,
            "frauds": fraud_count,
        },
    }

    return jsonify(response)

# if __name__ == '__main__':
#     app.run(debug=True)
if __name__ == "__main__":
    # bind to 0.0.0.0 so the container exposes port 5000 to host
    app.run(host="0.0.0.0", port=5000, debug=False)

