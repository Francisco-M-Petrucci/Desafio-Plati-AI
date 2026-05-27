import os
import json
from typing import List, Dict, Any, Optional, Set
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
        self._metadata_cache = None  # Cache for recipe metadata (avoids repeated Chroma queries)
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

        from app.ingredients_formatter import standardize_ingredient
        documents = []
        for r in recipes:
            # Standardize ingredients in the recipe
            r['ingredients'] = [standardize_ingredient(ing) for ing in r['ingredients']]
            
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
                "description": r["description"],
                # New structured metadata for pre-filtering
                "required_appliances": json.dumps(r.get("required_appliances", [])),
                "cuisine_type": r.get("cuisine_type", ""),
                "dietary_tags": json.dumps(r.get("dietary_tags", []))
            }
            documents.append(Document(page_content=content, metadata=metadata))

        self.vector_store.add_documents(documents)
        # Invalidate metadata cache after seeding
        self._metadata_cache = None
        print(f"Successfully indexed {len(documents)} recipes in Chroma Vector DB.")

    def get_all_recipe_metadata(self) -> List[Dict[str, Any]]:
        """
        Returns lightweight metadata for ALL recipes (no embeddings, no full content).
        Used by the deterministic pre-filter to check appliances, dietary tags, and cuisine.
        Results are cached in memory since recipe data does not change at runtime.
        """
        if self._metadata_cache is not None:
            return self._metadata_cache

        if not self.vector_store:
            return []

        try:
            collection = self.vector_store._collection
            results = collection.get()

            recipes = []
            for meta in results["metadatas"]:
                recipes.append({
                    "id": meta.get("id"),
                    "name": meta.get("name", ""),
                    "required_appliances": json.loads(meta.get("required_appliances", "[]")),
                    "cuisine_type": meta.get("cuisine_type", ""),
                    "dietary_tags": json.loads(meta.get("dietary_tags", "[]")),
                    "ingredients": json.loads(meta.get("ingredients", "[]")),
                    "tags": json.loads(meta.get("tags", "[]")),
                    "description": meta.get("description", "")
                })

            self._metadata_cache = recipes
            return recipes
        except Exception as e:
            print(f"Error loading recipe metadata: {e}")
            return []

    def get_recipe_by_id(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """
        Directly queries Chroma for a recipe by its ID.
        Returns the recipe dict (including steps and ingredients) or None if not found.
        """
        if not self.vector_store:
            return None
        try:
            collection = self.vector_store._collection
            results = collection.get(where={"id": recipe_id})
            if results and results["metadatas"]:
                meta = results["metadatas"][0]
                return {
                    "id": meta.get("id"),
                    "name": meta.get("name"),
                    "minutes": meta.get("minutes"),
                    "ingredients": json.loads(meta.get("ingredients", "[]")),
                    "steps": json.loads(meta.get("steps", "[]")),
                    "tags": json.loads(meta.get("tags", "[]")),
                    "description": meta.get("description")
                }
        except Exception as e:
            print(f"Error fetching recipe by ID {recipe_id}: {e}")
        return None

    def _lexical_search(self, query: str, recipe_id_set: Set[int]) -> Dict[int, float]:
        """
        Simple keyword-based scoring for recipes to act as Sparse Search.
        Returns a dict of {recipe_id: score}.
        """
        import re
        scores = {}
        all_meta = self.get_all_recipe_metadata()
        
        # Tokenize query into lowercase words (3+ chars)
        query_words = [w.lower() for w in re.findall(r'\b\w{3,}\b', query)]
        if not query_words:
            return scores
            
        for meta in all_meta:
            r_id = meta.get("id")
            if r_id not in recipe_id_set:
                continue
                
            score = 0.0
            name = meta.get("name", "").lower()
            ingredients = " ".join(meta.get("ingredients", [])).lower()
            tags = " ".join(meta.get("tags", [])).lower()
            
            for word in query_words:
                word_escaped = re.escape(word)
                # High boost for exact word match in name
                if re.search(r'\b' + word_escaped + r'\b', name):
                    score += 10.0
                elif word in name:
                    score += 2.0
                    
                # Medium boost for exact word match in ingredients
                if re.search(r'\b' + word_escaped + r'\b', ingredients):
                    score += 5.0
                elif word in ingredients:
                    score += 1.0
                    
                # Small boost for tags
                if re.search(r'\b' + word_escaped + r'\b', tags):
                    score += 2.0
                    
            if score > 0:
                scores[r_id] = score
                
        return scores

    def search_recipes_filtered(
        self,
        query: Optional[str] = None,
        recipe_ids: Set[int] = None,
        excluded_ids: Optional[Set[int]] = None,
        limit: int = 5,
        culture: Optional[str] = None,
        season: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search recipes constrained to a pre-filtered set of recipe IDs.
        If query is empty/None, returns any compatible recipes directly.
        """
        if culture in (None, "null", "None", "NoneType", ""):
            culture = None
        if season in (None, "null", "None", "NoneType", ""):
            season = None

        if not self.vector_store:
            return []

        recipe_id_set = set(recipe_ids) if recipe_ids else set()
        if excluded_ids:
            recipe_id_set = recipe_id_set - set(excluded_ids)

        if not query:
            # Python-based fallback: bypass similarity search and return any compatible recipes
            processed_results = []
            all_meta = self.get_all_recipe_metadata()
            for meta in all_meta:
                recipe_id = meta.get("id")
                if recipe_id not in recipe_id_set:
                    continue
                if culture:
                    recipe_cuisine = meta.get("cuisine_type", "")
                    if culture.lower() != recipe_cuisine.lower():
                        continue
                if season:
                    tags = json.loads(meta.get("tags", "[]"))
                    if season.lower() not in [t.lower() for t in tags]:
                        continue
                
                recipe_full = self.get_recipe_by_id(recipe_id)
                if recipe_full:
                    processed_results.append(recipe_full)
                if len(processed_results) >= limit:
                    break
            return processed_results

        results_dense = self.vector_store.similarity_search_with_score(query, k=100)

        # 1. Calculate Dense Ranks
        dense_rank = {}
        current_rank = 1
        for doc, _ in results_dense:
            r_id = doc.metadata.get("id")
            if r_id not in recipe_id_set:
                continue
                
            # Filter by culture and season
            if culture:
                recipe_cuisine = doc.metadata.get("cuisine_type", "")
                if culture.lower() != recipe_cuisine.lower():
                    continue
            if season:
                tags = json.loads(doc.metadata.get("tags", "[]"))
                if season.lower() not in [t.lower() for t in tags]:
                    continue
                    
            if r_id not in dense_rank:
                dense_rank[r_id] = current_rank
                current_rank += 1
                
        # 2. Calculate Sparse Ranks
        lexical_scores = self._lexical_search(query, recipe_id_set)
        
        # Filter lexical matches by culture and season before ranking
        filtered_lexical_scores = {}
        all_meta = {m["id"]: m for m in self.get_all_recipe_metadata()}
        
        for r_id, score in lexical_scores.items():
            meta = all_meta.get(r_id)
            if not meta:
                continue
            if culture:
                recipe_cuisine = meta.get("cuisine_type", "")
                if culture.lower() != recipe_cuisine.lower():
                    continue
            if season:
                tags = json.loads(meta.get("tags", "[]")) if isinstance(meta.get("tags"), str) else meta.get("tags", [])
                if season.lower() not in [t.lower() for t in tags]:
                    continue
            filtered_lexical_scores[r_id] = score
            
        # Sort sparse scores descending
        sorted_sparse = sorted(filtered_lexical_scores.items(), key=lambda x: x[1], reverse=True)
        sparse_rank = {r_id: rank + 1 for rank, (r_id, _) in enumerate(sorted_sparse)}
        
        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        combined_scores = {}
        
        # Union of all valid recipe IDs from both methods
        all_valid_ids = set(dense_rank.keys()) | set(sparse_rank.keys())
        
        for r_id in all_valid_ids:
            score = 0.0
            if r_id in dense_rank:
                score += 1.0 / (rrf_k + dense_rank[r_id])
            if r_id in sparse_rank:
                score += 1.0 / (rrf_k + sparse_rank[r_id])
            combined_scores[r_id] = score
            
        # 4. Sort by RRF score descending
        sorted_final = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 5. Fetch full recipe details for the top `limit` results
        processed_results = []
        for r_id, _ in sorted_final:
            recipe_full = self.get_recipe_by_id(r_id)
            if recipe_full:
                processed_results.append(recipe_full)
            if len(processed_results) >= limit:
                break

        return processed_results

    def search_recipes(
        self,
        query: str,
        limit: int = 5,
        culture: Optional[str] = None,
        season: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search recipes with optional culture and season tag filtering.
        Kept for backward compatibility with the /api/recipes exploration endpoint."""
        if culture in (None, "null", "None", "NoneType", ""):
            culture = None
        if season in (None, "null", "None", "NoneType", ""):
            season = None

        if not self.vector_store:
            return []

        # Perform similarity search with a larger pool of candidates to avoid post-filtering starvation
        results = self.vector_store.similarity_search(query, k=100)

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
