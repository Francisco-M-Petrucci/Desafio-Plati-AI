import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.ingredient_categories import get_ingredient_category, resolve_category_aliases, CATEGORY_ORDER
from app.agent.prompts import SYSTEM_PROMPT_WITH_SEARCH, SYSTEM_PROMPT_WITHOUT_SEARCH, SYSTEM_PROMPT_POST_SEARCH, FACT_EXTRACTION_PROMPT, POST_SEARCH_CROSS_CHECK_SECTION
from app.agent.tools import (
    get_user_profile_data,
    update_ingredients_in_db,
    add_user_fact_to_db,
    remove_user_fact_from_db,
    save_temporary_preferences_to_db,
    get_filtered_recipe_ids,
    format_recipe_results,
    get_recipe_details_by_id,
    recipe_db,
    set_user_asked_preferences
)

# 1. LLM Initializer
_llm_instance_70b = None
_llm_instance_8b = None

def get_llm(model_name: str = "meta/llama-3.1-70b-instruct") -> ChatOpenAI:
    global _llm_instance_70b, _llm_instance_8b
    
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and not groq_key.startswith("gsk-your-key") and not groq_key.startswith("your_groq_api_key") and len(groq_key) > 5:
        # Use Groq Cloud
        if "70b" in model_name or model_name == "llama-3.3-70b-versatile":
            if _llm_instance_70b is None:
                _llm_instance_70b = ChatOpenAI(
                    model="llama-3.3-70b-versatile",
                    api_key=groq_key,
                    base_url="https://api.groq.com/openai/v1",
                    temperature=0.0,
                    max_retries=5
                )
            return _llm_instance_70b
        else:
            if _llm_instance_8b is None:
                _llm_instance_8b = ChatOpenAI(
                    model="llama-3.1-8b-instant",
                    api_key=groq_key,
                    base_url="https://api.groq.com/openai/v1",
                    temperature=0.0,
                    max_retries=5
                )
            return _llm_instance_8b

    # Fallback to Nvidia NIM
    if model_name == "meta/llama-3.1-70b-instruct":
        if _llm_instance_70b is None:
            nvidia_key = os.getenv("NVIDIA_API_KEY")
            if not nvidia_key or nvidia_key.startswith("nvapi-your-key"):
                raise ValueError("NVIDIA_API_KEY is not set. Please add it to your .env file.")
            _llm_instance_70b = ChatOpenAI(
                model=model_name,
                api_key=nvidia_key,
                base_url="https://integrate.api.nvidia.com/v1",
                temperature=0.0,
                max_retries=5
            )
        return _llm_instance_70b
        
    elif model_name == "meta/llama-3.1-8b-instruct":
        if _llm_instance_8b is None:
            nvidia_key = os.getenv("NVIDIA_API_KEY")
            if not nvidia_key or nvidia_key.startswith("nvapi-your-key"):
                raise ValueError("NVIDIA_API_KEY is not set. Please add it to your .env file.")
            _llm_instance_8b = ChatOpenAI(
                model=model_name,
                api_key=nvidia_key,
                base_url="https://integrate.api.nvidia.com/v1",
                temperature=0.0,
                max_retries=5
            )
        return _llm_instance_8b
        
    else:
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        return ChatOpenAI(
            model=model_name,
            api_key=nvidia_key,
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            max_retries=5
        )

# 2. Define LangChain Structured Tools for LLM Tool Binding
@tool
def search_recipes(
    query: str = "",
    culture: Optional[str] = None,
    season: Optional[str] = None
) -> str:
    """
    Search recipes by cuisine or ingredient preference. Results are pre-filtered for dietary/appliance compatibility.
    - query: specific cuisine or ingredient term (e.g., 'pasta', 'chicken', 'Mexican'). Optional; if omitted, returns any compatible recipes.
    - culture: cuisine filter if user specified one (e.g. 'Italian'). Omit if not specified.
    - season: seasonal filter if applicable (e.g. 'Summer'). Omit if not specified.
    """
    # This function body is not called directly during graph execution.
    # The tools_runner_node handles actual execution with pre-filtered IDs.
    # This definition exists for LLM tool binding (schema generation).
    return "Tool executed by runner."


@tool
def update_inventory_tool(action: str, items: List[str]) -> str:
    """
    Updates the user's kitchen ingredients inventory.
    Parameters:
    - action: 'add' (if user acquired/bought ingredients) or 'remove' (if user explicitly ran out of / finished / no longer has ingredients)
    - items: a list of ingredient names (e.g. ['tomato', 'milk'])
    """
    # The actual database update is executed in the tool runner node which has the user_id.
    # This tool definition is mostly for schema binding.
    return "Inventory updated successfully."



@tool
def get_recipe_details_tool(recipe_id: int) -> str:
    """
    Get full ingredients and cooking steps for a recipe by its ID.
    """
    return "Tool executed by runner."


@tool
def get_inventory_tool(categories: Optional[List[str]] = None) -> str:
    """
    Retrieve the user's kitchen inventory, organized by type.
    - categories: optional list of section keywords to filter (e.g. ['meat', 'vegetables']). Omit to retrieve all sections.
    """
    return "Tool executed by runner."





# 3. Graph Nodes
def load_profile_node(state: AgentState) -> Dict[str, Any]:
    """Loads the user's profile context from the SQLite database."""
    user_id = state["user_id"]
    profile = get_user_profile_data(user_id)
    return {"user_profile": profile}


def extract_preferences_node(state: AgentState) -> Dict[str, Any]:
    """
    Programmatically extracts facts/preferences from the latest user message
    using the same LLM model as the main agent and stores them directly in the SQLite database.
    This runs BEFORE the main agent node.
    """
    # 1. Retrieve the latest user message
    latest_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_user_msg = msg.content
            break
            
    if not latest_user_msg:
        return {}

    # 2. Get current profile details
    p = state["user_profile"]
    asked_pref_at_start = p.get("asked_preferences", False)
    existing_facts_str = "\n".join(f"- {f}" for f in p.get("facts", [])) if p.get("facts") else "None"
    existing_wants_str = p.get("wants_temporary", "") or "None"
    existing_not_wants_str = p.get("does_not_want_temporary", "") or "None"
    existing_appliances_str = ", ".join(p.get("appliances", [])) if p.get("appliances") else "None"
    existing_restrictions_str = ", ".join(p.get("restrictions", [])) if p.get("restrictions") else "None"

    # 3. Format the prompt and run the LLM (same as main agent)
    llm = get_llm()
    prompt = FACT_EXTRACTION_PROMPT.format(
        existing_facts=existing_facts_str,
        existing_wants=existing_wants_str,
        existing_not_wants=existing_not_wants_str,
        existing_appliances=existing_appliances_str,
        existing_restrictions=existing_restrictions_str,
        user_msg=latest_user_msg,
        asked_preferences=str(asked_pref_at_start)
    )

    intent = "general_chat"
    try:
        # Enable native JSON Mode for Groq/OpenAI to ensure schema compliance
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and not groq_key.startswith("gsk-your-key") and not groq_key.startswith("your_groq_api_key") and len(groq_key) > 5:
            llm_json = llm.bind(response_format={"type": "json_object"})
            response = llm_json.invoke([HumanMessage(content=prompt)])
        else:
            response = llm.invoke([HumanMessage(content=prompt)])
            
        content = response.content.strip()
        
        # Clean potential markdown block formatting
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        parsed = json.loads(content)
        user_id = state["user_id"]
        intent = parsed.get("user_intent", "general_chat")

        # 4. Save/remove extracted facts
        saved_facts = []
        for fact in parsed.get("permanent_facts", []):
            res = add_user_fact_to_db(user_id, fact)
            if "Saved fact" in res:
                saved_facts.append(fact)
                
        removed_facts = []
        for fact in parsed.get("permanent_facts_to_remove", []):
            res = remove_user_fact_from_db(user_id, fact)
            if "Removed fact" in res:
                removed_facts.append(fact)
                
        # Save extracted temporary preferences
        wants = parsed.get("wants_temporary", [])
        not_wants = parsed.get("does_not_want_temporary", [])
        
        # Enforce: If asked_preferences was False at start of turn, extractor must not write "anything"
        if not asked_pref_at_start:
            wants = [w for w in wants if w.lower().strip() != "anything"]
            
        # If user intent is NOT a recipe recommendation request, and we did NOT just ask them
        # for their preferences in the previous turn, do not save temporary wants!
        # This prevents statements of general preferences (like "I love Mexican food") from
        # populating the wants list when the user hasn't asked for a recipe recommendation.
        if intent != "recipe_recommendation_request" and not asked_pref_at_start:
            wants = []
        
        if wants or not_wants:
            res = save_temporary_preferences_to_db(user_id, wants, not_wants)
            print(f"Extracted temporary preferences - Result: {res}")

        if saved_facts:
            print(f"Extracted memory - Saved facts: {saved_facts}")
        if removed_facts:
            print(f"Extracted memory - Removed facts: {removed_facts}")
            
    except Exception as e:
        saved_facts = []
        removed_facts = []
        print(f"Error in extract_preferences_node: {e}")

    # 5. Reload user profile to ensure state contains the newly saved facts/preferences
    profile = get_user_profile_data(state["user_id"])
    return {
        "user_profile": profile,
        "recent_memory_updates": {"added": saved_facts, "removed": removed_facts},
        "user_intent": intent
    }



def pre_filter_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic pre-filter: removes recipes that are incompatible with
    the user's appliances or dietary restrictions BEFORE the LLM sees them.
    
    This is the key optimization — by narrowing the search space before
    the LLM runs, we prevent wasted tokens on unusable recipes and
    eliminate retry tool calls when the LLM receives incompatible results.
    """
    profile = state["user_profile"]
    compatible_ids = get_filtered_recipe_ids(profile)
    print(f"Pre-filter: {len(compatible_ids)} compatible recipes for user (from {len(recipe_db.get_all_recipe_metadata())} total)")
    return {"compatible_recipe_ids": compatible_ids}


# Module-level cache for known food/cuisine terms
_known_food_terms = None

def _get_known_food_terms() -> set:
    """Build a set of food-related terms from the recipe DB cuisines, recipe names/ingredients, and curated keywords."""
    global _known_food_terms
    if _known_food_terms is not None:
        return _known_food_terms

    # Data-driven: extract cuisine types, recipe name words, and ingredient words from recipe data
    cuisines = set()
    try:
        import re
        for r in recipe_db.get_all_recipe_metadata():
            ct = r.get("cuisine_type", "").lower().strip()
            if ct:
                cuisines.add(ct)
            name = r.get("name", "").lower().strip()
            if name:
                for word in re.findall(r'[a-zA-Z]{3,}', name):
                    cuisines.add(word)
            for ing in r.get("ingredients", []):
                for word in re.findall(r'[a-zA-Z]{3,}', ing.lower()):
                    cuisines.add(word)
    except Exception:
        pass

    # Curated: common food categories and ingredients users might mention
    food_keywords = {
        "pasta", "chicken", "beef", "pork", "fish", "salmon", "shrimp", "prawn",
        "rice", "noodle", "noodles", "soup", "salad", "steak", "curry", "stew",
        "tacos", "taco", "pizza", "burger", "sushi", "tofu", "seafood",
        "chocolate", "cake", "pie", "bread", "sandwich", "wrap",
        "spicy", "grilled", "baked", "fried", "roasted", "braised",
        "tomato", "mushroom", "potato", "cheese", "egg", "eggs",
        "vegan", "vegetarian", "dessert", "appetizer", "breakfast",
    }

    _known_food_terms = cuisines | food_keywords
    return _known_food_terms



def check_details_intent(messages: List[Any]) -> bool:
    keywords = {"step", "steps", "instruction", "instructions", "detail", "details", "how to make", "how to cook"}
    import re
    if messages:
        msg = messages[-1]
        if msg.content:
            text_lower = msg.content.lower()
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower) for kw in keywords):
                return True
            if re.search(r'\b\d+\b', text_lower):
                return True
    return False


def check_inventory_intent(messages: List[Any]) -> bool:
    # 1. Broad but specific inventory keywords
    inventory_keywords = {
        "inventory", "stock", "pantry", "fridge", "cupboard", "cabinet",
        "purchased", "used up", "consume", "run out", "ran out",
        "no longer", "no more", "none left"
    }
    # 2. Specific phrases for showing or asking about inventory
    phrases = [
        r"\bdo i have\b",
        r"\bwhat do i have\b",
        r"\bwhat ingredients\b",
        r"\blist my\b",
        r"\bshow my\b",
        r"\bwhat's in\b",
        r"\bwhats in\b",
        r"\bwhat is in\b",
        r"\bwhat have i\b"
    ]
    # 3. Action verbs indicating inventory changes when referencing food/items
    actions = {
        "bought", "got", "acquired", "used", "cooked", "remove", "add", "finish", "finished", "out of"
    }
    
    import re
    user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    for msg in reversed(user_messages[-2:]):
        if not msg.content:
            continue
        text_lower = msg.content.lower()
        
        # Check direct keywords
        for kw in inventory_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                return True
                
        # Check phrases
        for phrase in phrases:
            if re.search(phrase, text_lower):
                return True
                
        # Check action verbs
        for act in actions:
            if re.search(r'\b' + re.escape(act) + r'\b', text_lower):
                return True
                
    return False


def _parse_failed_tool_call(error: Exception) -> Optional[dict]:
    """Parse a Groq tool_use_failed error to recover the intended tool call.
    
    When Llama 3.1/3.3 70B generates tool calls in the raw <function=name {json}</function>
    format instead of the structured API format, Groq rejects it with a tool_use_failed
    error. This function extracts the intended function name and arguments so we can
    recover gracefully.
    
    Handles both direct openai.BadRequestError (with .body attribute) and
    LangChain-wrapped exceptions (by falling back to string parsing).
    """
    import re
    import uuid
    import json
    
    failed_gen = None
    
    # Strategy 1: Extract from exception .body attribute (direct openai error)
    # Strategy 2: Check .__cause__ for chained/wrapped exceptions
    for exc in [error, getattr(error, "__cause__", None)]:
        if exc is None:
            continue
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error_info = body.get("error", body)
            if isinstance(error_info, dict) and error_info.get("code") == "tool_use_failed":
                failed_gen = error_info.get("failed_generation", "")
                break
    
    # Strategy 3: Fallback to parsing the error string representation
    if not failed_gen and "tool_use_failed" in str(error):
        failed_gen = str(error)
    
    if not failed_gen:
        return None
    
    # Parse the <function=name ...></function> pattern
    # Llama might omit the space between the function name and the JSON arguments.
    match = re.search(r'<function=(\w+)\s*(\{.*?\})\s*</function>', failed_gen, re.DOTALL)
    if not match:
        return None
    
    func_name = match.group(1)
    try:
        args = json.loads(match.group(2))
    except json.JSONDecodeError:
        return None
    
    return {
        "name": func_name,
        "args": args,
        "id": f"call_{uuid.uuid4().hex[:24]}"
    }
def agent_node(state: AgentState) -> Dict[str, Any]:
    """Executes the main LLM agent model with tool binding."""
    llm = get_llm()
    
    # 1. Find the latest user message
    latest_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_user_msg = msg.content
            break

    # Count how many search_recipes calls have been made since the last HumanMessage.
    # This drives:
    #   - is_post_search: True after ANY search result so the LLM can cross-check and
    #     re-search as many times as needed when the user has many dislikes.
    #   - Safety cap: after MAX_SEARCH_CALLS searches, bind_search is forced off so the
    #     LLM must present whatever it has, preventing an infinite loop.
    MAX_SEARCH_CALLS = 5
    search_calls_this_turn = 0
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, AIMessage) and msg.tool_calls:
            search_calls_this_turn += sum(
                1 for tc in msg.tool_calls if tc["name"] == "search_recipes"
            )

    # is_post_search: True whenever a search result just arrived (first OR re-search).
    # The LLM may call search_recipes again up to MAX_SEARCH_CALLS times if every
    # retrieved batch is fully filtered out by the user's dislikes or long-term facts.
    is_post_search = (
        isinstance(state["messages"][-1], ToolMessage)
        and search_calls_this_turn >= 1
    )
    print(f"agent_node debug: is_post_search={is_post_search}, search_calls_this_turn={search_calls_this_turn}/{MAX_SEARCH_CALLS}")


    # 2. Get profile details
    p = state["user_profile"]
    wants_str = (p.get("wants_temporary") or "").strip()
    not_wants_str = (p.get("does_not_want_temporary") or "").strip()
    
    # 3. Check if Wants is empty or contains "anything"
    wants_list = [w.strip().lower() for w in wants_str.split(",") if w.strip()]
    has_anything = "anything" in wants_list
    wants_empty = len(wants_list) == 0

    latest_has_desire = (state.get("user_intent") == "recipe_recommendation_request")

    # Programmatic fallback: if Wants is empty but the user intent indicates recipe desire,
    # check if the user mentioned any known food terms in their message.
    # If they did, we programmatically extract those food terms as temporary wants.
    if wants_empty and latest_has_desire:
        known_terms = _get_known_food_terms()
        extracted_wants = []
        import re
        
        # Split user message by word boundary, keeping apostrophes for words like don't
        words_in_msg = re.findall(r"\b[a-zA-Z']{3,}\b", latest_user_msg.lower())
        
        # Build sets of temporary and permanent dislikes to filter out
        not_wants_list = [nw.strip().lower() for nw in not_wants_str.split(",") if nw.strip()]
        disliked_terms = set(not_wants_list)
        
        # Add permanent dislikes (e.g. from facts like "dislikes fish")
        for fact in p.get("facts", []):
            fact_lower = fact.lower()
            if any(neg in fact_lower for neg in ["dislike", "hate", "allergic", "avoid"]):
                for term in known_terms:
                    if term in fact_lower:
                        disliked_terms.add(term)
                        
        negation_words = {"no", "not", "without", "avoid", "dont", "don't", "hate", "dislike", "dislikes", "hates", "never"}
        
        for i, word in enumerate(words_in_msg):
            word_clean = word.replace("'", "") # standardize
            if word_clean in known_terms and word_clean not in disliked_terms:
                # Check for negation in preceding 3 words
                is_negated = False
                for prev_word in words_in_msg[max(0, i-3):i]:
                    if prev_word in negation_words:
                        is_negated = True
                        break
                if not is_negated:
                    extracted_wants.append(word_clean)
        
        if extracted_wants:
            # Deduplicate while preserving order
            seen = set()
            extracted_wants = [x for x in extracted_wants if not (x in seen or seen.add(x))]
            
            # Save to database to keep session persistent
            save_temporary_preferences_to_db(state["user_id"], extracted_wants, [])
            
            # Update local state variables
            p["wants_temporary"] = ",".join(extracted_wants)
            wants_str = p["wants_temporary"]
            wants_list = extracted_wants
            wants_empty = False
            print(f"agent_node: Programmatically extracted wants {extracted_wants} from user message '{latest_user_msg}'")

    # Get asked_preferences status at start of turn
    asked_pref_at_start = p.get("asked_preferences", False)

    # If the user intent is detected to recommend a recipe, check asked_preferences status
    if latest_has_desire and not asked_pref_at_start and wants_empty:
        # Set asked_preferences to True in DB so that next turn has it as True
        set_user_asked_preferences(state["user_id"], True)
        p["asked_preferences"] = True
    # 4. Check if we should bind search.
    #
    # bind_inventory is computed here (earlier than the tool-binding block below) because
    # it is also needed to determine bind_search correctly.
    #
    # The key insight: when wants_str is already set (the extractor captured a preference),
    # we should bind search_recipes regardless of whether the user intent is active.
    # User intent only guards the case where wants are *empty* (to decide
    # whether the agent should ask for preferences or wait). When wants are already populated,
    # the intent to search is implicit — unless the current message is a pure inventory action.
    bind_inventory = check_inventory_intent(state["messages"])
    
    is_anything_and_asked = has_anything and asked_pref_at_start
    is_empty_and_asked = wants_empty and asked_pref_at_start
    
    if not wants_empty and not has_anything:
        # Specific preferences exist
        bind_search = latest_has_desire or not bind_inventory
    elif (is_anything_and_asked or is_empty_and_asked) and latest_has_desire:
        # Wants "anything" or is empty, but asked_preferences is True and user wants recommendations
        bind_search = True
    else:
        bind_search = False

    # Safety cap: once MAX_SEARCH_CALLS searches have happened in the same turn,
    # force bind_search off so search_recipes cannot be called again.
    # This is a last-resort safeguard — normal flow should terminate earlier
    # because the recipe pool is exhausted or the LLM finds valid survivors.
    if search_calls_this_turn >= MAX_SEARCH_CALLS:
        bind_search = False
        print(f"agent_node debug: safety cap reached ({MAX_SEARCH_CALLS} searches) — bind_search forced to False")

    # 5. Programmatic search is no longer used. We let the agent call the search_recipes tool.
    rag_recipes = []

    # 6. Determine tool bindings dynamically to prevent hallucinations:
    # - If Wants is empty, user is asking for recommendations, and asked_preferences is False,
    #   bind no tools (forces the agent to ask for preferences instead of picking a random recipe).
    # - Otherwise, bind search_recipes if bind_search is True, inventory tools if
    #   inventory intent is detected, and get_recipe_details_tool only when recipe
    #   IDs have already been shown in the conversation (prevents random ID calls).
    # Note: bind_inventory was already computed above alongside bind_search.
    bind_details = check_details_intent(state["messages"])
    
    # Check if any recipe IDs have been shown in prior messages so the user has
    # concrete recipes to reference. Matches both raw ("Recipe ID: <num>") and minified ("(ID: <num>)") formats.
    import re
    has_shown_recipes = any(
        msg.content and re.search(r'(?i)\b(?:recipe\s+)?id[:\s]+\d+\b', msg.content)
        for msg in state["messages"]
    )
    
    if wants_empty and latest_has_desire and not asked_pref_at_start:
        tools = []
        # If recipe IDs have been shown, they might be asking for details/cooking steps of one of them.
        # We must bind get_recipe_details_tool in this case so the agent can retrieve them.
        if has_shown_recipes:
            tools.append(get_recipe_details_tool)
    else:
        tools = []
        if bind_search:
            tools.append(search_recipes)
        if bind_inventory:
            tools.append(update_inventory_tool)
            tools.append(get_inventory_tool)
        # Only bind get_recipe_details_tool when recipe IDs have been shown in the
        # conversation, so the model can't call it with a made-up ID before any search.
        if has_shown_recipes:
            tools.append(get_recipe_details_tool)

    print(f"agent_node debug: wants='{wants_str}', bind_search={bind_search}, bind_inventory={bind_inventory}, has_shown_recipes={has_shown_recipes}, tools={[t.name for t in tools]}")

    # Format the profile variables for the system prompt
    facts_str = "\n".join(f"- {f}" for f in p["facts"]) if p["facts"] else "None"
    restrictions_str = ", ".join(p["restrictions"]) if p.get("restrictions") else "None"

    # Format recent memory updates if present
    recent_updates = state.get("recent_memory_updates", {})
    added = recent_updates.get("added", [])
    removed = recent_updates.get("removed", [])
    
    # Show memory updates in the system prompt if we are in a conversational run
    # (either we just executed a tool, or search_recipes is not bound).
    # This prevents the LLM from outputting conversational acknowledgement text
    # at the same time as a tool call, which causes provider validation crashes.
    has_tool_message = isinstance(state["messages"][-1], ToolMessage)
    show_updates = has_tool_message or (not tools)
    
    recent_updates_str = ""
    if show_updates and (added or removed):
        recent_updates_str = "\nRecent Memory Updates:"
        if added:
            recent_updates_str += "\n- Added: " + ", ".join(f'"{f}"' for f in added)
        if removed:
            recent_updates_str += "\n- Removed: " + ", ".join(f'"{f}"' for f in removed)

    # Build the cross-check section only when we are responding to search_recipes results.
    # Format it separately first (resolves all inline variables),
    # then pass the rendered string into the main prompt via {cross_check_section}.
    if is_post_search:
        cross_check_section = POST_SEARCH_CROSS_CHECK_SECTION.format(
            username=state["user_name"],
            does_not_want_str=not_wants_str if not_wants_str else "None",
            search_calls_this_turn=search_calls_this_turn,
            max_search_calls=MAX_SEARCH_CALLS,
        )
    else:
        cross_check_section = ""


    search_results_str = ""
    if is_post_search:
        last_msg = state["messages"][-1]
        search_results_str = last_msg.content if last_msg and hasattr(last_msg, "content") else ""

    if is_post_search:
        prompt_template = SYSTEM_PROMPT_POST_SEARCH
    else:
        prompt_template = SYSTEM_PROMPT_WITH_SEARCH if bind_search else SYSTEM_PROMPT_WITHOUT_SEARCH

    sys_message = SystemMessage(
        content=prompt_template.format(
            username=state["user_name"],
            facts=facts_str,
            restrictions=restrictions_str,
            wants_temporary=wants_str if wants_str else "None",
            does_not_want_temporary=not_wants_str if not_wants_str else "None",
            asked_preferences=str(asked_pref_at_start),
            recent_memory_updates=recent_updates_str,
            cross_check_section=cross_check_section,
            search_results=search_results_str
        )
    )

    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm
    
    # Run the LLM on the chat history (System message + conversation messages)
    history = [sys_message] + state["messages"]
    try:
        response = llm_with_tools.invoke(history)
    except Exception as e:
        # Handle Groq/Nvidia NIM tool_use_failed: Llama sometimes generates tool calls in raw
        # <function=name {json}</function> format instead of using the structured API.
        # Recover by parsing the intended call from the error.
        parsed_call = _parse_failed_tool_call(e)
        if parsed_call:
            response = AIMessage(content="", tool_calls=[parsed_call])
            print(f"Recovered from tool_use_failed: parsed tool call '{parsed_call['name']}'")
        else:
            raise
    
    # Intercept and override response if user merely used ingredients but didn't run out
    if not response.tool_calls:
        latest_user_msg_lower = latest_user_msg.lower().strip() if latest_user_msg else ""
        
        # Determine if the message is a question or request
        is_question = latest_user_msg_lower.endswith("?") or any(
            qw in latest_user_msg_lower for qw in ["how", "what", "why", "where", "when", "who", "which", "can i", "can you", "could you", "recommend", "suggest"]
        )
        
        # Determine if they used/consumed/cooked but didn't run out
        use_keywords = ["used", "use", "using", "cooked", "cook", "cooking", "spent", "consumed", "consuming", "ate", "eat", "eating", "had some", "took some", "put some"]
        run_out_keywords = ["run out", "ran out", "finished", "finish", "empty", "no more", "dont have", "don't have", "no longer have", "out of"]
        
        import re
        has_use = any(re.search(r'\b' + re.escape(kw) + r'\b', latest_user_msg_lower) for kw in use_keywords)
        has_run_out = any(re.search(r'\b' + re.escape(kw) + r'\b', latest_user_msg_lower) for kw in run_out_keywords)
        
        is_recipe_request = (state.get("user_intent") == "recipe_recommendation_request")
        is_checking_inventory = any(kw in latest_user_msg_lower for kw in ["do i have", "what do i have", "what ingredients", "list my", "show my"])
        
        # Also check if LLM generated response contains explanations that they still have it
        response_lower = response.content.lower() if response.content else ""
        has_still_have = "still have" in response_lower
        has_not_run_out = any(x in response_lower for x in ["not run", "running out", "only mentioned", "did not run", "didn't run"])
        is_explanation = has_still_have and has_not_run_out
        
        # Check if explanation by phrases
        phrases = [
            "only mentioned using",
            "only said you used",
            "didn't say you ran out",
            "did not say you ran out",
            "didn't mention running out",
            "did not mention running out",
            "didn't run out",
            "did not run out"
        ]
        is_phrase_explanation = any(p in response_lower for p in phrases)
        
        is_remove_explanation = any(x in response_lower for x in ["didn't remove", "did not remove", "have not removed", "haven't removed"]) and any(y in response_lower for y in ["only", "mention", "some"])
        
        is_any_explanation = is_explanation or is_phrase_explanation or is_remove_explanation
        
        if (has_use and not has_run_out and not is_recipe_request and not is_checking_inventory and not is_question) or is_any_explanation:
            username = state["user_name"].capitalize() if state.get("user_name") else "Carol"
            response.content = f"Ok {username}!, If you completely run out of those ingredients, let me know anytime!"
            
    output = {"messages": [response]}
    if rag_recipes:
        output["rag_recipes"] = rag_recipes
        
    # Reset recent_memory_updates if this is the final conversational run (no tool calls generated)
    if not response.tool_calls:
        output["recent_memory_updates"] = {"added": [], "removed": []}
        
    return output


def format_conversational_inventory_update(username: str, action: str, items: Any) -> str:
    # Normalize input types (sometimes the LLM passes stringified JSON arrays or single dictionaries)
    if isinstance(items, str):
        try:
            import json
            items = json.loads(items)
        except Exception:
            pass

    if isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list):
        items = []

    from app.ingredients_formatter import standardize_ingredient

    parts = []
    for item in items:
        if isinstance(item, str):
            name = standardize_ingredient(item)
        else:
            # Handle Pydantic models or standard dictionaries
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif hasattr(item, "dict"):
                item_dict = item.dict()
            elif isinstance(item, dict):
                item_dict = item
            else:
                try:
                    item_dict = dict(item)
                except Exception:
                    item_dict = {}
            raw_name = item_dict.get("name", "").strip()
            name = standardize_ingredient(raw_name) if raw_name else ""

        if name:
            parts.append(name.capitalize())
            
    items_str = ", ".join(parts)
    if action == "add":
        return f"Ok {username}, I have updated your inventory with {items_str}."
    else:
        return f"Ok {username}, I have removed {items_str} from your inventory."


def format_conversational_recipe_details(username: str, recipe: Dict[str, Any], user_ingredients: List[str]) -> str:
    recipe_name = recipe.get("name", "recipe").title()
    cook_time = recipe.get("minutes", 0)
    
    user_ing_names = {name.lower().strip() for name in user_ingredients}
    have = []
    missing = []
    for ing in recipe.get('ingredients', []):
        ing_lower = ing.lower().strip()
        found = False
        for user_ing in user_ing_names:
            if user_ing in ing_lower or ing_lower in user_ing:
                found = True
                break
        if found:
            have.append(ing)
        else:
            missing.append(ing)
            
    have_str = ", ".join(have) if have else "None"
    missing_str = ", ".join(missing) if missing else "None"
    steps_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(recipe.get('steps', [])))
    
    msg = (
        f"Ok {username}, here are the details for **{recipe_name}** ({cook_time} mins cook time):\n\n"
        f"**Ingredients you already have:**\n{have_str}\n\n"
        f"**Missing ingredients you will need:**\n{missing_str}\n\n"
        f"**Cooking Steps:**\n{steps_str}"
    )
    return msg



def tools_runner_node(state: AgentState) -> Dict[str, Any]:
    """Executes any tool calls requested by the agent, with pre-filtered scoped search."""
    last_msg = state["messages"][-1]
    if not last_msg.tool_calls:
        return {}

    new_messages = []
    actions = list(state.get("actions", []))
    rag_recipes = list(state.get("rag_recipes", []))
    
    user_id = state["user_id"]
    compatible_ids = set(state.get("compatible_recipe_ids", []))

    # Parse previous messages in the history to find already suggested recipe IDs
    import re
    previously_suggested_ids = set()
    for msg in state["messages"]:
        if msg.content:
            ids = re.findall(r'(?i)\b(?:recipe\s+)?id[:\s]+(\d+)\b', msg.content)
            for r_id in ids:
                previously_suggested_ids.add(int(r_id))
    print(f"Previously suggested recipe IDs to exclude: {previously_suggested_ids}")

    # Check if there are active memory updates in this turn
    recent_updates = state.get("recent_memory_updates", {})
    has_memory_updates = bool(recent_updates.get("added") or recent_updates.get("removed"))

    # Determine if we can short-circuit this turn
    short_circuit_replies = []
    can_short_circuit = not has_memory_updates


    for tool_call in last_msg.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]

        if name == "search_recipes":
            can_short_circuit = False
            query = args.get("query")
            # If query is passed as empty string, treat it as None
            if not query or query.strip() == "":
                query = None
            culture = args.get("culture")
            season = args.get("season")

            # Normalize null-like string inputs
            if culture in (None, "null", "None", "NoneType", ""):
                culture = None
            if season in (None, "null", "None", "NoneType", ""):
                season = None

            # Get forbidden keywords from does_not_want_temporary
            not_wants_str = state["user_profile"].get("does_not_want_temporary", "")
            forbidden_keywords = [w.strip().lower() for w in not_wants_str.split(",") if w.strip()]
            print(f"Temporary forbidden keywords: {forbidden_keywords}")

            excluded_ids = previously_suggested_ids.copy()
            recipes_raw = []
            max_attempts = 3
            
            for attempt in range(max_attempts):
                # Search within compatible_ids minus excluded_ids
                search_pool = compatible_ids - excluded_ids
                print(f"Attempt {attempt + 1}/{max_attempts}: searching recipes for query='{query}' (pool size: {len(search_pool)})")
                
                candidates = recipe_db.search_recipes_filtered(
                    query=query,
                    recipe_ids=search_pool,
                    excluded_ids=excluded_ids,
                    limit=10, # Request more to have buffer for post-filtering
                    culture=culture,
                    season=season
                )
                
                # Fallback: if no results with culture/season filter, retry without culture/season
                if not candidates and (culture or season):
                    print(f"No results with culture='{culture}'/season='{season}', falling back to all compatible recipes")
                    candidates = recipe_db.search_recipes_filtered(
                        query=query,
                        recipe_ids=search_pool,
                        excluded_ids=excluded_ids,
                        limit=10,
                        culture=None,
                        season=None
                    )
                
                if not candidates:
                    print("No candidate recipes found.")
                    break
                    
                # Post-filter in Python
                viable_in_this_run = []
                for r in candidates:
                    has_forbidden = False
                    
                    # Check each forbidden keyword
                    for forbidden in forbidden_keywords:
                        # 1. Check ingredients
                        ingredients_str = " ".join(r.get("ingredients", [])).lower()
                        if forbidden in ingredients_str:
                            has_forbidden = True
                            excluded_ids.add(r["id"])
                            break
                        # 2. Check recipe name
                        if forbidden in r.get("name", "").lower():
                            has_forbidden = True
                            excluded_ids.add(r["id"])
                            break
                            
                    if not has_forbidden:
                        viable_in_this_run.append(r)
                
                if viable_in_this_run:
                    # We found at least 1 viable recipe, satisfying the threshold of 1
                    recipes_raw = viable_in_this_run[:3] # Suggest up to 3
                    break
                else:
                    # 0 viable recipes remain, so we continue loop to re-search
                    print(f"All candidate recipes in attempt {attempt + 1} were filtered out. Excluded IDs: {excluded_ids}")
            
            rag_recipes.extend(recipes_raw)

            # Format results directly (no double-search)
            result_str = format_recipe_results(
                recipes_raw,
                user_ingredients=state["user_profile"]["ingredients"]
            )
            new_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
            actions.append(f"Searched recipes for: {query}" + (f" (cuisine: {culture})" if culture else ""))

        elif name == "update_inventory_tool":
            print(f"Executing update_inventory_tool: {args}")
            # Execute actual DB write
            action = args.get("action", "add")
            items = args.get("items", [])
            result_str = update_ingredients_in_db(user_id, action, items)
            
            new_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
            actions.append(result_str)

            if "warning:" in result_str.lower():
                can_short_circuit = False
            else:
                conv_msg = format_conversational_inventory_update(
                    state["user_name"],
                    action,
                    items
                )
                short_circuit_replies.append(conv_msg)

        elif name == "get_recipe_details_tool":
            recipe_id = args.get("recipe_id")
            if recipe_id is not None:
                try:
                    recipe_id = int(recipe_id)
                except (TypeError, ValueError):
                    pass
            print(f"Executing get_recipe_details_tool: recipe_id={recipe_id}")
            # Retrieve details and format in Python
            result_str = get_recipe_details_by_id(recipe_id, state["user_profile"]["ingredients"])
            
            new_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
            actions.append(f"Retrieved details for recipe ID: {recipe_id}")

            recipe = recipe_db.get_recipe_by_id(recipe_id)
            if recipe:
                conv_msg = format_conversational_recipe_details(
                    state["user_name"],
                    recipe,
                    state["user_profile"]["ingredients"]
                )
            else:
                conv_msg = f"Recipe with ID {recipe_id} not found."
            short_circuit_replies.append(conv_msg)

        elif name == "get_inventory_tool":
            can_short_circuit = False
            user_ingredients = state["user_profile"]["ingredients"]
            
            # Resolve optional category filter
            raw_categories = args.get("categories") or []
            requested_categories = resolve_category_aliases(raw_categories) if raw_categories else []
            
            if not user_ingredients:
                result_str = "Kitchen inventory is empty."
            else:
                # Group ingredients by category
                grouped = {}
                for ing in user_ingredients:
                    cat = get_ingredient_category(ing)
                    if cat not in grouped:
                        grouped[cat] = []
                    grouped[cat].append(ing.capitalize())

                # If the LLM passed specific categories, keep only those sections
                if requested_categories:
                    grouped = {cat: items for cat, items in grouped.items() if cat in requested_categories}

                if not grouped:
                    result_str = "No items found in the requested categories."
                else:
                    # Build output following the canonical category order.
                    # Each category is a bold header on its own line, items listed beneath,
                    # sections separated by a blank line for clear visual boundaries.
                    sections = []
                    for cat in CATEGORY_ORDER:
                        if cat in grouped:
                            items_str = ", ".join(sorted(grouped[cat]))
                            sections.append(f"**{cat}**\n• {items_str}")
                    result_str = "Kitchen inventory:\n\n" + "\n\n".join(sections)

            new_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
            actions.append("Retrieved kitchen inventory")



        else:
            # Handle unrecognized/hallucinated tools to avoid premature END
            print(f"Warning: Model called unrecognized tool '{name}'")
            new_messages.append(
                ToolMessage(
                    content=f"Error: Tool '{name}' is not recognized or not available in this turn. "
                            f"If you wanted to suggest recipes, ask the user for their preference (cuisine or ingredient) first.",
                    tool_call_id=call_id
                )
            )
            can_short_circuit = False

    # If all executed tools were short-circuitable, append conversational AIMessage
    if can_short_circuit and short_circuit_replies:
        combined_reply = "\n\n".join(short_circuit_replies)
        new_messages.append(AIMessage(content=combined_reply))

    # Reload user profile to ensure any preference/inventory changes are synced in the state
    profile = get_user_profile_data(user_id)

    return {
        "messages": new_messages,
        "actions": actions,
        "rag_recipes": rag_recipes,
        "user_profile": profile
    }


# 4. Routing Decision Edges
def route_agent(state: AgentState) -> str:
    """Decides if the agent should continue to tool running or end the turn."""
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return END


def route_tools(state: AgentState) -> str:
    """Decides if the graph should return to the agent or end (short-circuiting)."""
    # If the last message is an AIMessage, it means the tools runner node short-circuited 
    # and produced the final conversational response directly.
    if isinstance(state["messages"][-1], AIMessage):
        return END
    return "agent"


# 5. Build state graph
workflow = StateGraph(AgentState)

workflow.add_node("load_profile", load_profile_node)
workflow.add_node("extract_preferences", extract_preferences_node)
workflow.add_node("pre_filter", pre_filter_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_runner_node)

# Flow routing: START → load_profile → extract_preferences → pre_filter → agent → (tools ↔ agent) → END
workflow.add_edge(START, "load_profile")
workflow.add_edge("load_profile", "extract_preferences")
workflow.add_edge("extract_preferences", "pre_filter")
workflow.add_edge("pre_filter", "agent")

workflow.add_conditional_edges(
    "agent",
    route_agent,
    {
        "tools": "tools",
        END: END
    }
)

workflow.add_conditional_edges(
    "tools",
    route_tools,
    {
        "agent": "agent",
        END: END
    }
)

# Compile
agent_graph = workflow.compile()
