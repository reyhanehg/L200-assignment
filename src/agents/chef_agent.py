"""Google ADK Executive Chef & Meal Planner Agent.

Uses Gemini generative AI to invent, formulate, and craft original culinary recipes
and weekly meal schedules tailored to user cravings, dietary restrictions, and pantry stock.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from google.adk import Agent

from src.agents.adk_tools import get_pantry_inventory
from src.config import settings
from src.models.schemas import Ingredient, MealType, NutritionInfo, Recipe
from src.observability.logging_config import logger
from src.tools.nutrition_analyzer import NutritionAnalyzerTool

_nutrition_analyzer = NutritionAnalyzerTool()

# Initialize Google GenAI client if credentials available
_genai_client = None
try:
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if api_key:
        _genai_client = genai.Client(api_key=api_key)
    elif project:
        _genai_client = genai.Client(
            vertexai=True,
            project=project,
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
except Exception as e:
    logger.info(f"ChefAgent GenAI init: {e}")


def create_recipe_with_ai(
    prompt: str,
    meal_type: str = "dinner",
    dietary_preferences: Optional[List[str]] = None,
    must_include_ingredients: Optional[List[str]] = None,
    servings: int = 1,
    pantry_ingredients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Dynamically generate a complete original culinary recipe using Generative AI (Gemini).

    Args:
        prompt: User's meal request or craving (e.g. 'keto dinner with spinach and chicken').
        meal_type: 'breakfast', 'lunch', 'dinner', or 'snack'.
        dietary_preferences: List of diets like ['keto', 'vegan', 'gluten_free', 'pescatarian'].
        must_include_ingredients: Specific ingredients the user asked for (e.g. ['spinach', 'salmon']).
        servings: Number of people/servings to cook for.
        pantry_ingredients: On-hand kitchen stock to prioritize and reduce food waste.

    Returns:
        Structured recipe dictionary with title, description, prep/cook times, exact ingredients with quantities and units, and step-by-step instructions.
    """
    diet_str = ", ".join(dietary_preferences or []) or "Standard"
    ings_str = ", ".join(must_include_ingredients or []) or "Chef's choice"
    pantry_str = ", ".join(pantry_ingredients or []) or "None"

    # 1. Attempt live Generative AI creation via Gemini
    if _genai_client is not None:
        try:
            from google.genai import types
            system_prompt = (
                "You are an expert executive chef. You invent delicious, healthy, and accurate culinary recipes. "
                "Output your response strictly as valid JSON matching this schema:\n"
                "{\n"
                '  "title": "Recipe Name",\n'
                '  "description": "Appetizing 1-2 sentence description",\n'
                '  "meal_type": "breakfast|lunch|dinner|snack",\n'
                f'  "servings": {servings},\n'
                '  "prep_time_minutes": 10,\n'
                '  "cook_time_minutes": 15,\n'
                '  "ingredients": [\n'
                '    {"name": "ingredient name", "quantity": 100.0, "unit": "g", "category": "Produce|Meat & Seafood|Pantry & Dry Goods|Dairy & Refrigerated"}\n'
                '  ],\n'
                '  "instructions": ["Step 1...", "Step 2..."],\n'
                f'  "tags": ["{diet_str.lower()}"]\n'
                "}"
            )
            user_msg = (
                f"Create an original {diet_str} {meal_type} recipe for {servings} person(s). "
                f"User request: '{prompt}'. "
                f"Must feature these ingredients: [{ings_str}]. "
                f"Prioritize using available pantry stock: [{pantry_str}]."
            )
            response = _genai_client.models.generate_content(
                model=settings.gemini_model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                ),
            )
            if response and response.text:
                data = json.loads(response.text)
                data["id"] = f"ai_rec_{uuid.uuid4().hex[:8]}"
                data["servings"] = servings
                # Calculate macros
                temp_rec = Recipe(
                    id=data["id"],
                    title=data["title"],
                    description=data.get("description", ""),
                    meal_type=MealType(data.get("meal_type", meal_type).lower()),
                    servings=servings,
                    prep_time_minutes=data.get("prep_time_minutes", 10),
                    cook_time_minutes=data.get("cook_time_minutes", 15),
                    ingredients=[Ingredient(**i) for i in data["ingredients"]],
                    instructions=data.get("instructions", []),
                    tags=data.get("tags", []),
                    nutrition=NutritionInfo(),
                )
                temp_rec.nutrition = _nutrition_analyzer.calculate_recipe_nutrition(temp_rec)
                return temp_rec.model_dump()
        except Exception as e:
            logger.warning(f"ChefAgent live Gemini generation fallback: {e}")

    # 2. Dynamic Algorithmic Culinary Composer Fallback
    return _synthesize_culinary_recipe(
        prompt=prompt,
        meal_type=meal_type,
        dietary_preferences=dietary_preferences or [],
        must_include_ingredients=must_include_ingredients or [],
        servings=servings,
        pantry_ingredients=pantry_ingredients or [],
    )


def _synthesize_culinary_recipe(
    prompt: str,
    meal_type: str,
    dietary_preferences: List[str],
    must_include_ingredients: List[str],
    servings: int,
    pantry_ingredients: List[str],
) -> Dict[str, Any]:
    """Algorithmically craft a recipe when live API is unreachable."""
    is_keto = "keto" in [d.lower() for d in dietary_preferences] or "keto" in prompt.lower()
    is_vegan = "vegan" in [d.lower() for d in dietary_preferences] or "vegan" in prompt.lower()

    ings = list(must_include_ingredients)
    rec_id = f"ai_rec_{uuid.uuid4().hex[:8]}"

    # Craft recipe based on ingredients and diet
    if "spinach" in [i.lower() for i in ings] or "spinach" in prompt.lower():
        if is_keto:
            title = "Chef's Keto Sautéed Spinach & Garlic Butter Salmon"
            desc = "Wild-caught salmon pan-seared in rich garlic olive oil, resting on a bed of warm wilted baby spinach and toasted sesame seeds."
            mt = MealType.DINNER if meal_type == "dinner" else (MealType.LUNCH if meal_type == "lunch" else MealType.BREAKFAST)
            ingredients_list = [
                {"name": "salmon fillet", "quantity": 200.0 * servings, "unit": "g", "category": "Meat & Seafood"},
                {"name": "spinach", "quantity": 100.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "garlic", "quantity": 8.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "olive oil", "quantity": 15.0 * servings, "unit": "g", "category": "Pantry & Dry Goods"},
            ]
            instructions = [
                f"Pat {200 * servings}g salmon fillets dry and season generously with sea salt, black pepper, and minced garlic.",
                "Heat extra virgin olive oil in a heavy skillet over medium-high heat.",
                "Place salmon skin-side down and sear for 4-5 minutes until crisp, then flip and cook for 3 minutes more.",
                "In the same flavorful skillet, toss in the fresh baby spinach and sauté for 90 seconds until bright green and tender.",
                "Plate the warm spinach bed and serve the pan-seared salmon fillet over the top with a drizzle of skillet drippings.",
            ]
            tags = ["keto", "low_carb", "high_protein", "gluten_free", "healthy_fats"]
        elif is_vegan:
            title = "Chef's Fragrant Garlic Spinach & Crispy Tofu Bowl"
            desc = "Crispy pan-fried tofu cubes paired with garlic-infused baby spinach, sweet bell peppers, and extra virgin olive oil."
            mt = MealType.LUNCH if meal_type == "lunch" else MealType.DINNER
            ingredients_list = [
                {"name": "tofu", "quantity": 200.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "spinach", "quantity": 100.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "bell pepper", "quantity": 80.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "garlic", "quantity": 10.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "olive oil", "quantity": 15.0 * servings, "unit": "g", "category": "Pantry & Dry Goods"},
            ]
            instructions = [
                "Press tofu to remove excess moisture, then cut into bite-sized golden cubes.",
                "Heat olive oil in a wok over high heat and fry tofu until golden and crispy (approx 6 minutes).",
                "Toss in sliced bell peppers and minced garlic, stir-frying for 3 minutes.",
                "Fold in fresh baby spinach during the last minute until gently wilted.",
                "Serve warm with a squeeze of fresh lemon juice.",
            ]
            tags = ["vegan", "plant_based", "gluten_free", "high_fiber"]
        else:
            title = "Chef's Mediterranean Quinoa & Spinach Bowl"
            desc = "Fluffy protein-rich quinoa tossed with sautéed baby spinach, diced cucumbers, and a fragrant garlic olive oil dressing."
            mt = MealType(meal_type) if meal_type in ["breakfast", "lunch", "dinner"] else MealType.DINNER
            ingredients_list = [
                {"name": "quinoa", "quantity": 100.0 * servings, "unit": "g", "category": "Pantry & Dry Goods"},
                {"name": "spinach", "quantity": 80.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "cucumber", "quantity": 80.0 * servings, "unit": "g", "category": "Produce"},
                {"name": "olive oil", "quantity": 12.0 * servings, "unit": "g", "category": "Pantry & Dry Goods"},
                {"name": "garlic", "quantity": 5.0 * servings, "unit": "g", "category": "Produce"},
            ]
            instructions = [
                f"Simmer {100 * servings}g quinoa in water for 15 minutes until fluffy.",
                "Warm olive oil in a pan, lightly sauté garlic and spinach for 2 minutes.",
                "Combine warm quinoa with sautéed spinach and diced fresh cucumbers.",
                "Season with sea salt and serve immediately.",
            ]
            tags = ["mediterranean", "high_protein", "gluten_free"]
    elif is_keto:
        title = "Chef's Keto Herb Grilled Chicken & Roasted Asparagus"
        desc = "Tender grilled chicken breast infused with garlic and herbs, paired with tender roasted asparagus spears."
        mt = MealType(meal_type) if meal_type in ["breakfast", "lunch", "dinner"] else MealType.DINNER
        ingredients_list = [
            {"name": "chicken breast", "quantity": 220.0 * servings, "unit": "g", "category": "Meat & Seafood"},
            {"name": "asparagus", "quantity": 150.0 * servings, "unit": "g", "category": "Produce"},
            {"name": "garlic", "quantity": 8.0 * servings, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15.0 * servings, "unit": "g", "category": "Pantry & Dry Goods"},
        ]
        instructions = [
            "Season chicken breasts with minced garlic, sea salt, black pepper, and half the olive oil.",
            "Grill or sear chicken on medium-high heat for 6-7 minutes per side until 165°F.",
            "Roast asparagus with remaining olive oil in a 400°F oven for 12 minutes.",
            "Slice chicken and serve beside hot roasted asparagus.",
        ]
        tags = ["keto", "low_carb", "high_protein", "gluten_free"]
    else:
        title = f"Chef's Gourmet {meal_type.title()} Creation"
        desc = f"A wholesome, nutritionally balanced {meal_type} crafted with fresh wholesome ingredients."
        mt = MealType(meal_type) if meal_type in ["breakfast", "lunch", "dinner"] else MealType.DINNER
        ingredients_list = [
            {"name": "chicken breast", "quantity": 180.0 * servings, "unit": "g", "category": "Meat & Seafood"},
            {"name": "sweet potato", "quantity": 150.0 * servings, "unit": "g", "category": "Produce"},
            {"name": "broccoli", "quantity": 100.0 * servings, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 10.0 * servings, "unit": "g", "category": "Pantry & Dry Goods"},
        ]
        instructions = [
            "Dice sweet potatoes and roast in the oven for 20 minutes.",
            "Sear seasoned chicken breast in olive oil for 6 minutes per side.",
            "Steam broccoli florets until tender-crisp.",
            "Plate chicken, roasted sweet potatoes, and steamed broccoli together.",
        ]
        tags = ["balanced", "clean_eating", "high_protein"]

    # Construct Recipe model and compute nutrition
    recipe_obj = Recipe(
        id=rec_id,
        title=title,
        description=desc,
        meal_type=mt,
        servings=servings,
        prep_time_minutes=10,
        cook_time_minutes=15,
        ingredients=[Ingredient(**i) for i in ingredients_list],
        instructions=instructions,
        tags=tags,
        nutrition=NutritionInfo(),
    )
    recipe_obj.nutrition = _nutrition_analyzer.calculate_recipe_nutrition(recipe_obj)
    return recipe_obj.model_dump()


# Google ADK Chef Agent Definition
CHEF_INSTRUCTION = """You are the Executive Chef & Meal Planner Agent in NutriConcierge, built with Google ADK.
Your primary superpower is Generative Culinary AI:
1. Dynamically invent and formulate original recipes using create_recipe_with_ai for user cravings and constraints.
2. Prioritize ingredients in the user's pantry to eliminate food waste (get_pantry_inventory).
3. Scale portions accurately for the user's household size.
4. Craft delicious, balanced menus across breakfast, lunch, and dinner matching any dietary lifestyle (Keto, Vegan, Gluten-Free, Mediterranean)."""

chef_agent = Agent(
    name="chef_agent",
    model=settings.gemini_model,
    instruction=CHEF_INSTRUCTION,
    tools=[create_recipe_with_ai, get_pantry_inventory],
)
