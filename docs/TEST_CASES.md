# FoodWise - Test Case Catalogue

Automated cases are implemented in `tests/test_app.py` (pytest) and can be run
with `python -m pytest tests/ -v`. Status shown = result of the final run
before delivery.

## TC01 - Register a new account (PASS - automated `test_register_login_logout`)

Steps: open /register, submit username `abirami`, valid email, password 6+ chars.
Expected: account created, redirected to /login, success flash shown.

## TC02 - Register with an already-used email (PASS - automated `test_register_rejects_duplicate_email`)

Steps: register twice with the same email.
Expected: second attempt rejected with "An account with that email already exists."

## TC03 - Login with wrong password (PASS - automated `test_login_rejects_wrong_password`)

Expected: "Invalid username/email or password." message, user stays on login page.

## TC04 - Login with valid credentials (PASS - automated `test_register_login_logout`)

Expected: redirected to dashboard, username visible in navbar.

## TC05 - Dashboard requires authentication (PASS - automated `test_dashboard_requires_login`)

Expected: anonymous request to /dashboard redirects to /login.

## TC06 - Add a food item (PASS - automated `test_add_edit_delete_food`)

Steps: /food/add with name, category, quantity, unit, purchase and expiry dates.
Expected: item appears in inventory with correct status badge.

## TC07 - Reject expiry date before purchase date (PASS - automated `test_add_food_rejects_expiry_before_purchase`)

Expected: validation error "Expiry date cannot be before the purchase date."

## TC08 - Edit a food item (PASS - automated `test_add_edit_delete_food`)

Expected: renamed item ("Fresh Milk") appears in inventory after saving.

## TC09 - Delete a food item (PASS - automated `test_add_edit_delete_food`)

Expected: confirmation dialog; item removed from inventory and database.

## TC10 - Report waste creates a training record (PASS - automated `test_waste_record_created_and_item_removed`)

Steps: open waste form, confirm quantity + reason, submit.
Expected: FoodWaste row created with snapshot fields (shelf_life_days=15,
days_held=10, category=Dairy); item removed from inventory.

## TC11 - ML gate: untrained below 8 records (PASS - automated `test_ml_gate_trains_only_after_8_waste_records`)

Steps: log exactly 7 waste records, open /analytics.
Expected: "Not trained yet" badge with a 7/8 progress bar; no predictions table.

## TC12 - ML gate: trains at the 8th record (PASS - automated `test_ml_gate_trains_only_after_8_waste_records`)

Steps: log the 8th waste record, reopen /analytics.
Expected: "Trained" badge with record count and metrics; predictions table for
active items appears.

## TC13 - Unit check of the training gate (PASS - automated `test_train_model_unit_level_gate`)

Expected: `train_model([])` returns status `untrained`; 8 records return
`trained` with `records == 8`.

## TC14 - Reminder generated for expiring item (PASS - automated `test_expiry_check_creates_notification`)

Steps: add an item expiring in 2 days, run `run_expiry_check()`.
Expected: notification created mentioning the item; a second run creates
**zero** new reminders (deduplication by unread reminder).

## TC15 - Recipe catalogue displayed (PASS - automated `test_recipes_page_lists_catalogue`)

Expected: /recipes lists seeded recipes such as "Veggie Stir Fry".

## TC16 - Recipe ranking uses inventory and expiry (PASS - automated `test_recipe_recommendation_matches_inventory`)

Steps: add "Milk" expiring tomorrow, call `recommend_recipes()`.
Expected: "Milk Smoothie" matched >= 50%, flagged `uses_expiring`, and results
sorted by score descending.

## TC17 - Change password flow (PASS - automated `test_change_password`)

Expected: wrong current password rejected; correct change succeeds; login works
with the new password.

## Manual smoke checks (for the viva)

| # | Check | Expected |
| --- | --- | --- |
| M1 | `python seed_demo.py` then login as demo_user | Dashboard shows 11 items, ML panel "Trained" (10 records) |
| M2 | Fresh registration | ML panel shows 0/8 progress bar, "Not trained yet" |
| M3 | Reminders page, "Run check now" | Reminder count matches items within 3 days of expiry |
| M4 | Inventory filters (search/category/status) | Table narrows correctly, sort works |
| M5 | Analytics charts | Doughnut/bar charts render from real waste rows only |
| M6 | Resize window to mobile width | Navbar collapses; tables scroll horizontally |
