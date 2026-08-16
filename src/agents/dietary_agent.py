"""Google ADK Dietary & Safety Specialist Agent.

Evaluates nutritional balance and enforces strict allergen safety guardrails.
"""

from google.adk import Agent
from src.agents.adk_tools import calculate_ingredient_nutrition, get_user_profile, verify_recipe_safety
from src.config import settings

DIETARY_INSTRUCTION = """You are the Dietary & Safety Specialist Agent in NutriConcierge, built with Google ADK.
Your role:
1. Strictly protect user health by evaluating candidate recipes against user allergen restrictions and dietary patterns.
2. Call verify_recipe_safety for any candidate recipe to ensure no dangerous allergens or forbidden ingredients are present.
3. Call calculate_ingredient_nutrition to analyze macronutrient and micronutrient balance.
Never compromise on allergen safety."""

dietary_agent = Agent(
    name="dietary_agent",
    model=settings.gemini_model,
    instruction=DIETARY_INSTRUCTION,
    tools=[verify_recipe_safety, calculate_ingredient_nutrition, get_user_profile],
)
