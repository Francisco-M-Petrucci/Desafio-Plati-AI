import os
import json
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Ingredient, UserFact, Appliance, DietaryRestriction, User
from app.recipes_vector_db import RecipeVectorDB
from app.ingredients_formatter import standardize_ingredient

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
            return {
                "ingredients": [],
                "appliances": [],
                "restrictions": [],
                "facts": [],
                "wants_temporary": "",
                "does_not_want_temporary": "",
                "asked_preferences": False
            }

        ingredients = [i.name for i in user.ingredients]
        appliances = [a.name for a in user.appliances]
        restrictions = [r.restriction for r in user.restrictions]
        facts = [f.fact for f in user.facts]

        return {
            "ingredients": ingredients,
            "appliances": appliances,
            "restrictions": restrictions,
            "facts": facts,
            "wants_temporary": user.wants_temporary or "",
            "does_not_want_temporary": user.does_not_want_temporary or "",
            "asked_preferences": user.asked_preferences if hasattr(user, "asked_preferences") else False
        }
    finally:
        db.close()


def set_user_asked_preferences(user_id: int, value: bool) -> str:
    """Updates the user's asked_preferences field in SQLite."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.asked_preferences = value
            db.commit()
            return f"Set asked_preferences to {value}"
        return "User not found"
    except Exception as e:
        db.rollback()
        return f"Error setting asked_preferences: {str(e)}"
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

    # Pre-build standardized user ingredient names set
    user_ing_names = set()
    for i in user_profile.get("ingredients", []):
        if isinstance(i, dict):
            name = i.get("name")
        else:
            name = i
        if name:
            user_ing_names.add(standardize_ingredient(str(name)))

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

        if not compatible:
            continue

        # --- Filter 3: Ingredient check ---
        # User must be missing AT MOST 4 of the necessary ingredients
        missing_count = 0
        recipe_ingredients = recipe.get("ingredients", [])
        for ing in recipe_ingredients:
            standard_ing = standardize_ingredient(ing)
            found = False
            if standard_ing in user_ing_names:
                found = True
            else:
                for user_ing in user_ing_names:
                    if user_ing in standard_ing or standard_ing in user_ing:
                        found = True
                        break
            if not found:
                missing_count += 1
                if missing_count > 4:
                    break

        if missing_count <= 4:
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

    user_ing_names = {standardize_ingredient(name) for name in user_ingredients}

    formatted = []
    for r in recipes:
        # Calculate missing ingredients
        missing = []
        for ing in r['ingredients']:
            standard_ing = standardize_ingredient(ing)
            found = False
            if standard_ing in user_ing_names:
                found = True
            else:
                for user_ing in user_ing_names:
                    if user_ing in standard_ing or standard_ing in user_ing:
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

    user_ing_names = {standardize_ingredient(name) for name in user_ingredients}

    # Calculate ingredients we have and missing ingredients
    have = []
    missing = []

    for ing in recipe['ingredients']:
        standard_ing = standardize_ingredient(ing)
        found = False
        if standard_ing in user_ing_names:
            found = True
        else:
            for user_ing in user_ing_names:
                if user_ing in standard_ing or standard_ing in user_ing:
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


# Load average unit weights from ingredients_weight.json
AVERAGE_UNIT_WEIGHTS_G = {}
try:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _weight_path = os.path.join(os.path.dirname(_base_dir), "ingredients_weight.json")
    if os.path.exists(_weight_path):
        with open(_weight_path, "r", encoding="utf-8") as f:
            AVERAGE_UNIT_WEIGHTS_G = json.load(f)
    else:
        print(f"Warning: ingredients_weight.json not found at {_weight_path}")
except Exception as e:
    print(f"Error loading ingredients_weight.json: {e}")

def convert_quantity(from_qty: float, from_unit: str, to_unit: str, ingredient_name: Optional[str] = None) -> Optional[float]:
    """Converts from_qty from from_unit to to_unit. Returns None if not convertible."""
    u_from = from_unit.strip().lower()
    u_to = to_unit.strip().lower()
    
    # Normalize unit names
    if u_from in ("unit", "units", "piece", "pieces"):
        u_from = "unit"
    if u_to in ("unit", "units", "piece", "pieces"):
        u_to = "unit"
        
    if u_from == u_to:
        return from_qty
        
    # Weight conversion
    weight_units = {"g": 1.0, "gram": 1.0, "grams": 1.0, "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0}
    if u_from in weight_units and u_to in weight_units:
        return from_qty * (weight_units[u_from] / weight_units[u_to])
        
    # Volume conversion
    volume_units = {"ml": 1.0, "milliliter": 1.0, "milliliters": 1.0, "l": 1000.0, "liter": 1000.0, "liters": 1000.0}
    if u_from in volume_units and u_to in volume_units:
        return from_qty * (volume_units[u_from] / volume_units[u_to])
        
    # Unit to Weight/Volume conversion (requires ingredient name)
    if ingredient_name:
        ing_clean = ingredient_name.strip().lower()
        if ing_clean in AVERAGE_UNIT_WEIGHTS_G:
            unit_weight_g = AVERAGE_UNIT_WEIGHTS_G[ing_clean]
            
            # Unit -> Weight
            if u_from == "unit" and u_to in weight_units:
                qty_in_g = from_qty * unit_weight_g
                return convert_quantity(qty_in_g, "g", u_to)
                
            # Weight -> Unit
            if u_from in weight_units and u_to == "unit":
                qty_in_g = convert_quantity(from_qty, u_from, "g")
                if qty_in_g is not None:
                    return qty_in_g / unit_weight_g
                    
    return None


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
            if isinstance(item, str):
                name = item.strip().lower()
            else:
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

            name = standardize_ingredient(name)
            if not name:
                continue

            # Find existing ingredient
            existing = db.query(Ingredient).filter(
                Ingredient.user_id == user_id,
                Ingredient.name == name
            ).first()

            if action == "add":
                if not existing:
                    new_ing = Ingredient(user_id=user_id, name=name, quantity=1.0, unit="unit")
                    db.add(new_ing)
                    updated_items.append(f"added {name.capitalize()}")
                else:
                    updated_items.append(f"{name.capitalize()} already in stock")

            elif action == "remove":
                if existing:
                    db.delete(existing)
                    updated_items.append(f"removed {name.capitalize()}")
                else:
                    updated_items.append(f"could not remove {name.capitalize()} (not in inventory)")

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


def remove_user_fact_from_db(user_id: int, fact: str) -> str:
    """Removes a long-term fact about the user from the database."""
    db = SessionLocal()
    try:
        fact_stripped = fact.strip().lower()
        existing_facts = db.query(UserFact).filter(UserFact.user_id == user_id).all()
        removed = False
        for f in existing_facts:
            if f.fact.strip().lower() == fact_stripped:
                db.delete(f)
                removed = True
        if removed:
            db.commit()
            return f"Removed fact: '{fact}'"
        return "Fact not found in profile."
    except Exception as e:
        db.rollback()
        return f"Error removing fact: {str(e)}"
    finally:
        db.close()



def save_temporary_preferences_to_db(user_id: int, wants: List[str], does_not_wants: List[str]) -> str:
    """Saves and merges new temporary wants and does_not_wants to the database, preventing duplicates and conflicts."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return "User not found."

        # Parse existing
        existing_wants = [w.strip() for w in (user.wants_temporary or "").split(",") if w.strip()]
        existing_not_wants = [n.strip() for n in (user.does_not_want_temporary or "").split(",") if n.strip()]

        existing_wants_lower = [w.lower() for w in existing_wants]
        existing_not_wants_lower = [n.lower() for n in existing_not_wants]

        # Merge wants (remove from does_not_want if there's a conflict)
        new_wants = []
        for w in wants:
            w_clean = w.strip()
            if w_clean:
                # Remove conflict if exists in does_not_wants
                if w_clean.lower() in existing_not_wants_lower:
                    idx = existing_not_wants_lower.index(w_clean.lower())
                    existing_not_wants.pop(idx)
                    existing_not_wants_lower.pop(idx)
                
                # Add to wants if not already present
                if w_clean.lower() not in existing_wants_lower:
                    existing_wants.append(w_clean)
                    existing_wants_lower.append(w_clean.lower())
                    new_wants.append(w_clean)

        # Merge does_not_wants (remove from wants if there's a conflict)
        new_not_wants = []
        for nw in does_not_wants:
            nw_clean = nw.strip()
            if nw_clean:
                # Remove conflict if exists in wants
                if nw_clean.lower() in existing_wants_lower:
                    idx = existing_wants_lower.index(nw_clean.lower())
                    existing_wants.pop(idx)
                    existing_wants_lower.pop(idx)
                
                # Add to does_not_wants if not already present
                if nw_clean.lower() not in existing_not_wants_lower:
                    existing_not_wants.append(nw_clean)
                    existing_not_wants_lower.append(nw_clean.lower())
                    new_not_wants.append(nw_clean)

        user.wants_temporary = ", ".join(existing_wants)
        user.does_not_want_temporary = ", ".join(existing_not_wants)
        db.commit()

        return f"Merged wants: {new_wants}, Merged does not wants: {new_not_wants}"
    except Exception as e:
        db.rollback()
        return f"Error saving temporary preferences: {str(e)}"
    finally:
        db.close()


def add_user_appliance_to_db(user_id: int, appliance: str) -> str:
    """Saves a new appliance for the user in the database."""
    db = SessionLocal()
    try:
        app_stripped = appliance.strip().lower()
        if not app_stripped:
            return "Appliance name cannot be empty."
        existing = db.query(Appliance).filter(
            Appliance.user_id == user_id,
            Appliance.name == app_stripped
        ).first()

        if not existing:
            new_app = Appliance(user_id=user_id, name=app_stripped)
            db.add(new_app)
            db.commit()
            return f"Added appliance: '{app_stripped}'"
        return "Appliance already added."
    except Exception as e:
        db.rollback()
        return f"Error adding appliance: {str(e)}"
    finally:
        db.close()


def remove_user_appliance_from_db(user_id: int, appliance: str) -> str:
    """Removes an appliance for the user from the database."""
    db = SessionLocal()
    try:
        app_stripped = appliance.strip().lower()
        existing = db.query(Appliance).filter(
            Appliance.user_id == user_id,
            Appliance.name == app_stripped
        ).first()

        if existing:
            db.delete(existing)
            db.commit()
            return f"Removed appliance: '{app_stripped}'"
        return "Appliance not found in profile."
    except Exception as e:
        db.rollback()
        return f"Error removing appliance: {str(e)}"
    finally:
        db.close()


def add_user_restriction_to_db(user_id: int, restriction: str) -> str:
    """Saves a new dietary restriction for the user in the database."""
    db = SessionLocal()
    try:
        rest_stripped = restriction.strip().lower()
        if not rest_stripped:
            return "Restriction name cannot be empty."
        existing = db.query(DietaryRestriction).filter(
            DietaryRestriction.user_id == user_id,
            DietaryRestriction.restriction == rest_stripped
        ).first()

        if not existing:
            new_rest = DietaryRestriction(user_id=user_id, restriction=rest_stripped)
            db.add(new_rest)
            db.commit()
            return f"Added restriction: '{rest_stripped}'"
        return "Restriction already added."
    except Exception as e:
        db.rollback()
        return f"Error adding restriction: {str(e)}"
    finally:
        db.close()


def remove_user_restriction_from_db(user_id: int, restriction: str) -> str:
    """Removes a dietary restriction for the user from the database."""
    db = SessionLocal()
    try:
        rest_stripped = restriction.strip().lower()
        existing = db.query(DietaryRestriction).filter(
            DietaryRestriction.user_id == user_id,
            DietaryRestriction.restriction == rest_stripped
        ).first()

        if existing:
            db.delete(existing)
            db.commit()
            return f"Removed restriction: '{rest_stripped}'"
        return "Restriction not found in profile."
    except Exception as e:
        db.rollback()
        return f"Error removing restriction: {str(e)}"
    finally:
        db.close()



# Search tool wrapper (kept for backward compatibility with /api/recipes endpoint)
def search_recipes(query: str, limit: int = 3, culture: Optional[str] = None, season: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search recipes from the vector knowledge base."""
    return recipe_db.search_recipes(query, limit=limit, culture=culture, season=season)



