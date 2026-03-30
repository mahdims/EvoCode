"""
Evaluation package: base evaluator abstractions and cross-domain utilities.

Exports:
  BaseEvaluator, EvalResult, SmokeTestResult — base evaluation contracts
  AILSEvaluator                              — AILS VRP evaluator
  FitnessAggregator                          — multi-score → scalar fitness
  compute_candidate_score_vector, pareto_select, pareto_tournament — Pareto selection
  MockMultiScoreEvaluator                    — test double
"""

from .base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from domains.ails_vrp.evaluator import AILSEvaluator
from .fitness_aggregator import FitnessAggregator
from .pareto_selection import (
    compute_candidate_score_vector,
    pareto_select,
    pareto_tournament,
)
from .mock_multi_score_evaluator import MockMultiScoreEvaluator
