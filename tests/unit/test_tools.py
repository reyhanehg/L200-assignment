"""Unit tests for NutriConcierge tools."""

import unittest
from datetime import date, timedelta
from src.models.schemas import (
    CommonAllergen,
    DietaryRestriction,
    Ingredient,
    MealType,
    NutritionInfo,
    PantryItem,
    Recipe,
    UserProfile,
)
from src.tools.allergen_checker import AllergenSafetyCheckerTool
from src.tools.grocery_exporter import GroceryCartExporterTool
from src.tools.nutrition_analyzer import NutritionAnalyzerTool
from src.tools.pantry_tool import PantryInventoryTool
from src.tools.recipe_tool import RecipeTool


class TestNutriConciergeTools(unittest.TestCase):
    """Test suite for core deterministic tools."""

    def test_nutrition_analyzer_calculation(self):
        tool = NutritionAnalyzerTool()
        ing = Ingredient(name="chicken breast", quantity=200, unit="g")
        nutrition = tool.calculate_ingredient_nutrition(ing)

        self.assertAlmostEqual(nutrition.calories, 330.0, delta=35.0)
        self.assertAlmostEqual(nutrition.protein_g, 62.0, delta=10.0)
        self.assertEqual(nutrition.carbs_g, 0.0)

    def test_allergen_checker_detects_peanuts_and_dairy(self):
        checker = AllergenSafetyCheckerTool()
        profile = UserProfile(
            allergens=[CommonAllergen.PEANUTS, CommonAllergen.MILK],
            dietary_restrictions=[],
        )

        unsafe_recipe = Recipe(
            id="unsafe_1",
            title="Peanut Butter Smoothie",
            description="Rich smoothie with peanut butter and whole milk",
            meal_type=MealType.SNACK,
            ingredients=[
                Ingredient(name="peanut butter", quantity=30, unit="g"),
                Ingredient(name="whole milk", quantity=200, unit="g"),
                Ingredient(name="banana", quantity=100, unit="g"),
            ],
            instructions=["Blend all ingredients."],
            nutrition=NutritionInfo(),
        )

        result = checker.check_recipe_safety(unsafe_recipe, profile)
        self.assertFalse(result.is_safe)
        self.assertGreaterEqual(len(result.violates_allergens), 2)

    def test_allergen_checker_enforces_vegan(self):
        checker = AllergenSafetyCheckerTool()
        profile = UserProfile(
            allergens=[],
            dietary_restrictions=[DietaryRestriction.VEGAN],
        )

        chicken_recipe = Recipe(
            id="unsafe_vegan",
            title="Chicken Bowl",
            description="Chicken with rice",
            meal_type=MealType.DINNER,
            ingredients=[
                Ingredient(name="chicken breast", quantity=200, unit="g"),
                Ingredient(name="white rice", quantity=100, unit="g"),
            ],
            instructions=["Cook and serve."],
            nutrition=NutritionInfo(),
        )

        result = checker.check_recipe_safety(chicken_recipe, profile)
        self.assertFalse(result.is_safe)
        self.assertTrue(any("Vegan violation" in v for v in result.violates_dietary_rules))

    def test_pantry_inventory_tool(self):
        pantry = PantryInventoryTool()
        pantry.add_or_update_item("quinoa", 200, "g", "Pantry & Dry Goods")
        pantry.add_or_update_item("quinoa", 100, "g", "Pantry & Dry Goods")

        item = pantry.find_item_by_name("quinoa")
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, 300.0)

        # Expiration check
        today = date.today()
        pantry.add_or_update_item("fresh spinach", 50, "g", "Produce", expiration_date=today + timedelta(days=2))
        expiring = pantry.get_expiring_soon(days_threshold=3)
        self.assertEqual(len(expiring), 1)
        self.assertEqual(expiring[0].name, "fresh spinach")

    def test_grocery_exporter_delta_calculation(self):
        pantry = PantryInventoryTool([
            PantryItem(id="p1", name="quinoa", quantity=100, unit="g", category="Pantry & Dry Goods")
        ])
        exporter = GroceryCartExporterTool(pantry_tool=pantry)

        recipe = Recipe(
            id="rec_test",
            title="Quinoa Salad",
            description="Test recipe",
            meal_type=MealType.LUNCH,
            ingredients=[
                Ingredient(name="quinoa", quantity=250, unit="g", category="Pantry & Dry Goods"),
                Ingredient(name="cucumber", quantity=100, unit="g", category="Produce"),
            ],
            instructions=["Mix ingredients."],
            nutrition=NutritionInfo(),
        )

        grocery_list = exporter.generate_grocery_list([recipe])

        dry_goods = grocery_list.items_by_category["Pantry & Dry Goods"]
        produce = grocery_list.items_by_category["Produce"]

        quinoa_item = next(i for i in dry_goods if "quinoa" in i.name.lower())
        self.assertEqual(quinoa_item.to_buy_quantity, 150.0)

        cucumber_item = next(i for i in produce if "cucumber" in i.name.lower())
        self.assertEqual(cucumber_item.to_buy_quantity, 100.0)


if __name__ == "__main__":
    unittest.main()
