"""Consumption / waste-risk model for FoodWise.

The idea
--------
Every time the user throws food away, a FoodWaste record is saved. Each record
tells us how long that item actually survived before being discarded:

    days_held          = waste_date - purchase_date
    shelf_life_days    = expiry_date - purchase_date
    utilisation_ratio  = days_held / shelf_life_days      (usually 0 .. 1)

The model (Ridge regression, scikit-learn) learns to predict this ratio from
the item profile: category, quantity and printed shelf life. For items still
in the inventory we can then estimate the date the user is likely to throw
them away - a personalised "effective expiry date" - and warn early when that
date is earlier than the printed expiry date.

Training gate
-------------
The model refuses to train until the user has at least ML_TRAINING_THRESHOLD
(= 8) waste records (see config.py). Below that the UI shows a "not trained"
panel with a progress bar instead of predictions.

Honesty note
------------
Metrics are computed with leave-one-out cross validation (appropriate for a
tiny dataset) and shown in the UI with a "small-sample estimates only"
disclaimer. We never claim food-safety accuracy.
"""
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict

from config import Config

FEATURE_CATEGORIES = ["Fruits", "Vegetables", "Dairy", "Meat", "Grains", "Other"]


def build_training_frame(ml_records):
    """Turn raw waste records into a clean DataFrame with the target column."""
    df = pd.DataFrame(ml_records)
    df = df[df["shelf_life_days"] > 0].copy()          # shelf life must be usable
    df["utilisation_ratio"] = (df["days_held"] / df["shelf_life_days"]).clip(0.0, 1.5)
    return df


def _feature_matrix(df):
    """Fixed feature columns so training and prediction always agree."""
    X = pd.DataFrame({
        "quantity": df["quantity"].astype(float).to_numpy(),
        "shelf_life_days": df["shelf_life_days"].astype(float).to_numpy(),
    })
    for cat in FEATURE_CATEGORIES:
        X[f"cat_{cat}"] = (df["category"] == cat).astype(float).to_numpy()
    return X


def train_model(ml_records):
    """Train the Ridge model for one user.

    Returns
    -------
    (model, metrics)
        model   - a fitted sklearn estimator, or None while below the gate
        metrics - dict describing the state (see routes for the UI fields)
    """
    required = Config.ML_TRAINING_THRESHOLD
    if len(ml_records) < required:
        return None, {"status": "untrained", "records": len(ml_records),
                      "required": required}

    df = build_training_frame(ml_records)
    if len(df) < 3:  # not enough usable rows even though the gate is passed
        return None, {"status": "untrained", "records": len(ml_records),
                      "required": required,
                      "note": "records lack a usable shelf life"}

    X, y = _feature_matrix(df), df["utilisation_ratio"].to_numpy()

    # Leave-one-out CV gives an honest error estimate on a tiny dataset.
    try:
        cv_pred = cross_val_predict(Ridge(alpha=1.0), X, y, cv=LeaveOneOut())
        mae = float(mean_absolute_error(y, cv_pred))
        r2 = float(r2_score(y, cv_pred))
    except Exception:
        fallback = Ridge(alpha=1.0).fit(X, y)
        mae = float(mean_absolute_error(y, fallback.predict(X)))
        r2 = float(r2_score(y, fallback.predict(X)))

    model = Ridge(alpha=1.0).fit(X, y)
    metrics = {
        "status": "trained",
        "records": int(len(df)),
        "required": required,
        "mae": round(mae, 3),          # avg error of the predicted ratio
        "r2": round(r2, 3),            # may be negative on tiny data - honest!
        "avg_ratio": round(float(y.mean()), 3),
    }
    return model, metrics


def predict_effective_expiry(model, item):
    """Predict the date an active item is likely to be thrown away.

    Returns (predicted_date, ratio) or None when the item has no usable
    shelf life. The ratio is clipped to [0, 1.2] so predictions stay sane.
    """
    shelf_life = (item.expiry_date - item.purchase_date).days
    if shelf_life <= 0:
        return None

    row = pd.DataFrame([{
        "category": item.category,
        "quantity": float(item.quantity or 0.0),
        "shelf_life_days": shelf_life,
    }])
    ratio = float(np.clip(model.predict(_feature_matrix(row))[0], 0.0, 1.2))
    predicted_date = item.purchase_date + timedelta(days=int(round(ratio * shelf_life)))
    return predicted_date, ratio
