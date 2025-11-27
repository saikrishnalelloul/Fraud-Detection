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
    cursor.execute(f"SELECT * FROM transactions ORDER BY rowid DESC LIMIT {n}")
    rows = cursor.fetchall()
    conn.close()

    transactions = []
    for row in rows:
        transactions.append({
            "transaction_id": row[0],
            "amount": row[1],
            "location": row[2],
            "device": row[3],
            "time": row[4],
            "prediction": row[5]
        })

    return jsonify(transactions)

# if __name__ == '__main__':
#     app.run(debug=True)
if __name__ == "__main__":
    # bind to 0.0.0.0 so the container exposes port 5000 to host
    app.run(host="0.0.0.0", port=5000, debug=False)

