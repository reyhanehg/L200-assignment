"""Integration tests for Multi-Agent Orchestration & Reflection Logic."""

import tempfile
import unittest
from pathlib import Path
from src.agents.coordinator import ConciergeCoordinator
from src.memory.user_store import UserStore
from src.models.schemas import CommonAllergen, DietaryRestriction, UserProfile


class TestMultiAgentWorkflow(unittest.TestCase):
    """Integration test suite for multi-agent workflow."""

    def test_multi_agent_meal_planning_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = UserStore(data_dir=Path(tmp_dir))
            profile = UserProfile(
                user_id="test_user",
                name="Jordan",
                household_size=2,
                allergens=[CommonAllergen.PEANUTS],
                dietary_restrictions=[DietaryRestriction.GLUTEN_FREE],
            )
            store.save_profile(profile)

            coordinator = ConciergeCoordinator(user_store=store)
            response = coordinator.run({
                "message": "Please plan my meals for the next 3 days",
                "user_id": "test_user",
                "session_id": "test_session",
                "num_days": 3,
            })

            self.assertEqual(response["status"], "success")
            self.assertTrue(response["safety_verified"])
            self.assertIn("meal_plan", response)
            self.assertEqual(len(response["meal_plan"].days), 3)
            self.assertIn("grocery_list", response)
            self.assertGreaterEqual(response["grocery_list"].total_items_to_buy, 0)

    def test_coordinator_intent_routing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = UserStore(data_dir=Path(tmp_dir))
            coordinator = ConciergeCoordinator(user_store=store)

            # 1. Pantry query intent
            res_pantry = coordinator.run({
                "message": "What is in my pantry inventory?",
                "user_id": "default_user",
            })
            self.assertTrue("pantry" in res_pantry or "Pantry" in res_pantry["message"])

            # 2. General greeting intent
            res_greet = coordinator.run({
                "message": "Hello there!",
                "user_id": "default_user",
            })
            self.assertIn("NutriConcierge", res_greet["message"])


if __name__ == "__main__":
    unittest.main()
