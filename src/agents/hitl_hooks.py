"""Human-in-the-Loop (HITL) Action Confirmation Hooks.

Provides deterministic approval barriers, proposal interception, and rollback capabilities
before executing state-mutating actions (profile modifications, meal plan overwrites, pantry changes).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.observability.logging_config import logger


class ActionType(str, Enum):
    UPDATE_PROFILE = "update_profile"
    OVERWRITE_MEAL_PLAN = "overwrite_meal_plan"
    MODIFY_PANTRY = "modify_pantry"
    CHECKOUT_GROCERY = "checkout_grocery"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass
class ActionProposal:
    """A proposed state-mutating action awaiting explicit human confirmation."""

    proposal_id: str
    action_type: ActionType
    description: str
    payload: Dict[str, Any]
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolution_message: Optional[str] = None


class HITLConfirmationManager:
    """Manages pending action proposals, human approval gates, and execution callbacks."""

    def __init__(self):
        self._pending_proposals: Dict[str, ActionProposal] = {}
        self._action_handlers: Dict[ActionType, Callable[[Dict[str, Any]], Any]] = {}

    def register_handler(self, action_type: ActionType, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register the execution function for an approved action."""
        self._action_handlers[action_type] = handler

    def create_proposal(
        self,
        action_type: ActionType,
        description: str,
        payload: Dict[str, Any],
    ) -> ActionProposal:
        """Create and register a pending proposal requiring human confirmation."""
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        proposal = ActionProposal(
            proposal_id=proposal_id,
            action_type=action_type,
            description=description,
            payload=payload,
            status=ProposalStatus.PENDING,
        )
        self._pending_proposals[proposal_id] = proposal
        logger.info(
            f"HITL Action Proposal Created [{proposal_id}]: {description}",
            extra={"proposal_id": proposal_id, "action_type": action_type.value, "status": "PENDING_CONFIRMATION"},
        )
        return proposal

    def get_pending_proposals(self) -> List[ActionProposal]:
        """List all proposals awaiting human decision."""
        return [p for p in self._pending_proposals.values() if p.status == ProposalStatus.PENDING]

    def get_proposal(self, proposal_id: str) -> Optional[ActionProposal]:
        """Fetch proposal by ID."""
        return self._pending_proposals.get(proposal_id)

    def approve_and_execute(self, proposal_id: str) -> Dict[str, Any]:
        """Approve a proposal and execute its registered action handler."""
        proposal = self._pending_proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": f"Proposal {proposal_id} not found."}

        if proposal.status != ProposalStatus.PENDING:
            return {"status": "error", "message": f"Proposal is already {proposal.status.value}."}

        proposal.status = ProposalStatus.APPROVED
        handler = self._action_handlers.get(proposal.action_type)
        if not handler:
            return {"status": "error", "message": f"No execution handler for {proposal.action_type}."}

        try:
            result = handler(proposal.payload)
            proposal.status = ProposalStatus.EXECUTED
            proposal.resolution_message = "Action approved and executed successfully."
            logger.info(f"HITL Proposal [{proposal_id}] APPROVED and EXECUTED.", extra={"proposal_id": proposal_id})
            return {"status": "success", "result": result, "proposal": proposal}
        except Exception as e:
            logger.error(f"Error executing approved proposal {proposal_id}: {e}")
            return {"status": "error", "message": f"Execution failed: {e}"}

    def reject(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject and cancel a proposed action."""
        proposal = self._pending_proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": f"Proposal {proposal_id} not found."}

        proposal.status = ProposalStatus.REJECTED
        proposal.resolution_message = f"Action rejected by user: {reason or 'No reason provided.'}"
        logger.info(f"HITL Proposal [{proposal_id}] REJECTED by user.", extra={"proposal_id": proposal_id, "reason": reason})
        return {"status": "rejected", "message": proposal.resolution_message, "proposal": proposal}
