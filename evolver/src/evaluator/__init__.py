"""
Evaluator Package — Backward-Compatibility Shim + Cross-Domain Utilities

The evaluator abstractions now live in:
  core.base_evaluator         → BaseEvaluator, EvalResult, SmokeTestResult
  domains.ails_vrp.evaluator  → AILSEvaluator

This file re-exports them for backward compatibility and also provides
cross-domain utilities that remain here: FitnessAggregator, pareto_selection,
MockMultiScoreEvaluator.
"""

from core.base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from domains.ails_vrp.evaluator import AILSEvaluator
from .fitness_aggregator import FitnessAggregator
from .pareto_selection import (
    compute_candidate_score_vector,
    pareto_select,
    pareto_tournament,
)
from .mock_multi_score_evaluator import MockMultiScoreEvaluator
