"""
Base Evaluator Interface

Defines the abstract interface and data classes for pluggable evaluators.
Evaluators handle smoke testing and evaluation of candidate strategies,
returning structured results that support single or multi-score outputs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalResult:
    """Result of evaluating a candidate on a single test instance."""
    instance: str                           # test case identifier
    success: bool
    scores: Dict[str, float]                # named scores (e.g. {"improvement": 0.013})
    metadata: Dict[str, Any] = field(default_factory=dict)  # extra info (initial_cost, final_cost, etc.)
    error: Optional[str] = None


@dataclass
class SmokeTestResult:
    """Result of a quick smoke test on a candidate."""
    success: bool
    output: str = ""
    runtime: float = 0.0
    exit_code: int = 0


class BaseEvaluator(ABC):
    """Abstract base class for candidate evaluators.

    Subclasses must implement smoke_test() and evaluate().
    Optionally override get_score_names() and calculate_fitness()
    for custom scoring behavior.
    """

    @abstractmethod
    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Run a quick validation test on a candidate.

        Args:
            artifact_path: Path to the compiled artifact (e.g. JAR file)
            candidate_name: Name/class of the candidate to test

        Returns:
            SmokeTestResult with success status and details
        """

    @abstractmethod
    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        """Evaluate a candidate on all target instances.

        Args:
            artifact_path: Path to the compiled artifact (e.g. JAR file)
            candidate_name: Name/class of the candidate to evaluate

        Returns:
            List of EvalResult, one per test instance
        """

    def get_score_names(self) -> List[str]:
        """Return the names of scores produced by this evaluator.

        Default returns ["fitness"]. Override to declare multi-score outputs.
        """
        return ["fitness"]

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        """Calculate a scalar fitness from evaluation results.

        Return a float to provide a custom fitness calculation.
        Return None to delegate to the FitnessAggregator.

        Args:
            results: List of EvalResult from evaluate()

        Returns:
            Scalar fitness value, or None to use aggregator
        """
        return None

    def get_instances(self) -> List[str]:
        """Return the list of test instances this evaluator runs on.

        Override to expose the evaluator's instance list so callers
        (e.g. EvolutionLoop) don't need to track instances separately.
        """
        return []
