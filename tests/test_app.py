"""Automated tests for FoodWise (pytest).

Run from the project root:

    python -m pytest tests/ -v
"""
import os

# Must be set before app is imported so the module-level app is not created.
os.environ.setdefault("FOODWISE_SKIP_APP_CREATION", "1")

from datetime import date, timedelta

import pytest

from app import create_app
from models import db, FoodItem, FoodWaste, Notification
from ml.consumption_model import train_model
from routes.notifications import run_expiry_check


@pytest.fixture()
def app(tmp_path):
    """A fresh app with its own temporary SQLite database."""
    return create_app({
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "TESTING": True,
        "SCHEDULER_ENABLED": False,
    })


@pytest.fixture()
def client(app):
    return app.test_client()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def register(client, username="abirami", email="abirami@example.com",
             password="secret123", follow_redirects=False):
    return client.post("/register", data={
        "username": username, "email": email,
        "password": password, "confirm": password,
    }, follow_redirects=follow_redirects)


def login(client, identifier="abirami", password="secret123",
          follow_redirects=False):
    return client.post("/login", data={
        "identifier": identifier, "password": password,
    }, follow_redirects=follow_redirects)


def add_item(client, name="Milk", category="Dairy", quantity="1", unit="L",
             purchased_days_ago=1, expires_in=5, follow_redirects=False):
    today = date.today()
    return client.post("/food/add", data={
        "food_name": name, "category": category, "quantity": quantity,
        "unit": unit,
        "purchase_date": (today - timedelta(days=purchased_days_ago)).isoformat(),
        "expiry_date": (today + timedelta(days=expires_in)).isoformat(),
    }, follow_redirects=follow_redirects)


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
def test_register_login_logout(client):
    resp = register(client)
    assert resp.status_code == 302  # redirect to /login

    resp = login(client)
    assert resp.status_code == 302  # redirect to /dashboard

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"abirami" in resp.data

    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302  # login required kicks in again


def test_register_rejects_duplicate_email(client):
    register(client, email="abi@example.com")
    client.get("/logout")
    resp = register(client, username="someoneelse", email="abi@example.com",
                    follow_redirects=True)
    assert resp.status_code == 200
    assert b"already exists" in resp.data


def test_login_rejects_wrong_password(client):
    register(client)
    client.get("/logout")
    resp = login(client, password="wrongpass", follow_redirects=True)
    assert b"Invalid" in resp.data


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# --------------------------------------------------------------------------
# Inventory CRUD
# --------------------------------------------------------------------------
def test_add_edit_delete_food(client, app):
    register(client)
    login(client)

    resp = add_item(client, name="Milk", expires_in=4, follow_redirects=True)
    assert b"Milk" in resp.data

    with app.app_context():
        item = FoodItem.query.filter_by(food_name="Milk").first()
        assert item is not None
        item_id = item.id

    resp = client.post(f"/food/{item_id}/edit", data={
        "food_name": "Fresh Milk", "category": "Dairy", "quantity": "2",
        "unit": "L",
        "purchase_date": date.today().isoformat(),
        "expiry_date": (date.today() + timedelta(days=6)).isoformat(),
    }, follow_redirects=True)
    assert b"Fresh Milk" in resp.data

    resp = client.post(f"/food/{item_id}/delete", follow_redirects=True)
    assert b"removed from your inventory" in resp.data
    assert b"No items found" in resp.data
    with app.app_context():
        assert FoodItem.query.count() == 0


def test_add_food_rejects_expiry_before_purchase(client):
    register(client)
    login(client)
    today = date.today()
    resp = client.post("/food/add", data={
        "food_name": "Bad dates", "category": "Other", "quantity": "1",
        "unit": "pcs",
        "purchase_date": today.isoformat(),
        "expiry_date": (today - timedelta(days=1)).isoformat(),
    }, follow_redirects=True)
    assert b"cannot be before the purchase date" in resp.data


# --------------------------------------------------------------------------
# Waste reporting + ML training gate (8 records)
# --------------------------------------------------------------------------
def _add_and_waste(client, app, index):
    name = f"Item{index}"
    add_item(client, name=name, category="Dairy", quantity="1", unit="pcs",
             purchased_days_ago=10, expires_in=5)
    with app.app_context():
        item = FoodItem.query.filter_by(food_name=name).first()
        item_id = item.id
    resp = client.post(f"/food/{item_id}/waste", data={
        "wasted_quantity": "1", "reason": "Expired",
    }, follow_redirects=True)
    assert b"logged as waste" in resp.data


def test_waste_record_created_and_item_removed(client, app):
    register(client)
    login(client)
    _add_and_waste(client, app, 1)
    with app.app_context():
        assert FoodWaste.query.count() == 1
        assert FoodItem.query.count() == 0  # item was removed
        record = FoodWaste.query.first()
        assert record.shelf_life_days == 15  # purchased 10d ago, expires in 5d
        assert record.days_held == 10
        assert record.category_snapshot == "Dairy"


def test_ml_gate_trains_only_after_8_waste_records(client, app):
    register(client)
    login(client)

    for i in range(7):  # one below the threshold
        _add_and_waste(client, app, i)

    resp = client.get("/analytics")
    assert b"Not trained" in resp.data
    assert b"7 / 8" in resp.data or b"7</strong>" in resp.data

    _add_and_waste(client, app, 7)  # the 8th record crosses the gate

    resp = client.get("/analytics")
    assert b"Not trained" not in resp.data
    assert b"Trained" in resp.data
    with app.app_context():
        assert FoodWaste.query.count() == 8


def test_train_model_unit_level_gate():
    model, metrics = train_model([])
    assert model is None and metrics["status"] == "untrained"

    records = [{"category": "Dairy", "quantity": 1.0,
                "shelf_life_days": 10 + i, "days_held": 8 + i}
               for i in range(8)]
    model, metrics = train_model(records)
    assert model is not None and metrics["status"] == "trained"
    assert metrics["records"] == 8


# --------------------------------------------------------------------------
# Reminders
# --------------------------------------------------------------------------
def test_expiry_check_creates_notification(client, app):
    register(client)
    login(client)
    add_item(client, name="Yogurt", expires_in=2)  # inside the 3-day window

    with app.app_context():
        created = run_expiry_check()
        assert created >= 1
        note = Notification.query.first()
        assert note is not None and "Yogurt" in note.message

        # Running again must not duplicate the reminder (dedupe by unread)
        assert run_expiry_check() == 0


# --------------------------------------------------------------------------
# Recipes
# --------------------------------------------------------------------------
def test_recipes_page_lists_catalogue(client):
    register(client)
    login(client)
    resp = client.get("/recipes")
    assert resp.status_code == 200
    assert b"Veggie Stir Fry" in resp.data  # part of the seeded catalogue


def test_recipe_recommendation_matches_inventory(client, app):
    register(client)
    login(client)
    add_item(client, name="Milk", category="Dairy", quantity="2", unit="L",
             expires_in=1)  # near expiry -> should boost milk recipes

    with app.app_context():
        from models import Recipe
        from ml.recommendation import recommend_recipes
        from models import User as UserModel

        user = UserModel.query.filter_by(username="abirami").first()
        items = user.foods.all()
        results = recommend_recipes(items, Recipe.query.all())

        assert results, "recommendations should never be empty with a catalogue"
        milk_smoothie = next(
            (r for r in results if r["recipe"].recipe_name == "Milk Smoothie"),
            None)
        assert milk_smoothie is not None
        assert milk_smoothie["match_pct"] >= 25          # milk matched
        assert len(milk_smoothie["matched"]) >= 1        # at least one hit
        assert milk_smoothie["uses_expiring"] is True     # expires tomorrow
        assert results[0]["score"] >= milk_smoothie["score"]  # sorted desc


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------
def test_change_password(client):
    register(client)
    login(client)

    resp = client.post("/profile/password", data={
        "current_password": "wrong", "new_password": "newpass123",
        "confirm_password": "newpass123",
    }, follow_redirects=True)
    assert b"incorrect" in resp.data

    resp = client.post("/profile/password", data={
        "current_password": "secret123", "new_password": "newpass123",
        "confirm_password": "newpass123",
    }, follow_redirects=True)
    assert b"updated" in resp.data

    client.get("/logout")
    resp = login(client, password="newpass123")
    assert resp.status_code == 302
