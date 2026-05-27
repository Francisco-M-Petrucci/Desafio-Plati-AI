import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

load_dotenv()

from app.database import get_db, engine, Base
from app.models import User, Appliance, Ingredient, DietaryRestriction, ChatMessage, UserFact, InitialSearchRecipe
from app.agent.graph import agent_graph
from app.agent.tools import get_user_profile_data
from app.ocr import parse_receipt_image
from app.recipes_vector_db import RecipeVectorDB
from app.ingredients_formatter import standardize_ingredient

# Initialize tables
Base.metadata.create_all(bind=engine)

# Migration step: ensure first_name exists in users table
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR;"))
except Exception as e:
    print(f"Migration error during main startup (first_name): {e}")

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN wants_temporary TEXT DEFAULT '';"))
        conn.execute(text("ALTER TABLE users ADD COLUMN does_not_want_temporary TEXT DEFAULT '';"))
except Exception as e:
    print(f"Migration error during main startup (temporary_preferences columns): {e}")

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN asked_preferences BOOLEAN DEFAULT 0;"))
except Exception as e:
    print(f"Migration error during main startup (asked_preferences column): {e}")

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN temporary_preferences_updated_at DATETIME;"))
except Exception as e:
    print(f"Migration error during main startup (temporary_preferences_updated_at column): {e}")


# Migration step: standardize existing ingredients and reset to checklist defaults
try:
    from app.database import SessionLocal
    db = SessionLocal()
    from app.ingredients_formatter import standardize_ingredient
    
    all_ingredients = db.query(Ingredient).all()
    updated_count = 0
    merged_count = 0
    
    from collections import defaultdict
    user_ingredients = defaultdict(list)
    for ing in all_ingredients:
        user_ingredients[ing.user_id].append(ing)
        
    for user_id, ings in user_ingredients.items():
        seen_names = {}
        for ing in ings:
            standard_name = standardize_ingredient(ing.name)
            
            # Reset all to checklist defaults
            if ing.quantity != 1.0 or ing.unit != "unit":
                ing.quantity = 1.0
                ing.unit = "unit"
                updated_count += 1
                
            if standard_name in seen_names:
                db.delete(ing)
                merged_count += 1
            else:
                seen_names[standard_name] = ing
                if standard_name != ing.name:
                    ing.name = standard_name
                    updated_count += 1
                    
    if updated_count > 0 or merged_count > 0:
        db.commit()
        print(f"Database migration: Standardized/reset {updated_count} ingredients and merged {merged_count} duplicates.")
    db.close()
except Exception as e:
    print(f"Migration error standardizing ingredients: {e}")


app = FastAPI(title="Recipe Companion API")

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT_DB = {}
def check_rate_limit(user_id: int):
    now = time.time()
    last_req = RATE_LIMIT_DB.get(user_id, 0)
    if now - last_req < 1.0:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")
    RATE_LIMIT_DB[user_id] = now

# Initialize vector DB connection
recipe_vector_db = RecipeVectorDB()

# --- Pydantic Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    user_id: int
    message: str = Field(..., max_length=2000)

class ApplianceUpdate(BaseModel):
    appliances: List[str]

class IngredientUpdate(BaseModel):
    ingredients: List[str]

class RestrictionUpdate(BaseModel):
    restrictions: List[str]

class TemporaryPreferencesUpdate(BaseModel):
    wants_temporary: str
    does_not_want_temporary: str

class RegisterRequest(BaseModel):
    first_name: str
    username: str
    password: str
    appliances: List[str]
    restrictions: List[str]
    ingredients: List[str]


from datetime import datetime

def check_and_trigger_cleanup(user_id: int, db: Session):
    """
    Check if temporary preferences have not been updated for an hour.
    If so, clean wants_temporary and does_not_want_temporary, reset asked_preferences,
    and output a direct separator message.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    # Check if there are temporary preferences to clean.
    has_temp_prefs = bool((user.wants_temporary or "").strip()) or bool((user.does_not_want_temporary or "").strip())
    if not has_temp_prefs:
        return

    # If temporary_preferences_updated_at is not set, initialize it to now.
    if not user.temporary_preferences_updated_at:
        user.temporary_preferences_updated_at = datetime.utcnow()
        db.commit()
        return

    # Calculate elapsed time in seconds
    elapsed = (datetime.utcnow() - user.temporary_preferences_updated_at).total_seconds()
    if elapsed >= 3600:  # 1 hour
        # Clear preferences
        user.wants_temporary = ""
        user.does_not_want_temporary = ""
        user.asked_preferences = False
        user.temporary_preferences_updated_at = None
        
        # Add cleanup message separating old conversation from new
        cleanup_msg = "\nMy kitchen is now clean, and I am ready for our next cooking session!\n"
        db.add(ChatMessage(user_id=user_id, role="assistant", content=cleanup_msg))
        db.commit()
        print(f"Triggered reactive cleanup for user_id={user_id} (elapsed={elapsed}s)")


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
        
    # Allow plaintext login for test accounts
    if username in ["alice", "bob", "carlos"]:
        if user.password == req.password:
            access_token = create_access_token(data={"sub": str(user.id)})
            return {"user_id": user.id, "username": user.username, "access_token": access_token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")
            
    # For normal accounts, use bcrypt verification
    try:
        is_valid = verify_password(req.password, user.password)
    except Exception:
        is_valid = False
        
    if not is_valid:
        raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")
            
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"user_id": user.id, "username": user.username, "access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user, store kitchen profile, and run initial 5 recipe matches."""
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
        
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
        
    # Create new User with hashed password
    hashed_password = get_password_hash(req.password)
    user = User(
        first_name=req.first_name.strip(),
        username=username,
        password=hashed_password,
        asked_preferences=False
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
        name = ing.strip().lower()
        name = standardize_ingredient(name)
        if name:
            db.add(Ingredient(
                user_id=user.id,
                name=name,
                quantity=1.0,
                unit="unit"
            ))
            
    db.commit()
    
    # Run initial search to find 5 recipes
    try:
        from app.agent.tools import get_filtered_recipe_ids
        
        user_profile = {
            "appliances": [a.strip().lower() for a in req.appliances if a.strip()],
            "restrictions": [r.strip().lower() for r in req.restrictions if r.strip()],
            "ingredients": [standardize_ingredient(i) for i in req.ingredients if i.strip()]
        }
        
        # 1. Filter by appliances and dietary restrictions
        compatible_ids = get_filtered_recipe_ids(user_profile)
        
        # 2. Search recipes matching ingredients
        user_ing_names = [standardize_ingredient(i) for i in req.ingredients if i.strip()]
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
        
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"user_id": user.id, "username": user.username, "access_token": access_token, "token_type": "bearer"}


@app.get("/api/users/{user_id}/initial-search")
def get_initial_search(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Retrieve full details of the 5 recipes matched during registration."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
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
def get_profile(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Retrieve full kitchen inventory, appliances, restrictions, and facts."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    check_and_trigger_cleanup(user_id, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    profile = get_user_profile_data(user_id)
    return profile


@app.post("/api/users/{user_id}/appliances")
def update_appliances(user_id: int, req: ApplianceUpdate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Overwrite the user's available appliances."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
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
def update_ingredients(user_id: int, req: IngredientUpdate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Overwrite the user's ingredients inventory."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Delete old ingredients
    db.query(Ingredient).filter(Ingredient.user_id == user_id).delete()
    
    # Add new ones
    for ing in req.ingredients:
        name = ing.strip().lower()
        name = standardize_ingredient(name)
        if name:
            db.add(Ingredient(
                user_id=user_id,
                name=name,
                quantity=1.0,
                unit="unit"
            ))
            
    db.commit()
    return {"status": "success", "ingredients": [standardize_ingredient(i) for i in req.ingredients if i.strip()]}


@app.post("/api/users/{user_id}/ingredients/add-all-kb")
def add_all_kb_ingredients(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Add all ingredients from the knowledge base to the user's inventory."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    import json
    kb_path = os.path.join(os.path.dirname(__file__), "ingredients_kb.json")
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load ingredients KB: {str(e)}")
        
    # Get user's existing ingredients
    existing_ingredients = db.query(Ingredient).filter(Ingredient.user_id == user_id).all()
    existing_names = {ing.name.lower() for ing in existing_ingredients}
    
    # Add new ones from KB
    added = []
    for name in kb_data.keys():
        standardized = standardize_ingredient(name)
        if standardized and standardized.lower() not in existing_names:
            db.add(Ingredient(
                user_id=user_id,
                name=standardized,
                quantity=1.0,
                unit="unit"
            ))
            added.append(standardized)
            
    if added:
        db.commit()
        
    return {"status": "success", "added_count": len(added), "added": added}


@app.post("/api/users/{user_id}/restrictions")
def update_restrictions(user_id: int, req: RestrictionUpdate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Overwrite the user's dietary restrictions."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
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
def chat(req: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Exposes chat agent endpoint, loading history, running graph, and saving history."""
    if req.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    check_rate_limit(req.user_id)
    check_and_trigger_cleanup(req.user_id, db)
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
        if "My kitchen is now clean, and I am ready for our next cooking session!" in msg.content:
            break
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
            "user_name": user.first_name if user.first_name else user.username.capitalize(),
            "user_profile": profile_data,
            "compatible_recipe_ids": [],
            "rag_recipes": [],
            "actions": [],
            "recent_memory_updates": {"added": [], "removed": []}
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
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """
    Upload a receipt image. Calls Nvidia Vision model (or mock fallback)
    to parse ingredients and return them.
    """
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    check_rate_limit(user_id)
    
    # File validation
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, and WebP are allowed.")
        
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB).")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    try:
        contents = await file.read()
        filename = file.filename
        
        # Parse image
        ingredients = parse_receipt_image(contents, filename=filename)
        for ing in ingredients:
            ing["name"] = standardize_ingredient(ing.get("name", ""))
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
def get_chat_history(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Fetch all database saved messages for UI reload."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    check_and_trigger_cleanup(user_id, db)
    msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return [{"role": m.role, "content": m.content} for m in msgs]


@app.delete("/api/users/{user_id}/chat-history")
def clear_chat_history(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Clear chat messages history and session state."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.wants_temporary = ""
        user.does_not_want_temporary = ""
        user.asked_preferences = False
    db.commit()
    return {"status": "success", "message": "Chat history and temporary preferences cleared."}


@app.post("/api/users/{user_id}/temporary-preferences")
def update_temporary_preferences(user_id: int, req: TemporaryPreferencesUpdate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Update wants_temporary and does_not_want_temporary fields for a user."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.wants_temporary = req.wants_temporary
    user.does_not_want_temporary = req.does_not_want_temporary
    user.temporary_preferences_updated_at = datetime.utcnow()
    db.commit()
    return {
        "status": "success",
        "wants_temporary": user.wants_temporary,
        "does_not_want_temporary": user.does_not_want_temporary
    }


@app.delete("/api/users/{user_id}/temporary-preferences")
def clear_temporary_preferences(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Clear AI short term memory temporary preferences."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.wants_temporary = ""
        user.does_not_want_temporary = ""
        user.asked_preferences = False
    db.commit()
    return {"status": "success", "message": "AI short term memory cleared."}


@app.delete("/api/users/{user_id}/facts")
def clear_user_facts(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Clear AI long term memory facts."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.query(UserFact).filter(UserFact.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "AI long term memory cleared."}

# Trigger reload for LangSmith and search tool fixes.
