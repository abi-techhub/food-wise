# FoodWise - Project Summary

## Abstract

FoodWise - Smart Food Expiry Predictor is a full-stack web application that
helps households reduce food waste. Users register an account, log the food
they buy (name, category, quantity, unit, purchase date, expiry date), and
receive automatic reminders before items expire. A recipe recommender suggests
dishes based on what is already in the kitchen, prioritising ingredients that
are close to expiry. Every item the user throws away is reported through a
guided waste form; these honest reports become the training data for a
machine-learning model that learns how much of the printed shelf life the
household typically uses and predicts which current items are most at risk of
being wasted. All analytics charts are rendered by Chart.js from real database
records - nothing is simulated.

## Objectives

1. Build a complete, runnable Flask application with authentication and
   per-user data isolation.
2. Track food inventory with clear visual statuses (green / orange / red).
3. Generate expiry reminders automatically (APScheduler) with de-duplication.
4. Recommend recipes from the user's actual inventory.
5. Collect waste events as ML training data and gate model training behind a
   minimum of 8 waste records so predictions are never fabricated.
6. Visualise waste patterns (category, month, reason) with Chart.js.

## Modules delivered

- **Authentication** - register / login / logout / change password; Werkzeug
  salted password hashes; Flask-Login session management.
- **Inventory management** - full CRUD with server-side validation (positive
  quantity, expiry >= purchase, bounded category/unit values), filters and
  sorting.
- **Expiry tracking & reminders** - background checker every 12 hours plus a
  manual "Run check now" button; unread badge in the navbar.
- **Recipe recommendation** - transparent ingredient-matching algorithm with a
  boost for recipes that rescue near-expiry items.
- **Waste analytics** - doughnut (category), bar (month), horizontal bar
  (reason) charts plus summary cards, all from live SQL aggregates.
- **Machine learning** - Ridge regression predicting the "utilisation ratio"
  (days held / shelf life) from category, quantity and shelf-life length;
  leave-one-out cross-validated metrics; per-item predicted waste dates and a
  priority-ranked risk table.

## The machine-learning design in one paragraph

Each waste report stores, as snapshots, how long the item survived
(`days_held`) relative to its printed shelf life (`shelf_life_days`). Their
ratio expresses the household's real behaviour: e.g. 0.8 means dairy is
typically thrown away after using 80% of the printed window. With fewer than 8
records the ML panel explicitly shows "Not trained yet (n/8)" and makes no
claims. At 8 records a Ridge regression trains on these ratios and the panel
switches to "Trained", reporting the average utilisation and its
leave-one-out error, and converting every active item's ratio into a predicted
waste date (`purchase_date + ratio x shelf_life`). Items whose predicted date
falls before the printed expiry - or within the next 7 days - are flagged as
at risk, highest urgency first.

## Testing

17 automated test cases (pytest) cover registration and login, duplicate
accounts, wrong passwords, protected routes, inventory CRUD, form validation,
waste snapshotting, the 8-record ML gate (both at the route level and unit
level), reminder generation and de-duplication, recipe ranking, and password
change. All passed before delivery; see `docs/TEST_CASES.md`.

## Limitations and ethical notes

- Predictions describe the user's own historical behaviour; they are estimates
  and **never** a claim that a date proves food is safe or unsafe to eat.
- The model is small-sample by design (Ridge + LOO-CV); R-squared is shown as
  "not meaningful" when the sample is too small for it to be honest.
- Reminders are generated only from expiry dates the user actually entered.
- The scheduler runs in-process; for production deployment a separate worker
  (e.g. cron or Celery beat) would be more robust.

## Future scope (optional extensions)

1. Email reminders (Flask-Mail) in addition to in-app notifications.
2. Food photo uploads for a more visual inventory.
3. Automatically generated PDF project/waste reports.
4. Per-user recipe learning (which suggestions were actually cooked).
5. Deployment hardening: Gunicorn + Nginx, environment-based secrets,
   PostgreSQL instead of SQLite.
