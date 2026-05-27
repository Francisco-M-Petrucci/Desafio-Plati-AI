from typing import List, Dict, Any, TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Short-term chat history (managed by LangGraph message reducer)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User session context
    user_id: int
    user_name: str
    
    # Collected context from DB
    user_profile: Dict[str, Any]
    
    # Pre-filtered recipe IDs (compatible with user's appliances and dietary restrictions)
    compatible_recipe_ids: List[int]
    
    # Recipes retrieved from the vector DB (RAG)
    rag_recipes: List[Dict[str, Any]]
    
    # Internal log of actions (e.g. "updated ingredients: +2 salt")
    actions: List[str]
    
    # Memory updates tracked in this turn (e.g. {"added": [...], "removed": [...]})
    recent_memory_updates: Dict[str, List[str]]
    
    # Extracted user intents (e.g. ["recipe_recommendation_request", "general_chat"])
    user_intents: List[str]


