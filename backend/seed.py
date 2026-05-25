import os
import shutil
from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app.models import User, Appliance, Ingredient, DietaryRestriction, UserFact, InitialSearchRecipe
from app.recipes_vector_db import RecipeVectorDB

def populate_initial_search_recipes(db, user, appliances, restrictions, ingredients):
    # Check if they already have initial recipes populated
    has_initial = db.query(InitialSearchRecipe).filter(InitialSearchRecipe.user_id == user.id).first()
    if not has_initial:
        print(f"Calculating initial recipe matches for {user.username}...")
        from app.agent.tools import get_filtered_recipe_ids
        from app.ingredients_formatter import standardize_ingredient
        
        standard_ingredients = [standardize_ingredient(ing) for ing in ingredients]
        
        user_profile = {
            "appliances": appliances,
            "restrictions": restrictions,
            "ingredients": [{"name": ing} for ing in standard_ingredients]
        }
        
        # Filter recipes by appliance & restriction
        compatible_ids = get_filtered_recipe_ids(user_profile)
        print(f"User {user.username} compatible IDs: {compatible_ids}")
        
        # Rank by ingredients matching
        query = ", ".join(standard_ingredients)
        vector_db = RecipeVectorDB()
        recipes_raw = vector_db.search_recipes_filtered(
            query=query,
            recipe_ids=set(compatible_ids),
            limit=5
        )
        
        # Fallback if < 5
        if len(recipes_raw) < 5:
            all_meta = vector_db.get_all_recipe_metadata()
            compatible_recipes = [r for r in all_meta if r["id"] in compatible_ids]
            existing_ids = {r["id"] for r in recipes_raw}
            for r in compatible_recipes:
                if len(recipes_raw) >= 5:
                    break
                if r["id"] not in existing_ids:
                    recipe_full = vector_db.get_recipe_by_id(r["id"])
                    if recipe_full:
                        recipes_raw.append(recipe_full)
                        existing_ids.add(r["id"])
                        
        for r in recipes_raw[:5]:
            db.add(InitialSearchRecipe(user_id=user.id, recipe_id=r["id"]))
        db.commit()
        print(f"Successfully seeded {len(recipes_raw[:5])} initial recipes for {user.username}.")

def seed_database():
    # 1. Reset Vector DB persist directory BEFORE instantiating any database connection
    print("Resetting Vector DB persist directory to apply dietary tags updates...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_dir = os.path.join(base_dir, "data", "chroma_db")
    if os.path.exists(chroma_dir):
        try:
            shutil.rmtree(chroma_dir)
            print("Deleted old Chroma database directory successfully.")
        except Exception as e:
            print(f"Could not delete Chroma directory: {e}")

    # 2. Seed Vector DB first so that the recipe database matches immediately when ORM matchmaking runs
    print("Seeding Vector DB...")
    vector_db = RecipeVectorDB()
    seed_file_path = os.path.join(base_dir, "data", "recipes_seed.json")
    vector_db.seed_recipes(seed_file_path)

    print("Creating SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Ensure first_name column exists
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR;"))
    except Exception as e:
        print(f"Migration error during seed execution: {e}")
    
    db = SessionLocal()
    
    # 1. Create User A (Alice)
    alice = db.query(User).filter(User.username == "alice").first()
    if not alice:
        print("Seeding user Alice...")
        alice = User(username="alice", password="password123", first_name="Alice")
        db.add(alice)
        db.commit()
        db.refresh(alice)
        
        # Add appliances
        db.add_all([
            Appliance(user_id=alice.id, name="airfryer"),
            Appliance(user_id=alice.id, name="blender/mixer")
        ])
        
        # Add ingredients
        from app.ingredients_formatter import standardize_ingredient
        db.add_all([
            Ingredient(user_id=alice.id, name=standardize_ingredient("chicken wings"), quantity=1.0, unit="kg"),
            Ingredient(user_id=alice.id, name=standardize_ingredient("olive oil"), quantity=500.0, unit="ml"),
            Ingredient(user_id=alice.id, name=standardize_ingredient("garlic powder"), quantity=1.0, unit="jar"),
            Ingredient(user_id=alice.id, name=standardize_ingredient("parmesan cheese"), quantity=200.0, unit="g"),
            Ingredient(user_id=alice.id, name=standardize_ingredient("salt"), quantity=1.0, unit="pack"),
            Ingredient(user_id=alice.id, name=standardize_ingredient("black pepper"), quantity=1.0, unit="shaker"),
            Ingredient(user_id=alice.id, name=standardize_ingredient("parsley"), quantity=1.0, unit="bunch")
        ])
        
        # Add dietary restrictions
        db.add_all([
            DietaryRestriction(user_id=alice.id, restriction="gluten-free"),
            DietaryRestriction(user_id=alice.id, restriction="low-carb")
        ])
        
        # Add long-term facts
        db.add_all([
            UserFact(user_id=alice.id, fact="Prefers quick and easy meals under 30 minutes"),
            UserFact(user_id=alice.id, fact="Loves garlic and savory flavors"),
            UserFact(user_id=alice.id, fact="Allergic to peanuts")
        ])
        db.commit()
        print("Alice seeded successfully.")
    else:
        print("User Alice already exists. Ensuring first_name is set.")
        alice.first_name = "Alice"
        db.commit()

    # Clear existing initial matches for Alice to rebuild
    db.query(InitialSearchRecipe).filter(InitialSearchRecipe.user_id == alice.id).delete()
    db.commit()

    # Populate Alice initial recipes
    populate_initial_search_recipes(
        db, alice,
        appliances=["airfryer", "blender/mixer"],
        restrictions=["gluten-free", "low-carb"],
        ingredients=["chicken wings", "olive oil", "garlic powder", "parmesan cheese", "salt", "black pepper", "parsley"]
    )

    # 2. Create User B (Bob)
    bob = db.query(User).filter(User.username == "bob").first()
    if not bob:
        print("Seeding user Bob...")
        bob = User(username="bob", password="password123", first_name="Bob")
        db.add(bob)
        db.commit()
        db.refresh(bob)
        
        # Add appliances
        db.add_all([
            Appliance(user_id=bob.id, name="oven"),
            Appliance(user_id=bob.id, name="stove"),
            Appliance(user_id=bob.id, name="blender/mixer")
        ])
        
        # Add ingredients
        from app.ingredients_formatter import standardize_ingredient
        db.add_all([
            Ingredient(user_id=bob.id, name=standardize_ingredient("pizza dough"), quantity=1.0, unit="unit"),
            Ingredient(user_id=bob.id, name=standardize_ingredient("canned san marzano tomatoes"), quantity=1.0, unit="can"),
            Ingredient(user_id=bob.id, name=standardize_ingredient("fresh mozzarella cheese"), quantity=250.0, unit="g"),
            Ingredient(user_id=bob.id, name=standardize_ingredient("fresh basil leaves"), quantity=1.0, unit="bunch"),
            Ingredient(user_id=bob.id, name=standardize_ingredient("extra virgin olive oil"), quantity=500.0, unit="ml"),
            Ingredient(user_id=bob.id, name=standardize_ingredient("salt"), quantity=1.0, unit="pack")
        ])
        
        # Add dietary restrictions
        db.add_all([
            DietaryRestriction(user_id=bob.id, restriction="vegetarian")
        ])
        
        # Add long-term facts
        db.add_all([
            UserFact(user_id=bob.id, fact="Loves authentic Italian food"),
            UserFact(user_id=bob.id, fact="Likes to cook from scratch"),
            UserFact(user_id=bob.id, fact="Dislikes spicy food")
        ])
        db.commit()
        print("Bob seeded successfully.")
    else:
        print("User Bob already exists. Ensuring first_name is set.")
        bob.first_name = "Bob"
        db.commit()

    # Clear existing initial matches for Bob to rebuild
    db.query(InitialSearchRecipe).filter(InitialSearchRecipe.user_id == bob.id).delete()
    db.commit()

    # Populate Bob initial recipes
    populate_initial_search_recipes(
        db, bob,
        appliances=["oven", "stove", "blender/mixer"],
        restrictions=["vegetarian"],
        ingredients=["pizza dough", "canned san marzano tomatoes", "fresh mozzarella cheese", "fresh basil leaves", "extra virgin olive oil", "salt"]
    )

    # 3. Handle User C (Carol)
    carol = db.query(User).filter(User.username == "carol").first()
    if carol:
        print("User Carol exists. Ensuring first_name is set.")
        carol.first_name = "Carol"
        db.commit()

        # Clear existing initial matches for Carol to rebuild
        db.query(InitialSearchRecipe).filter(InitialSearchRecipe.user_id == carol.id).delete()
        db.commit()

        # Populate Carol initial recipes
        populate_initial_search_recipes(
            db, carol,
            appliances=[a.name for a in carol.appliances],
            restrictions=[r.restriction for r in carol.restrictions],
            ingredients=[i.name for i in carol.ingredients]
        )
        
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
