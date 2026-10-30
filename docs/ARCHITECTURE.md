# FoodWise - System Architecture

## 1. High-level architecture

```
┌─────────────────────────────┐
│          Browser            │
│  Bootstrap 5 + Chart.js +   │
│  vanilla JS (script.js)     │
└──────────────┬──────────────┘
               │ HTTP (Jinja2-rendered pages, form posts)
┌──────────────▼───────────────────────────────────────────────┐
│                    Flask application                          │
│                                                               │
│  app.py  (create_app factory, landing route, login manager)   │
│     │                                                         │
│     ├── routes/auth.py          register / login / profile    │
│     ├── routes/food.py          dashboard, inventory, waste   │
│     ├── routes/recipes.py       recommender page              │
│     ├── routes/analytics.py     charts + ML panel             │
│     ├── routes/notifications.py reminders + expiry checker    │
│     │                                                         │
│     ├── ml/consumption_model.py   gated Ridge regression      │
│     ├── ml/recommendation.py      ingredient matching         │
│     │                                                         │
│  models.py  (SQLAlchemy ORM - 5 tables)                       │
│     │                                                         │
│  APScheduler  ── runs run_expiry_check() every 12 hours       │
└──────────────┬───────────────────────────────────────────────┘
               │ SQLAlchemy
┌──────────────▼──────────────┐
│   SQLite database/          │
│   foodwise.db               │
│   users, food_items,        │
│   notifications, food_waste,│
│   recipes                   │
└─────────────────────────────┘
```

## 2. Module responsibilities

| Module | Responsibility |
| --- | --- |
| `app.py` | Application factory, blueprint registration, login manager, template globals (unread badge), starter recipe seeding, background scheduler |
| `config.py` | Central configuration: secret key, DB URI, `REMINDER_DAYS_BEFORE = 3`, `ML_TRAINING_THRESHOLD = 8` |
| `models.py` | The 5 ORM models + shared choice lists + derived properties (`days_to_expiry`, `status`, `utilisation_ratio`) |
| `routes/auth.py` | Registration with validation, login (username or email), logout, profile, change password |
| `routes/food.py` | Dashboard aggregation, inventory listing with filters, add/edit/delete, waste reporting, mark-as-consumed |
| `routes/recipes.py` | Passes inventory + catalogue to the recommender, applies search filter |
| `routes/analytics.py` | Aggregates waste data for Chart.js, computes ML status and per-item predictions |
| `routes/notifications.py` | Reminder list UI and `run_expiry_check()` (shared by scheduler and manual button) |
| `ml/consumption_model.py` | Builds the training frame, trains Ridge with LOO-CV metrics, predicts effective expiry per item |
| `ml/recommendation.py` | Normalises names, matches inventory to recipe ingredients, scores and sorts recipes |

## 3. Request flow (example: reporting waste)

```
User clicks waste icon
  -> GET  /food/<id>/waste            routes/food.py renders report_waste.html
  -> POST /food/<id>/waste            validates quantity + reason
     -> creates FoodWaste row with snapshot fields
        (category, shelf_life_days, days_held)  <- ML training data
     -> marks related unread reminders as read
     -> deletes the FoodItem
     -> flash "logged as waste ... ML progress: n/8"
  -> next dashboard/analytics render calls ml.train_model()
     -> below 8 records: "Not trained yet" panel
     -> at 8+: Ridge trained, predictions shown
```

## 4. ML pipeline

```
FoodWaste records (per user)
   │  snapshot: category, quantity, shelf_life_days, days_held
   ▼
utilisation_ratio = days_held / shelf_life_days      (target, clipped 0..1.5)
   │
   ▼
Features: [quantity, shelf_life_days, one-hot(category)]   (8 columns)
   │
   ├── records < 8            -> model=None, UI shows "Not trained yet" (n/8)
   └── records >= 8           -> Ridge(alpha=1.0)
                                 metrics via LeaveOneOut CV: MAE, R²
                                 per active item:
                                   predicted_date = purchase_date + ratio x shelf_life
                                   at-risk if predicted_date <= min(expiry, today+7)
```

## 5. Design decisions

1. **Snapshot columns on `food_waste`** - training history survives even after
   the food item (or its reminders) is deleted.
2. **App-factory pattern** - tests and the seeder create isolated apps with
   their own database; no global state leaks.
3. **Single shared expiry checker** - the scheduler and the manual button call
   the same `run_expiry_check()`, which de-duplicates unread reminders.
4. **Small-data-first ML** - Ridge regression with leave-one-out CV instead of
   deep learning: explainable, fast, and honest about uncertainty.
5. **Gate on real data** - the ML panel never fabricates predictions; it trains
   only on the user's own, actually logged waste events.
