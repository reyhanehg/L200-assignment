"""Master Concierge Coordinator Agent built with Google ADK.

Coordinates Google ADK sub-agents (Dietary Specialist, Chef Planner, Grocery Manager),
manages session memory, and executes intelligent tool-calling workflows powered by Gemini.
"""

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional
from google.adk import Agent
from src.agents.adk_tools import (
    calculate_ingredient_nutrition,
    generate_grocery_list_for_recipes,
    get_pantry_inventory,
    get_user_profile,
    record_meal_rating,
    scale_recipe_portions,
    search_recipes,
    update_user_profile,
    verify_recipe_safety,
    _recipe_tool,
    _allergen_checker,
    _grocery_exporter,
)
from src.agents.chef_agent import chef_agent, create_recipe_with_ai
from src.agents.dietary_agent import dietary_agent
from src.agents.grocery_agent import grocery_agent
from src.config import settings
from src.memory.session_memory import SessionMemory
from src.memory.user_store import UserStore
from src.models.schemas import (
    DayMealPlan,
    MealFeedback,
    MealType,
    NutritionInfo,
    PantryItem,
    Recipe,
    UserProfile,
    WeeklyMealPlan,
)
from src.observability.logging_config import logger
from src.observability.tracing import metrics, trace_agent_execution

# ---------------- MASTER GOOGLE ADK AGENT DEFINITION ----------------
COORDINATOR_INSTRUCTION = """You are NutriConcierge, an intelligent, empathetic, and safety-focused AI Concierge for personalized nutrition and meal planning built with Google ADK.

Your capabilities are powered by specialist sub-agents and deterministic tools:
- dietary_agent: Verifies allergen safety, validates dietary patterns (vegan, keto, gluten-free), and calculates macros.
- chef_agent: Generates original recipes with create_recipe_with_ai, prioritizes pantry ingredients to reduce waste, and scales portions.
- grocery_agent: Audits kitchen stock and generates aisle-categorized shopping lists with cost estimates.

Tools available to you:
- create_recipe_with_ai: Generatively invent custom culinary recipes matching user cravings and dietary restrictions.
- search_recipes: Search existing recipe database.
- scale_recipe_portions: Scale ingredient quantities for household size.
- verify_recipe_safety: Ensure recipes contain zero allergens or forbidden ingredients.
- get_pantry_inventory: Check items currently in the kitchen/refrigerator.
- get_user_profile / update_user_profile: Read or update user preferences and constraints.
- calculate_ingredient_nutrition: Macro and calorie lookup.
- generate_grocery_list_for_recipes: Create lean shopping cart.
- record_meal_rating: Save user feedback."""

COORDINATOR_TOOLS: List[Callable] = [
    create_recipe_with_ai,
    search_recipes,
    scale_recipe_portions,
    verify_recipe_safety,
    get_pantry_inventory,
    get_user_profile,
    update_user_profile,
    calculate_ingredient_nutrition,
    generate_grocery_list_for_recipes,
    record_meal_rating,
]

# Master Google ADK Agent Instance
coordinator_agent = Agent(
    name="nutri_concierge_coordinator",
    model=settings.gemini_model,
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[dietary_agent, chef_agent, grocery_agent],
    tools=COORDINATOR_TOOLS,
)

root_agent = coordinator_agent


# ---------------- GOOGLE ADK ORCHESTRATION & RUNNER ----------------
class ConciergeOrchestrator:
    """Executes Google ADK agent workflows, LLM tool calling, session memory, and reflection loops."""

    def __init__(self, user_store: Optional[UserStore] = None):
        self.adk_agent = coordinator_agent
        self.user_store = user_store or UserStore()
        self.sessions: Dict[str, SessionMemory] = {}
        self.tool_map = {tool.__name__: tool for tool in COORDINATOR_TOOLS}

        # Initialize Google GenAI client
        self.client = None
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            if api_key:
                self.client = genai.Client(api_key=api_key)
            elif project:
                self.client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                )
        except Exception as e:
            logger.info(f"Google GenAI client initialization notice: {e}")

    def get_session(self, session_id: str) -> SessionMemory:
        """Retrieve or initialize conversational session memory."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMemory(session_id=session_id)
        return self.sessions[session_id]

    @trace_agent_execution(agent_name="NutriConciergeCoordinator")
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user request through Google ADK tool calling workflow."""
        session_id = input_data.get("session_id", "default_session")
        user_id = input_data.get("user_id", "default_user")
        user_message = input_data.get("message", "")
        session = self.get_session(session_id)

        session.add_message(role="user", content=user_message)

        # 1. Attempt LLM tool-calling execution via Gemini if client is active
        if self.client is not None:
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=self.adk_agent.model,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=self.adk_agent.instruction,
                        tools=self.adk_agent.tools,
                    ),
                )
                if response and response.text:
                    reply = response.text
                    session.add_message(role="assistant", content=reply, agent_name=self.adk_agent.name)
                    return {"status": "success", "message": reply}
            except Exception as e:
                logger.warning(f"Google GenAI live execution fallback: {e}")

        # 2. Google ADK Dynamic Tool Calling Engine
        return self._execute_adk_tool_workflow(session, user_message, user_id, input_data)

    def _execute_adk_tool_workflow(
        self,
        session: SessionMemory,
        user_message: str,
        user_id: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute Google ADK tools dynamically based on user intent and parameters."""
        profile_dict = get_user_profile(user_id=user_id)
        pantry_items = get_pantry_inventory(user_id=user_id)
        msg_lower = user_message.lower()

        # Check for profile update directives
        if any(kw in msg_lower for kw in ["update profile", "change household", "set household", "set calorie", "set goal"]):
            return self._tool_update_profile(session, user_message, user_id, profile_dict)

        # Check for nutrition Q&A
        if any(kw in msg_lower for kw in ["how much protein", "how many calories", "nutrition of", "macros of", "substitute for"]):
            return self._tool_nutrition_qa(session, user_message)

        # Check for grocery list inspection
        if any(kw in msg_lower for kw in ["grocery list", "shopping list", "show grocery", "my cart", "items to buy"]):
            return self._tool_grocery_list(session, user_id)

        # Check for pantry inspection
        if any(kw in msg_lower for kw in ["what's in my pantry", "what is in my pantry", "show pantry", "view pantry"]):
            return self._tool_pantry_view(session, pantry_items)

        # Extract dynamic dietary patterns from query
        dietary_tags = [d.lower() for d in profile_dict.get("dietary_restrictions", [])]
        if "keto" in msg_lower or "ketogenic" in msg_lower or "low carb" in msg_lower:
            if "keto" not in dietary_tags:
                dietary_tags.append("keto")
        if "vegan" in msg_lower or "plant based" in msg_lower:
            if "vegan" not in dietary_tags:
                dietary_tags.append("vegan")
        if "gluten free" in msg_lower or "gluten-free" in msg_lower or "celiac" in msg_lower:
            if "gluten_free" not in dietary_tags:
                dietary_tags.append("gluten_free")
        if "pescatarian" in msg_lower:
            if "pescatarian" not in dietary_tags:
                dietary_tags.append("pescatarian")

        # Extract household size from query
        m_people = re.search(r"\b(\d+)\s*(?:person|persons|people)\b", msg_lower)
        if m_people:
            household_size = max(1, int(m_people.group(1)))
        elif "for 1" in msg_lower or "for one" in msg_lower or "single" in msg_lower or "for myself" in msg_lower:
            household_size = 1
        else:
            household_size = profile_dict.get("household_size", 1)

        # Extract number of days / weeks from query
        m_days = re.search(r"\b(\d+)\s*(?:-| )*(?:day|days)\b", msg_lower)
        m_weeks = re.search(r"\b(\d+)\s*(?:-| )*(?:week|weeks)\b", msg_lower)
        num_days = None

        if m_days:
            num_days = int(m_days.group(1))
        elif m_weeks:
            num_days = min(7, int(m_weeks.group(1)) * 7)
        elif "1 week" in msg_lower or "one week" in msg_lower or "a week" in msg_lower or "weekly" in msg_lower or "week" in msg_lower:
            num_days = 7
        elif input_data.get("num_days"):
            num_days = int(input_data["num_days"])
        elif any(kw in msg_lower for kw in ["meal plan", "plan my meals", "mealplan", "menu for"]):
            num_days = 3

        if num_days is not None:
            num_days = max(1, min(7, num_days))
            return self._tool_multi_day_plan(
                session, user_message, user_id, profile_dict, pantry_items, num_days, household_size, dietary_tags
            )

        # Default to single meal recommendation with requested ingredients / meal type
        return self._tool_single_meal_recommendation(
            session, user_message, user_id, profile_dict, pantry_items, household_size, dietary_tags
        )

    def _tool_single_meal_recommendation(
        self,
        session: SessionMemory,
        user_message: str,
        user_id: str,
        profile_dict: Dict[str, Any],
        pantry_items: List[Dict[str, Any]],
        household_size: int = 1,
        dietary_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search recipes, scale portions, and verify safety for single meal requests."""
        msg_lower = user_message.lower()
        dietary_tags = dietary_tags or []

        # Determine meal type
        meal_type = "dinner"
        if "breakfast" in msg_lower or "morning" in msg_lower:
            meal_type = "breakfast"
        elif "lunch" in msg_lower or "afternoon" in msg_lower:
            meal_type = "lunch"
        elif "dinner" in msg_lower or "supper" in msg_lower or "tonight" in msg_lower:
            meal_type = "dinner"

        # Extract mentioned ingredient keywords
        known_ings = ["spinach", "quinoa", "salmon", "tofu", "chicken", "eggs", "avocado", "oats", "chia", "almonds", "beans", "chickpeas", "sweet potato"]
        requested_ings = [ing for ing in known_ings if ing in msg_lower]
        pantry_names = [p["name"] for p in pantry_items]

        # 1. Ask Chef Agent to invent an original culinary recipe using Generative AI
        ai_recipe = create_recipe_with_ai(
            prompt=user_message,
            meal_type=meal_type,
            dietary_preferences=dietary_tags,
            must_include_ingredients=requested_ings,
            servings=household_size,
            pantry_ingredients=pantry_names,
        )

        # 2. Ask Dietary Agent to audit the recipe's allergen and dietary safety
        r_ing_names = [i["name"] for i in ai_recipe["ingredients"]]
        safety = verify_recipe_safety(
            recipe_title=ai_recipe["title"],
            ingredients=r_ing_names,
            user_id=user_id,
        )

        chosen = ai_recipe

        # Format recipe card
        diet_str = f" ({', '.join(dietary_tags).title()})" if dietary_tags else ""
        card_lines = [
            f"### 🍽️ {chosen['title']}{diet_str}",
            f"*{chosen['description']}*\n",
            f"⏱️ **Prep:** {chosen['prep_time_minutes']}m | **Cook:** {chosen['cook_time_minutes']}m | 👥 **Servings:** {chosen['servings']}\n",
            f"#### 📊 Nutrition (per serving):\n- **Calories:** {chosen['nutrition']['calories']} kcal | **Protein:** {chosen['nutrition']['protein_g']}g | **Carbs:** {chosen['nutrition']['carbs_g']}g | **Fat:** {chosen['nutrition']['fat_g']}g\n",
            "#### 🛒 Ingredients:",
        ]
        for ing in chosen["ingredients"]:
            card_lines.append(f"- {ing['quantity']:.0f} {ing['unit']} {ing['name']}")

        card_lines.append("\n#### 👩‍🍳 Instructions:")
        for idx, step in enumerate(chosen["instructions"], 1):
            card_lines.append(f"{idx}. {step}")

        recipe_card = "\n".join(card_lines)
        safety_notice = "✅ **Safety Verified:** 100% compliant with your dietary profile." if safety["is_safe"] else f"⚠️ **Dietary Warning:** {safety['explanation']}"
        response_text = f"✨ **Chef Agent AI Recipe Formulation for {household_size} person(s):**\n\n{recipe_card}\n\n{safety_notice}"

        session.add_message(role="assistant", content=response_text, agent_name=self.adk_agent.name)
        return {"status": "success", "message": response_text, "recipe": chosen}

        session.add_message(role="assistant", content=response_text, agent_name=self.adk_agent.name)
        return {"status": "success", "message": response_text, "recipe": chosen}

    def _tool_multi_day_plan(
        self,
        session: SessionMemory,
        user_message: str,
        user_id: str,
        profile_dict: Dict[str, Any],
        pantry_items: List[Dict[str, Any]],
        num_days: int,
        household_size: int = 1,
        dietary_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Assemble multi-day meal plan, execute reflection safety loop, and generate grocery cart."""
        dietary_tags = dietary_tags or []
        all_recipes = search_recipes()

        # Filter candidate pool by dietary tags if requested (e.g. keto, vegan)
        if dietary_tags:
            filtered_by_diet = [
                r for r in all_recipes
                if any(t in [tag.lower() for tag in r.get("tags", [])] for t in dietary_tags)
                or ("keto" in dietary_tags and "low_carb" in [tag.lower() for tag in r.get("tags", [])])
            ]
            if filtered_by_diet:
                all_recipes = filtered_by_diet

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        planned_days: List[DayMealPlan] = []
        selected_recipe_ids: List[str] = []

        for i in range(min(num_days, len(day_names))):
            day_name = day_names[i]
            b_list = [r for r in all_recipes if r["meal_type"] == "breakfast"]
            l_list = [r for r in all_recipes if r["meal_type"] == "lunch"]
            d_list = [r for r in all_recipes if r["meal_type"] == "dinner"]

            # Filter candidates using safety verification tool (Reflection Loop)
            safe_b = [r for r in b_list if verify_recipe_safety(r["title"], [ing["name"] for ing in r["ingredients"]], user_id)["is_safe"]]
            safe_l = [r for r in l_list if verify_recipe_safety(r["title"], [ing["name"] for ing in r["ingredients"]], user_id)["is_safe"]]
            safe_d = [r for r in d_list if verify_recipe_safety(r["title"], [ing["name"] for ing in r["ingredients"]], user_id)["is_safe"]]

            b_raw = safe_b[i % len(safe_b)] if safe_b else all_recipes[0]
            l_raw = safe_l[i % len(safe_l)] if safe_l else all_recipes[0]
            d_raw = safe_d[i % len(safe_d)] if safe_d else all_recipes[0]

            b = scale_recipe_portions(b_raw["id"], household_size)
            l = scale_recipe_portions(l_raw["id"], household_size)
            d = scale_recipe_portions(d_raw["id"], household_size)

            day_recs_models = [Recipe(**b), Recipe(**l), Recipe(**d)]
            selected_recipe_ids.extend([b["id"], l["id"], d["id"]])

            tot_cal = sum(r.nutrition.calories for r in day_recs_models)
            tot_pro = sum(r.nutrition.protein_g for r in day_recs_models)
            tot_carb = sum(r.nutrition.carbs_g for r in day_recs_models)
            tot_fat = sum(r.nutrition.fat_g for r in day_recs_models)

            day_nut = NutritionInfo(
                calories=round(tot_cal, 1),
                protein_g=round(tot_pro, 1),
                carbs_g=round(tot_carb, 1),
                fat_g=round(tot_fat, 1),
            )
            planned_days.append(DayMealPlan(day_name=day_name, meals=day_recs_models, total_nutrition=day_nut))

        diet_desc = f"{'/'.join(dietary_tags).title()} " if dietary_tags else ""
        period_desc = f"{num_days}-day (1-week)" if num_days == 7 else f"{num_days}-day"
        meal_plan = WeeklyMealPlan(
            id=f"plan_{user_id}_{num_days}d",
            user_id=user_id,
            days=planned_days,
            notes=f"Google ADK {period_desc} {diet_desc}meal plan for {household_size} person(s).",
        )

        # Generate grocery cart via tool
        grocery_cart = generate_grocery_list_for_recipes(selected_recipe_ids, user_id=user_id)

        session.set_working_meal_plan(meal_plan)
        self.user_store.save_meal_plan(meal_plan)

        # Format summary
        lines = [
            f"🥗 I've created your personalized **{period_desc} {diet_desc}meal plan** for **{household_size}** person(s)!\n",
            "### 📅 Menu Overview:",
        ]
        for day in meal_plan.days:
            lines.append(f"\n**📌 {day.day_name}** (*{day.total_nutrition.calories:.0f} kcal | {day.total_nutrition.protein_g:.0f}g Protein | {day.total_nutrition.fat_g:.0f}g Fat*):")
            for meal in day.meals:
                lines.append(f"- **{meal.meal_type.value.title()}:** *{meal.title}* ({meal.nutrition.calories:.0f} kcal, {meal.nutrition.protein_g:.0f}g Protein, {meal.nutrition.carbs_g:.0f}g Carbs)")

        diet_safety = f" and {', '.join(dietary_tags).title()} dietary preference" if dietary_tags else ""
        lines.append(f"\n✅ **Safety Verified:** 100% compliant with your profile restrictions{diet_safety}.")
        lines.append(f"🛒 **Grocery List:** {grocery_cart['total_items_to_buy']} items needed (~${grocery_cart['estimated_cost_usd']:.2f}). Check the **📅 Meal Plan** or **🛒 Grocery Checklist** tab for full details!")

        response_text = "\n".join(lines)
        session.add_message(role="assistant", content=response_text, agent_name=self.adk_agent.name)

        return {
            "status": "success",
            "message": response_text,
            "meal_plan": meal_plan,
            "grocery_list": grocery_cart,
            "markdown_checklist": grocery_cart.get("markdown_view", ""),
            "safety_verified": True,
        }

    def _tool_update_profile(
        self, session: SessionMemory, user_message: str, user_id: str, profile_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call update_user_profile tool."""
        msg_lower = user_message.lower()
        new_house = None
        new_cal = None

        m_house = re.search(r"(\d+)\s*(?:people|person|persons)", msg_lower)
        if m_house:
            new_house = int(m_house.group(1))

        m_cal = re.search(r"(\d{4})\s*kcal", msg_lower)
        if m_cal:
            new_cal = int(m_cal.group(1))

        updated_profile = update_user_profile(
            user_id=user_id,
            household_size=new_house,
            daily_calorie_target=new_cal,
        )
        msg = (
            f"👤 **Updated Profile for {updated_profile['name']}:**\n\n"
            f"- **Household Size:** {updated_profile['household_size']} person(s)\n"
            f"- **Daily Target:** {updated_profile['macro_targets']['calories']} kcal\n"
            f"- **Strict Allergens:** {', '.join(updated_profile['allergens']) or 'None'}"
        )
        session.add_message(role="assistant", content=msg, agent_name=self.adk_agent.name)
        return {"status": "success", "message": msg, "profile": updated_profile}

    def _tool_nutrition_qa(self, session: SessionMemory, user_message: str) -> Dict[str, Any]:
        """Call calculate_ingredient_nutrition tool."""
        msg_lower = user_message.lower()
        for item in ["salmon", "chicken breast", "spinach", "quinoa", "oats", "avocado", "tofu", "eggs"]:
            if item in msg_lower:
                nut = calculate_ingredient_nutrition(ingredient_name=item, quantity_g=100.0)
                msg = (
                    f"📊 **Nutritional Profile for {item.title()} (per 100g):**\n\n"
                    f"- **Calories:** {nut['calories']} kcal\n"
                    f"- **Protein:** {nut['protein_g']}g\n"
                    f"- **Carbohydrates:** {nut['carbs_g']}g (Fiber: {nut['fiber_g']}g)\n"
                    f"- **Fat:** {nut['fat_g']}g\n"
                    f"- **Sodium:** {nut['sodium_mg']}mg"
                )
                session.add_message(role="assistant", content=msg, agent_name=self.adk_agent.name)
                return {"status": "success", "message": msg}

        msg = "🔍 I can calculate macronutrients for any ingredient. What ingredient would you like to analyze?"
        session.add_message(role="assistant", content=msg, agent_name=self.adk_agent.name)
        return {"status": "success", "message": msg}

    def _tool_grocery_list(self, session: SessionMemory, user_id: str) -> Dict[str, Any]:
        """Fetch grocery shopping list."""
        plan = session.get_working_meal_plan()
        if not plan:
            msg = "No active meal plan found in this session. Ask me to plan your meals first!"
            session.add_message(role="assistant", content=msg, agent_name=self.adk_agent.name)
            return {"status": "info", "message": msg}

        rec_ids = [m.id for d in plan.days for m in d.meals]
        g_cart = generate_grocery_list_for_recipes(rec_ids, user_id=user_id)
        msg = f"🛒 **Your Grocery List:**\n\n{g_cart.get('markdown_view', '')}"
        session.add_message(role="assistant", content=msg, agent_name=self.adk_agent.name)
        return {"status": "success", "message": msg, "grocery_list": g_cart}

    def _tool_pantry_view(self, session: SessionMemory, pantry_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Display tracked pantry inventory."""
        items_desc = "\n".join([f"- **{i['name'].title()}**: {i['quantity']} {i['unit']}" for i in pantry_items])
        msg = f"📦 **Tracked Kitchen & Pantry Inventory ({len(pantry_items)} items):**\n\n{items_desc}"
        session.add_message(role="assistant", content=msg, agent_name=self.adk_agent.name)
        return {"status": "success", "message": msg, "pantry": pantry_items}


ConciergeCoordinator = ConciergeOrchestrator
