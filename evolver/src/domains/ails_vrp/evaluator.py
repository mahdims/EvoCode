"""
AILS Evaluator

Wraps the AILS evaluation harness to conform to the BaseEvaluator interface.
"""

from typing import List, Optional

from loguru import logger

from core.base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from .evaluator_stub import Evaluator


class AILSEvaluator(BaseEvaluator):
    """Adapter wrapping the AILS Evaluator as a BaseEvaluator."""

    def __init__(self,
                 ails_jar: str = "AILS/AILSII.jar",
                 data_dir: str = "AILS/data/XL",
                 warmstart_dir: str = "AILS/warm_start/XL",
                 temp_dir: str = None,
                 target_instances: List[str] = None,
                 max_workers: int = None,
                 seed: int = 42,
                 iterations: int = 10000,
                 timeout: int = 3600,
                 smoke_test_instance: Optional[str] = None):
        self._inner = Evaluator(
            ails_jar=ails_jar,
            data_dir=data_dir,
            warmstart_dir=warmstart_dir,
            temp_dir=temp_dir,
        )
        self.target_instances = target_instances or []
        self.max_workers = max_workers
        self.seed = seed
        self.iterations = iterations
        self.timeout = timeout
        self.smoke_test_instance = smoke_test_instance

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        result = self._inner.smoke_test(
            jar_path=artifact_path,
            class_name=candidate_name,
            seed=self.seed,
            instance=self.smoke_test_instance,
        )
        return SmokeTestResult(
            success=result["success"],
            output=result.get("output", ""),
            runtime=result.get("runtime", 0.0),
            exit_code=result.get("exit_code", 0),
        )

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        raw_results = self._inner.evaluate_endgame_parallel(
            jar_path=artifact_path,
            class_name=candidate_name,
            instances=self.target_instances,
            seed=self.seed,
            iterations=self.iterations,
            timeout=self.timeout,
            max_workers=self.max_workers,
        )

        return [
            EvalResult(
                instance=r.get("instance", "unknown"),
                success=r.get("success", False),
                scores={"improvement": r.get("improvement", 0.0)},
                metadata={
                    "initial_cost": r.get("initial_cost", float('inf')),
                    "final_cost": r.get("final_cost", float('inf')),
                    "runtime": r.get("runtime", 0.0),
                    "exit_code": r.get("exit_code"),
                },
                error=r.get("error"),
            )
            for r in raw_results
        ]

    def get_score_names(self) -> List[str]:
        return ["improvement"]

    def get_instances(self) -> List[str]:
        return self.target_instances

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        """Average improvement across all results (not just successful)."""
        if not results:
            return -float('inf')
        successful = [r for r in results if r.success]
        if not successful:
            return -float('inf')
        total = sum(r.scores.get("improvement", 0.0) for r in successful)
        return total / len(results)
