# ChefCompanion — Personalized AI Recipe Assistant

ChefCompanion is a local-first conversational web application that suggests hyper-personalized recipes to users based on their kitchen appliances, available ingredients, dietary restrictions, and seasonal preferences.

The core AI engine uses **LangChain & LangGraph** for stateful routing and memory extraction, integrated with the **Nvidia NIM API** (`llama-3.1-70b-instruct` and `llama-3.2-11b-vision-instruct`).

---

## 🏗️ Architecture

ChefCompanion combines three layers of context to drive personalization:
1. **Short-Term Context**: The active conversation window (last 10 messages from the database).
2. **User Profile (SQLite)**: User inventory, available appliances, dietary restrictions, and long-term memory facts extracted by the AI across sessions.
3. **Knowledge Base (RAG)**: A vector search collection loaded with 22 curated recipes matching the schema of the Food.com Recipes dataset.

### Agent Workflow (LangGraph)

```
       START
         │
         ▼
 ┌───────────────┐
 │ Load Profile  │ ── Fetch user stock/appliances/restrictions/facts from SQLite
 └───────────────┘
         │
         ▼
 ┌───────────────┐
 │  Agent LLM    │ ── Formulate system prompt & decide tool call (RAG or inventory)
 └───────────────┘
         │
    ┌────┴────┐ (Conditional routing)
    ▼         ▼
[Tool Call] [Final Text]
    │         │
    │         ▼
    │   ┌──────────────┐
    │   │ Extract Facts│ ── Analyze exchange to extract permanent user preferences
    │   └──────────────┘
    │         │
    ▼         ▼
 ┌──────┐    END
 │Tools │ ── Execute SQLite inventory updates or Vector DB queries
 └──────┘
    │
    ▼
 (Loop back to Agent LLM)
```

---

## 🛠️ Technology Stack & Rationale

- **Backend**: `FastAPI` (Python) — Lightweight, fast asynchronous execution, and excellent auto-documentation.
- **Agent Framework**: `LangChain` and `LangGraph` — Standard for stateful, multi-turn tool-calling workflows.
- **Database**: `SQLite` (SQLAlchemy ORM) — Ideal for a local serverless environment, ensuring separate isolated contexts per user profile.
- **Vector Store**: `Chroma` (with `ChromaONNXEmbeddings` fallback) — Runs completely serverless, stores embeddings locally, and provides fast cosine similarity.
- **LLM Engine**: `Nvidia NIM API`
  - *Text Reasoning & Tools*: `meta/llama-3.1-70b-instruct` (industry leader for multi-tool calling and extraction).
  - *Vision Scanner*: `meta/llama-3.2-11b-vision-instruct` (lightweight, highly accurate multimodal model for receipt OCR).

---

## 🚀 How to Run Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Configure Environment
Create a `.env` file in the project root:
```env
NVIDIA_API_KEY=nvapi-your-key-here
```

### 3. Setup and Seed Backend
In a terminal, run the following from the root directory:
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install python dependencies
pip install -r backend/requirements.txt

# Create tables and seed data (users Alice/Bob + 22 recipes)
python backend/seed.py

# Start FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```

### 4. Setup and Run Frontend
Open a new terminal window and run:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🍽️ Demonstrable Personalization Scenarios

You can verify hyper-personalization immediately by using the preseeded test personas:

### User A: Alice (Gluten-Free, Low-Carb, Airfryer owner)
1. Log in as **Alice**.
2. Go to **My Kitchen** to see preloaded stock (chicken wings, parmesan cheese, garlic powder, parsley) and restrictions.
3. In **Assistant Chat**, ask: *"What should I cook for dinner today?"*
4. **AI response**: Recommends *Airfryer Garlic Parmesan Chicken Wings* (since it is low-carb, gluten-free, matches her airfryer, and uses her chicken wings).

### User B: Bob (Vegetarian, Oven owner, loves Italian)
1. Log in as **Bob**.
2. Go to **My Kitchen** to see stock (pizza dough, tomatoes, fresh mozzarella, basil) and restrictions.
3. In **Assistant Chat**, ask: *"What should I cook for dinner today?"*
4. **AI response**: Recommends *Classic Italian Margherita Pizza* (since it is vegetarian, matches his oven, and uses his pizza dough/mozzarella).

### Long-Term Memory Test
1. Log in as any user.
2. In Chat, tell the assistant: *"I training for a half-marathon and need carb-heavy meals next week. Also, I absolutely hate mushrooms."*
3. Log out and log back in.
4. Go to **My Kitchen** and notice the new facts saved under **AI Long-Term Memory**:
   - `Training for a half-marathon`
   - `Needs carb-heavy meals`
   - `Hates mushrooms`
5. Ask: *"Suggest a dinner recipe."*
6. **AI response**: Recommends a high-carb dish (e.g. Pasta Primavera) and avoids Creamy Mushroom Risotto, explicitly referencing the marathon training.
