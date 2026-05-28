(Pt-Br version available)
# ChefCompanion

ChefCompanion is a local-first conversational web application that suggests hyper-personalized recipes to users based on their kitchen appliances, available ingredients, dietary restrictions, and seasonal preferences.

This project was built to demonstrate an AI assistant capable of long-term memory extraction and Retrieval-Augmented Generation (RAG) for the Plati AI challenge.

## Architecture

ChefCompanion combines three layers of context to drive personalization:

1. **Short-Term Context**: Temporary preference tags ("Wants" and "Does Not Want") combined with a heavily compressed, minified history of recent agent actions. To prevent context bloat, only the most recent user message is passed into the prompt each turn, rather than a full rolling window.
2. **User Profile & Long-Term Memory (SQLite)**: User inventory, available appliances, dietary restrictions, and permanent facts extracted programmatically across sessions.
3. **Knowledge Base (RAG)**: A vector search collection loaded with curated recipes matching the schema of the Food.com Recipes dataset.

### Agent Workflow (LangGraph Orchestration)

```text
          START
            |
            v
    [ Load Profile ] ---- Fetch user stock/appliances/restrictions/facts from SQLite
            |
            v
 [ Extract Preferences ]- Analyze latest message to extract facts and user intent
            |
            v
      [ Pre-Filter ] ---- Filter recipes by appliances/diet before LLM sees them
            |
            v
      [ Agent LLM ] ----- Formulate prompt & decide tool calls (RAG or inventory)
            |
       +----+----+ (Conditional routing)
       v         v
    [Tools]   [Output]
       |         |
       +---------+
            |
            v
           END
```

## Memory Strategy

The system relies on a multi-layered memory approach:
- **Fact Extraction Pre-Processing**: Before the main conversational LLM runs, a dedicated LangGraph node analyzes the user's latest message to extract permanent facts (e.g., "I am lactose intolerant") and temporary intents (e.g., "I want a quick dinner"). This is parsed as JSON and persisted directly to the SQLite database.
- **Context Isolation**: Each user has an isolated profile in SQLite.
- **Security & Prompt Injection**: The fact extraction prompt wraps user messages in XML tags (`<user_message>`) and explicitly instructs the extractor to ignore instructions inside the tags, preventing prompt injections from rewriting sensitive database facts.

## Token Cost Minimization Strategies

To maintain performance and keep token costs low:
- **Deterministic Pre-Filtering**: Before querying the vector database or sending results to the LLM, the system programmatically filters out recipes that are incompatible with the user's registered dietary restrictions or appliances. This prevents wasting tokens on irrelevant data.
- **Targeted RAG Invocation**: The LLM only searches the vector database when explicitly requested or when a recommendation intent is detected, falling back to general knowledge for basic cooking inquiries.

## Technology Stack & Rationale

- **Agent Framework**: `LangChain` and `LangGraph`. LangGraph provides optimal control for stateful, multi-turn orchestration. It allows for strict routing between memory extraction, tool execution, and LLM reasoning based on specific application states.
- **LLM Engine**: `Llama 3.3 70B Versatile` via **Groq**. 
  - *Why*: This model excels at complex tool calling and delivers exceptional inference speeds. Furthermore, its massive 128k context window easily accommodates extensive conversational history and retrieved RAG documents without truncation risk. 
  - *Note*: It is highly recommended to use the Groq Llama 3.3 70B Versatile model. Using alternative or weaker models may significantly degrade the agent's ability to output valid tool calls and follow strict JSON schemas.
- **Database (Long-Term Memory)**: `SQLite`. Chosen for its lightweight, serverless nature. It is ideal for a local proof-of-concept, enabling rapid setup and seamless isolation of context per user without requiring external database hosting.
- **Vector Store (Knowledge Base)**: `Chroma`. Operates entirely serverless and stores embeddings locally. It integrates seamlessly into Python workflows for rapid similarity searches without external dependencies.
- **Backend**: `FastAPI` (Python). Lightweight, fast asynchronous execution, and excellent auto-documentation.

## Main Challenges

During development, the most significant challenge was identifying the right orchestration strategy and model. Initial iterations utilized a less capable model and a convoluted graph strategy, which resulted in continuous errors with tool-calling formats and schema adherence. By migrating to a simpler LangGraph architecture relying on a intent-extractor node, and upgrading to Groq's Llama 3.3 70B, development accelerated significantly, resolving the tool-calling inconsistencies and improving overall reliability.

## Demonstrable Personalization (Test Cases)

To verify hyper-personalization, use the pre-seeded test personas (password: `password123`):

### User A: Alice (Gluten-Free, Quick Cook)
**Profile:** Airfryer owner, Gluten-Free, prefers quick meals.
1. **Direct Request:** Ask *"I'm really hungry and I only have about 20 minutes to cook something. What can I make with my chicken wings?"*
   **Result:** Recommends a fast airfryer recipe based on her ingredients and facts.
2. **Dietary Safety Check:** Ask *"Can I make a classic pasta dish?"*
   **Result:** The strict pre-filter blocks all gluten recipes. The AI will only present 100% gluten-free alternatives.

### User B: Bob (Vegetarian, Traditional Italian)
**Profile:** Oven owner, Vegetarian, dislikes spicy food.
1. **Memory Check:** Ask *"I want to make something really spicy for dinner, just for tonight."*
   **Result:** The agent checks his long-term facts and gently reminds him he usually dislikes spicy food.
2. **RAG vs Base Knowledge:** Ask *"I have some pizza dough and fresh mozzarella. Walk me through making a pizza step-by-step."*
   **Result:** The agent answers from general knowledge.
   Then ask: *"Walk me through making a margherita pizza step-by-step."*
   **Result:** The agent fetches the specific *Classic Italian Margherita Pizza* from the vector database.

## Evaluation Suite

To programmatically guarantee the application's safety, hallucination-prevention, and architectural intent, a robust test suite (`evals.py`) is included using `pytest`. 

The suite comprises 11 distinct evaluation cases covering the agent's three core responsibilities:
1. **Deterministic Pre-filtering (5 cases):** Asserts that users with dietary restrictions (e.g., Gluten-Free, Vegetarian) or missing appliances (e.g., Oven) strictly cannot be recommended incompatible recipes.
2. **Fact Extraction Accuracy (3 cases):** Asserts that the LLM correctly parses user messages to permanently memorize facts (e.g., "training for a marathon") and temporarily capture session wants.
3. **Tool Selection Accuracy (3 cases):** Asserts that the LLM reliably decides when to use Base Knowledge (general chat) versus RAG (recipe requests), successfully managing token expenditure and preventing unprompted database searches.

**Results:** `11/11 PASSED` (100% Success Rate). 

To run the evaluations locally:
```bash
cd backend
pytest evals.py -v
```

## Future Implementations Roadmap

- **Receipt OCR Integration:** Implementing a feature to upload photos of grocery store receipts to automatically parse and update the user's kitchen inventory using a multimodal vision model.
- **Expanded Recipe Database:** Significantly increasing the size of the Chroma vector database to include a much wider variety of recipes from different cuisines and dietary niches.
- **Cooking Assistance Mode:** Creating a dedicated hands-free interface mode designed for active cooking. It will feature large, accessible buttons for step-by-step navigation, ensuring users with messy or occupied hands don't need to type messages.

## How to Run Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Configure Environment
Copy `.env.example` to `.env` in the project root and fill in your keys:
```bash
cp .env.example .env
```
Ensure your `GROQ_API_KEY` is populated for the primary LLM.

### 3. Automated Setup
The easiest way to install all dependencies and seed the database is using the setup scripts.

**For Windows:**
```cmd
setup.bat
```

**For Mac/Linux:**
```bash
chmod +x setup.sh start.sh
./setup.sh
```

### 4. Start the Application
**For Windows:**
```cmd
start.bat
```

**For Mac/Linux:**
```bash
./start.sh
```
The application will be available at http://localhost:5173.
