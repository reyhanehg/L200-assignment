"""Allergen and Dietary Safety Verification Tool.

Provides deterministic, rule-based safety checking of recipes against user allergy profiles,
dietary restrictions, and ingredient dislikes to prevent hallucinations and allergic hazards.
"""

from typing import Dict, List, Set

from src.models.schemas import (
    CommonAllergen,
    DietaryRestriction,
    Recipe,
    SafetyCheckResult,
    UserProfile,
)

# Comprehensive mapping of allergen categories to trigger keywords & derivatives
ALLERGEN_TRIGGER_MAP: Dict[CommonAllergen, Set[str]] = {
    CommonAllergen.PEANUTS: {
        "peanut", "peanuts", "peanut butter", "peanut oil", "groundnut", "groundnuts",
        "arachis oil", "beer nuts", "monkey nuts"
    },
    CommonAllergen.TREE_NUTS: {
        "almond", "almonds", "almond milk", "almond flour", "almond butter",
        "walnut", "walnuts", "cashew", "cashews", "cashew milk", "cashew cream",
        "pecan", "pecans", "pistachio", "pistachios", "hazelnut", "hazelnuts",
        "macadamia", "macadamias", "brazil nut", "brazil nuts", "pine nut", "pine nuts",
        "praline", "marzipan", "nutella"
    },
    CommonAllergen.MILK: {
        "dairy", "cheese", "butter", "ghee", "yogurt", "cream", "sour cream",
        "whey", "casein", "parmesan", "cheddar", "mozzarella", "feta", "ricotta",
        "brie", "heavy cream", "buttermilk", "ice cream", "custard", "whole milk",
        "skim milk", "cow milk", "goat milk", "milk chocolate"
    },
    CommonAllergen.EGGS: {
        "egg", "eggs", "egg white", "egg whites", "egg yolk", "egg yolks",
        "mayonnaise", "mayo", "meringue", "ovalbumin", "albumin", "custard"
    },
    CommonAllergen.WHEAT: {
        "wheat", "flour", "all-purpose flour", "whole wheat", "bread", "pasta",
        "couscous", "semolina", "bulgur", "farro", "spelt", "seitan", "breadcrumbs",
        "soy sauce", "wheat bran", "wheat germ"
    },
    CommonAllergen.SOY: {
        "soy", "soya", "soybean", "soybeans", "tofu", "tempeh", "edamame",
        "soy sauce", "tamari", "miso", "soy milk", "soy lecithin", "natto", "textured vegetable protein"
    },
    CommonAllergen.FISH: {
        "fish", "salmon", "tuna", "cod", "tilapia", "trout", "halibut", "mackerel",
        "sardine", "sardines", "anchovy", "anchovies", "fish sauce", "bass", "snapper", "mahi mahi"
    },
    CommonAllergen.SHELLFISH: {
        "shellfish", "shrimp", "shrimps", "prawn", "prawns", "crab", "crabs", "crabmeat",
        "lobster", "lobsters", "clam", "clams", "mussel", "mussels", "oyster", "oysters",
        "scallop", "scallops", "squid", "calamari", "octopus"
    },
    CommonAllergen.SESAME: {
        "sesame", "sesame seed", "sesame seeds", "sesame oil", "tahini", "hummus", "halva"
    },
    CommonAllergen.SULFITES: {
        "sulfite", "sulfites", "sulphite", "sulphites", "wine", "red wine", "white wine",
        "dried fruit", "dried apricots"
    },
}

# Meat triggers for vegetarian/vegan diets
MEAT_TRIGGERS: Set[str] = {
    "beef", "ground beef", "steak", "pork", "bacon", "ham", "prosciutto", "sausage",
    "chicken", "chicken breast", "chicken thigh", "turkey", "ground turkey", "duck",
    "lamb", "veal", "gelatin", "lard", "bone broth"
}


class AllergenSafetyCheckerTool:
    """Deterministic allergen and dietary constraint safety validation tool."""

    def __init__(self):
        self.allergen_map = ALLERGEN_TRIGGER_MAP
        self.meat_triggers = MEAT_TRIGGERS

    def check_recipe_safety(self, recipe: Recipe, profile: UserProfile) -> SafetyCheckResult:
        """Verify that a recipe strictly complies with a user's allergen, dietary, and taste constraints."""
        violates_allergens: List[str] = []
        violates_dietary: List[str] = []
        warnings: List[str] = []

        # Collect all ingredient text strings
        ingredient_texts = [ing.name.lower().strip() for ing in recipe.ingredients]

        # 1. Check Allergens
        for allergen in profile.allergens:
            triggers = self.allergen_map.get(allergen, set())
            for ing_text in ingredient_texts:
                for trig in triggers:
                    if trig in ing_text or ing_text in trig:
                        violates_allergens.append(
                            f"Allergen [{allergen.value.upper()}] detected in ingredient '{ing_text}' (trigger: '{trig}')"
                        )
                        break

        # 2. Check Dietary Restrictions
        for diet in profile.dietary_restrictions:
            if diet == DietaryRestriction.VEGAN:
                # No meat, fish, shellfish, dairy, eggs, honey, gelatin
                for ing_text in ingredient_texts:
                    if any(m in ing_text for m in self.meat_triggers):
                        violates_dietary.append(f"Vegan violation: meat ingredient '{ing_text}'")
                    elif any(f in ing_text for f in self.allergen_map[CommonAllergen.FISH]):
                        violates_dietary.append(f"Vegan violation: fish ingredient '{ing_text}'")
                    elif any(s in ing_text for s in self.allergen_map[CommonAllergen.SHELLFISH]):
                        violates_dietary.append(f"Vegan violation: shellfish ingredient '{ing_text}'")
                    elif any(d in ing_text for d in self.allergen_map[CommonAllergen.MILK]):
                        violates_dietary.append(f"Vegan violation: dairy ingredient '{ing_text}'")
                    elif any(e in ing_text for e in self.allergen_map[CommonAllergen.EGGS]):
                        violates_dietary.append(f"Vegan violation: egg ingredient '{ing_text}'")
                    elif "honey" in ing_text:
                        violates_dietary.append(f"Vegan violation: honey ingredient '{ing_text}'")

            elif diet == DietaryRestriction.VEGETARIAN:
                for ing_text in ingredient_texts:
                    if any(m in ing_text for m in self.meat_triggers):
                        violates_dietary.append(f"Vegetarian violation: meat ingredient '{ing_text}'")
                    elif any(f in ing_text for f in self.allergen_map[CommonAllergen.FISH]):
                        violates_dietary.append(f"Vegetarian violation: fish ingredient '{ing_text}'")
                    elif any(s in ing_text for s in self.allergen_map[CommonAllergen.SHELLFISH]):
                        violates_dietary.append(f"Vegetarian violation: shellfish ingredient '{ing_text}'")

            elif diet == DietaryRestriction.PESCATARIAN:
                for ing_text in ingredient_texts:
                    if any(m in ing_text for m in self.meat_triggers):
                        violates_dietary.append(f"Pescatarian violation: land meat ingredient '{ing_text}'")

            elif diet == DietaryRestriction.GLUTEN_FREE:
                for ing_text in ingredient_texts:
                    if any(w in ing_text for w in self.allergen_map[CommonAllergen.WHEAT]):
                        violates_dietary.append(f"Gluten-Free violation: gluten-containing ingredient '{ing_text}'")

            elif diet == DietaryRestriction.DAIRY_FREE:
                for ing_text in ingredient_texts:
                    if any(d in ing_text for d in self.allergen_map[CommonAllergen.MILK]):
                        violates_dietary.append(f"Dairy-Free violation: dairy ingredient '{ing_text}'")

            elif diet == DietaryRestriction.KETO:
                high_carb_triggers = ["sugar", "pasta", "white rice", "bread", "potato", "flour", "syrup"]
                for ing_text in ingredient_texts:
                    if any(c in ing_text for c in high_carb_triggers):
                        violates_dietary.append(f"Keto violation: high carb ingredient '{ing_text}'")

        # 3. Check Disliked Ingredients
        for disliked in profile.disliked_ingredients:
            d_clean = disliked.lower().strip()
            for ing_text in ingredient_texts:
                if d_clean in ing_text or ing_text in d_clean:
                    warnings.append(f"Ingredient '{ing_text}' contains disliked item '{disliked}'")

        is_safe = len(violates_allergens) == 0 and len(violates_dietary) == 0
        if is_safe:
            explanation = "Recipe passed all allergen and dietary safety constraints."
            if warnings:
                explanation += f" Warning notes: {'; '.join(warnings)}"
        else:
            explanation = "Recipe failed safety check: "
            if violates_allergens:
                explanation += f"Allergens: {'; '.join(violates_allergens)}. "
            if violates_dietary:
                explanation += f"Dietary Violations: {'; '.join(violates_dietary)}."

        return SafetyCheckResult(
            is_safe=is_safe,
            violates_allergens=violates_allergens,
            violates_dietary_rules=violates_dietary,
            warnings=warnings,
            explanation=explanation,
        )
