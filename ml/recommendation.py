"""Recipe recommender: matches inventory items against recipe ingredients.

This is a transparent ingredient-matching algorithm (kept deliberately simple
for an academic mini-project). It is structured so a real ML recommender can
replace `recommend_recipes()` later without touching the routes.
"""


def _norm(text):
    return (text or "").strip().lower()


def recommend_recipes(items, recipes):
    """Rank recipes by how much of the user's inventory they use.

    Parameters
    ----------
    items    : list of FoodItem currently in the user's inventory
    recipes  : list of Recipe from the shared catalogue

    Returns
    -------
    list of dicts with keys:
        recipe        - the Recipe object
        matched       - [(ingredient, FoodItem), ...] ingredients you have
        missing       - [ingredient, ...] still to buy
        match_pct     - % of ingredients matched
        uses_expiring - True if a matched item expires within 3 days
        score         - match_pct + bonus for near-expiry items (sorting only)
    """
    inventory = {_norm(i.food_name): i for i in items}
    results = []

    for recipe in recipes:
        ingredients = recipe.ingredient_list()
        if not ingredients:
            continue

        matched, missing, uses_expiring = [], [], False
        for ing in ingredients:
            hit = None
            for inv_name, item in inventory.items():
                if inv_name in ing or ing in inv_name:  # "milk" ~ "milk powder"
                    hit = item
                    break
            if hit is not None:
                matched.append((ing, hit))
                if hit.status == "near":  # only fresh-but-urgent items
                    uses_expiring = True
            else:
                missing.append(ing)

        match_pct = round(100.0 * len(matched) / len(ingredients))
        score = match_pct / 100.0
        if uses_expiring:
            score += 0.15  # gently push waste-saving recipes to the top

        results.append({
            "recipe": recipe,
            "matched": matched,
            "missing": missing,
            "match_pct": match_pct,
            "uses_expiring": uses_expiring,
            "score": score,
        })

    results.sort(key=lambda r: (-r["score"], r["recipe"].recipe_name.lower()))
    return results
