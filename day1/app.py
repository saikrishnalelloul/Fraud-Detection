from flask import Flask, request, jsonify
import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import IsolationForest

app = Flask(__name__)

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
    """
    Expect JSON like:
    {
      "amount": 120.5,
      "location": "Hyderabad,IN",
      "device": "Android",
      "time": "2025-10-24T12:00:00",
      "prev_txns_24h": 3,
      "avg_amount_24h": 40.0
    }
    """
    data = request.get_json(force=True)
    try:
        # Convert to DataFrame
        df_input = pd.DataFrame([data])

        # Use the updated prepare_features with fit=False
        X_input, df_transformed, _ = prepare_features(
            df_input,
            le_loc=le_loc,
            le_dev=le_dev,
            scaler=scaler,
            fit=False
        )

        pred = model.predict(X_input)[0]
        result = "fraud" if pred == -1 else "normal"

        return jsonify({
            "prediction": result,
            "processed_data": df_transformed.to_dict(orient="records")[0]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400



@app.route('/get-data', methods=['GET'])
def get_data():
    # Return last few generated transactions
    sample = df_prepared.sample(10).to_dict(orient='records')
    return jsonify(sample)


if __name__ == '__main__':
    app.run(debug=True)
