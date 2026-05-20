## Challenge 2 — Conversational Assistant with Memory and RAG

### Context

At Plati, we build AI agents ("workers") that converse with users via WhatsApp on behalf of Brazilian companies. One of the key differentiators we pursue is *hyper-personalization*: the agent needs to remember the user across conversations, retrieve specific information from the client's business, and adapt the response based on what it knows about the person on the other side.

This challenge simulates this problem on a smaller scale.

### Objective

Create a conversational application (text-based, local) where an AI assistant *remembers past conversations* with each user and *queries a private knowledge base* to deliver hyper-personalized responses. The assistant must combine three layers of context: the current conversation, the user profile built over time, and the "business" knowledge base.

### Suggested Scenario

Choose a niche where personalization and specific knowledge matter — e.g., a specialty coffee shop, a personal trainer, a clinic, a language school, a real estate agency, or an e-commerce platform. The assistant should "know" the user across multiple sessions, rather than treating them as a stranger in every new conversation.

### Requirements

*1. Conversation Memory (short and long-term)*
•⁠ *Short-term:* context window of the current conversation (the last N messages).
•⁠ *Long-term:* the system must extract and store relevant facts about the user across conversations (e.g., "prefers pour-over coffee", "lactose intolerant", "training for a half-marathon in July"). This memory persists between sessions and is retrieved in subsequent conversations.
•⁠ Use a *memory summarization* or *fact extraction* strategy — simply stacking all messages is not enough; there must be curation.

*2. RAG over Knowledge Base*
•⁠ Index a database of documents for the chosen "business" (e.g., menu + description of coffee beans for the coffee shop; property catalog for the real estate agency; workout plans for the personal trainer). Minimum of 10–20 documents.
•⁠ The AI must decide *when* to query the RAG vs. replying from its own knowledge vs. querying the user's memory (ideally via tool calling).

*3. Framework — Your Choice*
We do not require LangChain. Some options (choose one and justify):
•⁠ *LangChain / LangGraph* — most popular, extensive documentation, great for graph-based orchestration.
•⁠ *LlamaIndex* — focused on RAG, more mature abstractions for indexing and retrieval.
•⁠ *Haystack* (deepset) — pipeline-oriented, strong for production environments.
•⁠ *Pydantic AI* — newer, type-safe, focused on structured agents.
•⁠ *DSPy* — declarative approach, automatically optimizes prompts.
•⁠ *Mastra* (TypeScript) — if you prefer JS/TS.
•⁠ *No framework* — custom orchestration calling the LLM API directly. Accepted as long as you justify the choice.

For the vector store: Chroma, Qdrant, pgvector, FAISS, Weaviate, LanceDB — your choice.

*4. Interface*
•⁠ A simple CLI or web UI. No need for WhatsApp integration.
•⁠ Must support *multiple users* (e.g., a command to switch users, or a basic login), each with their own isolated memory.

*5. Orchestration*
•⁠ Flow: receive message → retrieve user memory → decide what to query (RAG, memory, nothing) → generate response → update memory.
•⁠ Function calling / tools for: `search_knowledge_base`, `get_user_facts`, `save_user_fact`, etc.

*6. Demonstrable Personalization*
•⁠ The presentation must show *the exact same question* being answered in different ways for different users, based on what the assistant knows about each of them.
•⁠ E.g., "What do you recommend for me today?" → for User A (lactose-intolerant, loves Ethiopian coffee) comes one response; for User B (likes sweets, first-time visitor) comes another.

*7. Minimum Stack*
•⁠ Python or TypeScript.
•⁠ LLM Provider of your choice (OpenAI, Anthropic, Gemini, open-source models via Ollama, etc.).
•⁠ Vector DB for RAG.
•⁠ Database for long-term memory (SQLite, Postgres, Redis — your choice).
•⁠ A README explaining the architecture, decisions, and how to run it.

### Deliverables

•⁠ A GitHub repository.
•⁠ A README containing: architecture (diagrams are welcome), the chosen stack and *why*, how to run it locally, conversation examples demonstrating memory + RAG, and main challenges.
•⁠ A script or seed file to populate the knowledge base.
•⁠ A live presentation demonstrating: (i) RAG working, (ii) memory persisting between sessions, (iii) two different personas receiving different responses to the same input.

### Deadline

10 days.

### Evaluation Criteria

•⁠ Quality of the memory strategy — simply dumping everything into history is not enough.
•⁠ Clear decision-making on when to use RAG vs. memory vs. the model's base knowledge.
•⁠ Correct isolation of context per user.
•⁠ Justification of framework, vector store, and model choices.
•⁠ Clean, modular, and testable code.
•⁠ Clarity in presenting technical decisions.

### Tips

•⁠ Think of *three layers of context*: current conversation, user profile (extracted facts), and knowledge base (RAG). Each solves a different problem.
•⁠ Watch out for prompt injection — what the user says should not be able to rewrite sensitive facts in memory without validation.
•⁠ Token budget matters: everything retrieved needs to fit into the context. Summarization and ranking are part of the challenge.
•⁠ Simple evals (10–20 cases) will help you defend your choices during the presentation.