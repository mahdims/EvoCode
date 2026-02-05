"""
Fitness Aggregator

Computes a scalar fitness value from multi-score EvalResults.
Used as a fallback when an evaluator's calculate_fitness() returns None.
"""

from typing import Dict, List, Optional
from loguru import logger

from base_evaluator import EvalResult


class FitnessAggregator:
    """Aggregates multi-score evaluation results into a scalar fitness.

    Supports three aggregation methods:
    - "mean": Average of all score means across instances (default)
    - "weighted": Weighted average using score_weights
    - "primary": Use only the primary_score's mean
    """

    def __init__(self,
                 method: str = "mean",
                 score_weights: Optional[Dict[str, float]] = None,
                 primary_score: Optional[str] = None):
        """Initialize fitness aggregator.

        Args:
            method: Aggregation method ("mean", "weighted", or "primary")
            score_weights: Weights per score name for "weighted" method
            primary_score: Score name to use for "primary" method
        """
        if method not in ("mean", "weighted", "primary"):
            raise ValueError(f"Unknown aggregation method: {method!r}. "
                             f"Must be 'mean', 'weighted', or 'primary'.")
        self.method = method
        self.score_weights = score_weights or {}
        self.primary_score = primary_score

    def aggregate(self, eval_results: List[EvalResult]) -> float:
        """Compute scalar fitness from evaluation results.

        Args:
            eval_results: List of EvalResult from an evaluator

        Returns:
            Scalar fitness value (higher is better)
        """
        if not eval_results:
            return -float('inf')

        successful = [r for r in eval_results if r.success]
        if not successful:
            return -float('inf')

        # Collect all score names present in results
        all_score_names = set()
        for r in successful:
            all_score_names.update(r.scores.keys())

        if not all_score_names:
            return -float('inf')

        # Compute mean per score across successful instances
        score_means: Dict[str, float] = {}
        for name in all_score_names:
            values = [r.scores.get(name, 0.0) for r in successful]
            score_means[name] = sum(values) / len(eval_results)

        if self.method == "primary":
            key = self.primary_score
            if key is None:
                # Fall back to first available score
                key = next(iter(all_score_names))
                logger.debug(f"[AGGREGATOR] No primary_score set, using '{key}'")
            if key not in score_means:
                logger.warning(f"[AGGREGATOR] primary_score '{key}' not found in results")
                return -float('inf')
            return score_means[key]

        elif self.method == "weighted":
            if not self.score_weights:
                logger.warning("[AGGREGATOR] No score_weights provided for 'weighted' method, "
                               "falling back to equal weights")
                return sum(score_means.values()) / len(score_means)

            total = 0.0
            weight_sum = 0.0
            for name, weight in self.score_weights.items():
                if name in score_means:
                    total += weight * score_means[name]
                    weight_sum += weight
            if weight_sum == 0:
                return -float('inf')
            return total / weight_sum

        else:  # "mean"
            return sum(score_means.values()) / len(score_means)
