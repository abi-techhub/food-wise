# FoodWise - Viva Demonstration Guide

A ready-to-run 10 minute script for presenting FoodWise with demo data.

## Before the viva (one-time, ~3 minutes)

```bash
cd food-wise
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py             # creates the demo account + data
python app.py                   # keep it running on http://127.0.0.1:5000
```

Login card on the login page shows the demo credentials:
`demo_user` / `Demo@123`.

## Demo script

### 1. Landing page (1 min)

Open `http://127.0.0.1:5000` **logged out**. Present the hero and the four
feature cards. Key sentence: "Everything you will see is computed from real
database records - no mock data in the charts."

### 2. Dashboard with demo data (2 min)

Log in as `demo_user`. Point out:

- **Stat cards**: 11 items in stock, several expiring within 3 days, one
  expired, 10 waste records.
- **Needs attention table**: orange "Expiring soon" and red "Expired" badges -
  statuses are derived live from today's date.
- **ML insight card**: badge **Trained**, average shelf life used, error
  estimate, and the at-risk item list. Explain the gate: "this only appears
  after 8 honest waste reports."
- **Inventory doughnut**: per-category counts from the database.

### 3. Inventory & waste reporting (2.5 min)

- Open **Inventory**. Show filters (search "milk", status "Expiring soon") and
  the expiry countdown column.
- Click the **waste icon** on any item. Walk through the form: quantity,
  reason, and the "ML progress" note. Submit it.
- Emphasise: "The item is removed and a snapshot row is stored - how long the
  item actually survived relative to its printed shelf life. That ratio is the
  ML target."
- Also click the green check on another item to show the no-waste path.

### 4. Analytics (2 min)

- Charts: waste by **category** (doughnut), by **month** (bar), by **reason**
  (horizontal bar) - all from real rows.
- **ML panel**: Ridge regression, trained on 10 records, leave-one-out error
  and the small-sample disclaimer.
- **Predictions table**: printed expiry vs predicted waste date, utilisation
  ratio, priority badges. Explain one row end-to-end.

### 5. The training gate with a fresh account (1.5 min)

- Log out, **Register** a brand-new account.
- Open **Analytics**: the ML panel shows **"Not trained yet"** with a 0/8
  progress bar and no predictions - the gate working as designed.
- (Optional) Add one item and report it as waste: the bar moves to 1/8.

### 6. Recipes + reminders (1 min)

- **Recipes**: matches for the demo inventory; note the "Uses an expiring
  item" badge and the green/grey ingredient chips.
- **Reminders**: click **Run check now** - new reminders appear for anything
  within 3 days of expiry; badge count in the navbar updates.

## Likely questions & answers

| Question | Answer |
| --- | --- |
| Why 8 records before training? | Below that any regression would overfit and produce misleading confidence; the gate guarantees a minimum sample. |
| Why predict a "utilisation ratio" instead of expiry directly? | The ratio normalises different shelf lives (milk 7 days vs rice 300 days) into one comparable behavioural target. |
| Why Ridge regression and not a neural network? | Tiny data, full explainability, deterministic training, and honest cross-validated metrics. |
| Why leave-one-out cross validation? | With 8-20 rows a single train/test split would be meaningless; LOO uses every row exactly once as a test case. |
| Where does the training data come from? | Only from waste reports the user actually submitted - snapshot columns survive item deletion. |
| Can the app say food is safe to eat? | No. Dates are user-entered and predictions are behavioural estimates; the UI states this explicitly. |

## Resetting the demo

`python seed_demo.py --fresh` wipes and rebuilds everything (relative to the
current date, so statuses always look correct).
