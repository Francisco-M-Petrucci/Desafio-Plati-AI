import os
import json
from typing import List, Dict, Any, Optional
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 1. Fallback Local Embeddings using Chroma's built-in ONNX model
class ChromaONNXEmbeddings(Embeddings):
    def __init__(self):
        try:
            import chromadb.utils.embedding_functions as ef
            self.func = ef.DefaultEmbeddingFunction()
        except Exception as e:
            print(f"Failed to load Chroma default embedding function: {e}")
            self.func = None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.func:
            # Fallback to zero vectors if everything fails (should not happen if chromadb is installed)
            return [[0.0] * 384 for _ in texts]
        return self.func(texts)

    def embed_query(self, text: str) -> List[float]:
        if not self.func:
            return [0.0] * 384
        return self.func([text])[0]


def get_embeddings_model() -> Embeddings:
    print("Using local ONNX embeddings (no API key required)...")
    return ChromaONNXEmbeddings()


class RecipeVectorDB:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            persist_directory = os.path.join(base_dir, "data", "chroma_db")
        self.persist_directory = persist_directory
        self.embeddings = get_embeddings_model()
        self.vector_store = None
        self._init_db()

    def _init_db(self):
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vector_store = Chroma(
            collection_name="food_com_recipes",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def seed_recipes(self, seed_file_path: str):
        """Seed the vector DB with recipes from a JSON file if the DB is empty."""
        # Check if already seeded
        try:
            results = self.vector_store.similarity_search("chicken", k=1)
            if results:
                print("Vector database already contains recipes. Skipping seeding.")
                return
        except Exception:
            pass

        if not os.path.exists(seed_file_path):
            print(f"Seed file not found at {seed_file_path}")
            return

        print(f"Seeding vector database from {seed_file_path}...")
        with open(seed_file_path, "r", encoding="utf-8") as f:
            recipes = json.load(f)

        documents = []
        for r in recipes:
            # Create a rich text representation for search
            content = f"Recipe: {r['name']}\n"
            content += f"Description: {r['description']}\n"
            content += f"Ingredients: {', '.join(r['ingredients'])}\n"
            content += f"Tags: {', '.join(r['tags'])}\n"
            
            metadata = {
                "id": r["id"],
                "name": r["name"],
                "minutes": r["minutes"],
                "ingredients": json.dumps(r["ingredients"]),
                "steps": json.dumps(r["steps"]),
                "tags": json.dumps(r["tags"]),
                "description": r["description"]
            }
            documents.append(Document(page_content=content, metadata=metadata))

        self.vector_store.add_documents(documents)
        print(f"Successfully indexed {len(documents)} recipes in Chroma Vector DB.")

    def search_recipes(
        self,
        query: str,
        limit: int = 5,
        culture: Optional[str] = None,
        season: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search recipes with optional culture and season tag filtering."""
        if not self.vector_store:
            return []

        # Perform similarity search
        results = self.vector_store.similarity_search(query, k=limit * 2)

        processed_results = []
        for doc in results:
            meta = doc.metadata
            tags = json.loads(meta.get("tags", "[]"))
            ingredients = json.loads(meta.get("ingredients", "[]"))
            steps = json.loads(meta.get("steps", "[]"))

            # Filter by culture and season if specified (case-insensitive)
            if culture and culture.lower() not in [t.lower() for t in tags]:
                continue
            if season and season.lower() not in [t.lower() for t in tags]:
                continue

            processed_results.append({
                "id": meta.get("id"),
                "name": meta.get("name"),
                "minutes": meta.get("minutes"),
                "ingredients": ingredients,
                "steps": steps,
                "tags": tags,
                "description": meta.get("description")
            })

            if len(processed_results) >= limit:
                break

        return processed_results
