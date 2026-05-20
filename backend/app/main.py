import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.database import get_db, engine, Base
from app.models import User, Appliance, Ingredient, DietaryRestriction, ChatMessage, UserFact
from app.agent.graph import agent_graph
from app.agent.tools import get_user_profile_data
from app.ocr import parse_receipt_image
from app.recipes_vector_db import RecipeVectorDB

# Initialize tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recipe Companion API")

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector DB connection
recipe_vector_db = RecipeVectorDB()

# --- Pydantic Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    user_id: int
    message: str

class ApplianceUpdate(BaseModel):
    appliances: List[str]

class IngredientItem(BaseModel):
    name: str
    quantity: float
    unit: str

class IngredientUpdate(BaseModel):
    ingredients: List[IngredientItem]

class RestrictionUpdate(BaseModel):
    restrictions: List[str]


# --- API Routes ---

@app.get("/")
def read_root():
    return {"message": "Recipe Companion API is running!"}


@app.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Simple login that creates the user if they don't exist (for easier local testing)."""
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
        
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Auto-register user for ease of local demo
        user = User(username=username, password=req.password)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Auto-registered user: {username}")
        
    return {"user_id": user.id, "username": user.username}


@app.get("/api/users/{user_id}/profile")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Retrieve full kitchen inventory, appliances, restrictions, and facts."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    profile = get_user_profile_data(user_id)
    return profile


@app.post("/api/users/{user_id}/appliances")
def update_appliances(user_id: int, req: ApplianceUpdate, db: Session = Depends(get_db)):
    """Overwrite the user's available appliances."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete old appliances
    db.query(Appliance).filter(Appliance.user_id == user_id).delete()
    
    # Add new ones
    for app_name in req.appliances:
        if app_name.strip():
            db.add(Appliance(user_id=user_id, name=app_name.strip().lower()))
            
    db.commit()
    return {"status": "success", "appliances": req.appliances}


@app.post("/api/users/{user_id}/ingredients")
def update_ingredients(user_id: int, req: IngredientUpdate, db: Session = Depends(get_db)):
    """Overwrite the user's ingredients inventory."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete old ingredients
    db.query(Ingredient).filter(Ingredient.user_id == user_id).delete()
    
    # Add new ones
    for ing in req.ingredients:
        name = ing.name.strip().lower()
        if name:
            db.add(Ingredient(
                user_id=user_id,
                name=name,
                quantity=ing.quantity,
                unit=ing.unit.strip().lower()
            ))
            
    db.commit()
    return {"status": "success", "ingredients": [i.dict() for i in req.ingredients]}


@app.post("/api/users/{user_id}/restrictions")
def update_restrictions(user_id: int, req: RestrictionUpdate, db: Session = Depends(get_db)):
    """Overwrite the user's dietary restrictions."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete old restrictions
    db.query(DietaryRestriction).filter(DietaryRestriction.user_id == user_id).delete()
    
    # Add new ones
    for rest in req.restrictions:
        if rest.strip():
            db.add(DietaryRestriction(user_id=user_id, restriction=rest.strip().lower()))
            
    db.commit()
    return {"status": "success", "restrictions": req.restrictions}


@app.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Exposes chat agent endpoint, loading history, running graph, and saving history."""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Load short-term history from DB (last 10 messages)
    history_msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == req.user_id
    ).order_by(ChatMessage.created_at.asc()).all()[-10:]

    # Map database messages to LangChain message formats
    from langchain_core.messages import HumanMessage, AIMessage
    formatted_messages = []
    for msg in history_msgs:
        if msg.role == "user":
            formatted_messages.append(HumanMessage(content=msg.content))
        else:
            formatted_messages.append(AIMessage(content=msg.content))

    # Add the current new message
    formatted_messages.append(HumanMessage(content=req.message))

    # Save user message to database
    db.add(ChatMessage(user_id=req.user_id, role="user", content=req.message))
    db.commit()

    # 2. Invoke LangGraph Agent
    try:
        # Load user profile to construct agent input state
        profile_data = get_user_profile_data(req.user_id)
        
        initial_state = {
            "messages": formatted_messages,
            "user_id": req.user_id,
            "user_name": user.username,
            "user_profile": profile_data,
            "rag_recipes": [],
            "actions": []
        }
        
        result = agent_graph.invoke(initial_state)
        
        # Extract response text
        final_msg = result["messages"][-1]
        response_text = final_msg.content

        # Save assistant response to database
        db.add(ChatMessage(user_id=req.user_id, role="assistant", content=response_text))
        db.commit()

        return {
            "response": response_text,
            "rag_recipes": result.get("rag_recipes", []),
            "actions": result.get("actions", [])
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/receipts/upload")
async def upload_receipt(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a receipt image. Calls Nvidia Vision model (or mock fallback)
    to parse ingredients and return them.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    try:
        contents = await file.read()
        filename = file.filename
        
        # Parse image
        ingredients = parse_receipt_image(contents, filename=filename)
        return {"ingredients": ingredients}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Receipt parsing error: {str(e)}")


@app.get("/api/recipes")
def list_recipes(
    query: Optional[str] = "",
    culture: Optional[str] = None,
    season: Optional[str] = None
):
    """Query the vector database directly (for recipes exploration tab)."""
    return recipe_vector_db.search_recipes(query, limit=10, culture=culture, season=season)


@app.get("/api/users/{user_id}/chat-history")
def get_chat_history(user_id: int, db: Session = Depends(get_db)):
    """Fetch all database saved messages for UI reload."""
    msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return [{"role": m.role, "content": m.content} for m in msgs]


@app.delete("/api/users/{user_id}/chat-history")
def clear_chat_history(user_id: int, db: Session = Depends(get_db)):
    """Clear chat messages history and session state."""
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "Chat history cleared."}


@app.delete("/api/users/{user_id}/facts")
def clear_user_facts(user_id: int, db: Session = Depends(get_db)):
    """Clear AI long term memory facts."""
    db.query(UserFact).filter(UserFact.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "AI long term memory cleared."}
