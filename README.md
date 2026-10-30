# food-wise

**FoodWise - Smart Food Expiry Predictor**: a full-stack web application that
helps households reduce food waste. Track what you buy, get reminded before it
expires, find recipes that use what you already have, and let a machine-learning
model learn your habits so it can predict which items are most likely to end up
in the bin.

Built as an academic mini-project (Flask + SQLite + scikit-learn).

---

## Features

| Module | What it does |
| --- | --- |
| Authentication | Register / login / logout, salted password hashes, per-user data isolation |
| Inventory | Add, edit, delete food items with quantity, category, purchase and expiry dates |
| Expiry tracking | Colour-coded statuses: green (fresh), orange (expiring within 3 days), red (expired) |
| Reminders | Background scheduler checks expiries every 12 hours; manual "Run check now" button; unread badge in the navbar |
| Recipes | Ingredient-matching recommender that ranks recipes by what you have and boosts ones that rescue near-expiry items |
| Waste analytics | Chart.js charts (category / month / reason) computed from real database records only |
| ML predictions | Ridge regression that predicts how much of the printed shelf life you typically use, and flags at-risk items |

### The ML training gate (8 waste records)

The prediction model is **personal** and deliberately honest:

- The ML panel stays in a **"Not trained yet"** state with a progress bar until
  the user has logged **8 waste records** (`ML_TRAINING_THRESHOLD` in `config.py`).
- Each waste report stores *how long the item actually survived* relative to its
  printed shelf life (the "utilisation ratio").
- At 8+ records a **Ridge regression** model trains on those ratios, evaluated
  with leave-one-out cross validation (appropriate for small datasets), and the
  panel switches to **"Trained"** with metrics and per-item risk predictions.
- Predictions are estimates only - the app never claims food-safety accuracy.

## Tech stack

- **Backend**: Python 3, Flask 3, Flask-SQLAlchemy, Flask-Login, APScheduler
- **Database**: SQLite (5 tables: users, food_items, notifications, food_waste, recipes)
- **Frontend**: Bootstrap 5, Bootstrap Icons, Chart.js, vanilla JavaScript
- **ML**: pandas, NumPy, scikit-learn

## Quick start

```bash
# 1. clone and enter the project
git clone https://github.com/abi-techhub/food-wise.git
cd food-wise

# 2. create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. install dependencies
pip install -r requirements.txt

# 4. (optional, recommended for demos) seed demo data
python seed_demo.py

# 5. run
python app.py                   # open http://127.0.0.1:5000
```

**Demo account** (after running `python seed_demo.py`):
username `demo_user` - password `Demo@123`.
It comes with 11 inventory items (some expiring, one expired) and 10 waste
records, so the ML panel is already **trained** - perfect for a viva demo.
Use `python seed_demo.py --fresh` to rebuild it from scratch.

A **freshly registered account** starts with 0/8 waste records and shows the
untrained ML panel, which is the intended way to demonstrate the training gate.

## Project structure

```
food-wise/
├── app.py                    # application factory, landing page, scheduler
├── config.py                 # configuration (reminder window, ML threshold)
├── models.py                 # 5 SQLAlchemy models
├── seed_demo.py              # viva demo data seeder (--fresh supported)
├── requirements.txt
├── routes/
│   ├── auth.py               # register / login / logout / profile
│   ├── food.py               # dashboard, inventory CRUD, waste reporting
│   ├── recipes.py            # recipe recommender page
│   ├── analytics.py          # charts + ML panel
│   └── notifications.py      # reminders + expiry checker job
├── ml/
│   ├── consumption_model.py  # gated Ridge model (utilisation-ratio target)
│   └── recommendation.py     # ingredient-matching recommender
├── templates/                # 13 Jinja2 templates
├── static/                   # css / js / logo
├── database/                 # SQLite file is created here at runtime
├── tests/
│   └── test_app.py           # pytest suite (auth, CRUD, ML gate, reminders)
└── docs/
    ├── ARCHITECTURE.md       # architecture diagram + module responsibilities
    ├── ER_DIAGRAM.md         # ER diagram + data dictionary
    ├── TEST_CASES.md         # manual + automated test case catalogue
    ├── PROJECT_SUMMARY.md    # abstract, objectives, limitations, future work
    └── VIVA_DEMO_GUIDE.md    # step-by-step viva presentation script
```

## Testing

```bash
python -m pytest tests/ -v
```

The suite covers registration/login, inventory CRUD, form validation, waste
logging, the **8-record ML training gate**, reminder generation and the recipe
recommender. See `docs/TEST_CASES.md` for the full catalogue.

## Pushing to GitHub

The repository was initialised with:

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/abi-techhub/food-wise.git
git push -u origin main
```

## Publishing (deployment)

- **Live web app**: see `DEPLOY.md` - step-by-step for Render (recommended
  free host), PythonAnywhere and Railway. The repo ships with a `Procfile`
  and `gunicorn`. Setting the environment variable `SEED_DEMO=1` on the host
  auto-seeds the viva demo data on first boot.
- **Public showcase site**: the `site/` folder is GitHub-Pages-ready.
  Repo → Settings → Pages → Deploy from branch → `main` → `/site` → Save,
  and the showcase goes live at `https://abi-techhub.github.io/food-wise/`.

## Documentation

- `docs/ARCHITECTURE.md` - system architecture and request flow
- `docs/ER_DIAGRAM.md` - entity-relationship diagram and data dictionary
- `docs/TEST_CASES.md` - test case catalogue
- `docs/PROJECT_SUMMARY.md` - abstract, objectives, limitations, future scope
- `docs/VIVA_DEMO_GUIDE.md` - 10-minute viva demonstration script

## Ethical notes

- Reminders are generated **only** from expiry dates the user actually entered.
- The model never claims that a date proves food is safe or unsafe to eat.
- Metrics are reported honestly (leave-one-out on small data) with a visible
  "estimates only" disclaimer in the UI.

## Author

Abirami - AI & Data Science mini-project.

## License

Released under the MIT License for educational use.
