"""FoodWise - Smart Food Expiry Predictor.

Application entry point. Run locally with:

    python app.py            ->  http://127.0.0.1:5000
"""
import os

from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from models import db, User, Notification, Recipe

login_manager = LoginManager()
scheduler = BackgroundScheduler(daemon=True)

# --------------------------------------------------------------------------
# Starter recipe catalogue (seeded once, shared by every user)
# --------------------------------------------------------------------------
DEFAULT_RECIPES = [
    ("Veggie Stir Fry", "mixed vegetables, soy sauce, garlic, rice, cooking oil",
     "Heat oil in a pan, add garlic and the vegetables and stir fry on high heat "
     "for 4-5 minutes. Add soy sauce, toss well and serve hot over cooked rice.",
     "Dinner"),
    ("Fruit Salad", "apple, banana, orange, grapes, honey",
     "Chop all the fruit into bite-sized pieces, place in a bowl, drizzle with "
     "honey and toss gently. Chill for 10 minutes before serving.",
     "Snack"),
    ("Vegetable Soup", "carrot, potato, onion, vegetable stock, salt, pepper",
     "Chop the vegetables and saute the onion in a pot until soft. Add carrot, "
     "potato and stock, then simmer for 20 minutes. Blend or serve chunky and "
     "season with salt and pepper.",
     "Dinner"),
    ("Cheese Omelette", "eggs, cheese, butter, salt, pepper",
     "Whisk the eggs with a pinch of salt and pepper. Melt butter in a pan, pour "
     "in the eggs and cook on low heat. Sprinkle cheese on top, fold and serve.",
     "Breakfast"),
    ("Milk Smoothie", "milk, banana, honey, oats",
     "Blend milk, a ripe banana, a spoon of honey and a handful of oats until "
     "smooth. Serve immediately for a filling breakfast drink.",
     "Breakfast"),
    ("Pasta with Tomato Sauce", "pasta, tomato, garlic, olive oil, cheese",
     "Boil the pasta until al dente. In a pan, warm olive oil with garlic, add "
     "chopped tomatoes and simmer for 10 minutes. Toss with the pasta and top "
     "with grated cheese.",
     "Dinner"),
    ("Fried Rice", "rice, egg, carrot, peas, soy sauce",
     "Cook the rice and let it cool. Scramble the egg in a hot wok, add diced "
     "carrot and peas, then add the rice and soy sauce. Stir fry for 3-4 minutes.",
     "Dinner"),
    ("Grilled Chicken Sandwich", "bread, chicken, cheese, lettuce, tomato",
     "Grill the chicken until cooked through. Layer bread with lettuce, sliced "
     "tomato, chicken and cheese, then toast the sandwich until the cheese melts.",
     "Lunch"),
    ("Yogurt Parfait", "yogurt, oats, berries, honey",
     "In a glass, layer yogurt, oats and berries twice. Drizzle honey on top and "
     "refrigerate for 15 minutes so the oats soften.",
     "Snack"),
    ("Pancakes", "flour, milk, eggs, sugar, butter",
     "Whisk flour, milk, eggs and sugar into a smooth batter. Pour ladlefuls onto "
     "a buttered pan and cook until bubbles appear, then flip and cook briefly.",
     "Breakfast"),
    ("Mashed Potatoes", "potato, butter, milk, salt",
     "Boil peeled potatoes until soft, mash with butter and warm milk, and season "
     "with salt. Serve as a side dish with vegetables or meat.",
     "Dinner"),
    ("Fruit Yogurt Bowl", "yogurt, apple, banana, honey",
     "Chop apple and banana into cubes, fold into yogurt and finish with a "
     "spoonful of honey. A quick, waste-free snack.",
     "Snack"),
]


def seed_default_recipes():
    """Insert the starter recipes the first time the app runs."""
    if Recipe.query.first() is not None:
        return
    for name, ingredients, instructions, category in DEFAULT_RECIPES:
        db.session.add(Recipe(recipe_name=name, ingredients=ingredients,
                              instructions=instructions, category=category))
    db.session.commit()
    print(f"[FoodWise] seeded {len(DEFAULT_RECIPES)} starter recipes")


def create_app(config_overrides=None):
    """Application factory (used by app.py, seed_demo.py and the tests)."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(os.path.join(os.path.dirname(__file__), "database"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # --- blueprints -------------------------------------------------------
    from routes.auth import auth_bp
    from routes.food import food_bp
    from routes.recipes import recipes_bp
    from routes.analytics import analytics_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(food_bp)
    app.register_blueprint(recipes_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(notifications_bp)

    with app.app_context():
        db.create_all()
        seed_default_recipes()
        # Optional auto-seeding for hosted demos: set SEED_DEMO=1 in the
        # hosting dashboard (e.g. Render) and the viva demo data (demo_user,
        # 11 items, 10 waste records) is created on first boot automatically.
        if os.environ.get("SEED_DEMO") == "1":
            try:
                from seed_demo import ensure_demo_data
                if ensure_demo_data():
                    print("[FoodWise] demo data seeded (SEED_DEMO=1)")
            except Exception as exc:
                print(f"[FoodWise] demo seeding skipped: {exc}")

    # --- Flask-Login ------------------------------------------------------
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- template globals ---------------------------------------------------
    @app.context_processor
    def inject_globals():
        unread = 0
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False).count()
        return dict(unread_count=unread)

    # --- landing page -------------------------------------------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("food.dashboard"))
        return render_template("index.html")

    # --- background expiry checker -----------------------------------------
    # Runs every 12 hours in the background; also reachable via the
    # "Run check now" button on the Reminders page.
    if app.config.get("SCHEDULER_ENABLED") and (
            os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug):

        def _run_scheduled_check():
            with app.app_context():
                from routes.notifications import run_expiry_check
                created = run_expiry_check()
                if created:
                    print(f"[FoodWise] expiry check created {created} reminder(s)")

        try:
            scheduler.add_job(_run_scheduled_check, "interval", hours=12,
                              id="expiry_check", replace_existing=True)
            scheduler.start()
        except Exception as exc:  # pragma: no cover - keep app usable without scheduler
            print(f"[FoodWise] scheduler disabled: {exc}")

    return app


# Module-level app for `python app.py` / `flask run`.
# Tests and seed_demo.py set FOODWISE_SKIP_APP_CREATION=1 and build their own app.
app = None if os.environ.get("FOODWISE_SKIP_APP_CREATION") == "1" else create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=5000)
