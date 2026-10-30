"""Recipe recommendation routes."""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models import Recipe
from ml.recommendation import recommend_recipes

recipes_bp = Blueprint("recipes", __name__)


@recipes_bp.route("/recipes")
@login_required
def recipes():
    items = current_user.foods.all()
    catalogue = Recipe.query.order_by(Recipe.category, Recipe.recipe_name).all()
    recommendations = recommend_recipes(items, catalogue)

    query = request.args.get("q", "").strip().lower()
    if query:
        recommendations = [
            r for r in recommendations
            if query in r["recipe"].recipe_name.lower()
            or query in r["recipe"].category.lower()
            or any(query in ing for ing in
                   (r["recipe"].ingredients or "").lower().split(","))
        ]

    return render_template("recipes.html", recommendations=recommendations, q=query)
