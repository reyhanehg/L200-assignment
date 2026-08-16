"""Google ADK Pantry & Grocery Manager Agent.

Reconciles kitchen inventory and compiles aisle-categorized shopping lists.
"""

from google.adk import Agent

from src.agents.adk_tools import generate_grocery_list_for_recipes, get_pantry_inventory
from src.config import settings

GROCERY_INSTRUCTION = """You are the Pantry & Grocery Manager Agent in NutriConcierge, built with Google ADK.
Your role:
1. Check pantry stock before generating shopping lists to prevent duplicate purchases.
2. Call generate_grocery_list_for_recipes to calculate missing ingredient quantities.
3. Organize the resulting grocery list into supermarket aisles (Produce, Dairy, Pantry, Meat, etc.) with cost estimates."""

grocery_agent = Agent(
    name="grocery_agent",
    model=settings.gemini_model,
    instruction=GROCERY_INSTRUCTION,
    tools=[generate_grocery_list_for_recipes, get_pantry_inventory],
)
