import numpy as np
import pandas as pd

RULE_DESCRIPTIONS = {
    "amount_spike": "amount jumped far above this user's recent average",
    "large_amount": "large transfer relative to recent spending",
    "huge_amount": "very large payment for a low-history user",
    "geo_velocity": "improbable location change within minutes",
    "high_velocity": "many transactions within a very short window",
    "model_anomaly": "anomaly model flagged the pattern",
}


def parse_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_time(value):
    if not value:
        return None
    try:
        ts = pd.to_datetime(value, utc=True, errors="coerce")
        if isinstance(ts, pd.Timestamp):
            return ts.tz_localize(None)
        return None
    except Exception:
        return None


def evaluate_rule_flags(tx, recent_transactions):
    flags = []
    amount = parse_float(tx.get("amount"))
    user_location = tx.get("location")
    tx_time = parse_time(tx.get("time")) or parse_time(tx.get("timestamp"))
    if tx_time is None:
        tx_time = pd.Timestamp.utcnow()

    if recent_transactions:
        historic_amounts = []
        for record in recent_transactions:
            val = parse_float(record.get("amount"))
            if val is not None:
                historic_amounts.append(val)

        if amount is not None and historic_amounts:
            avg_amount = float(np.mean(historic_amounts))
            if avg_amount > 0:
                if amount > max(avg_amount * 4, avg_amount + 2000):
                    flags.append("amount_spike")
                elif amount > avg_amount * 3 and amount >= 5000:
                    flags.append("large_amount")
        elif amount is not None and amount >= 10000:
            flags.append("huge_amount")

        last_tx = recent_transactions[0]
        last_time = parse_time(last_tx.get("time") or last_tx.get("timestamp"))
        last_location = last_tx.get("location")
        if (
            last_time is not None
            and tx_time is not None
            and last_location
            and user_location
            and str(last_location).strip().lower() != str(user_location).strip().lower()
        ):
            minutes_apart = abs((tx_time - last_time).total_seconds()) / 60.0
            if minutes_apart <= 15:
                flags.append("geo_velocity")

        recent_window_minutes = 2
        rapid_count = 0
        for record in recent_transactions:
            record_time = parse_time(record.get("time") or record.get("timestamp"))
            if record_time is None:
                continue
            delta = tx_time - record_time
            if pd.isna(delta):
                continue
            seconds = delta.total_seconds()
            if 0 <= seconds <= recent_window_minutes * 60:
                rapid_count += 1
        if rapid_count >= 3:
            flags.append("high_velocity")
    else:
        if amount is not None and amount >= 3000:
            flags.append("huge_amount")

    return sorted(set(flags))


def describe_flags(flags):
    return [RULE_DESCRIPTIONS.get(flag, flag) for flag in flags]
