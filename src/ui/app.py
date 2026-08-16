import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import streamlit as st

from src.agents.coordinator import ConciergeCoordinator
from src.models.schemas import (
    CommonAllergen,
    DietaryRestriction,
    PantryItem,
)
from src.observability.tracing import metrics

st.set_page_config(
    page_title="NutriConcierge AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize coordinator in session state
if "coordinator" not in st.session_state:
    st.session_state.coordinator = ConciergeCoordinator()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 Hi there! I'm **NutriConcierge AI**, your personal nutritionist and executive chef. How can I help you plan your meals or manage your pantry today?",
        }
    ]

if "current_plan" not in st.session_state:
    st.session_state.current_plan = None

if "current_grocery" not in st.session_state:
    st.session_state.current_grocery = None

coordinator: ConciergeCoordinator = st.session_state.coordinator
user_id = "default_user"
profile = coordinator.user_store.get_profile(user_id)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/salad.png", width=64)
    st.title("🥗 NutriConcierge")
    st.caption("Autonomous Nutrition & Logistics Concierge")

    st.subheader("👤 User Profile & Safety")
    user_name = st.text_input("Name", value=profile.name)
    household_size = st.number_input("Household Size", min_value=1, max_value=10, value=profile.household_size)

    # Allergens
    all_allergens = [a.value for a in CommonAllergen]
    curr_allergens = [a.value for a in profile.allergens]
    selected_allergens = st.multiselect("⚠️ Strict Allergens", options=all_allergens, default=curr_allergens)

    # Diets
    all_diets = [d.value for d in DietaryRestriction]
    curr_diets = [d.value for d in profile.dietary_restrictions]
    selected_diets = st.multiselect("🥗 Dietary Restrictions", options=all_diets, default=curr_diets)

    # Macros
    cal_target = st.slider("Daily Calories (kcal)", min_value=1200, max_value=4000, value=profile.macro_targets.calories, step=50)
    pro_target = st.slider("Protein Target (g)", min_value=40, max_value=250, value=int(profile.macro_targets.protein_g), step=5)

    if st.button("💾 Save Profile", use_container_width=True):
        profile.name = user_name
        profile.household_size = household_size
        profile.allergens = [CommonAllergen(a) for a in selected_allergens]
        profile.dietary_restrictions = [DietaryRestriction(d) for d in selected_diets]
        profile.macro_targets.calories = cal_target
        profile.macro_targets.protein_g = float(pro_target)
        coordinator.user_store.save_profile(profile)
        st.success("Profile saved successfully!")

    st.divider()
    st.subheader("📦 Pantry Quick Add")
    p_name = st.text_input("Item Name", placeholder="e.g. spinach")
    col1, col2 = st.columns(2)
    with col1:
        p_qty = st.number_input("Qty", min_value=1.0, value=100.0, step=10.0)
    with col2:
        p_unit = st.selectbox("Unit", ["g", "oz", "count", "cups", "tbsp"])

    if st.button("➕ Add to Pantry", use_container_width=True):
        if p_name:
            current_pantry = coordinator.user_store.get_pantry(user_id)
            current_pantry.append(
                PantryItem(
                    id=f"p_{p_name.lower().replace(' ', '_')}",
                    name=p_name.strip(),
                    quantity=p_qty,
                    unit=p_unit,
                )
            )
            coordinator.user_store.save_pantry(current_pantry, user_id=user_id)
            st.success(f"Added {p_name} to pantry!")

# ----------------- MAIN CONTENT TABS -----------------
tab_chat, tab_plan, tab_grocery, tab_metrics = st.tabs([
    "💬 Concierge Chat",
    "📅 Meal Plan",
    "🛒 Grocery Checklist",
    "📈 Observability & Tracing",
])

# TAB 1: CONCIERGE CHAT
with tab_chat:
    st.header("💬 Talk with your Concierge Agent")
    st.caption("Ask to plan a 3-day menu, check your pantry, or generate a grocery list.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("E.g., Plan my meals for the next 3 days"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Multi-agent team coordinating (Dietary Agent -> Chef -> Grocery)..."):
                result = coordinator.run({
                    "message": user_input,
                    "user_id": user_id,
                })
                reply = result.get("message", "Request completed.")
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

                if "meal_plan" in result and result["meal_plan"]:
                    st.session_state.current_plan = result["meal_plan"]
                if "grocery_list" in result and result["grocery_list"]:
                    st.session_state.current_grocery = result["markdown_checklist"]

# TAB 2: MEAL PLAN
with tab_plan:
    st.header("📅 Active Meal Plan")
    plan = st.session_state.current_plan
    if not plan:
        st.info("No meal plan generated yet. Ask NutriConcierge in the Chat tab or click below:")
        if st.button("🚀 Generate 3-Day Meal Plan Now"):
            with st.spinner("Generating plan..."):
                res = coordinator.run({"intent": "PLAN_MEALS", "user_id": user_id, "num_days": 3})
                st.session_state.current_plan = res.get("meal_plan")
                st.session_state.current_grocery = res.get("markdown_checklist")
                st.rerun()
    else:
        st.success(f"✅ {plan.notes}")
        for day in plan.days:
            with st.expander(f"📌 {day.day_name} — Total: {day.total_nutrition.calories} kcal | {day.total_nutrition.protein_g}g Protein", expanded=True):
                cols = st.columns(len(day.meals))
                for idx, meal in enumerate(day.meals):
                    with cols[idx]:
                        st.markdown(f"#### {meal.meal_type.value.upper()}: {meal.title}")
                        st.write(f"*{meal.description}*")
                        st.markdown(f"⏱️ **Prep:** {meal.prep_time_minutes}m | **Cook:** {meal.cook_time_minutes}m")
                        st.markdown(f"🔥 **{meal.nutrition.calories} kcal** (P: {meal.nutrition.protein_g}g | C: {meal.nutrition.carbs_g}g | F: {meal.nutrition.fat_g}g)")
                        with st.popover("View Ingredients & Instructions"):
                            st.write("**Ingredients:**")
                            for ing in meal.ingredients:
                                st.write(f"- {ing.quantity} {ing.unit} {ing.name}")
                            st.write("**Instructions:**")
                            for s_idx, s in enumerate(meal.instructions, 1):
                                st.write(f"{s_idx}. {s}")

# TAB 3: GROCERY CHECKLIST
with tab_grocery:
    st.header("🛒 Smart Grocery Shopping List")
    if st.session_state.current_grocery:
        st.markdown(st.session_state.current_grocery)
    else:
        st.info("No active grocery list. Generate a meal plan first to compile your shopping list.")

# TAB 4: OBSERVABILITY & METRICS
with tab_metrics:
    st.header("📈 Observability & Execution Telemetry")
    summary = metrics.get_summary()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Allergen Safety Checks", summary["safety_checks"]["total"])
    with col2:
        st.metric("Safety Guardrail Pass Rate", f"{summary['safety_checks']['pass_rate_pct']}%")
    with col3:
        st.metric("Total Tool/Agent Calls", sum(summary["tool_invocations"].values()))

    st.subheader("Invocation Counts by Tool / Sub-Agent")
    st.json(summary["tool_invocations"])
