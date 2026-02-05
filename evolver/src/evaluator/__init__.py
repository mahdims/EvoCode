"""
Evaluator Package

Pluggable evaluation system for the evolution loop.
Re-exports key classes for convenient imports.
"""

from .base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from .ails_evaluator import AILSEvaluator
from .fitness_aggregator import FitnessAggregator
from .pareto_selection import (
    compute_candidate_score_vector,
    pareto_select,
    pareto_tournament,
)
from .mock_multi_score_evaluator import MockMultiScoreEvaluator
