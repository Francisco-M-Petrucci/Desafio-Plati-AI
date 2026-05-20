import os
import json
from typing import List, Dict, Any
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
    search_recipes
)

# 1. LLM Initializer
def get_llm() -> ChatOpenAI:
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_key or nvidia_key.startswith("nvapi-your-key"):
        raise ValueError("NVIDIA_API_KEY is not set. Please add it to your .env file.")
    
    return ChatOpenAI(
        model="meta/llama-3.1-70b-instruct",
        api_key=nvidia_key,
        base_url="https://integrate.api.nvidia.com/v1",
        temperature=0.2
    )

# 2. Define LangChain Structured Tools for LLM Tool Binding
@tool
def search_recipes_tool(query: str, culture: str = None, season: str = None) -> str:
    """
    Search the Food.com Recipes knowledge base for recipes.
    Parameters:
    - query: search terms (e.g. 'chicken', 'tacos', 'pasta')
    - culture: optional cuisine filter (e.g. 'Mexican', 'Indian', 'Italian')
    - season: optional season filter (e.g. 'Spring', 'Summer', 'Winter')
    """
    recipes = search_recipes(query, culture=culture, season=season)
    if not recipes:
        return "No recipes found in the database matching those filters."
    
    formatted = []
    for r in recipes:
        formatted.append(
            f"Recipe ID: {r['id']}\n"
            f"Name: {r['name']}\n"
            f"Cook Time: {r['minutes']} mins\n"
            f"Ingredients: {', '.join(r['ingredients'])}\n"
            f"Steps: \n" + "\n".join(f"  {i+1}. {step}" for i, step in enumerate(r['steps'])) + "\n"
            f"Description: {r['description']}\n"
            f"Tags: {', '.join(r['tags'])}"
        )
    return "\n---\n".join(formatted)


@tool
def update_inventory_tool(action: str, items: List[Dict[str, Any]]) -> str:
    """
    Updates the user's kitchen ingredients inventory.
    Parameters:
    - action: 'add' (if user acquired/bought ingredients) or 'remove' (if user used/cooked ingredients)
    - items: a list of items, each containing 'name' (str), 'quantity' (float), and optionally 'unit' (str, e.g. 'kg', 'g', 'unit')
    """
    # The actual database update is executed in the tool runner node which has the user_id.
    # This tool definition is mostly for schema binding.
    return "Inventory updated successfully."


# 3. Graph Nodes
def load_profile_node(state: AgentState) -> Dict[str, Any]:
    """Loads the user's profile context from the SQLite database."""
    user_id = state["user_id"]
    profile = get_user_profile_data(user_id)
    return {"user_profile": profile}


def agent_node(state: AgentState) -> Dict[str, Any]:
    """Executes the main LLM agent model with tool binding."""
    llm = get_llm()
    
    # Format the profile variables for the system prompt
    p = state["user_profile"]
    appliances_str = ", ".join(p["appliances"]) if p["appliances"] else "None"
    restrictions_str = ", ".join(p["restrictions"]) if p["restrictions"] else "None"
    facts_str = "\n".join(f"- {f}" for f in p["facts"]) if p["facts"] else "None"
    
    ing_list = []
    for i in p["ingredients"]:
        ing_list.append(f"{i['quantity']} {i['unit']} of {i['name']}")
    ingredients_str = ", ".join(ing_list) if ing_list else "Empty"

    sys_message = SystemMessage(
        content=SYSTEM_PROMPT.format(
            username=state["user_name"],
            appliances=appliances_str,
            restrictions=restrictions_str,
            facts=facts_str,
            ingredients=ingredients_str
        )
    )

    # Bind tools
    tools = [search_recipes_tool, update_inventory_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # Run the LLM on the chat history (System message + conversation messages)
    history = [sys_message] + state["messages"]
    response = llm_with_tools.invoke(history)
    
    return {"messages": [response]}


def tools_runner_node(state: AgentState) -> Dict[str, Any]:
    """Executes any tool calls requested by the agent, updating state and DB."""
    last_msg = state["messages"][-1]
    if not last_msg.tool_calls:
        return {}

    new_messages = []
    actions = list(state.get("actions", []))
    rag_recipes = list(state.get("rag_recipes", []))
    
    user_id = state["user_id"]

    for tool_call in last_msg.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]

        if name == "search_recipes_tool":
            print(f"Executing search_recipes_tool: {args}")
            # Query vector DB
            recipes_raw = search_recipes(
                query=args.get("query", ""),
                culture=args.get("culture"),
                season=args.get("season")
            )
            rag_recipes.extend(recipes_raw)
            
            # Format recipe summary as tool output
            result_str = search_recipes_tool.invoke(tool_call)
            new_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
            actions.append(f"Searched recipes for: {args.get('query')}")

        elif name == "update_inventory_tool":
            print(f"Executing update_inventory_tool: {args}")
            # Execute actual DB write
            action = args.get("action", "add")
            items = args.get("items", [])
            result_str = update_ingredients_in_db(user_id, action, items)
            
            new_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
            actions.append(result_str)

    return {
        "messages": new_messages,
        "actions": actions,
        "rag_recipes": rag_recipes
    }


def extract_facts_node(state: AgentState) -> Dict[str, Any]:
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
        return {}

    try:
        llm = get_llm()
        existing_facts = "\n".join(f"- {f}" for f in state["user_profile"]["facts"]) if state["user_profile"]["facts"] else "None"
        
        prompt = FACT_EXTRACTION_PROMPT.format(
            existing_facts=existing_facts,
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
        
        facts = json.loads(content)
        user_id = state["user_id"]
        
        saved_facts = []
        for fact in facts:
            res = add_user_fact_to_db(user_id, fact)
            if "Saved fact" in res:
                saved_facts.append(fact)
                
        if saved_facts:
            print(f"Extracted and saved new facts: {saved_facts}")
            
    except Exception as e:
        print(f"Fact extraction failed: {e}")

    return {}


# 4. Routing Decision Edges
def route_agent(state: AgentState) -> str:
    """Decides if the agent should continue to tool running or end the turn."""
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return "extract_facts"


# 5. Build state graph
workflow = StateGraph(AgentState)

workflow.add_node("load_profile", load_profile_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_runner_node)
workflow.add_node("extract_facts", extract_facts_node)

# Flow routing
workflow.add_edge(START, "load_profile")
workflow.add_edge("load_profile", "agent")

workflow.add_conditional_edges(
    "agent",
    route_agent,
    {
        "tools": "tools",
        "extract_facts": "extract_facts"
    }
)

workflow.add_edge("tools", "agent")
workflow.add_edge("extract_facts", END)

# Compile
agent_graph = workflow.compile()
