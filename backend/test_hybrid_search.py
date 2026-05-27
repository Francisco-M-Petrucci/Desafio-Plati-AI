import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath("c:\\Users\\franc\\Desktop\\PROJETO RECEITA\\backend"))

from app.recipes_vector_db import RecipeVectorDB

db = RecipeVectorDB()
# Provide a set of all valid IDs
all_meta = db.get_all_recipe_metadata()
all_ids = {m["id"] for m in all_meta}
print("Testing hybrid search for 'pasta'")
results = db.search_recipes_filtered("pasta", recipe_ids=all_ids, limit=5)

for i, r in enumerate(results):
    print(f"{i+1}. {r['name']}")
    print(f"   Ingredients: {', '.join(r['ingredients'])}")
    print()
