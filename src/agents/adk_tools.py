"""Google ADK Tool Definitions for NutriConcierge.

Defines deterministic, typed tool functions accessible by Google ADK Agents.
"""

from typing import Any, Dict, List, Optional

from src.memory.user_store import UserStore
from src.models.schemas import (
    CommonAllergen,
    DietaryRestriction,
    Ingredient,
    MealFeedback,
    MealType,
    NutritionInfo,
    Recipe,
)
from src.tools.allergen_checker import AllergenSafetyCheckerTool
from src.tools.grocery_exporter import GroceryCartExporterTool
from src.tools.nutrition_analyzer import NutritionAnalyzerTool
from src.tools.pantry_tool import PantryInventoryTool
from src.tools.recipe_tool import RecipeTool

# Singleton tool instances
_user_store = UserStore()
_recipe_tool = RecipeTool()
_allergen_checker = AllergenSafetyCheckerTool()
_pantry_tool = PantryInventoryTool()
_grocery_exporter = GroceryCartExporterTool(pantry_tool=_pantry_tool)
_nutrition_analyzer = NutritionAnalyzerTool()


def set_global_user_store(store: UserStore) -> None:
    """Set the active user store for tool functions."""
    global _user_store, _pantry_tool, _grocery_exporter
    _user_store = store
    pantry_items = store.get_pantry("default_user")
    _pantry_tool = PantryInventoryTool(initial_items=pantry_items)
    _grocery_exporter = GroceryCartExporterTool(pantry_tool=_pantry_tool)


def get_user_profile(user_id: str = "default_user") -> Dict[str, Any]:
    """Retrieve the current user's profile, including dietary restrictions, strict allergens, household size, and calorie targets.

    Args:
        user_id: The unique ID of the user.

    Returns:
        Dictionary containing user profile information.
    """
    profile = _user_store.get_profile(user_id)
    return profile.model_dump()


def update_user_profile(
    user_id: str = "default_user",
    allergens: Optional[List[str]] = None,
    dietary_restrictions: Optional[List[str]] = None,
    household_size: Optional[int] = None,
    daily_calorie_target: Optional[int] = None,
) -> Dict[str, Any]:
    """Update user dietary preferences, allergens, household size, or calorie goals.

    Args:
        user_id: The unique ID of the user.
        allergens: Optional list of allergens to avoid (e.g. ['peanuts', 'shellfish', 'milk']).
        dietary_restrictions: Optional list of dietary patterns (e.g. ['vegan', 'gluten_free', 'keto']).
        household_size: Optional number of people in the household to cook for.
        daily_calorie_target: Optional daily caloric target in kcal.

    Returns:
        Updated user profile dictionary.
    """
    profile = _user_store.get_profile(user_id)
    if allergens is not None:
        profile.allergens = [CommonAllergen(a) for a in allergens if a in [e.value for e in CommonAllergen]]
    if dietary_restrictions is not None:
        profile.dietary_restrictions = [
            DietaryRestriction(d) for d in dietary_restrictions if d in [e.value for e in DietaryRestriction]
        ]
    if household_size is not None:
        profile.household_size = max(1, household_size)
    if daily_calorie_target is not None:
        profile.macro_targets.calories = daily_calorie_target

    _user_store.save_profile(profile)
    return profile.model_dump()


def get_pantry_inventory(user_id: str = "default_user") -> List[Dict[str, Any]]:
    """Retrieve all tracked ingredients currently on hand in the user's pantry and refrigerator.

    Args:
        user_id: The unique ID of the user.

    Returns:
        List of pantry item dictionaries with name, quantity, unit, and expiration status.
    """
    items = _user_store.get_pantry(user_id)
    return [i.model_dump() for i in items]


def search_recipes(
    query: Optional[str] = None,
    meal_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search the culinary recipe database for dishes matching keywords, ingredients, meal types, or dietary tags.

    Args:
        query: Search keywords or ingredients (e.g. 'spinach', 'salmon', 'quinoa', 'oats', 'chicken').
        meal_type: Optional meal category ('breakfast', 'lunch', 'dinner', 'snack').
        tags: Optional dietary tags (e.g. ['vegan', 'gluten_free', 'high_protein']).

    Returns:
        List of matching recipe dictionaries with ingredients, nutrition, and preparation steps.
    """
    mt = MealType(meal_type.lower()) if meal_type else None
    results = _recipe_tool.search_recipes(query=query, meal_type=mt, tags=tags)
    return [r.model_dump() for r in results]


def scale_recipe_portions(recipe_id: str, target_servings: int) -> Dict[str, Any]:
    """Scale ingredient quantities of a recipe based on target household size or number of servings.

    Args:
        recipe_id: The ID of the recipe to scale (e.g. 'rec_001', 'rec_007').
        target_servings: The number of servings to scale to.

    Returns:
        Scaled recipe dictionary.
    """
    all_recipes = _recipe_tool.get_all_recipes()
    matched = next((r for r in all_recipes if r.id == recipe_id or r.id.startswith(recipe_id)), None)
    if not matched:
        return {"error": f"Recipe '{recipe_id}' not found"}
    scaled = _recipe_tool.scale_recipe(matched, target_servings)
    return scaled.model_dump()


def verify_recipe_safety(
    recipe_title: str,
    ingredients: List[str],
    user_id: str = "default_user",
) -> Dict[str, Any]:
    """Verify that a candidate recipe is 100% compliant with the user's strict allergen restrictions and dietary rules.

    Args:
        recipe_title: Title of the recipe.
        ingredients: List of ingredient names included in the recipe.
        user_id: The unique ID of the user.

    Returns:
        Dictionary indicating is_safe (boolean), allergen conflicts, dietary violations, and explanation.
    """
    profile = _user_store.get_profile(user_id)
    mock_recipe = Recipe(
        id="safety_eval",
        title=recipe_title,
        description="Safety verification",
        meal_type="dinner",  # type: ignore
        ingredients=[
            Ingredient(name=ing, quantity=100.0, unit="g", category="Pantry")
            for ing in ingredients
        ],
        instructions=[],
        nutrition=NutritionInfo(),
    )
    check = _allergen_checker.check_recipe_safety(mock_recipe, profile)
    from src.observability.tracing import metrics
    metrics.record_safety_check(check.is_safe)
    return check.model_dump()


def calculate_ingredient_nutrition(ingredient_name: str, quantity_g: float = 100.0) -> Dict[str, Any]:
    """Look up nutritional macronutrients and calories for an ingredient.

    Args:
        ingredient_name: The name of the food ingredient (e.g. 'salmon fillet', 'spinach', 'chicken breast', 'quinoa').
        quantity_g: Weight in grams (defaults to 100g).

    Returns:
        Dictionary of calories, protein, carbs, fat, fiber, and sodium.
    """
    ing = Ingredient(name=ingredient_name, quantity=quantity_g, unit="g")
    nut = _nutrition_analyzer.calculate_ingredient_nutrition(ing)
    return nut.model_dump()


def generate_grocery_list_for_recipes(recipe_ids: List[str], user_id: str = "default_user") -> Dict[str, Any]:
    """Reconcile required recipe ingredients against on-hand pantry inventory and produce an aisle-categorized shopping cart.

    Args:
        recipe_ids: List of recipe IDs to purchase ingredients for.
        user_id: The unique ID of the user.

    Returns:
        Dictionary containing categorized items to buy, items already on hand, and total estimated cost.
    """
    all_recipes = _recipe_tool.get_all_recipes()
    selected_recipes = [r for r in all_recipes if r.id in recipe_ids or any(r.id.startswith(rid) for rid in recipe_ids)]
    if not selected_recipes:
        selected_recipes = all_recipes[:3]

    g_list = _grocery_exporter.generate_grocery_list(selected_recipes, user_id=user_id)
    md = _grocery_exporter.format_markdown(g_list)
    result = g_list.model_dump()
    result["markdown_view"] = md
    return result


def record_meal_rating(recipe_id: str, rating: int, comments: str, user_id: str = "default_user") -> Dict[str, Any]:
    """Record user feedback and 1-5 star rating for a prepared recipe to refine future recommendations.

    Args:
        recipe_id: ID of the recipe rated.
        rating: Integer rating from 1 to 5 stars.
        comments: Text feedback or notes.
        user_id: The unique ID of the user.

    Returns:
        Confirmation status.
    """
    all_recipes = _recipe_tool.get_all_recipes()
    matched = next((r for r in all_recipes if r.id == recipe_id or r.id.startswith(recipe_id)), None)
    title = matched.title if matched else "Prepared Recipe"

    feedback = MealFeedback(
        recipe_id=recipe_id,
        recipe_title=title,
        rating=rating,
        comments=comments,
    )
    _user_store.record_feedback(feedback, user_id=user_id)
    return {"status": "success", "recorded_rating": rating, "recipe_title": title}
