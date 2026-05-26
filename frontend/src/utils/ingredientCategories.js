// Categorization structure for premium UI styling and semantic separation
export const CATEGORY_STYLES = {
  'Meat, Poultry & Seafood': {
    emoji: '🥩',
    bg: 'rgba(239, 68, 68, 0.08)', // Red/orange tint
    border: 'rgba(239, 68, 68, 0.2)',
    text: '#fca5a5',
    pillBg: 'rgba(239, 68, 68, 0.15)',
    accent: '#ef4444'
  },
  'Fruits': {
    emoji: '🍎',
    bg: 'rgba(236, 72, 153, 0.08)', // Pink/magenta tint
    border: 'rgba(236, 72, 153, 0.2)',
    text: '#fbcfe8',
    pillBg: 'rgba(236, 72, 153, 0.15)',
    accent: '#ec4899'
  },
  'Vegetables & Greens': {
    emoji: '🥦',
    bg: 'rgba(34, 197, 94, 0.08)', // Green tint
    border: 'rgba(34, 197, 94, 0.2)',
    text: '#bbf7d0',
    pillBg: 'rgba(34, 197, 94, 0.15)',
    accent: '#22c55e'
  },
  'Dairy & Eggs': {
    emoji: '🧀',
    bg: 'rgba(234, 179, 8, 0.08)', // Amber/yellow tint
    border: 'rgba(234, 179, 8, 0.2)',
    text: '#fef08a',
    pillBg: 'rgba(234, 179, 8, 0.15)',
    accent: '#eab308'
  },
  'Grains, Pasta & Baking': {
    emoji: '🌾',
    bg: 'rgba(217, 119, 6, 0.08)', // Gold/brown tint
    border: 'rgba(217, 119, 6, 0.2)',
    text: '#fde047',
    pillBg: 'rgba(217, 119, 6, 0.15)',
    accent: '#d97706'
  },
  'Oils, Condiments & Liquids': {
    emoji: '🫒',
    bg: 'rgba(99, 102, 241, 0.08)', // Indigo/blue tint
    border: 'rgba(99, 102, 241, 0.2)',
    text: '#c7d2fe',
    pillBg: 'rgba(99, 102, 241, 0.15)',
    accent: '#6366f1'
  },
  'Herbs, Spices & Seasonings': {
    emoji: '🌿',
    bg: 'rgba(20, 184, 166, 0.08)', // Teal/emerald tint
    border: 'rgba(20, 184, 166, 0.2)',
    text: '#99f6e4',
    pillBg: 'rgba(20, 184, 166, 0.15)',
    accent: '#14b8a6'
  },
  'Other Pantry Items': {
    emoji: '📦',
    bg: 'rgba(148, 163, 184, 0.08)', // Slate/gray tint
    border: 'rgba(148, 163, 184, 0.2)',
    text: '#cbd5e1',
    pillBg: 'rgba(148, 163, 184, 0.15)',
    accent: '#94a3b8'
  }
};

// Maps standard ingredient names from ingredients_kb.json to their respective category
const INGREDIENT_TO_CATEGORY_MAP = {
  // --- Meat, Poultry & Seafood ---
  'chicken wings': 'Meat, Poultry & Seafood',
  'chicken breast': 'Meat, Poultry & Seafood',
  'chicken thigh': 'Meat, Poultry & Seafood',
  'beef chuck roast': 'Meat, Poultry & Seafood',
  'salmon fillets': 'Meat, Poultry & Seafood',
  'shrimp': 'Meat, Poultry & Seafood',
  'tofu': 'Meat, Poultry & Seafood', // Soy-based protein alternative

  // --- Fruits ---
  'watermelon': 'Fruits',
  'bananas': 'Fruits',
  'avocado': 'Fruits',
  'lemon': 'Fruits',
  'acai': 'Fruits',
  'guava': 'Fruits',
  'passion fruit': 'Fruits',
  'mango': 'Fruits',
  'papaya': 'Fruits',
  'acerola': 'Fruits',
  'cupuacu': 'Fruits',
  'graviola': 'Fruits',
  'cashew fruit': 'Fruits',
  'jabuticaba': 'Fruits',
  'pitanga': 'Fruits',
  'orange': 'Fruits',
  'apple': 'Fruits',
  'strawberry': 'Fruits',
  'blueberry': 'Fruits',
  'grape': 'Fruits',
  'pineapple': 'Fruits',
  'peach': 'Fruits',
  'pear': 'Fruits',
  'cherry': 'Fruits',
  'plum': 'Fruits',
  'raspberry': 'Fruits',
  'blackberry': 'Fruits',
  'kiwi': 'Fruits',

  // --- Vegetables & Greens ---
  'red onion': 'Vegetables & Greens',
  'onion': 'Vegetables & Greens',
  'garlic': 'Vegetables & Greens',
  'ginger': 'Vegetables & Greens',
  'spinach': 'Vegetables & Greens',
  'mixed mushrooms': 'Vegetables & Greens',
  'potatoes': 'Vegetables & Greens',
  'carrots': 'Vegetables & Greens',
  'celery': 'Vegetables & Greens',
  'asparagus spears': 'Vegetables & Greens',
  'cucumber': 'Vegetables & Greens',
  'green onions': 'Vegetables & Greens',
  'kalamata olives': 'Vegetables & Greens',
  'cherry tomatoes': 'Vegetables & Greens',
  'zucchini': 'Vegetables & Greens',
  'bell pepper': 'Vegetables & Greens',
  'peas': 'Vegetables & Greens',
  'roma tomato': 'Vegetables & Greens',
  'tomato': 'Vegetables & Greens',
  'jalapeno': 'Vegetables & Greens',
  'sweet potatoes': 'Vegetables & Greens',
  'bamboo shoots': 'Vegetables & Greens',
  'broccoli florets': 'Vegetables & Greens',

  // --- Dairy & Eggs ---
  'parmesan cheese': 'Dairy & Eggs',
  'feta cheese': 'Dairy & Eggs',
  'fresh mozzarella cheese': 'Dairy & Eggs',
  'butter': 'Dairy & Eggs',
  'eggs': 'Dairy & Eggs',
  'gruyere cheese': 'Dairy & Eggs',
  'heavy cream': 'Dairy & Eggs',
  'milk': 'Dairy & Eggs',
  'greek yogurt': 'Dairy & Eggs',
  'almond milk': 'Dairy & Eggs', // Dairy alternative

  // --- Grains, Pasta & Baking ---
  'red lentils': 'Grains, Pasta & Baking',
  'pizza dough': 'Grains, Pasta & Baking',
  'all-purpose flour': 'Grains, Pasta & Baking',
  'sugar': 'Grains, Pasta & Baking',
  'baking soda': 'Grains, Pasta & Baking',
  'cocoa powder': 'Grains, Pasta & Baking',
  'dark chocolate chips': 'Grains, Pasta & Baking',
  'corn tortillas': 'Grains, Pasta & Baking',
  'arborio rice': 'Grains, Pasta & Baking',
  'almond flour': 'Grains, Pasta & Baking',
  'baking powder': 'Grains, Pasta & Baking',
  'rice paper wrappers': 'Grains, Pasta & Baking',
  'rice vermicelli noodles': 'Grains, Pasta & Baking',
  'baguette slices': 'Grains, Pasta & Baking',
  'cornstarch': 'Grains, Pasta & Baking',
  'penne pasta': 'Grains, Pasta & Baking',
  'brown sugar': 'Grains, Pasta & Baking',

  // --- Oils, Condiments & Liquids ---
  'olive oil': 'Oils, Condiments & Liquids',
  'extra virgin olive oil': 'Oils, Condiments & Liquids',
  'lime juice': 'Oils, Condiments & Liquids',
  'canned tomatoes': 'Oils, Condiments & Liquids',
  'coconut milk': 'Oils, Condiments & Liquids',
  'vegetable broth': 'Oils, Condiments & Liquids',
  'canned san marzano tomatoes': 'Oils, Condiments & Liquids',
  'maple syrup': 'Oils, Condiments & Liquids',
  'salsa': 'Oils, Condiments & Liquids',
  'white wine': 'Oils, Condiments & Liquids',
  'beef broth': 'Oils, Condiments & Liquids',
  'tomato paste': 'Oils, Condiments & Liquids',
  'worcestershire sauce': 'Oils, Condiments & Liquids',
  'peanut butter': 'Oils, Condiments & Liquids',
  'soy sauce': 'Oils, Condiments & Liquids',
  'hoisin sauce': 'Oils, Condiments & Liquids',
  'dry sherry': 'Oils, Condiments & Liquids',
  'sesame oil': 'Oils, Condiments & Liquids',
  'red wine vinegar': 'Oils, Condiments & Liquids',
  'canned crushed tomatoes': 'Oils, Condiments & Liquids',
  'canned tomato sauce': 'Oils, Condiments & Liquids',

  // --- Herbs, Spices & Seasonings ---
  'garlic powder': 'Herbs, Spices & Seasonings',
  'salt': 'Herbs, Spices & Seasonings',
  'black pepper': 'Herbs, Spices & Seasonings',
  'parsley': 'Herbs, Spices & Seasonings',
  'fresh mint leaves': 'Herbs, Spices & Seasonings',
  'turmeric': 'Herbs, Spices & Seasonings',
  'cumin': 'Herbs, Spices & Seasonings',
  'garam masala': 'Herbs, Spices & Seasonings',
  'cilantro': 'Herbs, Spices & Seasonings',
  'fresh basil leaves': 'Herbs, Spices & Seasonings',
  'vanilla extract': 'Herbs, Spices & Seasonings',
  'cinnamon': 'Herbs, Spices & Seasonings',
  'taco seasoning': 'Herbs, Spices & Seasonings',
  'thyme': 'Herbs, Spices & Seasonings',
  'rosemary': 'Herbs, Spices & Seasonings',
  'fresh dill': 'Herbs, Spices & Seasonings',
  'bay leaf': 'Herbs, Spices & Seasonings',
  'sesame seeds': 'Herbs, Spices & Seasonings',
  'dried oregano': 'Herbs, Spices & Seasonings',
  'lemon zest': 'Herbs, Spices & Seasonings',
  'chili powder': 'Herbs, Spices & Seasonings',
  'paprika': 'Herbs, Spices & Seasonings',
  'thai green curry paste': 'Herbs, Spices & Seasonings'
};

export function getIngredientCategory(name) {
  if (!name) return 'Other Pantry Items';
  const cleanName = name.trim().toLowerCase();
  
  // 1. Direct lookup in the KB mapping dictionary
  if (INGREDIENT_TO_CATEGORY_MAP[cleanName]) {
    return INGREDIENT_TO_CATEGORY_MAP[cleanName];
  }
  
  // 2. Fallback heuristics for custom or unmatched ingredients (e.g. "pork chops")
  
  // Meat, Poultry & Seafood
  if (/\b(chicken|beef|steak|pork|chops|ribs|turkey|lamb|duck|sausage|bacon|ham|salmon|shrimp|prawn|crab|lobster|tuna|fish|meat|mutton|veal|seafood|tofu)\b/i.test(cleanName)) {
    return 'Meat, Poultry & Seafood';
  }
  
  // Herbs, Spices & Seasonings
  if (/\b(powder|salt|seasoning|extract|cinnamon|oregano|basil|mint|parsley|cilantro|thyme|rosemary|dill|bay leaf|curry|cumin|masala|seeds|herb|spice|spices|seasonings|zest)\b/i.test(cleanName)) {
    return 'Herbs, Spices & Seasonings';
  }
  
  // Oils, Condiments & Liquids
  if (/\b(oil|sauce|vinegar|broth|stock|syrup|honey|juice|wine|sherry|salsa|paste|liquid|liquids|condiment|condiments|ketchup|mustard|mayo|mayonnaise|dressing)\b/i.test(cleanName)) {
    return 'Oils, Condiments & Liquids';
  }
  
  // Fruits
  if (/\b(apple|banana|orange|grape|melon|watermelon|peach|pear|cherry|plum|pineapple|mango|papaya|guava|kiwi|lemon|lime|coconut|fig|date|berry|berries|strawberry|blueberry|raspberry|blackberry)\b/i.test(cleanName)) {
    return 'Fruits';
  }
  
  // Vegetables & Greens
  if (/\b(onion|garlic|tomato|potato|carrot|celery|spinach|lettuce|cabbage|broccoli|cauliflower|cucumber|zucchini|squash|mushroom|kale|peas|asparagus|ginger|eggplant|pepper|chili|jalapeno|greens|vegetable|vegetables)\b/i.test(cleanName)) {
    return 'Vegetables & Greens';
  }
  
  // Dairy & Eggs
  if (/\b(cheese|milk|butter|egg|eggs|cream|yogurt|dairy)\b/i.test(cleanName)) {
    return 'Dairy & Eggs';
  }
  
  // Grains, Pasta & Baking
  if (/\b(flour|sugar|rice|pasta|noodle|noodles|bread|baguette|tortilla|tortillas|dough|oats|grain|grains|baking)\b/i.test(cleanName)) {
    return 'Grains, Pasta & Baking';
  }

  // Default fallback for completely unmatched custom ingredients
  return 'Other Pantry Items';
}
