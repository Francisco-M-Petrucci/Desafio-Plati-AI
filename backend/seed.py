import os
from app.database import engine, Base, SessionLocal
from app.models import User, Appliance, Ingredient, DietaryRestriction, UserFact
from app.recipes_vector_db import RecipeVectorDB

def seed_database():
    print("Creating SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Create User A (Alice)
    alice = db.query(User).filter(User.username == "alice").first()
    if not alice:
        print("Seeding user Alice...")
        alice = User(username="alice", password="password123")
        db.add(alice)
        db.commit()
        db.refresh(alice)
        
        # Add appliances
        db.add_all([
            Appliance(user_id=alice.id, name="airfryer"),
            Appliance(user_id=alice.id, name="blender/mixer")
        ])
        
        # Add ingredients
        db.add_all([
            Ingredient(user_id=alice.id, name="chicken wings", quantity=1.0, unit="kg"),
            Ingredient(user_id=alice.id, name="olive oil", quantity=500.0, unit="ml"),
            Ingredient(user_id=alice.id, name="garlic powder", quantity=1.0, unit="jar"),
            Ingredient(user_id=alice.id, name="parmesan cheese", quantity=200.0, unit="g"),
            Ingredient(user_id=alice.id, name="salt", quantity=1.0, unit="pack"),
            Ingredient(user_id=alice.id, name="black pepper", quantity=1.0, unit="shaker"),
            Ingredient(user_id=alice.id, name="parsley", quantity=1.0, unit="bunch")
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
        print("User Alice already exists. Skipping user seed.")

    # 2. Create User B (Bob)
    bob = db.query(User).filter(User.username == "bob").first()
    if not bob:
        print("Seeding user Bob...")
        bob = User(username="bob", password="password123")
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
        db.add_all([
            Ingredient(user_id=bob.id, name="pizza dough", quantity=1.0, unit="unit"),
            Ingredient(user_id=bob.id, name="canned san marzano tomatoes", quantity=1.0, unit="can"),
            Ingredient(user_id=bob.id, name="fresh mozzarella cheese", quantity=250.0, unit="g"),
            Ingredient(user_id=bob.id, name="fresh basil leaves", quantity=1.0, unit="bunch"),
            Ingredient(user_id=bob.id, name="extra virgin olive oil", quantity=500.0, unit="ml"),
            Ingredient(user_id=bob.id, name="salt", quantity=1.0, unit="pack")
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
        print("User Bob already exists. Skipping user seed.")
        
    db.close()

    # 3. Seed Vector DB
    print("Seeding Vector DB...")
    vector_db = RecipeVectorDB()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    seed_file_path = os.path.join(base_dir, "data", "recipes_seed.json")
    vector_db.seed_recipes(seed_file_path)
    print("Database seeding completed!")

if __name__ == "__main__":
    seed_database()
