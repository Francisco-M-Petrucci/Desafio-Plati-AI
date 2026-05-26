# Backend equivalent of frontend/src/utils/ingredientCategories.js
# Maps standard ingredient names to their display category for organized inventory output.

# Ordered list of categories for consistent display
CATEGORY_ORDER = [
    "Meat, Poultry & Seafood",
    "Fruits",
    "Vegetables & Greens",
    "Dairy & Eggs",
    "Grains, Pasta & Baking",
    "Oils, Condiments & Liquids",
    "Herbs, Spices & Seasonings",
    "Other Pantry Items",
]

# Short aliases that the LLM can use to request specific sections.
# Maps lowercase alias → canonical category name.
CATEGORY_ALIASES = {
    # Meat, Poultry & Seafood
    "meat": "Meat, Poultry & Seafood",
    "meats": "Meat, Poultry & Seafood",
    "poultry": "Meat, Poultry & Seafood",
    "seafood": "Meat, Poultry & Seafood",
    "fish": "Meat, Poultry & Seafood",
    "protein": "Meat, Poultry & Seafood",
    "proteins": "Meat, Poultry & Seafood",
    # Fruits
    "fruit": "Fruits",
    "fruits": "Fruits",
    # Vegetables & Greens
    "vegetable": "Vegetables & Greens",
    "vegetables": "Vegetables & Greens",
    "veggies": "Vegetables & Greens",
    "greens": "Vegetables & Greens",
    # Dairy & Eggs
    "dairy": "Dairy & Eggs",
    "eggs": "Dairy & Eggs",
    "cheese": "Dairy & Eggs",
    # Grains, Pasta & Baking
    "grains": "Grains, Pasta & Baking",
    "pasta": "Grains, Pasta & Baking",
    "baking": "Grains, Pasta & Baking",
    "bread": "Grains, Pasta & Baking",
    # Oils, Condiments & Liquids
    "oils": "Oils, Condiments & Liquids",
    "condiments": "Oils, Condiments & Liquids",
    "liquids": "Oils, Condiments & Liquids",
    "sauces": "Oils, Condiments & Liquids",
    # Herbs, Spices & Seasonings
    "herbs": "Herbs, Spices & Seasonings",
    "spices": "Herbs, Spices & Seasonings",
    "seasonings": "Herbs, Spices & Seasonings",
    # Other
    "other": "Other Pantry Items",
    "pantry": "Other Pantry Items",
}

# Direct mapping: standard ingredient name → category
INGREDIENT_TO_CATEGORY = {
    # --- Meat, Poultry & Seafood ---
    "chicken wings": "Meat, Poultry & Seafood",
    "chicken breast": "Meat, Poultry & Seafood",
    "chicken thigh": "Meat, Poultry & Seafood",
    "beef chuck roast": "Meat, Poultry & Seafood",
    "salmon fillets": "Meat, Poultry & Seafood",
    "shrimp": "Meat, Poultry & Seafood",
    "tofu": "Meat, Poultry & Seafood",

    # --- Fruits ---
    "watermelon": "Fruits",
    "bananas": "Fruits",
    "avocado": "Fruits",
    "lemon": "Fruits",
    "acai": "Fruits",
    "guava": "Fruits",
    "passion fruit": "Fruits",
    "mango": "Fruits",
    "papaya": "Fruits",
    "acerola": "Fruits",
    "cupuacu": "Fruits",
    "graviola": "Fruits",
    "cashew fruit": "Fruits",
    "jabuticaba": "Fruits",
    "pitanga": "Fruits",
    "orange": "Fruits",
    "apple": "Fruits",
    "strawberry": "Fruits",
    "blueberry": "Fruits",
    "grape": "Fruits",
    "pineapple": "Fruits",
    "peach": "Fruits",
    "pear": "Fruits",
    "cherry": "Fruits",
    "plum": "Fruits",
    "raspberry": "Fruits",
    "blackberry": "Fruits",
    "kiwi": "Fruits",

    # --- Vegetables & Greens ---
    "red onion": "Vegetables & Greens",
    "onion": "Vegetables & Greens",
    "garlic": "Vegetables & Greens",
    "ginger": "Vegetables & Greens",
    "spinach": "Vegetables & Greens",
    "mixed mushrooms": "Vegetables & Greens",
    "potatoes": "Vegetables & Greens",
    "carrots": "Vegetables & Greens",
    "celery": "Vegetables & Greens",
    "asparagus spears": "Vegetables & Greens",
    "cucumber": "Vegetables & Greens",
    "green onions": "Vegetables & Greens",
    "kalamata olives": "Vegetables & Greens",
    "cherry tomatoes": "Vegetables & Greens",
    "zucchini": "Vegetables & Greens",
    "bell pepper": "Vegetables & Greens",
    "peas": "Vegetables & Greens",
    "roma tomato": "Vegetables & Greens",
    "tomato": "Vegetables & Greens",
    "jalapeno": "Vegetables & Greens",
    "sweet potatoes": "Vegetables & Greens",
    "bamboo shoots": "Vegetables & Greens",
    "broccoli florets": "Vegetables & Greens",

    # --- Dairy & Eggs ---
    "parmesan cheese": "Dairy & Eggs",
    "feta cheese": "Dairy & Eggs",
    "fresh mozzarella cheese": "Dairy & Eggs",
    "butter": "Dairy & Eggs",
    "eggs": "Dairy & Eggs",
    "gruyere cheese": "Dairy & Eggs",
    "heavy cream": "Dairy & Eggs",
    "milk": "Dairy & Eggs",
    "greek yogurt": "Dairy & Eggs",
    "almond milk": "Dairy & Eggs",

    # --- Grains, Pasta & Baking ---
    "red lentils": "Grains, Pasta & Baking",
    "pizza dough": "Grains, Pasta & Baking",
    "all-purpose flour": "Grains, Pasta & Baking",
    "sugar": "Grains, Pasta & Baking",
    "baking soda": "Grains, Pasta & Baking",
    "cocoa powder": "Grains, Pasta & Baking",
    "dark chocolate chips": "Grains, Pasta & Baking",
    "corn tortillas": "Grains, Pasta & Baking",
    "arborio rice": "Grains, Pasta & Baking",
    "almond flour": "Grains, Pasta & Baking",
    "baking powder": "Grains, Pasta & Baking",
    "rice paper wrappers": "Grains, Pasta & Baking",
    "rice vermicelli noodles": "Grains, Pasta & Baking",
    "baguette slices": "Grains, Pasta & Baking",
    "cornstarch": "Grains, Pasta & Baking",
    "penne pasta": "Grains, Pasta & Baking",
    "brown sugar": "Grains, Pasta & Baking",

    # --- Oils, Condiments & Liquids ---
    "olive oil": "Oils, Condiments & Liquids",
    "extra virgin olive oil": "Oils, Condiments & Liquids",
    "lime juice": "Oils, Condiments & Liquids",
    "canned tomatoes": "Oils, Condiments & Liquids",
    "coconut milk": "Oils, Condiments & Liquids",
    "vegetable broth": "Oils, Condiments & Liquids",
    "canned san marzano tomatoes": "Oils, Condiments & Liquids",
    "maple syrup": "Oils, Condiments & Liquids",
    "salsa": "Oils, Condiments & Liquids",
    "white wine": "Oils, Condiments & Liquids",
    "beef broth": "Oils, Condiments & Liquids",
    "tomato paste": "Oils, Condiments & Liquids",
    "worcestershire sauce": "Oils, Condiments & Liquids",
    "peanut butter": "Oils, Condiments & Liquids",
    "soy sauce": "Oils, Condiments & Liquids",
    "hoisin sauce": "Oils, Condiments & Liquids",
    "dry sherry": "Oils, Condiments & Liquids",
    "sesame oil": "Oils, Condiments & Liquids",
    "red wine vinegar": "Oils, Condiments & Liquids",
    "canned crushed tomatoes": "Oils, Condiments & Liquids",
    "canned tomato sauce": "Oils, Condiments & Liquids",

    # --- Herbs, Spices & Seasonings ---
    "garlic powder": "Herbs, Spices & Seasonings",
    "salt": "Herbs, Spices & Seasonings",
    "black pepper": "Herbs, Spices & Seasonings",
    "parsley": "Herbs, Spices & Seasonings",
    "fresh mint leaves": "Herbs, Spices & Seasonings",
    "turmeric": "Herbs, Spices & Seasonings",
    "cumin": "Herbs, Spices & Seasonings",
    "garam masala": "Herbs, Spices & Seasonings",
    "cilantro": "Herbs, Spices & Seasonings",
    "fresh basil leaves": "Herbs, Spices & Seasonings",
    "vanilla extract": "Herbs, Spices & Seasonings",
    "cinnamon": "Herbs, Spices & Seasonings",
    "taco seasoning": "Herbs, Spices & Seasonings",
    "thyme": "Herbs, Spices & Seasonings",
    "rosemary": "Herbs, Spices & Seasonings",
    "fresh dill": "Herbs, Spices & Seasonings",
    "bay leaf": "Herbs, Spices & Seasonings",
    "sesame seeds": "Herbs, Spices & Seasonings",
    "dried oregano": "Herbs, Spices & Seasonings",
    "lemon zest": "Herbs, Spices & Seasonings",
    "chili powder": "Herbs, Spices & Seasonings",
    "paprika": "Herbs, Spices & Seasonings",
    "thai green curry paste": "Herbs, Spices & Seasonings",
}

import re

def get_ingredient_category(name: str) -> str:
    """Returns the category for a given ingredient name.

    1. Direct lookup in INGREDIENT_TO_CATEGORY.
    2. Regex-based heuristic fallback for unknown ingredients.
    3. Falls back to 'Other Pantry Items'.
    """
    if not name:
        return "Other Pantry Items"
    clean = name.strip().lower()

    # 1. Direct lookup
    if clean in INGREDIENT_TO_CATEGORY:
        return INGREDIENT_TO_CATEGORY[clean]

    # 2. Heuristic fallbacks (mirrors frontend logic)
    if re.search(r"\b(chicken|beef|steak|pork|chops|ribs|turkey|lamb|duck|sausage|bacon|ham|salmon|shrimp|prawn|crab|lobster|tuna|fish|meat|mutton|veal|seafood|tofu)\b", clean):
        return "Meat, Poultry & Seafood"
    if re.search(r"\b(powder|salt|seasoning|extract|cinnamon|oregano|basil|mint|parsley|cilantro|thyme|rosemary|dill|bay leaf|curry|cumin|masala|seeds|herb|spice|spices|seasonings|zest)\b", clean):
        return "Herbs, Spices & Seasonings"
    if re.search(r"\b(oil|sauce|vinegar|broth|stock|syrup|honey|juice|wine|sherry|salsa|paste|liquid|liquids|condiment|condiments|ketchup|mustard|mayo|mayonnaise|dressing)\b", clean):
        return "Oils, Condiments & Liquids"
    if re.search(r"\b(apple|banana|orange|grape|melon|watermelon|peach|pear|cherry|plum|pineapple|mango|papaya|guava|kiwi|lemon|lime|coconut|fig|date|berry|berries|strawberry|blueberry|raspberry|blackberry)\b", clean):
        return "Fruits"
    if re.search(r"\b(onion|garlic|tomato|potato|carrot|celery|spinach|lettuce|cabbage|broccoli|cauliflower|cucumber|zucchini|squash|mushroom|kale|peas|asparagus|ginger|eggplant|pepper|chili|jalapeno|greens|vegetable|vegetables)\b", clean):
        return "Vegetables & Greens"
    if re.search(r"\b(cheese|milk|butter|egg|eggs|cream|yogurt|dairy)\b", clean):
        return "Dairy & Eggs"
    if re.search(r"\b(flour|sugar|rice|pasta|noodle|noodles|bread|baguette|tortilla|tortillas|dough|oats|grain|grains|baking)\b", clean):
        return "Grains, Pasta & Baking"

    return "Other Pantry Items"


def resolve_category_aliases(raw_names: list[str]) -> list[str]:
    """Converts a list of short alias strings (e.g. ['meat', 'vegetables'])
    into canonical category names, deduplicating while preserving order."""
    seen = set()
    result = []
    for alias in raw_names:
        canonical = CATEGORY_ALIASES.get(alias.strip().lower())
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result
