import os
import json
import difflib

# Module-level cache for knowledge base and synonym maps
_kb_data = None
_synonym_to_standard_map = None

def _load_kb():
    global _kb_data, _synonym_to_standard_map
    if _kb_data is not None:
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    kb_path = os.path.join(base_dir, "ingredients_kb.json")
    
    if os.path.exists(kb_path):
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                _kb_data = json.load(f)
        except Exception as e:
            print(f"Error loading ingredients_kb.json: {e}")
            _kb_data = {}
    else:
        print(f"Warning: ingredients_kb.json not found at {kb_path}")
        _kb_data = {}
        
    # Build a flat dictionary mapping standard name and all synonyms to standard name
    _synonym_to_standard_map = {}
    for standard_name, synonyms in _kb_data.items():
        standard_clean = standard_name.strip().lower()
        _synonym_to_standard_map[standard_clean] = standard_name
        for syn in synonyms:
            syn_clean = syn.strip().lower()
            if syn_clean:
                _synonym_to_standard_map[syn_clean] = standard_name

def standardize_ingredient(raw_name: str) -> str:
    """
    Standardizes a raw ingredient name.
    
    1. Cleans input (lowercase, strips spaces).
    2. Performs exact lookup in standard names and synonyms list.
    3. Performs fuzzy matching using difflib with a cutoff of 0.55.
    4. Falls back to cleaned raw name if no high-confidence match is found.
    """
    if not raw_name:
        return ""
        
    _load_kb()
    
    # 1. Clean input
    cleaned_name = raw_name.strip().lower()
    if not cleaned_name:
        return ""
        
    # 2. Exact match check
    if cleaned_name in _synonym_to_standard_map:
        return _synonym_to_standard_map[cleaned_name]
        
    # 3. Fuzzy matching using difflib
    all_keys = list(_synonym_to_standard_map.keys())
    matches = difflib.get_close_matches(cleaned_name, all_keys, n=1, cutoff=0.55)
    
    if matches:
        matched_key = matches[0]
        return _synonym_to_standard_map[matched_key]
        
    # 4. Fallback to cleaned raw name
    return cleaned_name
