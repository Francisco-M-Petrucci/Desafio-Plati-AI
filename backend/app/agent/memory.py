import re
from typing import Optional
from app.recipes_vector_db import RecipeVectorDB

recipe_db = RecipeVectorDB()

def find_recipe_id(name: str, name_to_id: dict) -> Optional[int]:
    name_clean = name.lower().strip()
    if name_clean in name_to_id:
        return name_to_id[name_clean]
    # Fallback to substring matching
    for k, v in name_to_id.items():
        if name_clean in k or k in name_clean:
            return v
    return None

def minify_assistant_message(content: str) -> str:
    """
    Minifies assistant message content to remove token-heavy formatting and recipe steps,
    replacing them with concise semantic descriptions (names & IDs) for the LLM history.
    """
    if not content:
        return content
        
    try:
        # Load all recipes metadata to build name-to-ID lookup map
        all_metadata = recipe_db.get_all_recipe_metadata()
        name_to_id = {r["name"].lower().strip(): r["id"] for r in all_metadata}
    except Exception as e:
        print(f"Error loading metadata in minifier: {e}")
        name_to_id = {}

    content_lower = content.lower()
    has_steps = any(kw in content_lower for kw in ["steps:", "steps\n", "instructions:"])
    
    # Matches bullet points like * **Name** or - **Name** or • **Name**
    # Using multiline matching to find bullets at the start of any line
    recipe_matches = re.findall(r"^\s*[\*\-•]\s*\*\*(?P<name>[^*]+?)\*\*", content, re.MULTILINE)
    
    excluded_headers = {"cook time", "ingredients you have", "missing ingredients", "steps", "inventory updates", "tone"}
    recipe_names = [name.strip() for name in recipe_matches if name.strip().lower() not in excluded_headers]
    
    # If no matches found in bullet headers, search for any bold text that matches a known recipe name
    if not recipe_names and name_to_id:
        bold_matches = re.findall(r"\*\*(?P<name>[^*]+?)\*\*", content)
        for name in bold_matches:
            if name.strip().lower() in name_to_id:
                recipe_names.append(name.strip())

    # Fallback: check if any known recipe name appears in the content text (case-insensitive substring match)
    if not recipe_names and name_to_id:
        # Sort names by length descending to match longer names first
        sorted_names = sorted(name_to_id.keys(), key=len, reverse=True)
        for r_name in sorted_names:
            if r_name in content_lower:
                proper_name = next((r["name"] for r in all_metadata if r["name"].lower().strip() == r_name), r_name)
                recipe_names.append(proper_name)
                break

    if not recipe_names:
        return content

    if has_steps:
        # Recipe instructions message: replace with compact placeholder for the main recipe discussed
        recipe_name = recipe_names[0]
        recipe_id = find_recipe_id(recipe_name, name_to_id)
        id_str = f" (ID: {recipe_id})" if recipe_id else ""
        return f"[Provided instructions for recipe: {recipe_name}{id_str}]"
    else:
        # Recipe recommendations message: replace with a list of suggested recipes with IDs
        recipes_found = []
        for name in recipe_names:
            recipe_id = find_recipe_id(name, name_to_id)
            id_str = f" (ID: {recipe_id})" if recipe_id else ""
            recipes_found.append(f"{name}{id_str}")
        return f"[Suggested recipes: {', '.join(recipes_found)}]"
