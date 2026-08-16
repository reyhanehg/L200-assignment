"""Grocery List Generator and Exporter Tool."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.schemas import (
    GroceryItem,
    GroceryList,
    Recipe,
    WeeklyMealPlan,
)
from src.tools.pantry_tool import PantryInventoryTool

CATEGORY_ORDER = [
    "Produce",
    "Meat & Seafood",
    "Dairy & Refrigerated",
    "Dairy & Alternatives",
    "Bakery",
    "Pantry & Dry Goods",
    "Spices & Condiments",
    "Frozen",
]


class GroceryCartExporterTool:
    """Tool for compiling, deduplicating, and exporting grocery shopping lists."""

    def __init__(self, pantry_tool: Optional[PantryInventoryTool] = None):
        self.pantry_tool = pantry_tool or PantryInventoryTool()

    def generate_grocery_list(
        self,
        recipes: List[Recipe],
        user_id: str = "default_user",
    ) -> GroceryList:
        """Reconcile all recipe ingredients against pantry inventory to generate a shopping list."""
        needed_ingredients: Dict[str, Dict[str, Any]] = {}

        # 1. Aggregate needed quantities across all recipes
        for recipe in recipes:
            for ing in recipe.ingredients:
                key = (ing.name.lower().strip(), ing.unit.lower().strip())
                if key not in needed_ingredients:
                    needed_ingredients[key] = {
                        "name": ing.name.title(),
                        "category": ing.category or "Pantry & Dry Goods",
                        "unit": ing.unit,
                        "needed_quantity": 0.0,
                    }
                needed_ingredients[key]["needed_quantity"] += ing.quantity

        # 2. Check pantry inventory and calculate delta
        items_by_category: Dict[str, List[GroceryItem]] = defaultdict(list)
        total_items_to_buy = 0

        for (ing_name_lower, unit), data in needed_ingredients.items():
            pantry_item = self.pantry_tool.find_item_by_name(ing_name_lower)
            pantry_qty = 0.0
            if pantry_item:
                pantry_qty = pantry_item.quantity

            to_buy = max(0.0, round(data["needed_quantity"] - pantry_qty, 2))

            if to_buy > 0:
                total_items_to_buy += 1

            category = data["category"]
            grocery_item = GroceryItem(
                name=data["name"],
                category=category,
                needed_quantity=round(data["needed_quantity"], 2),
                pantry_quantity=round(pantry_qty, 2),
                to_buy_quantity=to_buy,
                unit=data["unit"],
                is_purchased=False,
            )
            items_by_category[category].append(grocery_item)

        # Sort items inside each category
        for cat in items_by_category:
            items_by_category[cat].sort(key=lambda x: x.name)

        return GroceryList(
            id=f"groc_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            items_by_category=dict(items_by_category),
            total_items_to_buy=total_items_to_buy,
            estimated_cost_usd=round(total_items_to_buy * 3.75, 2),  # Estimated benchmark
            generated_at=datetime.utcnow(),
        )

    def generate_from_meal_plan(
        self, meal_plan: WeeklyMealPlan, user_id: Optional[str] = None
    ) -> GroceryList:
        """Convenience method to generate grocery list directly from a weekly meal plan."""
        all_recipes = []
        for day in meal_plan.days:
            all_recipes.extend(day.meals)
        return self.generate_grocery_list(all_recipes, user_id=user_id or meal_plan.user_id)

    def format_markdown(self, grocery_list: GroceryList) -> str:
        """Format grocery list into an interactive markdown checklist."""
        lines = [
            "# 🛒 Grocery Shopping List",
            f"**Generated:** {grocery_list.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Total Items to Buy:** {grocery_list.total_items_to_buy} | **Estimated Cost:** ${grocery_list.estimated_cost_usd:.2f}",
            "",
        ]

        if not grocery_list.items_by_category:
            lines.append("*Your pantry is fully stocked! No additional items needed.*")
            return "\n".join(lines)

        # Iterate in standard supermarket aisle order
        for category in CATEGORY_ORDER:
            items = grocery_list.items_by_category.get(category)
            if not items:
                continue

            to_buy_items = [item for item in items if item.to_buy_quantity > 0]
            if not to_buy_items:
                continue

            lines.append(f"### 📍 {category}")
            for item in to_buy_items:
                pantry_note = f" *(in pantry: {item.pantry_quantity} {item.unit})*" if item.pantry_quantity > 0 else ""
                lines.append(
                    f"- [ ] **{item.name}**: {item.to_buy_quantity} {item.unit}{pantry_note}"
                )
            lines.append("")

        # Add any other categories not in CATEGORY_ORDER
        for category, items in grocery_list.items_by_category.items():
            if category not in CATEGORY_ORDER:
                to_buy_items = [item for item in items if item.to_buy_quantity > 0]
                if to_buy_items:
                    lines.append(f"### 📍 {category}")
                    for item in to_buy_items:
                        lines.append(f"- [ ] **{item.name}**: {item.to_buy_quantity} {item.unit}")
                    lines.append("")

        return "\n".join(lines)
