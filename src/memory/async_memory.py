"""Asynchronous and Background Task Engine for Memory Operations.

Provides non-blocking background workers and coroutine executors for flushing memory state,
syncing relational tables, and updating semantic preferences without blocking request latency.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List, Optional

from src.memory.db_store import DatabaseStore
from src.models.schemas import MealFeedback, PantryItem, UserProfile, WeeklyMealPlan
from src.observability.logging_config import logger


class AsyncMemoryManager:
    """Asynchronous memory manager dispatching persistence and memory compaction tasks to background workers."""

    def __init__(self, db_store: Optional[DatabaseStore] = None, max_workers: int = 4):
        self.db_store = db_store or DatabaseStore()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="AsyncMemoryWorker")

    def run_in_background(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Submit a memory persistence or indexing function to the background executor."""
        try:
            future = self.executor.submit(func, *args, **kwargs)
            future.add_done_callback(self._task_completion_callback)
        except Exception as e:
            logger.error(f"Failed to submit background memory task: {e}")

    def _task_completion_callback(self, future: Any) -> None:
        """Log background memory task results or errors."""
        try:
            future.result()
            logger.debug("Background memory task completed successfully.")
        except Exception as e:
            logger.error(f"Error in background memory operation: {e}")

    # ---------------- ASYNC COROUTINES & BACKGROUND DISPATCHERS ----------------
    async def async_save_profile(self, profile: UserProfile) -> None:
        """Persist user profile asynchronously."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self.db_store.save_profile, profile)

    def dispatch_save_profile_background(self, profile: UserProfile) -> None:
        """Fire-and-forget background worker task for profile persistence."""
        self.run_in_background(self.db_store.save_profile, profile)

    async def async_save_meal_plan(self, plan: WeeklyMealPlan) -> None:
        """Persist meal plan asynchronously."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self.db_store.save_meal_plan, plan)

    def dispatch_save_meal_plan_background(self, plan: WeeklyMealPlan) -> None:
        """Fire-and-forget background worker task for meal plan persistence."""
        self.run_in_background(self.db_store.save_meal_plan, plan)

    async def async_save_pantry(self, user_id: str, items: List[PantryItem]) -> None:
        """Persist pantry inventory asynchronously."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self.db_store.save_pantry, user_id, items)

    def dispatch_save_pantry_background(self, user_id: str, items: List[PantryItem]) -> None:
        """Fire-and-forget background worker task for pantry inventory persistence."""
        self.run_in_background(self.db_store.save_pantry, user_id, items)

    async def async_save_feedback(self, feedback: MealFeedback) -> None:
        """Persist meal feedback asynchronously."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self.db_store.save_feedback, feedback)

    def dispatch_save_feedback_background(self, feedback: MealFeedback) -> None:
        """Fire-and-forget background worker task for meal feedback persistence."""
        self.run_in_background(self.db_store.save_feedback, feedback)

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully shut down background workers."""
        self.executor.shutdown(wait=wait)
