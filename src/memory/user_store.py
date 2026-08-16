"""Long-term persistent memory store for User Profiles, Pantry, and Feedback History."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from src.config import settings
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

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir = self.data_dir / "profiles"
        self.pantry_dir = self.data_dir / "pantry"
        self.feedback_dir = self.data_dir / "feedback"
        self.plans_dir = self.data_dir / "plans"

        for d in [self.profiles_dir, self.pantry_dir, self.feedback_dir, self.plans_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # 1. Profile Management
    def get_profile(self, user_id: str = "default_user") -> UserProfile:
        """Load user profile from persistent storage or initialize default."""
        file_path = self.profiles_dir / f"{user_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserProfile(**data)

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

    def save_profile(self, profile: UserProfile) -> None:
        """Persist user profile to disk."""
        file_path = self.profiles_dir / f"{profile.user_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))

    # 2. Pantry Management
    def get_pantry(self, user_id: str = "default_user") -> List[PantryItem]:
        """Load tracked pantry inventory for a user."""
        file_path = self.pantry_dir / f"{user_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [PantryItem(**item) for item in data]

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

    def save_pantry(self, items: List[PantryItem], user_id: str = "default_user") -> None:
        """Persist pantry inventory to disk."""
        file_path = self.pantry_dir / f"{user_id}.json"
        data = [item.model_dump(mode="json") for item in items]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # 3. Meal Feedback & Long-Term Preferences
    def record_feedback(self, feedback: MealFeedback, user_id: str = "default_user") -> None:
        """Save user feedback on a cooked recipe to personalize future plans."""
        file_path = self.feedback_dir / f"{user_id}.json"
        feedback_list = []
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                feedback_list = json.load(f)

        feedback_list.append(feedback.model_dump(mode="json"))
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feedback_list, f, indent=2, default=str)

    def get_feedback_history(self, user_id: str = "default_user") -> List[MealFeedback]:
        """Load history of recipe ratings and comments."""
        file_path = self.feedback_dir / f"{user_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [MealFeedback(**item) for item in data]
        return []

    # 4. Meal Plan Persistence
    def save_meal_plan(self, plan: WeeklyMealPlan) -> None:
        """Persist a generated weekly meal plan."""
        file_path = self.plans_dir / f"{plan.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))

    def get_meal_plan(self, plan_id: str) -> Optional[WeeklyMealPlan]:
        """Load a saved meal plan by ID."""
        file_path = self.plans_dir / f"{plan_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return WeeklyMealPlan(**data)
        return None
