"""Strategic LLM Model Routing Engine.

Dynamically selects the optimal Gemini model tier based on task complexity,
token budget, latency requirements, and reasoning depth.
"""

from enum import Enum
from typing import Optional

from src.config import settings
from src.observability.logging_config import logger


class TaskTier(str, Enum):
    FAST = "fast"          # Triage, intent classification, nutrition lookups, pantry audits
    STANDARD = "standard"  # Single meal queries, grocery reconciliation
    REASONING = "reasoning"# Combinatorial multi-day planning, generative AI recipe creation, reflection safety


class ModelRouter:
    """Strategic router mapping incoming agent tasks to the optimal Gemini model tier."""

    def __init__(
        self,
        flash_model: str = "gemini-1.5-flash",
        pro_model: str = "gemini-1.5-pro",
    ):
        self.flash_model = flash_model
        self.pro_model = pro_model or settings.gemini_model

    def select_model(self, task_type: str, user_message: Optional[str] = None) -> str:
        """Dynamically select the optimal model tier based on semantic task classification.

        Args:
            task_type: Identified agent task ('triage', 'nutrition_qa', 'recipe_creation', 'weekly_planning', 'safety_reflection').
            user_message: Raw user query text for complexity heuristics.

        Returns:
            The selected model identifier (e.g. 'gemini-1.5-flash' vs 'gemini-1.5-pro').
        """
        msg_lower = (user_message or "").lower()

        # 1. Fast Tier -> Flash (low latency, high throughput, cost-efficient)
        if task_type in ["triage", "nutrition_qa", "pantry_audit", "greeting"]:
            selected = self.flash_model
            tier = TaskTier.FAST
        # 2. Deep Reasoning Tier -> Pro (high reasoning, combinatorial constraints, reflection)
        elif task_type in ["weekly_planning", "recipe_creation", "safety_reflection", "multi_agent_coordination"]:
            selected = self.pro_model
            tier = TaskTier.REASONING
        # 3. Dynamic query heuristic
        elif any(kw in msg_lower for kw in ["week", "7-day", "plan meals", "invent", "create recipe"]):
            selected = self.pro_model
            tier = TaskTier.REASONING
        else:
            selected = self.flash_model
            tier = TaskTier.FAST

        logger.info(
            f"Strategic Model Routing: Task [{task_type}] routed to tier [{tier.value}] -> Model: {selected}",
            extra={"task_type": task_type, "tier": tier.value, "model": selected},
        )
        return selected
