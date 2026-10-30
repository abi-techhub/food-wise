# FoodWise - Entity Relationship Diagram

## 1. ER diagram (Mermaid)

```mermaid
erDiagram
    USERS ||--o{ FOOD_ITEMS     : "owns"
    USERS ||--o{ NOTIFICATIONS  : "receives"
    USERS ||--o{ FOOD_WASTE     : "reports"
    FOOD_ITEMS ||--o{ FOOD_WASTE : "was wasted as (snapshot kept)"
    FOOD_ITEMS ||--o{ NOTIFICATIONS : "triggered"

    USERS {
        int id PK
        string username UK "unique, not null"
        string email UK "unique, not null"
        string password_hash "werkzeug salted hash"
        datetime created_at
    }
    FOOD_ITEMS {
        int id PK
        int user_id FK
        string food_name "max 120 chars"
        string category "Fruits|Vegetables|Dairy|Meat|Grains|Other"
        float quantity "> 0"
        string unit "pcs|kg|g|L|ml|pack|bottle"
        date purchase_date "not null"
        date expiry_date ">= purchase_date"
        datetime created_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        int food_id FK "nullable"
        string message "max 255 chars"
        datetime notification_date
        bool is_read "default false"
    }
    FOOD_WASTE {
        int id PK
        int user_id FK
        int food_id FK "nullable after item deletion"
        string food_name_snapshot
        string category_snapshot
        float wasted_quantity
        string reason "Expired|Spoiled|Over-purchased|Not used in time|Other"
        date waste_date
        int shelf_life_days "ML snapshot"
        int days_held "ML snapshot"
    }
    RECIPES {
        int id PK
        string recipe_name
        text ingredients "comma separated"
        text instructions
        string category "Breakfast|Lunch|Dinner|Snack|Dessert"
    }
```

## 2. Relationship summary

| Relationship | Cardinality | Notes |
| --- | --- | --- |
| users → food_items | 1 : N | `ON DELETE CASCADE` via SQLAlchemy `delete-orphan` |
| users → notifications | 1 : N | cascade with the user |
| users → food_waste | 1 : N | cascade with the user |
| food_items → food_waste | 1 : N | waste rows **survive** item deletion thanks to snapshot columns (ML history is preserved) |
| food_items → notifications | 1 : N | reminder rows reference the item; unread ones are closed when the item is removed |
| recipes | standalone | shared catalogue, seeded on first run, no user link |

## 3. Derived (non-stored) fields

| Model | Property | Definition |
| --- | --- | --- |
| FoodItem | `days_to_expiry` | `expiry_date - today` (negative = expired) |
| FoodItem | `status` | `expired` if `< 0`, `near` if `<= 3`, else `safe` |
| FoodWaste | `utilisation_ratio` | `days_held / shelf_life_days`, clipped to 0..1.5 |
| Recipe | `ingredient_list()` | splits the comma-separated ingredients text |

## 4. Data dictionary notes

- `password_hash` - generated with Werkzeug's `generate_password_hash`
  (salted PBKDF2 by default); plain passwords are never stored.
- `shelf_life_days` = `expiry_date - purchase_date` copied at waste time.
- `days_held` = `waste_date - purchase_date` copied at waste time; together
  with `shelf_life_days` it forms the ML target
  `utilisation_ratio = days_held / shelf_life_days`.
- `ML_TRAINING_THRESHOLD = 8` (config.py) gates model training on the count of
  `food_waste` rows per user.
