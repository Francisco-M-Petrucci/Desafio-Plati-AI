import traceback
import sys

from backend.app.database import SessionLocal
from backend.app.models import User, Appliance, DietaryRestriction, Ingredient, InitialSearchRecipe
from backend.app.auth import get_password_hash
from backend.app.ingredients_formatter import standardize_ingredient
from backend.app.agent.tools import get_filtered_recipe_ids
from backend.app.recipes_vector_db import RecipeVectorDB

def test_register():
    db = SessionLocal()
    try:
        first_name = "samename3"
        username = "samename3"
        password = "password"
        appliances = ["oven"]
        restrictions = []
        ingredients = ["tomato"]

        # Step 1
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print("Username taken")
            return

        print("Creating user")
        hashed_password = get_password_hash(password)
        user = User(
            first_name=first_name.strip(),
            username=username,
            password=hashed_password,
            asked_preferences=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"Created user with id {user.id}")

        # Step 2
        for app_name in appliances:
            if app_name.strip():
                db.add(Appliance(user_id=user.id, name=app_name.strip().lower()))
                
        for rest in restrictions:
            if rest.strip():
                db.add(DietaryRestriction(user_id=user.id, restriction=rest.strip().lower()))
                
        for ing in ingredients:
            name = ing.strip().lower()
            name = standardize_ingredient(name)
            if name:
                db.add(Ingredient(
                    user_id=user.id,
                    name=name,
                    quantity=1.0,
                    unit="unit"
                ))
                
        db.commit()
        print("Commited appliances, restrictions, ingredients")

        # Step 3
        recipe_vector_db = RecipeVectorDB()
        user_profile = {
            "appliances": [a.strip().lower() for a in appliances if a.strip()],
            "restrictions": [r.strip().lower() for r in restrictions if r.strip()],
            "ingredients": [standardize_ingredient(i) for i in ingredients if i.strip()]
        }
        
        compatible_ids = get_filtered_recipe_ids(user_profile)
        print(f"compatible_ids: {compatible_ids}")
        
        user_ing_names = [standardize_ingredient(i) for i in ingredients if i.strip()]
        query = ", ".join(user_ing_names) if user_ing_names else "recipe"
        
        recipes_raw = recipe_vector_db.search_recipes_filtered(
            query=query,
            recipe_ids=set(compatible_ids),
            limit=5
        )
        print(f"recipes_raw length: {len(recipes_raw)}")
        
        if len(recipes_raw) < 5:
            all_meta = recipe_vector_db.get_all_recipe_metadata()
            compatible_recipes = [r for r in all_meta if r["id"] in compatible_ids]
            existing_ids = {r["id"] for r in recipes_raw}
            for r in compatible_recipes:
                if len(recipes_raw) >= 5:
                    break
                if r["id"] not in existing_ids:
                    recipe_full = recipe_vector_db.get_recipe_by_id(r["id"])
                    if recipe_full:
                        recipes_raw.append(recipe_full)
                        existing_ids.add(r["id"])
                        
        print(f"saving initial search recipes")
        for r in recipes_raw[:5]:
            db.add(InitialSearchRecipe(user_id=user.id, recipe_id=r["id"]))
        db.commit()

        print("Success!")
    except Exception as e:
        print("EXCEPTION:")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

test_register()
