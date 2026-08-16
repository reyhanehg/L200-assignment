"""Short-term conversational context and session state memory."""

from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.models.schemas import ChatMessage, WeeklyMealPlan


class SessionMemory:
    """Manages short-term conversation turns, active context, and working plan drafts."""

    def __init__(self, session_id: str = "default_session", max_turns: int = 20):
        self.session_id = session_id
        self.max_turns = max_turns
        self._history: deque[ChatMessage] = deque(maxlen=max_turns)
        self.current_meal_plan: Optional[WeeklyMealPlan] = None
        self.active_intent: Optional[str] = None
        self.scratchpad: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()

    def add_message(
        self,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Append a new message to the conversation history."""
        msg = ChatMessage(
            role=role,
            content=content,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        self._history.append(msg)
        return msg

    def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get chronological list of conversation messages."""
        msgs = list(self._history)
        if limit:
            return msgs[-limit:]
        return msgs

    def set_working_meal_plan(self, plan: WeeklyMealPlan) -> None:
        """Store the current working meal plan draft in session context."""
        self.current_meal_plan = plan

    def get_working_meal_plan(self) -> Optional[WeeklyMealPlan]:
        """Retrieve the current working meal plan."""
        return self.current_meal_plan

    def clear(self) -> None:
        """Reset session memory."""
        self._history.clear()
        self.current_meal_plan = None
        self.active_intent = None
        self.scratchpad.clear()
