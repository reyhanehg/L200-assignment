"""Long-term persistent memory store for User Profiles, Pantry, and Feedback History.

Backed by an ACID-compliant SQLite Database (DatabaseStore) with asynchronous
background task dispatching (AsyncMemoryManager).
"""

import json
from pathlib import Path
from typing import List, Optional

from src.config import settings
from src.memory.async_memory import AsyncMemoryManager
from src.memory.db_store import DatabaseStore
from src.models.schemas import (
    CommonAllergen,
    DietaryRestriction,
    MealFeedback,
    PantryItem,
    UserProfile,
    WeeklyMealPlan,
)


class UserStore:
    """Persistent storage engine for user context, kitchen inventory, and long-term feedback."""

    def __init__(self, data_dir: Optional[Path] = None, enable_async: bool = True):
        self.data_dir = data_dir or settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir = self.data_dir / "profiles"
        self.pantry_dir = self.data_dir / "pantry"
        self.feedback_dir = self.data_dir / "feedback"
        self.plans_dir = self.data_dir / "plans"

        for d in [self.profiles_dir, self.pantry_dir, self.feedback_dir, self.plans_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite Database and Async Memory Engine
        self.db = DatabaseStore(db_path=self.data_dir / "nutriconcierge.db")
        self.async_manager = AsyncMemoryManager(db_store=self.db) if enable_async else None

    # 1. Profile Management
    def get_profile(self, user_id: str = "default_user") -> UserProfile:
        """Load user profile from SQLite database or fallback to file/defaults."""
        profile = self.db.get_profile(user_id)
        if profile:
            return profile

        file_path = self.profiles_dir / f"{user_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                prof = UserProfile(**data)
                self.db.save_profile(prof)
                return prof

        # Default profile initialization
        default_profile = UserProfile(
            user_id=user_id,
            name="Alex",
            household_size=2,
            allergens=[CommonAllergen.PEANUTS],
            dietary_restrictions=[DietaryRestriction.GLUTEN_FREE],
            disliked_ingredients=["cilantro", "olives"],
            cooking_skill_level="intermediate",
        )
        self.save_profile(default_profile)
        return default_profile

    def save_profile(self, profile: UserProfile, background: bool = False) -> None:
        """Persist user profile to SQLite database and mirror to disk."""
        if background and self.async_manager:
            self.async_manager.dispatch_save_profile_background(profile)
        else:
            self.db.save_profile(profile)

        # JSON file mirror for file inspection
        file_path = self.profiles_dir / f"{profile.user_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))

    # 2. Pantry Management
    def get_pantry(self, user_id: str = "default_user") -> List[PantryItem]:
        """Load tracked pantry inventory from SQLite database."""
        items = self.db.get_pantry(user_id)
        if items:
            return items

        file_path = self.pantry_dir / f"{user_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                pantry = [PantryItem(**item) for item in data]
                self.db.save_pantry(user_id, pantry)
                return pantry

        # Default starter pantry
        starter_pantry = [
            PantryItem(id="p1", name="quinoa", quantity=300, unit="g", category="Pantry & Dry Goods"),
            PantryItem(id="p2", name="olive oil", quantity=250, unit="g", category="Pantry & Dry Goods"),
            PantryItem(id="p3", name="garlic", quantity=50, unit="g", category="Produce"),
            PantryItem(id="p4", name="rolled oats", quantity=500, unit="g", category="Pantry & Dry Goods"),
            PantryItem(id="p5", name="spinach", quantity=100, unit="g", category="Produce"),
        ]
        self.save_pantry(starter_pantry, user_id=user_id)
        return starter_pantry

    def save_pantry(self, items: List[PantryItem], user_id: str = "default_user", background: bool = False) -> None:
        """Persist pantry inventory to SQLite database."""
        if background and self.async_manager:
            self.async_manager.dispatch_save_pantry_background(user_id, items)
        else:
            self.db.save_pantry(user_id, items)

        file_path = self.pantry_dir / f"{user_id}.json"
        data = [item.model_dump(mode="json") for item in items]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # 3. Meal Feedback & Long-Term Preferences
    def record_feedback(self, feedback: MealFeedback, user_id: str = "default_user", background: bool = False) -> None:
        """Save user feedback to SQLite database with optional non-blocking background dispatch."""
        if background and self.async_manager:
            self.async_manager.dispatch_save_feedback_background(feedback)
        else:
            self.db.save_feedback(feedback, user_id=user_id)

        file_path = self.feedback_dir / f"{user_id}.json"
        feedback_list = []
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                feedback_list = json.load(f)

        feedback_list.append(feedback.model_dump(mode="json"))
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feedback_list, f, indent=2, default=str)

    def get_feedback_history(self, user_id: str = "default_user") -> List[MealFeedback]:
        """Load history of recipe ratings and comments from SQLite database."""
        feedbacks = self.db.get_feedback(user_id)
        if feedbacks:
            return feedbacks

        file_path = self.feedback_dir / f"{user_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [MealFeedback(**item) for item in data]
        return []

    # 4. Meal Plan Persistence
    def save_meal_plan(self, plan: WeeklyMealPlan, background: bool = False) -> None:
        """Persist a generated weekly meal plan to SQLite database."""
        if background and self.async_manager:
            self.async_manager.dispatch_save_meal_plan_background(plan)
        else:
            self.db.save_meal_plan(plan)

        file_path = self.plans_dir / f"{plan.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))

    def get_meal_plan(self, plan_id: str) -> Optional[WeeklyMealPlan]:
        """Load a saved meal plan by ID from SQLite database."""
        plan = self.db.get_meal_plan(plan_id)
        if plan:
            return plan

        file_path = self.plans_dir / f"{plan_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return WeeklyMealPlan(**data)
        return None
