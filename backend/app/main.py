import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.database import get_db, engine, Base
from app.models import User, Appliance, Ingredient, DietaryRestriction, ChatMessage, UserFact, TemporaryPreference, InitialSearchRecipe
from app.agent.graph import agent_graph, extract_facts_from_state
from app.agent.tools import get_user_profile_data
from app.ocr import parse_receipt_image
from app.recipes_vector_db import RecipeVectorDB

# Initialize tables
Base.metadata.create_all(bind=engine)

# Migration step: ensure first_name exists in users table
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR;"))
except Exception as e:
    print(f"Migration error during main startup: {e}")

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

class RegisterRequest(BaseModel):
    first_name: str
    username: str
    password: str
    appliances: List[str]
    restrictions: List[str]
    ingredients: List[IngredientItem]


# --- API Routes ---

@app.get("/")
def read_root():
    return {"message": "Recipe Companion API is running!"}


@app.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login and verify username and password."""
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
        
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please register first.")
        
    if user.password != req.password:
        raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")
        
    return {"user_id": user.id, "username": user.username}


@app.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user, store kitchen profile, and run initial 5 recipe matches."""
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
        
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
        
    # Create new User
    user = User(
        first_name=req.first_name.strip(),
        username=username,
        password=req.password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Add appliances
    for app_name in req.appliances:
        if app_name.strip():
            db.add(Appliance(user_id=user.id, name=app_name.strip().lower()))
            
    # Add restrictions
    for rest in req.restrictions:
        if rest.strip():
            db.add(DietaryRestriction(user_id=user.id, restriction=rest.strip().lower()))
            
    # Add ingredients
    for ing in req.ingredients:
        name = ing.name.strip().lower()
        if name:
            db.add(Ingredient(
                user_id=user.id,
                name=name,
                quantity=ing.quantity,
                unit=ing.unit.strip().lower()
            ))
            
    db.commit()
    
    # Run initial search to find 5 recipes
    try:
        from app.agent.tools import get_filtered_recipe_ids
        
        user_profile = {
            "appliances": [a.strip().lower() for a in req.appliances if a.strip()],
            "restrictions": [r.strip().lower() for r in req.restrictions if r.strip()],
            "ingredients": [{"name": i.name.strip().lower()} for i in req.ingredients if i.name.strip()]
        }
        
        # 1. Filter by appliances and dietary restrictions
        compatible_ids = get_filtered_recipe_ids(user_profile)
        
        # 2. Search recipes matching ingredients
        user_ing_names = [i.name.strip().lower() for i in req.ingredients if i.name.strip()]
        query = ", ".join(user_ing_names) if user_ing_names else "recipe"
        
        recipes_raw = recipe_vector_db.search_recipes_filtered(
            query=query,
            recipe_ids=set(compatible_ids),
            limit=5
        )
        
        # If fewer than 5, fill with remaining compatible recipes
        if len(recipes_raw) < 5:
            all_meta = recipe_vector_db.get_all_recipe_metadata()
            compatible_recipes = [r for r in all_meta if r["id"] in compatible_ids]
            existing_ids = {r["id"] for r in recipes_raw}
            for r in compatible_recipes:
                if len(recipes_raw) >= 5:
                    break
                if r["id"] not in existing_ids:
                    recipe_full = recipe_vector_db.get_recipe_by_id(r["id"])
                    if recipe_full:
                        recipes_raw.append(recipe_full)
                        existing_ids.add(r["id"])
                        
        # Store selected 5 recipe IDs in initial_search_recipes
        for r in recipes_raw[:5]:
            db.add(InitialSearchRecipe(user_id=user.id, recipe_id=r["id"]))
        db.commit()
        
    except Exception as e:
        print(f"Error during registration recipe search: {e}")
        
    return {"user_id": user.id, "username": user.username}


@app.get("/api/users/{user_id}/initial-search")
def get_initial_search(user_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of the 5 recipes matched during registration."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    initial_matches = db.query(InitialSearchRecipe).filter(InitialSearchRecipe.user_id == user_id).all()
    
    recipes_list = []
    for match in initial_matches:
        recipe = recipe_vector_db.get_recipe_by_id(match.recipe_id)
        if recipe:
            recipes_list.append(recipe)
            
    return recipes_list


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
def chat(req: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Exposes chat agent endpoint, loading history, running graph, and saving history."""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Load short-term history from DB (up to 15 assistant messages to select from by token budget)
    history_msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == req.user_id,
        ChatMessage.role == "assistant"
    ).order_by(ChatMessage.created_at.desc()).limit(15).all()

    # Map database messages to LangChain message formats fitting within token budget
    from langchain_core.messages import HumanMessage, AIMessage
    from app.agent.memory import minify_assistant_message
    
    MAX_HISTORY_TOKENS = 400
    token_count = 0
    formatted_messages = []
    for msg in history_msgs:
        minified_content = minify_assistant_message(msg.content)
        msg_tokens = len(minified_content) // 4  # Estimate: 4 chars ≈ 1 token
        if token_count + msg_tokens > MAX_HISTORY_TOKENS:
            break
        formatted_messages.insert(0, AIMessage(content=minified_content))
        token_count += msg_tokens

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
            "compatible_recipe_ids": [],
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

        # Extract facts in the background to improve response time
        background_tasks.add_task(extract_facts_from_state, result)

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
    db.query(TemporaryPreference).filter(TemporaryPreference.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "Chat history and temporary preferences cleared."}


@app.delete("/api/users/{user_id}/temporary-preferences")
def clear_temporary_preferences(user_id: int, db: Session = Depends(get_db)):
    """Clear AI short term memory temporary preferences."""
    db.query(TemporaryPreference).filter(TemporaryPreference.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "AI short term memory cleared."}


@app.delete("/api/users/{user_id}/facts")
def clear_user_facts(user_id: int, db: Session = Depends(get_db)):
    """Clear AI long term memory facts."""
    db.query(UserFact).filter(UserFact.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "AI long term memory cleared."}

# Trigger reload for LangSmith and search tool fixes.
