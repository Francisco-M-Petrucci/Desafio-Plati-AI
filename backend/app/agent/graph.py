import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_PROMPT_WITH_SEARCH, SYSTEM_PROMPT_WITHOUT_SEARCH, FACT_EXTRACTION_PROMPT
from app.agent.tools import (
    get_user_profile_data,
    update_ingredients_in_db,
    add_user_fact_to_db,
    add_user_temporary_preference_to_db,
    get_filtered_recipe_ids,
    format_recipe_results,
    get_recipe_details_by_id,
    recipe_db
)

# 1. LLM Initializer
_llm_instance_70b = None
_llm_instance_8b = None

def get_llm(model_name: str = "meta/llama-3.1-70b-instruct") -> ChatOpenAI:
    global _llm_instance_70b, _llm_instance_8b
    
    if model_name == "meta/llama-3.1-70b-instruct":
        if _llm_instance_70b is None:
            nvidia_key = os.getenv("NVIDIA_API_KEY")
            if not nvidia_key or nvidia_key.startswith("nvapi-your-key"):
                raise ValueError("NVIDIA_API_KEY is not set. Please add it to your .env file.")
            _llm_instance_70b = ChatOpenAI(
                model=model_name,
                api_key=nvidia_key,
                base_url="https://integrate.api.nvidia.com/v1",
                temperature=0.2
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
                temperature=0.2
            )
        return _llm_instance_8b
        
    else:
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        return ChatOpenAI(
            model=model_name,
            api_key=nvidia_key,
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.2
        )

# 2. Define LangChain Structured Tools for LLM Tool Binding
@tool
def search_recipes(
    query: str,
    include_steps: bool = False,
    culture: Optional[str] = None,
    season: Optional[str] = None
) -> str:
    """
    Search recipes by cuisine or ingredient preference. Results are pre-filtered for dietary/appliance compatibility.
    - query: specific cuisine or ingredient term (e.g., 'pasta', 'chicken', 'Mexican')
    - include_steps: True only if user asked for cooking steps (default False)
    - culture: cuisine filter if user specified one (e.g. 'Italian')
    - season: seasonal filter if applicable (e.g. 'Summer')
    """
    # This function body is not called directly during graph execution.
    # The tools_runner_node handles actual execution with pre-filtered IDs.
    # This definition exists for LLM tool binding (schema generation).
    return "Tool executed by runner."


class InventoryItem(BaseModel):
    name: str = Field(description="The lowercased name of the ingredient (e.g., 'milk', 'tomato')")
    quantity: float = Field(default=1.0, description="The quantity of the ingredient acquired or used")
    unit: str = Field(default="unit", description="The unit of measurement (e.g., 'kg', 'g', 'unit')")

@tool
def update_inventory_tool(action: str, items: List[InventoryItem]) -> str:
    """
    Updates the user's kitchen ingredients inventory.
    Parameters:
    - action: 'add' (if user acquired/bought ingredients) or 'remove' (if user used/cooked ingredients)
    - items: a list of items, each containing 'name' (str), 'quantity' (float), and optionally 'unit' (str, e.g. 'kg', 'g', 'unit')
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


# 3. Graph Nodes
def load_profile_node(state: AgentState) -> Dict[str, Any]:
    """Loads the user's profile context from the SQLite database."""
    user_id = state["user_id"]
    profile = get_user_profile_data(user_id)
    return {"user_profile": profile}


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
    """Build a set of food-related terms from the recipe DB cuisines + curated keywords."""
    global _known_food_terms
    if _known_food_terms is not None:
        return _known_food_terms

    # Data-driven: extract cuisine types from actual recipe data
    cuisines = set()
    try:
        for r in recipe_db.get_all_recipe_metadata():
            ct = r.get("cuisine_type", "").lower().strip()
            if ct:
                cuisines.add(ct)
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


def agent_node(state: AgentState) -> Dict[str, Any]:
    """Executes the main LLM agent model with tool binding."""
    llm = get_llm()
    
    # Determine which tools to bind dynamically
    tools = []
    bind_search = False
    bind_inventory = False
    bind_details = False

    # Find the latest user message
    latest_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_user_msg = msg.content
            break

    if latest_user_msg:
        import re
        latest_user_msg_lower = latest_user_msg.lower()
        words = set(re.findall(r'\b[a-z]{3,}\b', latest_user_msg_lower))
        
        # 1. Check Food Preference / Search Intent (robust plural/substring matching)
        known_terms = _get_known_food_terms()
        has_food_preference = False
        for term in known_terms:
            pattern = r'\b' + re.escape(term) + r'(s|es)?\b'
            if re.search(pattern, latest_user_msg_lower):
                has_food_preference = True
                break
        if has_food_preference:
            bind_search = True
            
        # 2. Check Inventory Action Intent
        inventory_keywords = {
            "add", "remove", "update", "bought", "acquired", "used", "cooked", 
            "purchased", "ate", "inventory", "groceries", "grocery", "shop", "shopped"
        }
        if bool(words & inventory_keywords):
            bind_inventory = True
            
        # 3. Check Recipe Details Request Intent
        details_keywords = {"step", "steps", "detail", "details", "instruction", "instructions", "how to"}
        if any(k in latest_user_msg_lower for k in details_keywords) or "recipe id" in latest_user_msg_lower:
            bind_details = True

    # Assemble tools list
    if bind_search:
        tools.append(search_recipes)
    if bind_inventory:
        tools.append(update_inventory_tool)
    if bind_details:
        tools.append(get_recipe_details_tool)

    # Format the profile variables for the system prompt
    p = state["user_profile"]
    facts_str = "\n".join(f"- {f}" for f in p["facts"]) if p["facts"] else "None"
    temp_prefs_str = "\n".join(f"- {f}" for f in p.get("temporary_preferences", [])) if p.get("temporary_preferences") else "None"
    ingredients_str = ", ".join(i["name"] for i in p["ingredients"]) if p["ingredients"] else "Empty"

    prompt_template = SYSTEM_PROMPT_WITH_SEARCH if bind_search else SYSTEM_PROMPT_WITHOUT_SEARCH
    sys_message = SystemMessage(
        content=prompt_template.format(
            username=state["user_name"],
            facts=facts_str,
            temporary_preferences=temp_prefs_str,
            ingredients=ingredients_str
        )
    )

    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm
    
    # Run the LLM on the chat history (System message + conversation messages)
    history = [sys_message] + state["messages"]
    response = llm_with_tools.invoke(history)
    return {"messages": [response]}


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

    parts = []
    for item in items:
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

        name = item_dict.get("name", "").strip()
        qty = item_dict.get("quantity", 1.0)
        qty_str = f"{int(qty)}" if qty == int(qty) else f"{qty}"
        unit = item_dict.get("unit", "unit").strip()
        if unit == "unit":
            parts.append(f"{qty_str}x {name.capitalize()}")
        else:
            parts.append(f"{qty_str} {unit} of {name.capitalize()}")
            
    items_str = ", ".join(parts)
    if action == "add":
        return f"Ok {username}, I have updated your inventory with {items_str}."
    else:
        return f"Ok {username}, I have removed {items_str} from your inventory."


def format_conversational_recipe_details(username: str, recipe: Dict[str, Any], user_ingredients: List[Dict[str, Any]]) -> str:
    recipe_name = recipe.get("name", "recipe").title()
    cook_time = recipe.get("minutes", 0)
    
    user_ing_names = {i['name'].lower().strip() for i in user_ingredients}
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

    # Determine if we can short-circuit this turn
    short_circuit_replies = []
    can_short_circuit = True

    for tool_call in last_msg.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]

        if name == "search_recipes":
            can_short_circuit = False
            query = args.get("query", "")
            culture = args.get("culture")
            season = args.get("season")
            include_steps = args.get("include_steps", False)

            # Normalize boolean input (in case it is passed as a string like "false")
            if include_steps in (False, "false", "False", 0, "0"):
                include_steps = False
            else:
                include_steps = bool(include_steps)

            # Normalize null-like string inputs
            if culture in (None, "null", "None", "NoneType", ""):
                culture = None
            if season in (None, "null", "None", "NoneType", ""):
                season = None

            print(f"Executing search_recipes: query='{query}', culture='{culture}', season='{season}' (searching within {len(compatible_ids)} compatible recipes)")

            # Search ONLY within pre-filtered compatible recipes
            recipes_raw = recipe_db.search_recipes_filtered(
                query=query,
                recipe_ids=compatible_ids,
                culture=culture,
                season=season
            )

            # Fallback: if no results with culture/season filter, retry without preferences
            if not recipes_raw and (culture or season):
                print(f"No results with culture='{culture}'/season='{season}', falling back to all compatible recipes")
                recipes_raw = recipe_db.search_recipes_filtered(
                    query=query,
                    recipe_ids=compatible_ids,
                    culture=None,
                    season=None
                )

            rag_recipes.extend(recipes_raw)

            # Format results directly (no double-search)
            result_str = format_recipe_results(
                recipes_raw,
                user_ingredients=state["user_profile"]["ingredients"],
                include_steps=include_steps
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

    return {
        "messages": new_messages,
        "actions": actions,
        "rag_recipes": rag_recipes
    }


def extract_facts_from_state(state: Dict[str, Any]) -> None:
    """Asynchronously extracts permanent facts from the latest dialogue exchange."""
    # We only analyze the last user message and the agent's final text response
    user_msg = ""
    assistant_msg = ""
    
    # Search backwards for the last HumanMessage and AIMessage (that isn't a tool call)
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage) and not user_msg:
            user_msg = msg.content
        elif isinstance(msg, AIMessage) and not msg.tool_calls and not assistant_msg:
            assistant_msg = msg.content
            
    if not user_msg or not assistant_msg:
        return

    try:
        # Use the faster Llama 3.1 8B Instruct model for background fact extraction
        llm = get_llm("meta/llama-3.1-8b-instruct")
        existing_facts = "\n".join(f"- {f}" for f in state["user_profile"]["facts"]) if state["user_profile"]["facts"] else "None"
        existing_temporary_preferences = "\n".join(f"- {f}" for f in state["user_profile"].get("temporary_preferences", [])) if state["user_profile"].get("temporary_preferences") else "None"
        
        prompt = FACT_EXTRACTION_PROMPT.format(
            existing_facts=existing_facts,
            existing_temporary_preferences=existing_temporary_preferences,
            user_msg=user_msg,
            assistant_msg=assistant_msg
        )
        
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Clean potential markdown JSON syntax
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        parsed = json.loads(content)
        user_id = state["user_id"]
        
        permanent_facts = parsed.get("permanent_facts", [])
        temporary_prefs = parsed.get("temporary_preferences", [])
        
        saved_facts = []
        for fact in permanent_facts:
            res = add_user_fact_to_db(user_id, fact)
            if "Saved fact" in res:
                saved_facts.append(fact)
                
        saved_prefs = []
        for pref in temporary_prefs:
            res = add_user_temporary_preference_to_db(user_id, pref)
            if "Saved temporary preference" in res:
                saved_prefs.append(pref)
                
        if saved_facts:
            print(f"Extracted and saved new permanent facts in background: {saved_facts}")
        if saved_prefs:
            print(f"Extracted and saved new temporary preferences in background: {saved_prefs}")
            
    except Exception as e:
        print(f"Background fact extraction failed: {e}")


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
workflow.add_node("pre_filter", pre_filter_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_runner_node)

# Flow routing: START → load_profile → pre_filter → agent → (tools ↔ agent) → END
workflow.add_edge(START, "load_profile")
workflow.add_edge("load_profile", "pre_filter")
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
