"""Recipe Search, Scaling, and Formatting Tool."""

from typing import Dict, List, Optional
from src.models.schemas import (
    Ingredient,
    MealType,
    NutritionInfo,
    Recipe,
    UserProfile,
)
from src.tools.nutrition_analyzer import NutritionAnalyzerTool

# Comprehensive starter recipe database covering diverse dietary needs
SAMPLE_RECIPES: List[Dict] = [
    # ---------------- BREAKFAST RECIPES ----------------
    {
        "id": "rec_001",
        "title": "Protein Power Berry Oatmeal with Almonds",
        "description": "Warm rolled oats simmered with almond milk, topped with antioxidant-rich blueberries, chia seeds, and sliced almonds.",
        "meal_type": MealType.BREAKFAST,
        "servings": 1,
        "prep_time_minutes": 5,
        "cook_time_minutes": 5,
        "ingredients": [
            {"name": "rolled oats", "quantity": 50, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "almond milk", "quantity": 200, "unit": "g", "category": "Dairy & Alternatives"},
            {"name": "blueberries", "quantity": 75, "unit": "g", "category": "Produce"},
            {"name": "chia seeds", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "almonds", "quantity": 20, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Combine rolled oats and almond milk in a small saucepan over medium heat.",
            "Cook for 4-5 minutes, stirring occasionally until creamy.",
            "Pour into a bowl and top with fresh blueberries, sliced almonds, and chia seeds.",
        ],
        "tags": ["vegan", "vegetarian", "dairy_free", "high_fiber", "quick"],
    },
    {
        "id": "rec_002",
        "title": "Chia Seed & Coconut Berry Pudding",
        "description": "Naturally gluten-free and nut-free chia pudding soaked in oat milk, layered with sliced strawberries and bananas.",
        "meal_type": MealType.BREAKFAST,
        "servings": 1,
        "prep_time_minutes": 5,
        "cook_time_minutes": 0,
        "ingredients": [
            {"name": "chia seeds", "quantity": 30, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "strawberries", "quantity": 100, "unit": "g", "category": "Produce"},
            {"name": "banana", "quantity": 80, "unit": "g", "category": "Produce"},
            {"name": "blueberries", "quantity": 50, "unit": "g", "category": "Produce"},
        ],
        "instructions": [
            "Mix chia seeds with water or seed milk and allow to set for 15 minutes.",
            "Top with sliced strawberries, blueberries, and fresh banana coins.",
        ],
        "tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "nut_free"],
    },
    {
        "id": "rec_003",
        "title": "Avocado & Spinach Scramble on Toast",
        "description": "Fluffy scrambled eggs folded with baby spinach, served over whole wheat toast with sliced creamy avocado.",
        "meal_type": MealType.BREAKFAST,
        "servings": 1,
        "prep_time_minutes": 5,
        "cook_time_minutes": 5,
        "ingredients": [
            {"name": "eggs", "quantity": 100, "unit": "g", "category": "Dairy & Refrigerated"},
            {"name": "spinach", "quantity": 50, "unit": "g", "category": "Produce"},
            {"name": "whole wheat bread", "quantity": 60, "unit": "g", "category": "Bakery"},
            {"name": "avocado", "quantity": 50, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 5, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Whisk eggs in a bowl with a pinch of black pepper.",
            "Toast whole wheat bread slices until golden brown.",
            "Warm olive oil in a skillet, sauté spinach for 1 minute until wilted, then pour in whisked eggs.",
            "Gently stir over low heat until soft curds form.",
            "Top toast with mashed avocado and the warm scrambled eggs.",
        ],
        "tags": ["vegetarian", "high_protein", "quick"],
    },

    # ---------------- LUNCH RECIPES ----------------
    {
        "id": "rec_004",
        "title": "Crispy Tofu & Sesame Veggie Stir-Fry",
        "description": "Golden pan-fried tofu cubes tossed with vibrant broccoli, red bell pepper, garlic, and toasted sesame seeds.",
        "meal_type": MealType.LUNCH,
        "servings": 2,
        "prep_time_minutes": 15,
        "cook_time_minutes": 10,
        "ingredients": [
            {"name": "tofu", "quantity": 250, "unit": "g", "category": "Produce"},
            {"name": "broccoli", "quantity": 150, "unit": "g", "category": "Produce"},
            {"name": "bell pepper", "quantity": 100, "unit": "g", "category": "Produce"},
            {"name": "garlic", "quantity": 10, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Press tofu with paper towels and cut into 1-inch cubes.",
            "Heat olive oil in a wok or large skillet over high heat.",
            "Add tofu cubes and fry until golden on all sides (approx 6 minutes).",
            "Toss in minced garlic, broccoli florets, and sliced bell pepper. Stir-fry for 4 minutes until crisp-tender.",
        ],
        "tags": ["vegan", "vegetarian", "dairy_free", "plant_based", "gluten_free"],
    },
    {
        "id": "rec_005",
        "title": "Hearty Black Bean & Quinoa Fiesta Salad",
        "description": "Zesty southwestern bowl packed with fiber-rich black beans, fluffy quinoa, bell pepper, and creamy avocado.",
        "meal_type": MealType.LUNCH,
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "ingredients": [
            {"name": "canned black beans", "quantity": 200, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "quinoa", "quantity": 120, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "bell pepper", "quantity": 100, "unit": "g", "category": "Produce"},
            {"name": "avocado", "quantity": 80, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 10, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Cook quinoa according to package instructions and let cool slightly.",
            "Rinse and drain black beans.",
            "Dice bell pepper and avocado into cubes.",
            "Toss all ingredients together in a large bowl with olive oil, lime juice, and salt.",
        ],
        "tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "nut_free", "high_fiber"],
    },
    {
        "id": "rec_006",
        "title": "Mediterranean Chickpea & Cucumber Salad",
        "description": "Refreshing and protein-dense salad with chickpeas, diced cucumber, cherry tomatoes, and extra virgin olive oil.",
        "meal_type": MealType.LUNCH,
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 0,
        "ingredients": [
            {"name": "chickpeas", "quantity": 250, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "cucumber", "quantity": 150, "unit": "g", "category": "Produce"},
            {"name": "tomato", "quantity": 120, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "garlic", "quantity": 5, "unit": "g", "category": "Produce"},
        ],
        "instructions": [
            "Rinse and drain chickpeas thoroughly.",
            "Dice cucumber and tomatoes into bite-sized chunks.",
            "Whisk minced garlic and olive oil with a pinch of sea salt.",
            "Toss chickpeas and vegetables with the dressing and serve chilled.",
        ],
        "tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "nut_free"],
    },

    # ---------------- DINNER RECIPES ----------------
    {
        "id": "rec_007",
        "title": "Mediterranean Quinoa Bowl with Lemon Herb Salmon",
        "description": "Hearty whole grain quinoa bowl topped with pan-seared wild salmon, fresh cucumbers, and olive oil.",
        "meal_type": MealType.DINNER,
        "servings": 2,
        "prep_time_minutes": 15,
        "cook_time_minutes": 15,
        "ingredients": [
            {"name": "salmon fillet", "quantity": 250, "unit": "g", "category": "Meat & Seafood"},
            {"name": "quinoa", "quantity": 150, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "cucumber", "quantity": 100, "unit": "g", "category": "Produce"},
            {"name": "spinach", "quantity": 80, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Rinse quinoa and simmer in 2 cups of water for 15 minutes until fluffy.",
            "Season salmon with salt, pepper, and olive oil.",
            "Pan-sear salmon on medium-high heat for 4-5 minutes per side until golden.",
            "Assemble bowls with quinoa, fresh baby spinach, sliced cucumbers, and flake the salmon over top.",
        ],
        "tags": ["high_protein", "pescatarian", "gluten_free", "dairy_free", "mediterranean"],
    },
    {
        "id": "rec_008",
        "title": "Garlic Herb Grilled Chicken with Roasted Sweet Potato",
        "description": "Juicy tender chicken breast seasoned with garlic and olive oil, paired with roasted sweet potato cubes and asparagus.",
        "meal_type": MealType.DINNER,
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 25,
        "ingredients": [
            {"name": "chicken breast", "quantity": 300, "unit": "g", "category": "Meat & Seafood"},
            {"name": "sweet potato", "quantity": 250, "unit": "g", "category": "Produce"},
            {"name": "asparagus", "quantity": 150, "unit": "g", "category": "Produce"},
            {"name": "garlic", "quantity": 10, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Preheat oven to 400°F (200°C). Dice sweet potatoes into bite-sized cubes.",
            "Toss sweet potatoes and asparagus with half the olive oil and roast for 20-25 minutes.",
            "Season chicken breasts with minced garlic, remaining olive oil, salt, and pepper.",
            "Grill or pan-sear chicken over medium-high heat for 6-7 minutes per side until internal temp reaches 165°F.",
            "Plate grilled chicken with roasted sweet potatoes and tender asparagus.",
        ],
        "tags": ["high_protein", "gluten_free", "dairy_free", "nut_free", "clean_eating"],
    },
    {
        "id": "rec_009",
        "title": "Savory Red Lentil & Spinach Dahl",
        "description": "A fragrant, comforting stew of tender red lentils simmered with garlic, sweet potato, and fresh baby spinach.",
        "meal_type": MealType.DINNER,
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "ingredients": [
            {"name": "lentils", "quantity": 200, "unit": "g", "category": "Pantry & Dry Goods"},
            {"name": "spinach", "quantity": 100, "unit": "g", "category": "Produce"},
            {"name": "sweet potato", "quantity": 150, "unit": "g", "category": "Produce"},
            {"name": "garlic", "quantity": 10, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 10, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Sauté minced garlic in olive oil in a deep pot until fragrant.",
            "Add diced sweet potato and rinsed red lentils with 3 cups of water.",
            "Simmer on medium-low heat for 18 minutes until lentils are soft and creamy.",
            "Stir in fresh baby spinach during the last 2 minutes until wilted.",
        ],
        "tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "nut_free", "high_fiber"],
    },
    {
        "id": "rec_010",
        "title": "Keto Avocado & Spinach Scramble",
        "description": "Whisked farm-fresh eggs scrambled in olive oil with tender baby spinach and sliced ripe avocado. Zero net carbs.",
        "meal_type": MealType.BREAKFAST,
        "servings": 1,
        "prep_time_minutes": 5,
        "cook_time_minutes": 5,
        "ingredients": [
            {"name": "eggs", "quantity": 120, "unit": "g", "category": "Dairy & Refrigerated"},
            {"name": "spinach", "quantity": 60, "unit": "g", "category": "Produce"},
            {"name": "avocado", "quantity": 60, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 10, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Whisk eggs with a pinch of sea salt and black pepper.",
            "Warm olive oil in a non-stick skillet and sauté baby spinach for 1 minute.",
            "Pour in whisked eggs and gently stir until soft, creamy curds form.",
            "Serve immediately topped with sliced fresh avocado.",
        ],
        "tags": ["keto", "low_carb", "vegetarian", "gluten_free", "high_protein", "healthy_fats"],
    },
    {
        "id": "rec_011",
        "title": "Keto Lemon Butter Salmon with Asparagus",
        "description": "Pan-seared wild salmon fillet cooked in olive oil and lemon juice, served alongside tender roasted asparagus spears.",
        "meal_type": MealType.DINNER,
        "servings": 1,
        "prep_time_minutes": 10,
        "cook_time_minutes": 12,
        "ingredients": [
            {"name": "salmon fillet", "quantity": 200, "unit": "g", "category": "Meat & Seafood"},
            {"name": "asparagus", "quantity": 150, "unit": "g", "category": "Produce"},
            {"name": "garlic", "quantity": 5, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Season salmon fillet with salt, garlic, and freshly cracked black pepper.",
            "Sear salmon in hot olive oil for 4 minutes per side until crisp and golden.",
            "In the same pan, sauté asparagus spears for 4-5 minutes until tender-crisp.",
            "Plate salmon with asparagus and drizzle with pan juices.",
        ],
        "tags": ["keto", "low_carb", "gluten_free", "dairy_free", "high_protein", "pescatarian"],
    },
    {
        "id": "rec_012",
        "title": "Keto Garlic Rosemary Chicken with Sautéed Greens",
        "description": "Pan-seared tender chicken breast infused with garlic and olive oil, served over a bed of warm wilted baby spinach and broccoli.",
        "meal_type": MealType.LUNCH,
        "servings": 1,
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "ingredients": [
            {"name": "chicken breast", "quantity": 200, "unit": "g", "category": "Meat & Seafood"},
            {"name": "spinach", "quantity": 80, "unit": "g", "category": "Produce"},
            {"name": "broccoli", "quantity": 100, "unit": "g", "category": "Produce"},
            {"name": "garlic", "quantity": 5, "unit": "g", "category": "Produce"},
            {"name": "olive oil", "quantity": 15, "unit": "g", "category": "Pantry & Dry Goods"},
        ],
        "instructions": [
            "Season chicken breast with minced garlic, sea salt, and black pepper.",
            "Cook chicken in olive oil over medium-high heat for 6-7 minutes per side until cooked through.",
            "Steam broccoli and flash-sauté baby spinach in the pan drippings.",
            "Slice chicken breast and serve hot over the warm greens.",
        ],
        "tags": ["keto", "low_carb", "gluten_free", "dairy_free", "high_protein"],
    },
]


class RecipeTool:
    """Tool for querying, scaling, and constructing recipes."""

    def __init__(self):
        self.nutrition_analyzer = NutritionAnalyzerTool()
        self.recipes: List[Recipe] = []
        for raw in SAMPLE_RECIPES:
            ingredients = [Ingredient(**i) for i in raw["ingredients"]]
            recipe_obj = Recipe(
                id=raw["id"],
                title=raw["title"],
                description=raw["description"],
                meal_type=raw["meal_type"],
                servings=raw["servings"],
                prep_time_minutes=raw["prep_time_minutes"],
                cook_time_minutes=raw["cook_time_minutes"],
                ingredients=ingredients,
                instructions=raw["instructions"],
                tags=raw.get("tags", []),
                nutrition=NutritionInfo(),
            )
            recipe_obj.nutrition = self.nutrition_analyzer.calculate_recipe_nutrition(recipe_obj)
            self.recipes.append(recipe_obj)

    def get_all_recipes(self) -> List[Recipe]:
        """Return all catalog recipes."""
        return self.recipes

    def search_recipes(
        self,
        query: Optional[str] = None,
        meal_type: Optional[MealType] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Recipe]:
        """Search recipes based on keywords, meal type, and dietary tags."""
        results = self.recipes
        if meal_type:
            results = [r for r in results if r.meal_type == meal_type]

        if query:
            q_clean = query.lower()
            results = [
                r for r in results
                if q_clean in r.title.lower()
                or q_clean in r.description.lower()
                or any(q_clean in ing.name.lower() for ing in r.ingredients)
            ]

        if tags:
            tag_set = set(t.lower() for t in tags)
            results = [r for r in results if tag_set.issubset(set(t.lower() for t in r.tags))]

        return results

    def scale_recipe(self, recipe: Recipe, target_servings: int) -> Recipe:
        """Scale ingredient quantities for desired number of servings."""
        if target_servings <= 0 or target_servings == recipe.servings:
            return recipe

        ratio = target_servings / recipe.servings
        scaled_ingredients = [
            Ingredient(
                name=ing.name,
                quantity=round(ing.quantity * ratio, 2),
                unit=ing.unit,
                category=ing.category,
                notes=ing.notes,
            )
            for ing in recipe.ingredients
        ]

        scaled = Recipe(
            id=f"{recipe.id}_s{target_servings}",
            title=f"{recipe.title} ({target_servings} servings)",
            description=recipe.description,
            meal_type=recipe.meal_type,
            servings=target_servings,
            prep_time_minutes=recipe.prep_time_minutes,
            cook_time_minutes=recipe.cook_time_minutes,
            ingredients=scaled_ingredients,
            instructions=recipe.instructions,
            tags=recipe.tags,
            nutrition=recipe.nutrition,
        )
        return scaled

    def format_recipe_markdown(self, recipe: Recipe) -> str:
        """Render a recipe as a rich Markdown card."""
        lines = [
            f"### 🍽️ {recipe.title}",
            f"*{recipe.description}*",
            "",
            f"⏱️ **Prep Time:** {recipe.prep_time_minutes} mins | **Cook Time:** {recipe.cook_time_minutes} mins | 👥 **Servings:** {recipe.servings}",
            "",
            "#### 📊 Nutrition (per serving):",
            f"- **Calories:** {recipe.nutrition.calories} kcal",
            f"- **Protein:** {recipe.nutrition.protein_g}g | **Carbs:** {recipe.nutrition.carbs_g}g | **Fat:** {recipe.nutrition.fat_g}g | **Fiber:** {recipe.nutrition.fiber_g}g",
            "",
            "#### 🛒 Ingredients:",
        ]
        for ing in recipe.ingredients:
            lines.append(f"- {ing.quantity} {ing.unit} **{ing.name}**")

        lines.append("")
        lines.append("#### 👩‍🍳 Instructions:")
        for idx, step in enumerate(recipe.instructions, 1):
            lines.append(f"{idx}. {step}")

        return "\n".join(lines)
