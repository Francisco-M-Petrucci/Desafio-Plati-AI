import os
import sys
import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agent.tools import get_filtered_recipe_ids, recipe_db
from app.agent.graph import agent_node, extract_preferences_node

# =====================================================================
# Category 1: RAG Pre-filtering Evals (Deterministic)
# =====================================================================

def test_case_1_gluten_free_filter():
    """Eval 1: A user with gluten-free restriction should not receive pasta/wheat recipes."""
    mock_profile = {
        "appliances": ["oven", "stove", "microwave", "airfryer", "blender"],
        "restrictions": ["gluten-free"],
        "ingredients": ["chicken"]
    }
    compatible_ids = get_filtered_recipe_ids(mock_profile)
    for recipe_id in compatible_ids:
        recipe = recipe_db.get_recipe_by_id(recipe_id)
        assert "gluten-free" in [t.lower() for t in recipe.get("dietary_tags", [])], f"Recipe {recipe_id} is not gluten-free"

def test_case_2_vegetarian_filter():
    """Eval 2: A user with vegetarian restriction should not receive meat recipes."""
    mock_profile = {
        "appliances": ["oven", "stove", "microwave", "airfryer", "blender"],
        "restrictions": ["vegetarian"],
        "ingredients": ["tomato"]
    }
    compatible_ids = get_filtered_recipe_ids(mock_profile)
    for recipe_id in compatible_ids:
        recipe = recipe_db.get_recipe_by_id(recipe_id)
        tags = [t.lower() for t in recipe.get("dietary_tags", [])]
        assert "vegetarian" in tags or "vegan" in tags, f"Recipe {recipe_id} is not vegetarian"

def test_case_3_appliance_filter_missing_oven():
    """Eval 3: A user without an oven should not get oven-only recipes."""
    mock_profile = {
        "appliances": ["stove", "microwave"], # missing oven
        "restrictions": [],
        "ingredients": ["chicken"]
    }
    compatible_ids = get_filtered_recipe_ids(mock_profile)
    for recipe_id in compatible_ids:
        recipe = recipe_db.get_recipe_by_id(recipe_id)
        req_appliances = [a.lower() for a in recipe.get("required_appliances", [])]
        assert "oven" not in req_appliances, f"Recipe {recipe_id} requires an oven but user lacks one"

def test_case_4_ingredient_availability():
    """Eval 4: User missing more than 4 ingredients is filtered out."""
    mock_profile = {
        "appliances": ["stove", "oven", "blender", "microwave", "airfryer"],
        "restrictions": [],
        "ingredients": [] # Empty inventory
    }
    compatible_ids = get_filtered_recipe_ids(mock_profile)
    for recipe_id in compatible_ids:
        recipe = recipe_db.get_recipe_by_id(recipe_id)
        assert len(recipe.get("ingredients", [])) <= 4, f"Recipe {recipe_id} has >4 ingredients and user has 0"

def test_case_5_perfect_match():
    """Eval 5: Allowed recipe passes all filters successfully."""
    mock_profile = {
        "appliances": ["airfryer", "stove", "oven"],
        "restrictions": ["gluten-free"],
        "ingredients": ["chicken wings", "parmesan cheese", "garlic powder"]
    }
    compatible_ids = get_filtered_recipe_ids(mock_profile)
    recipes = [recipe_db.get_recipe_by_id(rid) for rid in compatible_ids]
    names = [r["name"].lower() for r in recipes if r]
    assert any("chicken wings" in name for name in names), "Perfect match recipe was incorrectly filtered out"


# =====================================================================
# Category 2: Fact Extraction Evals (LLM-based)
# =====================================================================

@patch("app.agent.graph.add_user_fact_to_db")
@patch("app.agent.graph.save_temporary_preferences_to_db")
def test_case_6_extract_permanent_fact(mock_save_temp, mock_add_fact):
    """Eval 6: Extracting a permanent fact (e.g., training for marathon)."""
    state = {
        "user_id": 999,
        "messages": [HumanMessage(content="I am training for a marathon next month.")],
        "user_profile": {"facts": [], "asked_preferences": False}
    }
    result = extract_preferences_node(state)
    assert mock_add_fact.called, "add_user_fact_to_db was not called"
    fact_saved = mock_add_fact.call_args[0][1].lower()
    assert "marathon" in fact_saved, f"Expected 'marathon' in extracted fact, got: {fact_saved}"

@patch("app.agent.graph.add_user_fact_to_db")
@patch("app.agent.graph.save_temporary_preferences_to_db")
def test_case_7_extract_temporary_want(mock_save_temp, mock_add_fact):
    """Eval 7: Extracting a temporary preference (want) when prompted."""
    state = {
        "user_id": 999,
        "messages": [HumanMessage(content="I want something sweet right now.")],
        "user_profile": {"facts": [], "asked_preferences": True}
    }
    result = extract_preferences_node(state)
    assert mock_save_temp.called, "save_temporary_preferences_to_db was not called"
    wants = [w.lower() for w in mock_save_temp.call_args[0][1]]
    assert any("sweet" in w for w in wants) or any("dessert" in w for w in wants), "Failed to extract temporary want"

@patch("app.agent.graph.add_user_fact_to_db")
@patch("app.agent.graph.save_temporary_preferences_to_db")
def test_case_8_extract_negative_fact(mock_save_temp, mock_add_fact):
    """Eval 8: Extracting a permanent dislike (spicy food)."""
    state = {
        "user_id": 999,
        "messages": [HumanMessage(content="I absolutely despise spicy food.")],
        "user_profile": {"facts": [], "asked_preferences": False}
    }
    result = extract_preferences_node(state)
    assert mock_add_fact.called, "add_user_fact_to_db was not called for negative fact"
    fact_saved = mock_add_fact.call_args[0][1].lower()
    assert "spicy" in fact_saved and ("dislike" in fact_saved or "hate" in fact_saved or "despise" in fact_saved), "Failed to extract negative fact"


# =====================================================================
# Category 3: Tool Selection & Intent Evals (LLM-based)
# =====================================================================

def test_case_9_general_chat_no_search():
    """Eval 9: General chat should NOT bind the search tool to prevent hallucinations."""
    state = {
        "user_id": 999,
        "messages": [HumanMessage(content="Hi, how are you?")],
        "user_profile": {"facts": [], "wants_temporary": "", "asked_preferences": False},
        "user_intents": ["general_chat"],
        "recent_memory_updates": {}
    }
    result = agent_node(state)
    # result can be a dict with "messages" or just the response depending on implementation
    last_msg = result["messages"][-1] if isinstance(result, dict) and "messages" in result else result
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        tool_names = [tc["name"] for tc in last_msg.tool_calls]
        assert "search_recipes" not in tool_names, "Search tool hallucinated for general chat"

def test_case_10_recipe_request_binds_search():
    """Eval 10: Explicit recipe requests MUST bind and call the search tool."""
    state = {
        "user_id": 999,
        "messages": [HumanMessage(content="Can you recommend a chicken recipe?")],
        "user_profile": {"facts": [], "wants_temporary": "chicken", "asked_preferences": False},
        "user_intents": ["recipe_recommendation_request"],
        "recent_memory_updates": {}
    }
    result = agent_node(state)
    last_msg = result["messages"][-1] if isinstance(result, dict) and "messages" in result else result
    assert hasattr(last_msg, "tool_calls") and last_msg.tool_calls, "Agent did not generate any tool calls"
    tool_names = [tc["name"] for tc in last_msg.tool_calls]
    assert "search_recipes" in tool_names, "Agent failed to bind/call search_recipes for a recipe request"

def test_case_11_recipe_details_intent():
    """Eval 11: Asking for steps/instructions should bind the recipe details tool."""
    state = {
        "user_id": 999,
        "messages": [
            AIMessage(content="I recommend Recipe ID: 123 - Chicken Parmesan"),
            HumanMessage(content="What are the exact steps to make it?")
        ],
        "user_profile": {"facts": [], "wants_temporary": "", "asked_preferences": False},
        "user_intents": ["recipe_details_request"],
        "recent_memory_updates": {}
    }
    result = agent_node(state)
    last_msg = result["messages"][-1] if isinstance(result, dict) and "messages" in result else result
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        tool_names = [tc["name"] for tc in last_msg.tool_calls]
        assert "get_recipe_details_tool" in tool_names, "Agent failed to bind/call details tool"
