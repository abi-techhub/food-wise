"""Application configuration for FoodWise - Smart Food Expiry Predictor."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_uri():
    """Use DATABASE_URL when provided by the host (e.g. postgres on a PaaS),
    but ignore malformed values; otherwise fall back to the local SQLite file."""
    uri = os.environ.get("DATABASE_URL", "")
    if uri.startswith(("sqlite", "postgresql", "postgres", "mysql")):
        return uri
    return "sqlite:///" + os.path.join(BASE_DIR, "database", "foodwise.db")


class Config:
    # --- Core Flask settings -------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "foodwise-dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Feature settings ----------------------------------------------
    REMINDER_DAYS_BEFORE = 3   # warn the user N days before expiry
    ML_TRAINING_THRESHOLD = 8  # waste records required before the ML model trains

    # --- Background scheduler ------------------------------------------
    SCHEDULER_ENABLED = True   # disabled automatically during tests / seeding
