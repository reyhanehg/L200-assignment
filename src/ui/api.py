import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.agents.coordinator import ConciergeCoordinator
from src.config import settings
from src.models.schemas import (
    PantryItem,
    UserProfile,
    WeeklyMealPlan,
)
from src.observability.logging_config import logger
from src.observability.tracing import metrics


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="REST API for Autonomous Personalized Nutrition & Meal Planning Concierge Agent",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

coordinator = ConciergeCoordinator()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    user_id: str = "default_user"
    num_days: Optional[int] = 3


class PlanRequest(BaseModel):
    user_id: str = "default_user"
    num_days: int = 3


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
    }


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest) -> Dict[str, Any]:
    """Chat with the Concierge Coordinator."""
    try:
        response = coordinator.run({
            "message": req.message,
            "session_id": req.session_id,
            "user_id": req.user_id,
            "num_days": req.num_days,
        })
        return response
    except Exception as e:
        logger.error(f"Error in /api/chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile/{user_id}")
def get_profile(user_id: str = "default_user") -> UserProfile:
    """Retrieve user profile."""
    return coordinator.user_store.get_profile(user_id)


@app.post("/api/profile")
def update_profile(profile: UserProfile) -> Dict[str, Any]:
    """Update user profile."""
    coordinator.user_store.save_profile(profile)
    return {"status": "success", "profile": profile}


@app.get("/api/pantry/{user_id}")
def get_pantry(user_id: str = "default_user") -> List[PantryItem]:
    """Retrieve pantry items."""
    return coordinator.user_store.get_pantry(user_id)


@app.post("/api/plan")
def generate_meal_plan(req: PlanRequest) -> Dict[str, Any]:
    """Generate a validated meal plan."""
    return coordinator.run({
        "intent": "PLAN_MEALS",
        "user_id": req.user_id,
        "num_days": req.num_days,
        "message": f"Generate a {req.num_days}-day meal plan.",
    })


@app.get("/api/metrics")
def get_observability_metrics() -> Dict[str, Any]:
    """Return runtime telemetry and evaluation metrics."""
    return metrics.get_summary()
