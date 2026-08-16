"""Pydantic schemas and data models for NutriConcierge."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DietaryRestriction(str, Enum):
    """Supported dietary restrictions."""
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    PESCATARIAN = "pescatarian"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    LOW_SODIUM = "low_sodium"
    DIABETIC_FRIENDLY = "diabetic_friendly"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    HALAL = "halal"
    KOSHER = "kosher"


class CommonAllergen(str, Enum):
    """Common allergen taxonomy."""
    PEANUTS = "peanuts"
    TREE_NUTS = "tree_nuts"
    MILK = "milk"
    EGGS = "eggs"
    WHEAT = "wheat"
    SOY = "soy"
    FISH = "fish"
    SHELLFISH = "shellfish"
    SESAME = "sesame"
    SULFITES = "sulfites"


class MealType(str, Enum):
    """Meal categories."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MacroTarget(BaseModel):
    """Macronutrient target goals."""
    calories: int = Field(default=2000, description="Target daily calories in kcal")
    protein_g: float = Field(default=120.0, description="Target daily protein in grams")
    carbs_g: float = Field(default=200.0, description="Target daily carbohydrates in grams")
    fat_g: float = Field(default=65.0, description="Target daily fats in grams")
    fiber_g: float = Field(default=30.0, description="Target daily dietary fiber in grams")
    max_sodium_mg: Optional[float] = Field(default=2300.0, description="Maximum daily sodium in mg")


class UserProfile(BaseModel):
    """Long-term user profile for dietary goals, restrictions, and preferences."""
    user_id: str = Field(default="default_user", description="Unique user identifier")
    name: str = Field(default="User", description="User's preferred display name")
    household_size: int = Field(default=1, ge=1, description="Number of people being cooked for")
    allergens: List[CommonAllergen] = Field(default_factory=list, description="Strict allergen avoidance list")
    dietary_restrictions: List[DietaryRestriction] = Field(default_factory=list, description="Dietary choices")
    disliked_ingredients: List[str] = Field(default_factory=list, description="Ingredients to avoid based on taste")
    macro_targets: MacroTarget = Field(default_factory=MacroTarget, description="Daily nutritional objectives")
    cooking_skill_level: str = Field(default="intermediate", description="beginner, intermediate, advanced")
    max_prep_time_minutes: int = Field(default=45, description="Maximum desired meal prep time")
    available_appliances: List[str] = Field(
        default_factory=lambda: ["stovetop", "oven", "refrigerator"],
        description="Kitchen equipment available"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PantryItem(BaseModel):
    """Item tracked in the user's pantry or refrigerator."""
    id: str = Field(..., description="Unique item ID")
    name: str = Field(..., description="Ingredient name")
    category: str = Field(default="Pantry", description="Produce, Dairy, Meat, Pantry, Spices, Frozen, Bakery")
    quantity: float = Field(default=1.0, ge=0.0)
    unit: str = Field(default="count", description="grams, count, cups, tbsp, oz, lbs, ml")
    expiration_date: Optional[date] = Field(default=None, description="Expiration date if perishable")
    added_at: datetime = Field(default_factory=datetime.utcnow)


class Ingredient(BaseModel):
    """Ingredient component of a recipe."""
    name: str
    quantity: float
    unit: str
    category: str = "Pantry"
    notes: Optional[str] = None


class NutritionInfo(BaseModel):
    """Nutritional breakdown of an ingredient or full recipe."""
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    sugar_g: float = 0.0


class SafetyCheckResult(BaseModel):
    """Outcome of deterministic allergen and dietary safety verification."""
    is_safe: bool = True
    violates_allergens: List[str] = Field(default_factory=list)
    violates_dietary_rules: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    explanation: str = "Safe for consumption."


class Recipe(BaseModel):
    """Detailed recipe specification."""
    id: str
    title: str
    description: str
    meal_type: MealType
    servings: int = 1
    prep_time_minutes: int = 15
    cook_time_minutes: int = 20
    ingredients: List[Ingredient]
    instructions: List[str]
    nutrition: NutritionInfo
    tags: List[str] = Field(default_factory=list)
    safety_check: Optional[SafetyCheckResult] = None


class DayMealPlan(BaseModel):
    """Meal plan for a single day."""
    day_name: str
    meals: List[Recipe] = Field(default_factory=list)
    total_nutrition: NutritionInfo = Field(default_factory=NutritionInfo)


class WeeklyMealPlan(BaseModel):
    """Weekly meal plan schedule."""
    id: str
    user_id: str
    days: List[DayMealPlan] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""


class GroceryItem(BaseModel):
    """Individual item on a grocery shopping list."""
    name: str
    category: str
    needed_quantity: float
    pantry_quantity: float
    to_buy_quantity: float
    unit: str
    is_purchased: bool = False


class GroceryList(BaseModel):
    """Complete grocery shopping list categorized by supermarket aisle."""
    id: str
    user_id: str
    items_by_category: Dict[str, List[GroceryItem]] = Field(default_factory=dict)
    total_items_to_buy: int = 0
    estimated_cost_usd: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MealFeedback(BaseModel):
    """User feedback and rating for a prepared meal."""
    recipe_id: str
    recipe_title: str
    rating: int = Field(..., ge=1, le=5, description="1 to 5 stars")
    comments: Optional[str] = None
    cooked_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRole(str, Enum):
    """Roles in the multi-agent orchestration architecture."""
    COORDINATOR = "Concierge Coordinator"
    DIETARY_SPECIALIST = "Dietary & Safety Specialist"
    CHEF_PLANNER = "Executive Chef & Meal Planner"
    GROCERY_MANAGER = "Pantry & Grocery Manager"


class ChatMessage(BaseModel):
    """Conversational turn message."""
    role: str = Field(..., description="user, assistant, or system")
    content: str
    agent_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
