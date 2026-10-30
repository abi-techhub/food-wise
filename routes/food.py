"""Food inventory routes: dashboard, CRUD and waste reporting."""
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from config import Config
from models import db, FoodItem, FoodWaste, Notification, \
    FOOD_CATEGORIES, FOOD_UNITS, WASTE_REASONS
from ml.consumption_model import train_model, predict_effective_expiry

food_bp = Blueprint("food", __name__)


def _get_own_item(item_id):
    """Fetch a food item, but only if it belongs to the logged-in user."""
    item = db.session.get(FoodItem, item_id)
    if item is None or item.user_id != current_user.id:
        abort(404)
    return item


def _parse_food_form():
    """Validate the add/edit food form. Returns (values, errors)."""
    errors, values = [], {}

    values["food_name"] = request.form.get("food_name", "").strip()
    if not values["food_name"]:
        errors.append("Food name is required.")
    elif len(values["food_name"]) > 120:
        errors.append("Food name must be 120 characters or fewer.")

    category = request.form.get("category", "Other")
    if category not in FOOD_CATEGORIES:
        errors.append("Please choose a valid category.")
    values["category"] = category

    try:
        quantity = float(request.form.get("quantity", "0"))
        if quantity <= 0:
            raise ValueError
        values["quantity"] = quantity
    except (TypeError, ValueError):
        errors.append("Quantity must be a positive number.")
        values["quantity"] = 1.0

    unit = request.form.get("unit", "pcs")
    if unit not in FOOD_UNITS:
        errors.append("Please choose a valid unit.")
    values["unit"] = unit

    try:
        values["purchase_date"] = datetime.strptime(
            request.form.get("purchase_date", ""), "%Y-%m-%d").date()
    except ValueError:
        errors.append("Please provide a valid purchase date.")

    try:
        values["expiry_date"] = datetime.strptime(
            request.form.get("expiry_date", ""), "%Y-%m-%d").date()
    except ValueError:
        errors.append("Please provide a valid expiry date.")

    if "purchase_date" in values and "expiry_date" in values \
            and values["expiry_date"] < values["purchase_date"]:
        errors.append("Expiry date cannot be before the purchase date.")

    return values, errors


def _build_ml_panel(items):
    """Train the ML model (if the user has enough waste records) and rank
    active items by predicted waste risk. Returns (model, ml_status, at_risk)."""
    today = date.today()
    waste_rows = current_user.waste_records.order_by(FoodWaste.waste_date).all()
    model, ml_status = train_model([w.to_ml_record() for w in waste_rows])

    at_risk = []
    if model is not None:
        for item in items:
            prediction = predict_effective_expiry(model, item)
            if prediction is None:
                continue
            predicted_date, ratio = prediction
            # At risk = the model expects the item to be thrown away before
            # its printed expiry (or within the next 7 days).
            if predicted_date <= min(item.expiry_date, today + timedelta(days=7)):
                at_risk.append({
                    "item": item,
                    "predicted_date": predicted_date,
                    "ratio": ratio,
                })
        at_risk.sort(key=lambda r: (r["predicted_date"], r["item"].expiry_date))
        at_risk = at_risk[:5]
    return model, ml_status, at_risk


@food_bp.route("/dashboard")
@login_required
def dashboard():
    items = current_user.foods.all()
    expiring_soon = sorted((i for i in items if i.status == "near"),
                           key=lambda i: i.expiry_date)
    expired = sorted((i for i in items if i.status == "expired"),
                     key=lambda i: i.expiry_date)
    focus_list = expired + expiring_soon

    category_counts = {}
    for item in items:
        category_counts[item.category] = category_counts.get(item.category, 0) + 1

    _, ml_status, at_risk = _build_ml_panel(items)
    waste_total = current_user.waste_records.count()

    return render_template(
        "dashboard.html",
        total_items=len(items),
        near_count=len(expiring_soon),
        expired_count=len(expired),
        waste_total=waste_total,
        focus_list=focus_list,
        category_counts=category_counts,
        ml_status=ml_status,
        at_risk=at_risk,
    )


@food_bp.route("/inventory")
@login_required
def inventory():
    query = FoodItem.query.filter_by(user_id=current_user.id)

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(FoodItem.food_name.ilike(f"%{search}%"))

    category = request.args.get("category", "")
    if category in FOOD_CATEGORIES:
        query = query.filter_by(category=category)

    items = query.all()

    status = request.args.get("status", "")
    if status in ("safe", "near", "expired"):
        items = [i for i in items if i.status == status]

    sort = request.args.get("sort", "expiry")
    sorters = {
        "expiry": lambda i: i.expiry_date,
        "name": lambda i: i.food_name.lower(),
        "created": lambda i: i.created_at,
    }
    items.sort(key=sorters.get(sort, sorters["expiry"]))

    return render_template("inventory.html", items=items,
                           categories=FOOD_CATEGORIES,
                           filters={"q": search, "category": category,
                                    "status": status, "sort": sort})


@food_bp.route("/food/add", methods=["GET", "POST"])
@login_required
def add_food():
    if request.method == "POST":
        values, errors = _parse_food_form()
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("add_food.html", values=values,
                                   categories=FOOD_CATEGORIES, units=FOOD_UNITS)

        item = FoodItem(user_id=current_user.id, **values)
        db.session.add(item)
        db.session.commit()
        flash(f'"{item.food_name}" added to your inventory.', "success")
        return redirect(url_for("food.inventory"))

    return render_template("add_food.html", values={},
                           categories=FOOD_CATEGORIES, units=FOOD_UNITS)


@food_bp.route("/food/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_food(item_id):
    item = _get_own_item(item_id)

    if request.method == "POST":
        values, errors = _parse_food_form()
        if errors:
            for e in errors:
                flash(e, "error")
            values["id"] = item.id
            return render_template("edit_food.html", values=values,
                                   categories=FOOD_CATEGORIES, units=FOOD_UNITS)

        item.food_name = values["food_name"]
        item.category = values["category"]
        item.quantity = values["quantity"]
        item.unit = values["unit"]
        item.purchase_date = values["purchase_date"]
        item.expiry_date = values["expiry_date"]
        db.session.commit()
        flash(f'"{item.food_name}" updated.', "success")
        return redirect(url_for("food.inventory"))

    values = {
        "id": item.id, "food_name": item.food_name, "category": item.category,
        "quantity": item.quantity, "unit": item.unit,
        "purchase_date": item.purchase_date, "expiry_date": item.expiry_date,
    }
    return render_template("edit_food.html", values=values,
                           categories=FOOD_CATEGORIES, units=FOOD_UNITS)


@food_bp.route("/food/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_food(item_id):
    item = _get_own_item(item_id)
    Notification.query.filter_by(food_id=item.id, is_read=False)\
        .update({"is_read": True})
    db.session.delete(item)
    db.session.commit()
    flash(f'"{item.food_name}" removed from your inventory.', "info")
    return redirect(url_for("food.inventory"))


@food_bp.route("/food/<int:item_id>/waste", methods=["GET", "POST"])
@login_required
def report_waste(item_id):
    """Log a waste event (feeds the ML model) and remove the item."""
    item = _get_own_item(item_id)

    if request.method == "POST":
        try:
            wasted_qty = float(request.form.get("wasted_quantity", "0"))
            if wasted_qty <= 0:
                raise ValueError
        except (TypeError, ValueError):
            flash("Wasted quantity must be a positive number.", "error")
            return redirect(url_for("food.report_waste", item_id=item.id))

        reason = request.form.get("reason", "Other")
        if reason not in WASTE_REASONS:
            reason = "Other"

        record = FoodWaste(
            user_id=current_user.id,
            food_id=item.id,
            food_name_snapshot=item.food_name,
            category_snapshot=item.category,
            wasted_quantity=wasted_qty,
            reason=reason,
            waste_date=date.today(),
            shelf_life_days=max((item.expiry_date - item.purchase_date).days, 0),
            days_held=max((date.today() - item.purchase_date).days, 0),
        )
        db.session.add(record)
        # Any unread reminder about this item is now obsolete.
        Notification.query.filter_by(food_id=item.id, is_read=False)\
            .update({"is_read": True})
        db.session.delete(item)
        db.session.commit()

        records_now = current_user.waste_records.count()
        flash(f'"{record.food_name_snapshot}" logged as waste and removed. '
              f"ML progress: {records_now}/{Config.ML_TRAINING_THRESHOLD} waste records.",
              "success")
        return redirect(url_for("food.inventory"))

    return render_template("report_waste.html", item=item,
                           reasons=WASTE_REASONS,
                           threshold=Config.ML_TRAINING_THRESHOLD,
                           records_now=current_user.waste_records.count())


@food_bp.route("/food/<int:item_id>/consume", methods=["POST"])
@login_required
def mark_consumed(item_id):
    """Item was fully eaten - remove it without logging waste."""
    item = _get_own_item(item_id)
    Notification.query.filter_by(food_id=item.id, is_read=False)\
        .update({"is_read": True})
    db.session.delete(item)
    db.session.commit()
    flash(f'"{item.food_name}" marked as fully consumed. Nice, zero waste!',
          "success")
    return redirect(url_for("food.inventory"))
