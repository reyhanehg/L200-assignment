"""Nutrition Analyzer Tool.

Calculates calories, macronutrients, and micronutrients for ingredients and recipes
using standard nutritional references.
"""

from typing import Any, Dict, List, Optional
from src.models.schemas import Ingredient, MacroTarget, NutritionInfo, Recipe


# Standard nutritional reference per 100g or standard unit
NUTRITION_DATABASE: Dict[str, Dict[str, float]] = {
    # Proteins & Meats
    "chicken breast": {"calories": 165, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "fiber_g": 0.0, "sodium_mg": 74},
    "salmon fillet": {"calories": 208, "protein_g": 20.0, "carbs_g": 0.0, "fat_g": 13.0, "fiber_g": 0.0, "sodium_mg": 59},
    "ground turkey": {"calories": 149, "protein_g": 22.0, "carbs_g": 0.0, "fat_g": 6.8, "fiber_g": 0.0, "sodium_mg": 70},
    "lean ground beef": {"calories": 218, "protein_g": 24.0, "carbs_g": 0.0, "fat_g": 13.0, "fiber_g": 0.0, "sodium_mg": 72},
    "tofu": {"calories": 76, "protein_g": 8.0, "carbs_g": 1.9, "fat_g": 4.8, "fiber_g": 0.3, "sodium_mg": 7},
    "tempeh": {"calories": 192, "protein_g": 20.3, "carbs_g": 7.6, "fat_g": 10.8, "fiber_g": 0.0, "sodium_mg": 9},
    "eggs": {"calories": 143, "protein_g": 12.6, "carbs_g": 0.7, "fat_g": 9.5, "fiber_g": 0.0, "sodium_mg": 142},
    "egg whites": {"calories": 52, "protein_g": 11.0, "carbs_g": 0.7, "fat_g": 0.2, "fiber_g": 0.0, "sodium_mg": 166},
    "canned black beans": {"calories": 91, "protein_g": 6.0, "carbs_g": 16.0, "fat_g": 0.4, "fiber_g": 5.5, "sodium_mg": 240},
    "chickpeas": {"calories": 164, "protein_g": 8.9, "carbs_g": 27.4, "fat_g": 2.6, "fiber_g": 7.6, "sodium_mg": 24},
    "lentils": {"calories": 116, "protein_g": 9.0, "carbs_g": 20.0, "fat_g": 0.4, "fiber_g": 7.9, "sodium_mg": 2},
    "shrimp": {"calories": 99, "protein_g": 24.0, "carbs_g": 0.2, "fat_g": 0.3, "fiber_g": 0.0, "sodium_mg": 111},

    # Grains & Carbohydrates
    "quinoa": {"calories": 120, "protein_g": 4.4, "carbs_g": 21.3, "fat_g": 1.9, "fiber_g": 2.8, "sodium_mg": 7},
    "brown rice": {"calories": 112, "protein_g": 2.3, "carbs_g": 23.5, "fat_g": 0.8, "fiber_g": 1.6, "sodium_mg": 5},
    "white rice": {"calories": 130, "protein_g": 2.7, "carbs_g": 28.2, "fat_g": 0.3, "fiber_g": 0.4, "sodium_mg": 1},
    "rolled oats": {"calories": 389, "protein_g": 16.9, "carbs_g": 66.3, "fat_g": 6.9, "fiber_g": 10.6, "sodium_mg": 2},
    "whole wheat bread": {"calories": 247, "protein_g": 13.0, "carbs_g": 41.0, "fat_g": 3.4, "fiber_g": 6.0, "sodium_mg": 450},
    "sweet potato": {"calories": 86, "protein_g": 1.6, "carbs_g": 20.1, "fat_g": 0.1, "fiber_g": 3.0, "sodium_mg": 55},
    "russet potato": {"calories": 77, "protein_g": 2.0, "carbs_g": 17.5, "fat_g": 0.1, "fiber_g": 2.2, "sodium_mg": 6},
    "whole wheat pasta": {"calories": 124, "protein_g": 5.3, "carbs_g": 26.5, "fat_g": 0.5, "fiber_g": 3.9, "sodium_mg": 4},

    # Vegetables & Greens
    "spinach": {"calories": 23, "protein_g": 2.9, "carbs_g": 3.6, "fat_g": 0.4, "fiber_g": 2.2, "sodium_mg": 79},
    "kale": {"calories": 49, "protein_g": 4.3, "carbs_g": 8.8, "fat_g": 0.9, "fiber_g": 3.6, "sodium_mg": 38},
    "broccoli": {"calories": 34, "protein_g": 2.8, "carbs_g": 6.6, "fat_g": 0.4, "fiber_g": 2.6, "sodium_mg": 33},
    "bell pepper": {"calories": 31, "protein_g": 1.0, "carbs_g": 6.0, "fat_g": 0.3, "fiber_g": 2.1, "sodium_mg": 4},
    "onion": {"calories": 40, "protein_g": 1.1, "carbs_g": 9.3, "fat_g": 0.1, "fiber_g": 1.7, "sodium_mg": 4},
    "garlic": {"calories": 149, "protein_g": 6.4, "carbs_g": 33.1, "fat_g": 0.5, "fiber_g": 2.1, "sodium_mg": 17},
    "avocado": {"calories": 160, "protein_g": 2.0, "carbs_g": 8.5, "fat_g": 14.7, "fiber_g": 6.7, "sodium_mg": 7},
    "cucumber": {"calories": 15, "protein_g": 0.7, "carbs_g": 3.6, "fat_g": 0.1, "fiber_g": 0.5, "sodium_mg": 2},
    "tomato": {"calories": 18, "protein_g": 0.9, "carbs_g": 3.9, "fat_g": 0.2, "fiber_g": 1.2, "sodium_mg": 5},
    "zucchini": {"calories": 17, "protein_g": 1.2, "carbs_g": 3.1, "fat_g": 0.3, "fiber_g": 1.0, "sodium_mg": 8},
    "asparagus": {"calories": 20, "protein_g": 2.2, "carbs_g": 3.9, "fat_g": 0.1, "fiber_g": 2.1, "sodium_mg": 2},

    # Fruits
    "banana": {"calories": 89, "protein_g": 1.1, "carbs_g": 22.8, "fat_g": 0.3, "fiber_g": 2.6, "sodium_mg": 1},
    "blueberries": {"calories": 57, "protein_g": 0.7, "carbs_g": 14.5, "fat_g": 0.3, "fiber_g": 2.4, "sodium_mg": 1},
    "apple": {"calories": 52, "protein_g": 0.3, "carbs_g": 13.8, "fat_g": 0.2, "fiber_g": 2.4, "sodium_mg": 1},
    "strawberries": {"calories": 32, "protein_g": 0.7, "carbs_g": 7.7, "fat_g": 0.3, "fiber_g": 2.0, "sodium_mg": 1},

    # Dairy & Plant Milks
    "greek yogurt": {"calories": 97, "protein_g": 10.0, "carbs_g": 3.6, "fat_g": 5.0, "fiber_g": 0.0, "sodium_mg": 36},
    "almond milk": {"calories": 15, "protein_g": 0.5, "carbs_g": 0.3, "fat_g": 1.2, "fiber_g": 0.2, "sodium_mg": 70},
    "whole milk": {"calories": 61, "protein_g": 3.2, "carbs_g": 4.8, "fat_g": 3.3, "fiber_g": 0.0, "sodium_mg": 43},
    "cheddar cheese": {"calories": 403, "protein_g": 25.0, "carbs_g": 1.3, "fat_g": 33.0, "fiber_g": 0.0, "sodium_mg": 621},
    "parmesan cheese": {"calories": 431, "protein_g": 38.0, "carbs_g": 4.1, "fat_g": 29.0, "fiber_g": 0.0, "sodium_mg": 1529},
    "feta cheese": {"calories": 264, "protein_g": 14.2, "carbs_g": 4.1, "fat_g": 21.3, "fiber_g": 0.0, "sodium_mg": 917},

    # Nuts, Seeds, & Oils
    "olive oil": {"calories": 884, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0, "fiber_g": 0.0, "sodium_mg": 2},
    "almonds": {"calories": 579, "protein_g": 21.2, "carbs_g": 21.6, "fat_g": 49.9, "fiber_g": 12.5, "sodium_mg": 1},
    "walnuts": {"calories": 654, "protein_g": 15.2, "carbs_g": 13.7, "fat_g": 65.2, "fiber_g": 6.7, "sodium_mg": 2},
    "peanut butter": {"calories": 588, "protein_g": 25.0, "carbs_g": 20.0, "fat_g": 50.0, "fiber_g": 6.0, "sodium_mg": 429},
    "chia seeds": {"calories": 486, "protein_g": 16.5, "carbs_g": 42.1, "fat_g": 30.7, "fiber_g": 34.4, "sodium_mg": 16},
}


class NutritionAnalyzerTool:
    """Tool for analyzing nutritional contents and evaluating macro targets."""

    def __init__(self, database: Optional[Dict[str, Dict[str, float]]] = None):
        self.db = database or NUTRITION_DATABASE

    def _normalize_name(self, name: str) -> str:
        """Find the closest standard ingredient in the database."""
        name_lower = name.lower().strip()
        for key in self.db:
            if key in name_lower or name_lower in key:
                return key
        return name_lower

    def calculate_ingredient_nutrition(self, ingredient: Ingredient) -> NutritionInfo:
        """Calculate nutritional breakdown for a single ingredient."""
        key = self._normalize_name(ingredient.name)
        base = self.db.get(key)
        if not base:
            # Default approximation if exact ingredient is not in the db
            return NutritionInfo(
                calories=50.0,
                protein_g=2.0,
                carbs_g=5.0,
                fat_g=2.0,
                fiber_g=1.0,
                sodium_mg=20.0,
            )

        # Standard multiplier: Assume quantity unit conversion
        unit = ingredient.unit.lower().strip()
        multiplier = 1.0

        if unit in ["g", "grams"]:
            multiplier = ingredient.quantity / 100.0
        elif unit in ["oz", "ounces"]:
            multiplier = (ingredient.quantity * 28.35) / 100.0
        elif unit in ["lbs", "pound", "pounds"]:
            multiplier = (ingredient.quantity * 453.59) / 100.0
        elif unit in ["cup", "cups"]:
            multiplier = (ingredient.quantity * 150.0) / 100.0
        elif unit in ["tbsp", "tablespoon", "tablespoons"]:
            multiplier = (ingredient.quantity * 15.0) / 100.0
        elif unit in ["tsp", "teaspoon", "teaspoons"]:
            multiplier = (ingredient.quantity * 5.0) / 100.0
        elif unit in ["count", "piece", "pieces", "item", "clove", "cloves"]:
            multiplier = (ingredient.quantity * 50.0) / 100.0

        return NutritionInfo(
            calories=round(base["calories"] * multiplier, 1),
            protein_g=round(base["protein_g"] * multiplier, 1),
            carbs_g=round(base["carbs_g"] * multiplier, 1),
            fat_g=round(base["fat_g"] * multiplier, 1),
            fiber_g=round(base.get("fiber_g", 0.0) * multiplier, 1),
            sodium_mg=round(base.get("sodium_mg", 0.0) * multiplier, 1),
        )

    def calculate_recipe_nutrition(self, recipe: Recipe) -> NutritionInfo:
        """Calculate aggregate nutrition per serving for a full recipe."""
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        total_sodium = 0.0

        for ing in recipe.ingredients:
            n = self.calculate_ingredient_nutrition(ing)
            total_calories += n.calories
            total_protein += n.protein_g
            total_carbs += n.carbs_g
            total_fat += n.fat_g
            total_fiber += n.fiber_g
            total_sodium += n.sodium_mg

        servings = max(1, recipe.servings)
        return NutritionInfo(
            calories=round(total_calories / servings, 1),
            protein_g=round(total_protein / servings, 1),
            carbs_g=round(total_carbs / servings, 1),
            fat_g=round(total_fat / servings, 1),
            fiber_g=round(total_fiber / servings, 1),
            sodium_mg=round(total_sodium / servings, 1),
        )

    def evaluate_macro_adherence(
        self, daily_total: NutritionInfo, target: MacroTarget
    ) -> Dict[str, Any]:
        """Evaluate how closely a day's nutrition matches the user's macro target."""
        cal_pct = round((daily_total.calories / max(1, target.calories)) * 100, 1)
        pro_pct = round((daily_total.protein_g / max(1.0, target.protein_g)) * 100, 1)
        carb_pct = round((daily_total.carbs_g / max(1.0, target.carbs_g)) * 100, 1)
        fat_pct = round((daily_total.fat_g / max(1.0, target.fat_g)) * 100, 1)
        fiber_pct = round((daily_total.fiber_g / max(1.0, target.fiber_g)) * 100, 1)

        is_within_tolerance = (
            abs(cal_pct - 100) <= 15.0
            and abs(pro_pct - 100) <= 20.0
            and (target.max_sodium_mg is None or daily_total.sodium_mg <= target.max_sodium_mg)
        )

        return {
            "within_target": is_within_tolerance,
            "calories_pct": cal_pct,
            "protein_pct": pro_pct,
            "carbs_pct": carb_pct,
            "fat_pct": fat_pct,
            "fiber_pct": fiber_pct,
            "sodium_limit_respected": (
                target.max_sodium_mg is None or daily_total.sodium_mg <= target.max_sodium_mg
            ),
        }
