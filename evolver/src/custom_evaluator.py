"""
Custom Evaluator for: accuracy, memory_usage
Auto-generated for EvoCode evolution loop.

Measures:
- accuracy: Solution quality improvement ratio (higher is better)
- memory_usage: Peak JVM heap usage in MB (lower is better)
"""

import re
from typing import List

from base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from evaluator import Evaluator


class AccuracyMemoryEvaluator(BaseEvaluator):
    """Evaluator measuring accuracy (solution quality) and memory_usage (peak heap)."""

    def __init__(self,
                 ails_jar: str = None,
                 data_dir: str = None,
                 warmstart_dir: str = None,
                 temp_dir: str = None,
                 target_instances: List[str] = None,
                 max_workers: int = None,
                 seed: int = 42,
                 iterations: int = 10000,
                 timeout: int = 3600,
                 **kwargs):
        """Initialize evaluator wrapping AILS for accuracy + memory measurement."""
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

    @staticmethod
    def _extract_peak_heap_mb(output: str) -> float:
        """Extract peak heap usage from JVM GC log output.

        Parses GC log lines like:
            [GC (Allocation Failure)  65536K->12345K(251392K), 0.012 secs]
        and returns the max post-GC heap in MB. Falls back to 0.0 if
        no GC output is found.
        """
        # Match patterns like "-> 12345K(" in GC log lines
        post_gc_sizes = re.findall(r'->\s*(\d+)K\(', output)
        if post_gc_sizes:
            peak_kb = max(int(s) for s in post_gc_sizes)
            return peak_kb / 1024.0
        return 0.0

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Run AILS smoke test."""
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
        """Evaluate candidate, measuring both accuracy and memory_usage."""
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
            # Parse peak heap from AILS output (if GC logging was enabled)
            output = r.get("output", "")
            peak_heap_mb = self._extract_peak_heap_mb(output)

            scores = {
                "accuracy": r.get("improvement", 0.0),
                "memory_usage": peak_heap_mb,
            }
            metadata = {
                "initial_cost": r.get("initial_cost", float('inf')),
                "final_cost": r.get("final_cost", float('inf')),
                "runtime": r.get("runtime", 0.0),
                "exit_code": r.get("exit_code"),
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
        """Return the metric names: accuracy and memory_usage."""
        return ["accuracy", "memory_usage"]

    def calculate_fitness(self, results: List[EvalResult]) -> None:
        """Return None to use fitness_aggregation from config."""
        return None
