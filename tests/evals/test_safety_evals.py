"""Safety Evaluation Benchmark Suite for NutriConcierge."""

import tempfile
import unittest
from pathlib import Path
from src.agents.coordinator import ConciergeCoordinator
from src.memory.user_store import UserStore
from src.models.schemas import CommonAllergen, DietaryRestriction, UserProfile
from src.observability.tracing import metrics
from src.tools.allergen_checker import AllergenSafetyCheckerTool


class TestSafetyEvaluations(unittest.TestCase):
    """Safety evaluation benchmarks testing diverse dietary constraints."""

    def test_safety_benchmark_profiles(self):
        """Run safety benchmark across multiple complex user profiles."""
        test_profiles = [
            UserProfile(
                user_id="bench_shellfish",
                name="Alice",
                allergens=[CommonAllergen.SHELLFISH, CommonAllergen.FISH],
                dietary_restrictions=[],
            ),
            UserProfile(
                user_id="bench_celiac",
                name="Bob",
                allergens=[CommonAllergen.WHEAT],
                dietary_restrictions=[DietaryRestriction.GLUTEN_FREE],
            ),
            UserProfile(
                user_id="bench_vegan",
                name="Charlie",
                allergens=[CommonAllergen.MILK, CommonAllergen.EGGS],
                dietary_restrictions=[DietaryRestriction.VEGAN],
            ),
        ]

        allergen_checker = AllergenSafetyCheckerTool()

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = UserStore(data_dir=Path(tmp_dir))
            coordinator = ConciergeCoordinator(user_store=store)

            for profile in test_profiles:
                store.save_profile(profile)
                response = coordinator.run({
                    "intent": "PLAN_MEALS",
                    "user_id": profile.user_id,
                    "num_days": 2,
                })

                self.assertEqual(response["status"], "success", f"Failed for profile {profile.user_id}")
                self.assertTrue(response["safety_verified"])

                # Double check all generated recipes in the meal plan
                plan = response["meal_plan"]
                for day in plan.days:
                    for meal in day.meals:
                        check = allergen_checker.check_recipe_safety(meal, profile)
                        self.assertTrue(
                            check.is_safe,
                            f"Safety violation detected in {meal.title} for {profile.user_id}: {check.explanation}",
                        )

        # Verify telemetry metrics recorded the safety verification audits
        summary = metrics.get_summary()
        self.assertGreater(summary["safety_checks"]["total"], 0)
        self.assertGreater(summary["safety_checks"]["passed"], 0)


if __name__ == "__main__":
    unittest.main()
