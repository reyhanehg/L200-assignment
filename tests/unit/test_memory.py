"""Unit tests for Context and Memory layer."""

import tempfile
import unittest
from pathlib import Path

from src.memory.session_memory import SessionMemory
from src.memory.user_store import UserStore
from src.models.schemas import CommonAllergen, DietaryRestriction, MealFeedback, UserProfile


class TestMemoryLayer(unittest.TestCase):
    """Test suite for memory and context persistence."""

    def test_session_memory_turns(self):
        session = SessionMemory(session_id="test_sess", max_turns=3)
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        session.add_message("user", "Plan my meals")
        session.add_message("assistant", "Sure!")

        messages = session.get_messages()
        # Max turns is 3, so oldest message was pruned
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].content, "Hi there!")
        self.assertEqual(messages[-1].content, "Sure!")

    def test_user_store_persistence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = UserStore(data_dir=Path(tmp_dir))

            profile = UserProfile(
                user_id="user_123",
                name="Taylor",
                household_size=3,
                allergens=[CommonAllergen.TREE_NUTS],
                dietary_restrictions=[DietaryRestriction.KETO],
            )
            store.save_profile(profile)

            loaded = store.get_profile("user_123")
            self.assertEqual(loaded.name, "Taylor")
            self.assertEqual(loaded.household_size, 3)
            self.assertIn(CommonAllergen.TREE_NUTS, loaded.allergens)
            self.assertIn(DietaryRestriction.KETO, loaded.dietary_restrictions)

            # Feedback test
            feedback = MealFeedback(
                recipe_id="rec_001",
                recipe_title="Salmon Quinoa Bowl",
                rating=5,
                comments="Delicious and quick!",
            )
            store.record_feedback(feedback, user_id="user_123")
            history = store.get_feedback_history(user_id="user_123")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].rating, 5)


if __name__ == "__main__":
    unittest.main()
