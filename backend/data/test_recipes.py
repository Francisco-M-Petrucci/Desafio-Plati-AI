import json
from collections import Counter

with open('c:/Users/franc/Desktop/PROJETO RECEITA/backend/data/recipes_seed.json', encoding='utf-8') as f:
    r = json.load(f)

alice_app = {'stove', 'airfryer', 'blender/mixer'}
alice_rest = {'gluten-free'}

bob_app = {'oven', 'stove', 'microwave', 'blender/mixer'}
bob_rest = {'vegetarian'}

def is_valid(recipe, apps, rests):
    req_apps = set(recipe.get('required_appliances', []))
    if not req_apps.issubset(apps):
        return False
    rec_tags = set(recipe.get('dietary_tags', []))
    if not rests.issubset(rec_tags):
        return False
    return True

alice_recipes = [x for x in r if is_valid(x, alice_app, alice_rest)]
bob_recipes = [x for x in r if is_valid(x, bob_app, bob_rest)]

alice_ings = Counter(i for x in alice_recipes for i in x['ingredients'])
bob_ings = Counter(i for x in bob_recipes for i in x['ingredients'])

print('Alice Top Ingredients:', alice_ings.most_common(15))
print('Bob Top Ingredients:', bob_ings.most_common(15))
