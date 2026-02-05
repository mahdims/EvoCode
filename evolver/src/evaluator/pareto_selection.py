"""
Pareto Selection (NSGA-II)

Multi-objective selection using non-dominated sorting and crowding distance.
Used when selection_mode is "pareto" and candidates have multiple scores.
"""

import random
from typing import Dict, List

from loguru import logger


def compute_candidate_score_vector(eval_results, score_names: List[str]) -> Dict[str, float]:
    """Compute mean score vector for a candidate from its eval results.

    Args:
        eval_results: List of EvalResult objects
        score_names: Score names to extract

    Returns:
        Dict mapping score name to mean value across successful instances
    """
    from .base_evaluator import EvalResult

    successful = [r for r in eval_results if r.success]
    if not successful:
        return {name: -float('inf') for name in score_names}

    total = len(successful)
    vector = {}
    for name in score_names:
        values = [r.scores.get(name, 0.0) for r in successful]
        vector[name] = sum(values) / total
    return vector


def dominates(a: Dict[str, float], b: Dict[str, float],
              maximize: Dict[str, bool] = None) -> bool:
    """Check if solution a dominates solution b.

    a dominates b if a is at least as good in all objectives
    and strictly better in at least one.

    Args:
        a: Score vector for candidate a
        b: Score vector for candidate b
        maximize: Dict mapping score name to whether to maximize (default: all True)

    Returns:
        True if a dominates b
    """
    if maximize is None:
        maximize = {k: True for k in a}

    at_least_as_good = True
    strictly_better = False

    for key in a:
        val_a = a[key]
        val_b = b[key]
        if maximize.get(key, True):
            if val_a < val_b:
                at_least_as_good = False
                break
            if val_a > val_b:
                strictly_better = True
        else:
            if val_a > val_b:
                at_least_as_good = False
                break
            if val_a < val_b:
                strictly_better = True

    return at_least_as_good and strictly_better


def fast_non_dominated_sort(candidates: List[Dict],
                            score_names: List[str],
                            maximize: Dict[str, bool] = None) -> List[List[int]]:
    """NSGA-II fast non-dominated sorting.

    Args:
        candidates: List of candidate dicts, each must have "score_vector"
        score_names: Score names to consider
        maximize: Dict mapping score name to maximize flag

    Returns:
        List of fronts, where each front is a list of candidate indices
    """
    n = len(candidates)
    if n == 0:
        return []

    # Extract score vectors
    vectors = []
    for c in candidates:
        sv = c.get("score_vector", {})
        vectors.append({name: sv.get(name, -float('inf')) for name in score_names})

    # Domination counts and dominated sets
    dominated_by_count = [0] * n  # number of solutions dominating i
    dominates_set = [[] for _ in range(n)]  # solutions dominated by i

    first_front = []

    for i in range(n):
        for j in range(i + 1, n):
            if dominates(vectors[i], vectors[j], maximize):
                dominates_set[i].append(j)
                dominated_by_count[j] += 1
            elif dominates(vectors[j], vectors[i], maximize):
                dominates_set[j].append(i)
                dominated_by_count[i] += 1

        if dominated_by_count[i] == 0:
            first_front.append(i)

    fronts = [first_front]
    current_front = first_front

    while current_front:
        next_front = []
        for i in current_front:
            for j in dominates_set[i]:
                dominated_by_count[j] -= 1
                if dominated_by_count[j] == 0:
                    next_front.append(j)
        if next_front:
            fronts.append(next_front)
        current_front = next_front

    return fronts


def crowding_distance(candidates: List[Dict],
                      front_indices: List[int],
                      score_names: List[str]) -> Dict[int, float]:
    """Compute crowding distance for candidates in a front.

    Args:
        candidates: Full candidate list
        front_indices: Indices of candidates in this front
        score_names: Score names to use

    Returns:
        Dict mapping candidate index to crowding distance
    """
    n = len(front_indices)
    if n == 0:
        return {}

    distances = {i: 0.0 for i in front_indices}

    if n <= 2:
        for i in front_indices:
            distances[i] = float('inf')
        return distances

    for score_name in score_names:
        # Sort front by this score
        sorted_indices = sorted(
            front_indices,
            key=lambda i: candidates[i].get("score_vector", {}).get(score_name, -float('inf'))
        )

        # Boundary points get infinite distance
        distances[sorted_indices[0]] = float('inf')
        distances[sorted_indices[-1]] = float('inf')

        # Score range for normalization
        min_val = candidates[sorted_indices[0]].get("score_vector", {}).get(score_name, 0)
        max_val = candidates[sorted_indices[-1]].get("score_vector", {}).get(score_name, 0)
        score_range = max_val - min_val

        if score_range == 0:
            continue

        # Interior points
        for k in range(1, n - 1):
            prev_val = candidates[sorted_indices[k - 1]].get("score_vector", {}).get(score_name, 0)
            next_val = candidates[sorted_indices[k + 1]].get("score_vector", {}).get(score_name, 0)
            distances[sorted_indices[k]] += (next_val - prev_val) / score_range

    return distances


def pareto_select(population: List[Dict],
                  target_size: int,
                  score_names: List[str],
                  maximize: Dict[str, bool] = None) -> List[Dict]:
    """Select candidates using NSGA-II non-dominated sorting + crowding distance.

    Args:
        population: List of candidate dicts with "score_vector" key
        target_size: Number of candidates to select
        score_names: Score names for multi-objective comparison
        maximize: Dict mapping score name to maximize flag

    Returns:
        Selected candidates (list of dicts)
    """
    if len(population) <= target_size:
        return list(population)

    fronts = fast_non_dominated_sort(population, score_names, maximize)

    selected = []
    for front in fronts:
        if len(selected) + len(front) <= target_size:
            selected.extend(front)
        else:
            # Need partial selection from this front using crowding distance
            remaining = target_size - len(selected)
            distances = crowding_distance(population, front, score_names)
            # Sort by crowding distance (descending) - prefer diverse solutions
            sorted_front = sorted(front, key=lambda i: distances.get(i, 0), reverse=True)
            selected.extend(sorted_front[:remaining])
            break

    logger.debug(f"[PARETO] Selected {len(selected)}/{len(population)} candidates "
                 f"across {len(fronts)} fronts")

    return [population[i] for i in selected]


def pareto_tournament(population: List[Dict],
                      tournament_size: int,
                      score_names: List[str],
                      maximize: Dict[str, bool] = None) -> Dict:
    """Tournament selection using Pareto dominance.

    Selects tournament_size candidates randomly, returns the one in the
    best (lowest-numbered) Pareto front. Ties broken by crowding distance.

    Args:
        population: List of candidate dicts with "score_vector" key
        tournament_size: Number of candidates in tournament
        score_names: Score names for comparison
        maximize: Dict mapping score name to maximize flag

    Returns:
        Selected candidate dict
    """
    actual_size = min(tournament_size, len(population))
    contestants = random.sample(population, actual_size)

    if len(contestants) == 1:
        return contestants[0]

    fronts = fast_non_dominated_sort(contestants, score_names, maximize)
    first_front = fronts[0] if fronts else [0]

    if len(first_front) == 1:
        return contestants[first_front[0]]

    # Tie-break with crowding distance
    distances = crowding_distance(contestants, first_front, score_names)
    best_idx = max(first_front, key=lambda i: distances.get(i, 0))
    return contestants[best_idx]
