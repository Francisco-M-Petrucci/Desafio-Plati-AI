from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Ingredient, UserFact, Appliance, DietaryRestriction, User, TemporaryPreference
from app.recipes_vector_db import RecipeVectorDB

# Instantiate the vector DB helper
recipe_db = RecipeVectorDB()

# Dietary restriction compatibility mapping.
# "vegetarian" users can also eat "vegan" food (vegan implies vegetarian).
# All other restrictions use exact matching.
RESTRICTION_COMPATIBLE_TAGS = {
    "vegetarian": ["vegetarian", "vegan"],
}


def get_user_profile_data(user_id: int) -> Dict[str, Any]:
    """Retrieves user details from SQLite to construct the profile context."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"ingredients": [], "appliances": [], "restrictions": [], "facts": [], "temporary_preferences": []}

        ingredients = [{"name": i.name, "quantity": i.quantity, "unit": i.unit} for i in user.ingredients]
        appliances = [a.name for a in user.appliances]
        restrictions = [r.restriction for r in user.restrictions]
        facts = [f.fact for f in user.facts]
        temporary_preferences = [t.preference for t in user.temporary_preferences]

        return {
            "ingredients": ingredients,
            "appliances": appliances,
            "restrictions": restrictions,
            "facts": facts,
            "temporary_preferences": temporary_preferences
        }
    finally:
        db.close()


def get_filtered_recipe_ids(user_profile: Dict[str, Any]) -> List[int]:
    """
    Deterministic hard filter: removes recipes that are structurally incompatible
    with the user's kitchen setup (missing appliances) or dietary restrictions.
    
    This runs BEFORE the LLM sees any recipes, preventing wasted tokens on
    recipes the user can never make or should never eat.
    
    Returns a list of compatible recipe IDs.
    """
    user_appliances = set(a.lower() for a in user_profile.get("appliances", []))
    user_restrictions = [r.lower() for r in user_profile.get("restrictions", [])]

    all_recipes = recipe_db.get_all_recipe_metadata()
    compatible_ids = []

    for recipe in all_recipes:
        # --- Filter 1: Appliance check ---
        # User must own ALL appliances the recipe requires
        required = set(a.lower() for a in recipe.get("required_appliances", []))
        if not required.issubset(user_appliances):
            continue

        # --- Filter 2: Dietary restriction check ---
        # For EACH user restriction, the recipe must have a compatible dietary tag
        dietary_tags = set(t.lower() for t in recipe.get("dietary_tags", []))
        compatible = True
        for restriction in user_restrictions:
            # Get the set of tags that satisfy this restriction
            acceptable_tags = RESTRICTION_COMPATIBLE_TAGS.get(restriction, [restriction])
            if not any(tag in dietary_tags for tag in acceptable_tags):
                compatible = False
                break

        if compatible:
            compatible_ids.append(recipe["id"])

    return compatible_ids


def format_recipe_results(
    recipes: List[Dict[str, Any]],
    user_ingredients: List[Dict[str, Any]],
    include_steps: bool = False
) -> str:
    """Formats a list of recipe dicts into a readable string for the LLM tool response."""
    if not recipes:
        return "No recipes found in the database matching those filters."

    user_ing_names = {i['name'].lower().strip() for i in user_ingredients}

    formatted = []
    for r in recipes:
        # Calculate missing ingredients
        missing = []
        for ing in r['ingredients']:
            ing_lower = ing.lower().strip()
            # Simple substring checking for robust matching
            found = False
            for user_ing in user_ing_names:
                if user_ing in ing_lower or ing_lower in user_ing:
                    found = True
                    break
            if not found:
                missing.append(ing)

        recipe_str = (
            f"Recipe ID: {r['id']}\n"
            f"Name: {r['name']}\n"
            f"Cook Time: {r['minutes']} mins\n"
        )
        if missing:
            recipe_str += f"Missing Ingredients: {', '.join(missing)}\n"

        if include_steps:
            recipe_str += f"Ingredients: {', '.join(r['ingredients'])}\n"
            recipe_str += f"Steps:\n" + "\n".join(f"  {i+1}. {step}" for i, step in enumerate(r['steps'])) + "\n"

        formatted.append(recipe_str.strip())
    return "\n---\n".join(formatted)


def get_recipe_details_by_id(recipe_id: int, user_ingredients: List[Dict[str, Any]]) -> str:
    """Retrieves full recipe ingredients and cooking steps by its ID, formatting them in Python."""
    recipe = recipe_db.get_recipe_by_id(recipe_id)
    if not recipe:
        return f"Recipe with ID {recipe_id} not found."

    user_ing_names = {i['name'].lower().strip() for i in user_ingredients}

    # Calculate ingredients we have and missing ingredients
    have = []
    missing = []

    for ing in recipe['ingredients']:
        ing_lower = ing.lower().strip()
        found = False
        for user_ing in user_ing_names:
            if user_ing in ing_lower or ing_lower in user_ing:
                found = True
                break
        if found:
            have.append(ing)
        else:
            missing.append(ing)

    # Format output details cleanly
    formatted = (
        f"Recipe ID: {recipe['id']}\n"
        f"Name: {recipe['name']}\n"
        f"Cook Time: {recipe['minutes']} mins\n"
        f"Ingredients You Have: {', '.join(have) if have else 'None'}\n"
        f"Missing Ingredients: {', '.join(missing) if missing else 'None'}\n"
        f"Steps:\n" + "\n".join(f"  {i+1}. {step}" for i, step in enumerate(recipe['steps']))
    )
    return formatted


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


def add_user_temporary_preference_to_db(user_id: int, preference: str) -> str:
    """Saves a new short-term temporary preference about the user in the database."""
    db = SessionLocal()
    try:
        # Check if preference already exists to prevent duplicate entries
        preference_stripped = preference.strip()
        existing = db.query(TemporaryPreference).filter(
            TemporaryPreference.user_id == user_id,
            TemporaryPreference.preference == preference_stripped
        ).first()

        if not existing:
            new_pref = TemporaryPreference(user_id=user_id, preference=preference_stripped)
            db.add(new_pref)
            db.commit()
            return f"Saved temporary preference: '{preference_stripped}'"
        return "Temporary preference already remembered."
    except Exception as e:
        db.rollback()
        return f"Error saving temporary preference: {str(e)}"
    finally:
        db.close()


# Search tool wrapper (kept for backward compatibility with /api/recipes endpoint)
def search_recipes(query: str, limit: int = 3, culture: Optional[str] = None, season: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search recipes from the vector knowledge base."""
    return recipe_db.search_recipes(query, limit=limit, culture=culture, season=season)
