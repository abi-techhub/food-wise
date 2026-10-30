"""Waste analytics routes: charts (rendered with Chart.js from real DB data)
and the full ML insight panel."""
from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import FoodWaste
from ml.consumption_model import train_model, predict_effective_expiry

analytics_bp = Blueprint("analytics", __name__)


def _last_n_month_keys(n=6):
    """Month labels like ['May 2026', ..., 'Oct 2026'] oldest first."""
    keys, cursor = [], date.today().replace(day=1)
    for _ in range(n):
        keys.append(cursor.strftime("%b %Y"))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return list(reversed(keys))


def _verdict(predicted_date, today):
    delta = (predicted_date - today).days
    if delta <= 3:
        return "High - use this first", "danger"
    if delta <= 7:
        return "Medium - plan to use", "warning"
    return "Low - on track", "success"


@analytics_bp.route("/analytics")
@login_required
def analytics():
    waste = current_user.waste_records.order_by(FoodWaste.waste_date).all()
    items = current_user.foods.all()
    today = date.today()

    # --- aggregates for the charts ----------------------------------------
    by_category, by_month, by_reason = {}, {}, {}
    for w in waste:
        cat = w.category_snapshot or "Other"
        by_category[cat] = by_category.get(cat, 0.0) + float(w.wasted_quantity or 0)
        month = w.waste_date.strftime("%b %Y")
        by_month[month] = by_month.get(month, 0.0) + float(w.wasted_quantity or 0)
        by_reason[w.reason] = by_reason.get(w.reason, 0) + 1

    months = _last_n_month_keys(6)
    by_month = {m: round(by_month.get(m, 0.0), 2) for m in months}
    by_category = dict(sorted(by_category.items(), key=lambda kv: -kv[1]))

    # --- summary cards ------------------------------------------------------
    total_qty = round(sum(float(w.wasted_quantity or 0) for w in waste), 2)
    top_category = max(by_category, key=by_category.get) if by_category else "-"
    top_reason = max(by_reason, key=by_reason.get) if by_reason else "-"

    # --- ML panel -------------------------------------------------------------
    model, ml_status = train_model([w.to_ml_record() for w in waste])

    predictions = []
    if model is not None:
        for item in items:
            prediction = predict_effective_expiry(model, item)
            if prediction is None:
                continue
            predicted_date, ratio = prediction
            verdict, tone = _verdict(predicted_date, today)
            predictions.append({
                "item": item,
                "predicted_date": predicted_date,
                "ratio": ratio,
                "verdict": verdict,
                "tone": tone,
            })
        predictions.sort(key=lambda r: r["predicted_date"])
        predictions = predictions[:12]

    return render_template(
        "analytics.html",
        total_events=len(waste),
        total_qty=total_qty,
        top_category=top_category,
        top_reason=top_reason,
        waste_by_category=by_category,
        waste_by_month=by_month,
        waste_by_reason=by_reason,
        ml_status=ml_status,
        predictions=predictions,
    )
