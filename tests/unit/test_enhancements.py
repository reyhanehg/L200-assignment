"""Unit tests for the new Architectural Enhancements:
- SQLite DatabaseStore
- AsyncMemoryManager
- ModelRouter
- HITL Confirmation Hooks
- PII Scrubber
- Secret Manager Loader
"""

import tempfile
import unittest
from pathlib import Path

from src.agents.hitl_hooks import ActionType, HITLConfirmationManager, ProposalStatus
from src.agents.model_router import ModelRouter
from src.config import load_secret_from_secret_manager
from src.memory.async_memory import AsyncMemoryManager
from src.memory.db_store import DatabaseStore
from src.models.schemas import CommonAllergen, DietaryRestriction, MealFeedback, PantryItem, UserProfile
from src.observability.pii_scrubber import PIIScrubber


class TestArchitecturalEnhancements(unittest.TestCase):
    """Tests covering Database, Async Memory, Model Routing, HITL, PII Redaction, and Secret Management."""

    def test_pii_scrubber_redaction(self):
        """Verify that PII tokens (emails, phones, API keys, cards, SSNs) are scrubbed."""
        raw_text = (
            "Contact user at alex.doe@example.com or +1-555-123-4567. "
            "Secret: AIzaSyD3fakeSecretKey1234567890abcdef and card 4111-2222-3333-4444. SSN: 123-45-6789."
        )
        scrubbed = PIIScrubber.scrub_text(raw_text)

        self.assertNotIn("alex.doe@example.com", scrubbed)
        self.assertNotIn("+1-555-123-4567", scrubbed)
        self.assertNotIn("AIzaSyD3fakeSecretKey1234567890abcdef", scrubbed)
        self.assertNotIn("4111-2222-3333-4444", scrubbed)
        self.assertNotIn("123-45-6789", scrubbed)

        self.assertIn("[REDACTED_EMAIL]", scrubbed)
        self.assertIn("[REDACTED_PHONE]", scrubbed)
        self.assertIn("[REDACTED_API_KEY]", scrubbed)
        self.assertIn("[REDACTED_CREDIT_CARD]", scrubbed)
        self.assertIn("[REDACTED_SSN]", scrubbed)

        # Dictionary scrubbing
        data = {"email": "test@example.com", "nested": [{"phone": "555-987-6543"}]}
        scrubbed_data = PIIScrubber.scrub_data(data)
        self.assertEqual(scrubbed_data["email"], "[REDACTED_EMAIL]")
        self.assertEqual(scrubbed_data["nested"][0]["phone"], "[REDACTED_PHONE]")

    def test_model_router_strategic_selection(self):
        """Verify dynamic tier selection between Flash (fast) and Pro (reasoning)."""
        router = ModelRouter(flash_model="gemini-1.5-flash", pro_model="gemini-1.5-pro")

        # Fast tasks route to Flash
        m_triage = router.select_model(task_type="triage")
        self.assertEqual(m_triage, "gemini-1.5-flash")

        m_nut = router.select_model(task_type="nutrition_qa")
        self.assertEqual(m_nut, "gemini-1.5-flash")

        # Complex reasoning tasks route to Pro
        m_week = router.select_model(task_type="weekly_planning")
        self.assertEqual(m_week, "gemini-1.5-pro")

        m_chef = router.select_model(task_type="recipe_creation")
        self.assertEqual(m_chef, "gemini-1.5-pro")

        # Dynamic query heuristic
        m_heur = router.select_model(task_type="custom", user_message="Please create a 7-day meal plan for 4 people")
        self.assertEqual(m_heur, "gemini-1.5-pro")

    def test_hitl_action_proposal_lifecycle(self):
        """Verify Human-in-the-Loop action creation, approval, and execution."""
        hitl = HITLConfirmationManager()
        executed_payloads = []

        # Register handler
        hitl.register_handler(ActionType.UPDATE_PROFILE, lambda p: executed_payloads.append(p))

        # Create proposal
        proposal = hitl.create_proposal(
            action_type=ActionType.UPDATE_PROFILE,
            description="Change household size to 4",
            payload={"user_id": "test_user", "household_size": 4},
        )
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(len(hitl.get_pending_proposals()), 1)

        # Approve and execute
        res = hitl.approve_and_execute(proposal.proposal_id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(proposal.status, ProposalStatus.EXECUTED)
        self.assertEqual(len(executed_payloads), 1)
        self.assertEqual(executed_payloads[0]["household_size"], 4)

        # Test Rejection
        proposal2 = hitl.create_proposal(
            action_type=ActionType.MODIFY_PANTRY,
            description="Clear entire pantry",
            payload={"user_id": "test_user"},
        )
        rej_res = hitl.reject(proposal2.proposal_id, reason="Do not clear my stock")
        self.assertEqual(rej_res["status"], "rejected")
        self.assertEqual(proposal2.status, ProposalStatus.REJECTED)

    def test_sqlite_database_store_persistence(self):
        """Verify ACID relational SQLite database storage for profiles, pantry, and feedback."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test_store.db"
            db = DatabaseStore(db_path=db_path)

            # Profile Persistence
            profile = UserProfile(
                user_id="u_sql",
                name="Sam",
                household_size=3,
                allergens=[CommonAllergen.SHELLFISH],
                dietary_restrictions=[DietaryRestriction.KETO],
            )
            db.save_profile(profile)
            fetched_profile = db.get_profile("u_sql")
            self.assertIsNotNone(fetched_profile)
            self.assertEqual(fetched_profile.name, "Sam")
            self.assertEqual(fetched_profile.household_size, 3)
            self.assertIn(CommonAllergen.SHELLFISH, fetched_profile.allergens)

            # Pantry Persistence
            pantry_items = [
                PantryItem(id="item_1", name="spinach", quantity=200, unit="g", category="Produce"),
                PantryItem(id="item_2", name="olive oil", quantity=500, unit="ml", category="Pantry"),
            ]
            db.save_pantry("u_sql", pantry_items)
            fetched_pantry = db.get_pantry("u_sql")
            self.assertEqual(len(fetched_pantry), 2)
            self.assertEqual(fetched_pantry[0].name, "spinach")

            # Feedback Persistence
            feedback = MealFeedback(recipe_id="rec_001", recipe_title="Salmon Bowl", rating=5, comments="Delicious meal!")
            db.save_feedback(feedback, user_id="u_sql")
            fetched_fb = db.get_feedback("u_sql")
            self.assertEqual(len(fetched_fb), 1)
            self.assertEqual(fetched_fb[0].rating, 5)

    def test_async_memory_manager_background_dispatch(self):
        """Verify asynchronous non-blocking memory task execution."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "async_test.db"
            db = DatabaseStore(db_path=db_path)
            async_mem = AsyncMemoryManager(db_store=db, max_workers=2)

            profile = UserProfile(user_id="async_user", name="Taylor", household_size=1)
            async_mem.dispatch_save_profile_background(profile)

            # Allow background worker to complete
            async_mem.shutdown(wait=True)

            fetched = db.get_profile("async_user")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.name, "Taylor")

    def test_secret_manager_loader_fallback(self):
        """Verify Secret Manager fallback to local environment variables."""
        secret_val = load_secret_from_secret_manager("non-existent-secret-id")
        self.assertIsNone(secret_val)
