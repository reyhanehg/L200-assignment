"""Pantry and Kitchen Inventory Management Tool.

Handles tracking of on-hand ingredients, expiry dates, and food waste minimization.
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.models.schemas import PantryItem


class PantryInventoryTool:
    """Tool for managing pantry stock, expiring goods, and inventory reconciliations."""

    def __init__(self, initial_items: Optional[List[PantryItem]] = None):
        self._inventory: Dict[str, PantryItem] = {}
        if initial_items:
            for item in initial_items:
                self._inventory[item.id] = item

    def get_all_items(self) -> List[PantryItem]:
        """Return all tracked pantry items."""
        return list(self._inventory.values())

    def add_or_update_item(
        self,
        name: str,
        quantity: float,
        unit: str,
        category: str = "Pantry",
        expiration_date: Optional[date] = None,
        item_id: Optional[str] = None,
    ) -> PantryItem:
        """Add or update an item in the pantry."""
        norm_name = name.strip().lower()
        if not item_id:
            # Check if matching item exists by name
            for existing_id, item in self._inventory.items():
                if item.name.lower() == norm_name and item.unit.lower() == unit.lower():
                    item_id = existing_id
                    break

        if item_id and item_id in self._inventory:
            existing = self._inventory[item_id]
            existing.quantity += quantity
            if expiration_date:
                existing.expiration_date = expiration_date
            return existing

        new_id = item_id or f"pantry_{len(self._inventory) + 1}_{norm_name.replace(' ', '_')}"
        new_item = PantryItem(
            id=new_id,
            name=name.strip(),
            category=category,
            quantity=quantity,
            unit=unit,
            expiration_date=expiration_date,
        )
        self._inventory[new_id] = new_item
        return new_item

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from inventory."""
        if item_id in self._inventory:
            del self._inventory[item_id]
            return True
        return False

    def find_item_by_name(self, name: str) -> Optional[PantryItem]:
        """Search pantry for an ingredient name."""
        norm_name = name.strip().lower()
        for item in self._inventory.values():
            if norm_name in item.name.lower() or item.name.lower() in norm_name:
                return item
        return None

    def get_expiring_soon(self, days_threshold: int = 4) -> List[PantryItem]:
        """Retrieve perishable items that expire within the specified number of days."""
        today = date.today()
        threshold_date = today + timedelta(days=days_threshold)
        expiring = []
        for item in self._inventory.values():
            if item.expiration_date and item.expiration_date <= threshold_date:
                expiring.append(item)
        return sorted(expiring, key=lambda x: x.expiration_date or date.max)

    def deduct_ingredients(self, ingredients: List[Dict[str, Any]]) -> Dict[str, float]:
        """Deduct ingredients used in a meal from pantry inventory."""
        deducted = {}
        for ing in ingredients:
            name = ing.get("name", "")
            qty = ing.get("quantity", 0.0)
            item = self.find_item_by_name(name)
            if item:
                item.quantity = max(0.0, round(item.quantity - qty, 2))
                deducted[item.name] = item.quantity
        return deducted
