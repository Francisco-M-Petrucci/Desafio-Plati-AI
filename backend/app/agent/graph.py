import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_PROMPT, FACT_EXTRACTION_PROMPT
from app.agent.tools import (
    get_user_profile_data,
    update_ingredients_in_db,
    add_user_fact_to_db,
    add_user_temporary_preference_to_db,
    search_recipes,
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
def search_recipes_tool(
    query: str,
    include_steps: bool = False,
    culture: Optional[str] = None,
    season: Optional[str] = None
) -> str:
    """
    Search the Recipe knowledge base for recipes that match the user's specific cuisine or ingredient preferences.
    DO NOT call this tool under any circumstances if the user has not yet specified a cuisine, ingredient, or recipe name they want.
    All results are already pre-filtered for appliance compatibility and dietary restrictions — you do NOT need to check those.
    Parameters:
    - query: A specific search term representing the user's cuisine or ingredient preference (e.g., 'pasta', 'tomato', 'chicken'). CRITICAL: Never pass an empty string or generic words like 'recipe'. If the user has not specified any preference yet, DO NOT call this tool.
    - include_steps: Set to True only if the user explicitly requested detailed cooking instructions/steps for a dish. Defaults to False to save context.
    - culture: Optional cuisine filter (e.g. 'Mexican', 'Indian', 'Italian'). Only pass this if the user explicitly mentioned a cuisine preference. Do NOT pass 'null' or 'None'.
    - season: Optional season filter (e.g. 'Spring', 'Summer', 'Winter'). Do NOT pass 'null' or 'None'.
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
    Retrieve the full ingredients list and cooking steps for a recipe by its database ID.
    Call this tool ONLY when the user explicitly asks for the detailed instructions or steps for a recipe.
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


def agent_node(state: AgentState) -> Dict[str, Any]:
    """Executes the main LLM agent model with tool binding."""
    llm = get_llm()
    
    # Format the profile variables for the system prompt
    p = state["user_profile"]
    facts_str = "\n".join(f"- {f}" for f in p["facts"]) if p["facts"] else "None"
    temp_prefs_str = "\n".join(f"- {f}" for f in p.get("temporary_preferences", [])) if p.get("temporary_preferences") else "None"
    ingredients_str = ", ".join(i["name"] for i in p["ingredients"]) if p["ingredients"] else "Empty"

    sys_message = SystemMessage(
        content=SYSTEM_PROMPT.format(
            username=state["user_name"],
            facts=facts_str,
            temporary_preferences=temp_prefs_str,
            ingredients=ingredients_str
        )
    )

    # Determine which tools to bind dynamically
    base_tools = [update_inventory_tool, get_recipe_details_tool]
    bind_search = True

    # Find the latest user message
    latest_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_user_msg = msg.content
            break

    if latest_user_msg:
        # Check if the assistant has already asked the preferences question in the history
        has_asked_question = False
        for msg in state["messages"]:
            if isinstance(msg, AIMessage) and "do you have a cuisine you feel like having today" in msg.content.lower():
                has_asked_question = True
                break

        # If the question wasn't asked yet, check if they specified any preference
        if not has_asked_question:
            import re
            text_lower = latest_user_msg.lower()
            generic_words = {
                "recipe", "recipes", "idea", "ideas", "suggestion", "suggestions", "something", "anything", "cook", "make", 
                "prepare", "eat", "food", "dinner", "lunch", "breakfast", "meal", "meals", "today", "tonight", "now",
                "ingredients", "ingredient", "inventory", "have", "stock", "fridge", "kitchen", "please", "can", "you", "i", "want", 
                "recommend", "suggest", "give", "show", "find", "me", "what", "should", "could", "would", "to", "for", "with",
                "hello", "hi", "hey", "assistant", "some", "any", "feel", "like", "having", "cuisine", "cuisines", "type",
                "types", "dish", "dishes", "menu", "options", "option", "list", "get", "got", "about", "a", "an", "the",
                "of", "in", "on", "at", "by", "from", "here", "there", "is", "are", "was", "were", "do", "does",
                "did", "done", "doing", "has", "had", "have", "having", "go", "going", "went", "gone", "need", "needs",
                "needed", "want", "wants", "wanted", "like", "likes", "liked", "love", "loves", "loved", "make", "makes", 
                "making", "cook", "cooks", "cooking", "cooked", "use", "uses", "using", "used", "prepare", "prepares", 
                "preparing", "prepared", "suggest", "suggests", "suggesting", "suggestions", "suggestion", "recommend", 
                "recommends", "recommending", "recommendations", "recommendation", "search", "searches", "searching", 
                "searched", "find", "finds", "finding", "show", "shows", "showing", "give", "gives", "giving", "get", "gets", 
                "getting", "what", "who", "where", "when", "why", "how", "which", "help", "helps", "helping", "helpful",
                "please", "thanks", "thank", "hello", "hi", "hey", "assistant", "bot", "ai", "dinner", "lunch", "breakfast", 
                "snack", "snacks", "brunch", "today", "tonight", "now", "something", "anything", "nothing", "pantry", 
                "cabinet", "cabinets", "refrigerator", "available", "have", "own", "got", "possess", "some", "any", "few", 
                "many", "all", "every", "each", "feel", "like", "having", "cuisine", "type", "types", "category", "categories", 
                "option", "options", "choice", "choices", "list", "lists", "listing", "listed", "about", "for", "with", 
                "without", "from", "into", "onto", "i", "me", "my", "myself", "you", "your", "yours", "yourself", "we", "us", 
                "our", "ours", "ourselves", "he", "him", "his", "she", "her", "hers", "it", "its", "they", "them", "their",
                "can", "could", "should", "would", "will", "shall", "may", "might", "must", "be", "been", "being", "am", 
                "is", "are", "was", "were", "and", "or", "but", "so", "because", "if", "here", "there"
            }
            # Words of length >= 3
            words = re.findall(r'\b[a-z]{3,}\b', text_lower)
            has_pref = any(word not in generic_words for word in words)

            # If there is no specific preference in the query, do not bind search tool
            if not has_pref:
                bind_search = False
                print("Dynamic Tool Binding: Excluded search_recipes_tool (general query, no preference yet)")

    if bind_search:
        tools = [search_recipes_tool] + base_tools
    else:
        tools = base_tools

    llm_with_tools = llm.bind_tools(tools)
    
    # Run the LLM on the chat history (System message + conversation messages)
    history = [sys_message] + state["messages"]
    response = llm_with_tools.invoke(history)
    
    return {"messages": [response]}


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

    for tool_call in last_msg.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]

        if name == "search_recipes_tool":
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

            print(f"Executing search_recipes_tool: query='{query}', culture='{culture}', season='{season}' (searching within {len(compatible_ids)} compatible recipes)")

            # Search ONLY within pre-filtered compatible recipes
            recipes_raw = recipe_db.search_recipes_filtered(
                query=query,
                recipe_ids=compatible_ids,
                culture=culture,
                season=season
            )

            # Fallback: if no results with culture/season filter, retry without preferences
            # This searches the SAME compatible set but without the culture/season constraint
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

workflow.add_edge("tools", "agent")

# Compile
agent_graph = workflow.compile()
