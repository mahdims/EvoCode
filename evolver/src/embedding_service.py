"""
Code Embedding Service using Gemini API

Generates real code embeddings for candidate strategies and projects
them to 2D via PCA for diversity visualization in the dashboard.

Caches embeddings by code_hash to avoid redundant API calls.
Falls back gracefully if Gemini SDK or API key is unavailable.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class EmbeddingService:
    """Manages code embedding via Gemini API with caching and PCA projection."""

    def __init__(self,
                 model: str = "gemini-embedding-001",
                 cache_file: str = "candidates/embedding_cache.json"):
        self.model = model
        self.cache_file = Path(cache_file)
        self.available = False
        self._cache: Dict[str, List[float]] = {}

        if not GENAI_AVAILABLE:
            logger.debug("[EMBEDDING] google-genai not installed — embedding service unavailable")
            return

        try:
            import os
            if not os.environ.get("GOOGLE_API_KEY"):
                logger.debug("[EMBEDDING] GOOGLE_API_KEY not set — embedding service unavailable")
                return
            self.client = genai.Client()
            self.available = True
            logger.debug(f"[EMBEDDING] Service ready (model={self.model})")
        except Exception as e:
            logger.warning(f"[EMBEDDING] Failed to initialize: {e}")
            return

        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, List[float]]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"[EMBEDDING] Cache load failed: {e}, starting fresh")
        return {}

    def _save_cache(self):
        self.cache_file.parent.mkdir(exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self._cache, f)

    def _get_embedding_text(self, candidate: dict) -> str:
        idea = candidate.get("idea", "") or ""
        code = candidate.get("code", "") or ""
        text = f"{idea}\n\n{code}" if idea else code
        # Truncate to ~8000 chars for token limits
        return text[:8000]

    def _get_code_hash(self, candidate: dict) -> str:
        meta = candidate.get("metadata", {})
        if isinstance(meta, dict) and meta.get("code_hash"):
            return meta["code_hash"]
        code = candidate.get("code", "") or ""
        return hashlib.sha256(code.encode()).hexdigest()

    def _fetch_embeddings_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=texts
            )
            return [emb.values for emb in result.embeddings]
        except Exception as e:
            logger.warning(f"[EMBEDDING] API call failed: {e}")
            return None

    def _pca_2d(self, vectors: List[List[float]]) -> List[Tuple[float, float]]:
        X = np.array(vectors, dtype=np.float64)
        n = X.shape[0]
        if n <= 1:
            return [(0.0, 0.0)] * n
        # Center
        X_centered = X - X.mean(axis=0)
        # SVD-based PCA
        U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
        # Project onto top-2 components
        k = min(2, Vt.shape[0])
        projected = X_centered @ Vt[:k].T
        if k == 1:
            return [(float(projected[i, 0]), 0.0) for i in range(n)]
        return [(float(projected[i, 0]), float(projected[i, 1])) for i in range(n)]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _get_embeddings_for_candidates(
        self, candidates: List[dict]
    ) -> Optional[Dict[Any, np.ndarray]]:
        """Fetch embeddings (from cache or API) for a list of candidates.

        Returns {candidate_id: np.ndarray} or None on API failure.
        """
        hashes = [self._get_code_hash(c) for c in candidates]
        texts_to_fetch = []
        indices_to_fetch = []
        for i, h in enumerate(hashes):
            if h not in self._cache:
                texts_to_fetch.append(self._get_embedding_text(candidates[i]))
                indices_to_fetch.append(i)

        if texts_to_fetch:
            new_vectors = self._fetch_embeddings_batch(texts_to_fetch)
            if new_vectors is None:
                return None
            for idx, vec in zip(indices_to_fetch, new_vectors):
                self._cache[hashes[idx]] = vec
            self._save_cache()

        return {
            c.get("candidate_id", i): np.array(self._cache[hashes[i]], dtype=np.float64)
            for i, c in enumerate(candidates)
        }

    def compute_population_diversity(self, population: List[dict]) -> Optional[dict]:
        """Compute embedding-based diversity metrics for the population.

        Returns dict with:
          avg_diversity: float — mean pairwise cosine distance across all pairs
          per_candidate: dict[candidate_id -> float] — each candidate's min distance to any other
          embeddings: dict[candidate_id -> np.ndarray] — raw embedding vectors
        Returns None if the service is unavailable or population has fewer than 2 members.
        """
        if not self.available or len(population) < 2:
            return None

        embeddings = self._get_embeddings_for_candidates(population)
        if embeddings is None:
            return None

        ids = list(embeddings.keys())
        vecs = [embeddings[cid] for cid in ids]
        n = len(vecs)

        pairwise_dists: List[float] = []
        min_dist: Dict[Any, float] = {cid: float("inf") for cid in ids}

        for a in range(n):
            for b in range(a + 1, n):
                sim = self._cosine_similarity(vecs[a], vecs[b])
                dist = 1.0 - sim  # cosine distance ∈ [0, 2]
                pairwise_dists.append(dist)
                if dist < min_dist[ids[a]]:
                    min_dist[ids[a]] = dist
                if dist < min_dist[ids[b]]:
                    min_dist[ids[b]] = dist

        for cid in ids:
            if min_dist[cid] == float("inf"):
                min_dist[cid] = 0.0

        return {
            "avg_diversity": float(np.mean(pairwise_dists)) if pairwise_dists else 0.0,
            "per_candidate": min_dist,
            "embeddings": embeddings,
        }

    def get_similarity_to_population(self, candidate: dict, population: List[dict]) -> float:
        """Return the maximum cosine similarity of *candidate* to any member of *population*.

        Returns 0.0 (no rejection) if the service is unavailable.
        """
        if not self.available or not population:
            return 0.0

        h = self._get_code_hash(candidate)
        if h not in self._cache:
            vecs = self._fetch_embeddings_batch([self._get_embedding_text(candidate)])
            if vecs is None:
                return 0.0
            self._cache[h] = vecs[0]
            self._save_cache()

        new_vec = np.array(self._cache[h], dtype=np.float64)

        pop_embeddings = self._get_embeddings_for_candidates(population)
        if pop_embeddings is None:
            return 0.0

        max_sim = 0.0
        for vec in pop_embeddings.values():
            sim = self._cosine_similarity(new_vec, vec)
            if sim > max_sim:
                max_sim = sim
        return max_sim

    def compute_2d_embeddings(self, population: List[Dict[str, Any]]) -> Optional[List[dict]]:
        """Compute 2D PCA-projected embeddings for the population.

        Returns list of dicts with keys: x, y, Strategy Cluster, Fitness, candidate_id, idea.
        Returns None if embedding is unavailable (caller should fall back).
        """
        if not self.available or not population:
            return None

        # Separate cached vs uncached
        hashes = [self._get_code_hash(c) for c in population]
        texts_to_fetch = []
        indices_to_fetch = []

        for i, h in enumerate(hashes):
            if h not in self._cache:
                texts_to_fetch.append(self._get_embedding_text(population[i]))
                indices_to_fetch.append(i)

        # Batch-fetch uncached embeddings
        if texts_to_fetch:
            new_vectors = self._fetch_embeddings_batch(texts_to_fetch)
            if new_vectors is None:
                return None
            for idx, vec in zip(indices_to_fetch, new_vectors):
                self._cache[hashes[idx]] = vec
            self._save_cache()

        # Assemble full matrix in population order
        all_vectors = [self._cache[h] for h in hashes]

        # PCA project to 2D
        points_2d = self._pca_2d(all_vectors)

        # Build result
        result = []
        for i, (x, y) in enumerate(points_2d):
            c = population[i]
            result.append({
                "x": x,
                "y": y,
                "Strategy Cluster": str(c.get("mutation_type", "Initial")),
                "Fitness": c.get("fitness", 0.0),
                "candidate_id": c.get("candidate_id"),
                "idea": (c.get("idea", "") or "")[:120],
            })

        return result
