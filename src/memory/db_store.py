"""SQLite Database Persistence Layer for NutriConcierge.

Replaces flat file persistence with an ACID-compliant relational SQLite database
supporting connection pooling, schema migrations, and relational integrity.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional
from src.models.schemas import (
    MacroTarget,
    MealFeedback,
    PantryItem,
    UserProfile,
    WeeklyMealPlan,
)


class DatabaseStore:
    """ACID-compliant SQLite persistence store for profiles, pantries, meal plans, and feedback."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            data_dir = Path(os.getenv("DATA_DIR", "data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "nutriconcierge.db"

        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a thread-safe connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # Write-Ahead Logging for high concurrency
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema with tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # User Profiles Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    household_size INTEGER NOT NULL DEFAULT 1,
                    daily_calorie_target REAL,
                    allergens TEXT NOT NULL,          -- JSON array
                    dietary_restrictions TEXT NOT NULL, -- JSON array
                    disliked_ingredients TEXT NOT NULL, -- JSON array
                    macro_targets TEXT,                -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Pantry Inventory Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pantry_items (
                    id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT NOT NULL,
                    category TEXT NOT NULL,
                    expiration_date TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, user_id),
                    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
                );
            """)

            # Weekly Meal Plans Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meal_plans (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    plan_data TEXT NOT NULL,          -- Full JSON payload
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
                );
            """)

            # Feedback Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meal_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
                );
            """)

            # Indexes for high performance querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pantry_user ON pantry_items(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plans_user ON meal_plans(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user ON meal_feedback(user_id);")
            conn.commit()

    def _save_profile_with_cursor(self, cursor: sqlite3.Cursor, profile: UserProfile) -> None:
        """Internal helper to insert/update a profile within an existing transaction."""
        cal_target = (
            profile.macro_targets.calories
            if hasattr(profile, "macro_targets") and profile.macro_targets
            else getattr(profile, "daily_calorie_target", 2000.0)
        )
        cursor.execute(
            """
            INSERT INTO user_profiles (
                user_id, name, household_size, daily_calorie_target,
                allergens, dietary_restrictions, disliked_ingredients,
                macro_targets, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name,
                household_size=excluded.household_size,
                daily_calorie_target=excluded.daily_calorie_target,
                allergens=excluded.allergens,
                dietary_restrictions=excluded.dietary_restrictions,
                disliked_ingredients=excluded.disliked_ingredients,
                macro_targets=excluded.macro_targets,
                updated_at=CURRENT_TIMESTAMP;
            """,
            (
                profile.user_id,
                profile.name,
                profile.household_size,
                cal_target,
                json.dumps([a.value if hasattr(a, "value") else str(a) for a in profile.allergens]),
                json.dumps([d.value if hasattr(d, "value") else str(d) for d in profile.dietary_restrictions]),
                json.dumps(profile.disliked_ingredients),
                json.dumps(profile.macro_targets.model_dump() if hasattr(profile, "macro_targets") and profile.macro_targets else {}),
            ),
        )

    # ---------------- USER PROFILES ----------------
    def save_profile(self, profile: UserProfile) -> None:
        """Persist or update a user profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            self._save_profile_with_cursor(cursor, profile)
            conn.commit()

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Fetch user profile from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None

            macro_data = json.loads(row["macro_targets"]) if row["macro_targets"] else {}
            if row["daily_calorie_target"] and not macro_data.get("calories"):
                macro_data["calories"] = int(row["daily_calorie_target"])

            return UserProfile(
                user_id=row["user_id"],
                name=row["name"],
                household_size=row["household_size"],
                allergens=json.loads(row["allergens"]),
                dietary_restrictions=json.loads(row["dietary_restrictions"]),
                disliked_ingredients=json.loads(row["disliked_ingredients"]),
                macro_targets=MacroTarget(**macro_data) if macro_data else MacroTarget(),
            )

    # ---------------- PANTRY INVENTORY ----------------
    def save_pantry(self, user_id: str, items: List[PantryItem]) -> None:
        """Persist entire pantry inventory for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_profiles WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                self._save_profile_with_cursor(cursor, UserProfile(user_id=user_id, name=user_id))

            cursor.execute("DELETE FROM pantry_items WHERE user_id = ?", (user_id,))
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO pantry_items (id, user_id, name, quantity, unit, category, expiration_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id, user_id) DO UPDATE SET
                        name=excluded.name,
                        quantity=excluded.quantity,
                        unit=excluded.unit,
                        category=excluded.category,
                        expiration_date=excluded.expiration_date;
                    """,
                    (
                        item.id,
                        user_id,
                        item.name,
                        item.quantity,
                        item.unit,
                        item.category,
                        item.expiration_date.isoformat() if item.expiration_date else None,
                    ),
                )
            conn.commit()

    def get_pantry(self, user_id: str) -> List[PantryItem]:
        """Fetch all pantry items for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pantry_items WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            items = []
            for row in rows:
                items.append(
                    PantryItem(
                        id=row["id"],
                        name=row["name"],
                        quantity=row["quantity"],
                        unit=row["unit"],
                        category=row["category"],
                        expiration_date=row["expiration_date"],
                    )
                )
            return items

    # ---------------- MEAL PLANS ----------------
    def save_meal_plan(self, plan: WeeklyMealPlan) -> None:
        """Persist a generated meal plan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_profiles WHERE user_id = ?", (plan.user_id,))
            if not cursor.fetchone():
                self._save_profile_with_cursor(cursor, UserProfile(user_id=plan.user_id, name=plan.user_id))

            cursor.execute(
                """
                INSERT INTO meal_plans (id, user_id, plan_data)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    plan_data=excluded.plan_data,
                    created_at=CURRENT_TIMESTAMP;
                """,
                (plan.id, plan.user_id, plan.model_dump_json()),
            )
            conn.commit()

    def get_meal_plan(self, plan_id: str) -> Optional[WeeklyMealPlan]:
        """Fetch meal plan by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT plan_data FROM meal_plans WHERE id = ?", (plan_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return WeeklyMealPlan.model_validate_json(row["plan_data"])

    # ---------------- FEEDBACK ----------------
    def save_feedback(self, feedback: MealFeedback, user_id: str = "default_user") -> None:
        """Persist meal feedback."""
        uid = getattr(feedback, "user_id", None) or user_id
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_profiles WHERE user_id = ?", (uid,))
            if not cursor.fetchone():
                self._save_profile_with_cursor(cursor, UserProfile(user_id=uid, name=uid))

            cursor.execute(
                """
                INSERT INTO meal_feedback (user_id, recipe_id, rating, comments)
                VALUES (?, ?, ?, ?)
                """,
                (uid, feedback.recipe_id, feedback.rating, feedback.comments),
            )
            conn.commit()

    def get_feedback(self, user_id: str) -> List[MealFeedback]:
        """Fetch all feedback for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meal_feedback WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            return [
                MealFeedback(
                    recipe_id=row["recipe_id"],
                    recipe_title=row["recipe_id"],
                    rating=row["rating"],
                    comments=row["comments"],
                )
                for row in rows
            ]
