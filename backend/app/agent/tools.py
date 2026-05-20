from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Ingredient, UserFact, Appliance, DietaryRestriction, User
from app.recipes_vector_db import RecipeVectorDB

# Instantiate the vector DB helper
recipe_db = RecipeVectorDB()

def get_user_profile_data(user_id: int) -> Dict[str, Any]:
    """Retrieves user details from SQLite to construct the profile context."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"ingredients": [], "appliances": [], "restrictions": [], "facts": []}

        ingredients = [{"name": i.name, "quantity": i.quantity, "unit": i.unit} for i in user.ingredients]
        appliances = [a.name for a in user.appliances]
        restrictions = [r.restriction for r in user.restrictions]
        facts = [f.fact for f in user.facts]

        return {
            "ingredients": ingredients,
            "appliances": appliances,
            "restrictions": restrictions,
            "facts": facts
        }
    finally:
        db.close()


def update_ingredients_in_db(user_id: int, action: str, items: Any) -> str:
    """
    Updates the user's ingredients list in SQLite.
    action: 'add' or 'remove'
    items: list of dicts like {"name": "tomato", "quantity": 2.0, "unit": "unit"}
    """
    # Normalize input types (sometimes the LLM passes stringified JSON arrays or single dictionaries)
    if isinstance(items, str):
        try:
            import json
            items = json.loads(items)
        except Exception:
            pass

    if isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list):
        items = []

    db = SessionLocal()
    try:
        updated_items = []
        for item in items:
            # Handle Pydantic models or standard dictionaries
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif hasattr(item, "dict"):
                item_dict = item.dict()
            elif isinstance(item, dict):
                item_dict = item
            else:
                try:
                    item_dict = dict(item)
                except Exception:
                    item_dict = {}

            name = item_dict.get("name", "").strip().lower()
            qty = float(item_dict.get("quantity", 1.0))
            unit = item_dict.get("unit", "unit").strip().lower()

            # Find existing ingredient
            existing = db.query(Ingredient).filter(
                Ingredient.user_id == user_id,
                Ingredient.name == name
            ).first()

            if action == "add":
                if existing:
                    existing.quantity += qty
                    # Update unit if it was default
                    if existing.unit == "unit" and unit != "unit":
                        existing.unit = unit
                else:
                    new_ing = Ingredient(user_id=user_id, name=name, quantity=qty, unit=unit)
                    db.add(new_ing)
                updated_items.append(f"+{qty} {unit} of {name}")

            elif action == "remove":
                if existing:
                    existing.quantity = max(0.0, existing.quantity - qty)
                    if existing.quantity <= 0.0:
                        db.delete(existing)
                        updated_items.append(f"removed all {name}")
                    else:
                        updated_items.append(f"-{qty} {unit} of {name} (remaining: {existing.quantity})")
                else:
                    updated_items.append(f"could not remove {name} (not in inventory)")

        db.commit()
        return f"Successfully updated inventory: {', '.join(updated_items)}"
    except Exception as e:
        db.rollback()
        return f"Error updating inventory: {str(e)}"
    finally:
        db.close()


def add_user_fact_to_db(user_id: int, fact: str) -> str:
    """Saves a new long-term fact about the user in the database."""
    db = SessionLocal()
    try:
        # Check if fact already exists to prevent duplicate entries
        fact_stripped = fact.strip()
        existing = db.query(UserFact).filter(
            UserFact.user_id == user_id,
            UserFact.fact == fact_stripped
        ).first()

        if not existing:
            new_fact = UserFact(user_id=user_id, fact=fact_stripped)
            db.add(new_fact)
            db.commit()
            return f"Saved fact: '{fact_stripped}'"
        return "Fact already remembered."
    except Exception as e:
        db.rollback()
        return f"Error saving fact: {str(e)}"
    finally:
        db.close()


# Search tool wrapper
def search_recipes(query: str, culture: Optional[str] = None, season: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search recipes from the vector knowledge base."""
    return recipe_db.search_recipes(query, limit=5, culture=culture, season=season)
