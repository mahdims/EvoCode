"""
AILS Evaluator Adapter

Wraps the existing Evaluator class to conform to the BaseEvaluator interface.
Preserves identical behavior to the original evaluation pipeline.
"""

from typing import List, Optional
from loguru import logger

from .base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from evaluator_stub import Evaluator


class AILSEvaluator(BaseEvaluator):
    """Adapter wrapping the existing AILS Evaluator as a BaseEvaluator."""

    def __init__(self,
                 ails_jar: str = "AILS/AILSII.jar",
                 data_dir: str = "AILS/data/XL",
                 warmstart_dir: str = "AILS/warm_start/XL",
                 temp_dir: str = "temp",
                 target_instances: List[str] = None,
                 max_workers: int = None,
                 seed: int = 42,
                 iterations: int = 10000,
                 timeout: int = 3600):
        """Initialize AILS evaluator adapter.

        Args:
            ails_jar: Path to AILS JAR
            data_dir: Directory containing instance files
            warmstart_dir: Directory containing warmstart solutions
            temp_dir: Directory for temporary output files
            target_instances: List of instance names for evaluation
            max_workers: Number of parallel workers for instance evaluation
            seed: Random seed for AILS
            iterations: Number of AILS iterations per evaluation
            timeout: Timeout per instance in seconds
        """
        self._inner = Evaluator(
            ails_jar=ails_jar,
            data_dir=data_dir,
            warmstart_dir=warmstart_dir,
            temp_dir=temp_dir
        )
        self.target_instances = target_instances or []
        self.max_workers = max_workers
        self.seed = seed
        self.iterations = iterations
        self.timeout = timeout

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Run AILS smoke test, wrapping result into SmokeTestResult."""
        result = self._inner.smoke_test(
            jar_path=artifact_path,
            class_name=candidate_name,
            seed=self.seed
        )
        return SmokeTestResult(
            success=result["success"],
            output=result.get("output", ""),
            runtime=result.get("runtime", 0.0),
            exit_code=result.get("exit_code", 0)
        )

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        """Evaluate using AILS parallel endgame evaluation.

        Delegates to the inner Evaluator.evaluate_endgame_parallel() and
        converts each result dict into an EvalResult.
        """
        raw_results = self._inner.evaluate_endgame_parallel(
            jar_path=artifact_path,
            class_name=candidate_name,
            instances=self.target_instances,
            seed=self.seed,
            iterations=self.iterations,
            timeout=self.timeout,
            max_workers=self.max_workers
        )

        eval_results = []
        for r in raw_results:
            scores = {"improvement": r.get("improvement", 0.0)}
            metadata = {
                "initial_cost": r.get("initial_cost", float('inf')),
                "final_cost": r.get("final_cost", float('inf')),
                "runtime": r.get("runtime", 0.0),
                "exit_code": r.get("exit_code", None),
            }
            eval_results.append(EvalResult(
                instance=r.get("instance", "unknown"),
                success=r.get("success", False),
                scores=scores,
                metadata=metadata,
                error=r.get("error")
            ))

        return eval_results

    def get_score_names(self) -> List[str]:
        return ["improvement"]

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        """Replicate original Evaluator.calculate_fitness() logic.

        Returns sum(successful improvements) / len(all results).
        """
        if not results:
            return -float('inf')

        successful = [r for r in results if r.success]
        if not successful:
            return -float('inf')

        total_improvement = sum(r.scores.get("improvement", 0.0) for r in successful)
        return total_improvement / len(results)
