"""
Population Survival Selection

Provides survival_select() — the single entry point used by the evolution loop
to trim the population at the end of each generation.

Two strategies:
  - Pareto (NSGA-II): multi-objective mode with score vectors
  - Quality-Diversity (greedy max-min): scalar mode, keeps top elites then fills
    remaining slots with the most structurally unique candidates in embedding space,
    falling back to pure elitism when embeddings are unavailable.
"""

from typing import Dict, List

from loguru import logger

from population.embedding_service import EmbeddingService
from evaluation import pareto_select


def _quality_diversity_select(
    population: List[dict],
    population_size: int,
    elite_size: int,
    embedding_service: EmbeddingService,
) -> List[dict]:
    """Greedy max-min quality-diversity selection.

    Guarantees the top `elite_size` candidates by fitness, then fills remaining
    slots by iteratively picking the candidate most distant (in embedding space)
    from the already-selected set. Falls back to pure elitism if the embedding
    service is unavailable.

    Assumes `population` is already sorted by fitness descending.
    """
    if len(population) <= population_size:
        return population

    diversity_info = embedding_service.compute_population_diversity(population)
    if diversity_info is None:
        # Embedding service unavailable — pure elitism
        return population[:population_size]

    embeddings = diversity_info["embeddings"]

    elites = [c for c in population[:elite_size] if c["candidate_id"] in embeddings]
    selected = list(elites)
    selected_ids = {c["candidate_id"] for c in selected}
    pool = [
        c for c in population
        if c["candidate_id"] not in selected_ids and c["candidate_id"] in embeddings
    ]

    while len(selected) < population_size and pool:
        selected_vecs = [embeddings[c["candidate_id"]] for c in selected]
        best_cand = None
        best_min_dist = -1.0
        for cand in pool:
            vec = embeddings[cand["candidate_id"]]
            if not selected_vecs:
                min_dist = 1.0
            else:
                sims = [embedding_service._cosine_similarity(vec, sv) for sv in selected_vecs]
                min_dist = 1.0 - max(sims)
            if min_dist > best_min_dist or (
                min_dist == best_min_dist
                and (best_cand is None or cand["fitness"] > best_cand["fitness"])
            ):
                best_min_dist = min_dist
                best_cand = cand
        if best_cand is None:
            break
        selected.append(best_cand)
        selected_ids.add(best_cand["candidate_id"])
        pool.remove(best_cand)

    # Fill any remaining slots (candidates missing from embeddings dict) by fitness
    if len(selected) < population_size:
        leftover = [c for c in population if c["candidate_id"] not in selected_ids]
        leftover.sort(key=lambda x: x["fitness"], reverse=True)
        selected.extend(leftover[: population_size - len(selected)])

    selected.sort(key=lambda x: x["fitness"], reverse=True)
    return selected


def survival_select(
    population: List[dict],
    population_size: int,
    elite_size: int,
    selection_mode: str,
    score_names: List[str],
    maximize_scores: Dict[str, bool],
    embedding_service: EmbeddingService,
) -> List[dict]:
    """Select survivors for the next generation.

    Args:
        population: Current candidates (will be sorted in place).
        population_size: Target size after selection.
        elite_size: Number of top-fitness candidates guaranteed in scalar mode.
        selection_mode: "pareto" enables NSGA-II; any other value uses quality-diversity.
        score_names: Objective names (used in Pareto mode).
        maximize_scores: Per-objective maximization flags (used in Pareto mode).
        embedding_service: Used for quality-diversity selection.

    Returns:
        Surviving population sorted by fitness descending.
    """
    population.sort(key=lambda x: x["fitness"], reverse=True)

    if (
        selection_mode == "pareto"
        and len(score_names) > 1
        and any(c.get("score_vector") for c in population)
    ):
        survivors = pareto_select(population, population_size, score_names, maximize_scores)
        survivors.sort(key=lambda x: x["fitness"], reverse=True)
        logger.debug("[SELECTION] Used Pareto (NSGA-II) selection")
        return survivors

    survivors = _quality_diversity_select(population, population_size, elite_size, embedding_service)
    logger.debug("[SELECTION] Used quality-diversity (greedy max-min) selection")
    return survivors
