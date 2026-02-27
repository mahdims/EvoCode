"""
Custom Evaluator for: accuracy, memory_usage
Auto-generated for EvoCode evolution loop.

Measures:
- accuracy: Solution quality improvement ratio (higher is better)
- memory_usage: Peak JVM heap usage in MB (lower is better)
"""

import re
from pathlib import Path
from typing import List

from core.base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from domains.ails_vrp.evaluator_stub import Evaluator


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
        # Resolve AILS paths from config when not provided explicitly
        config = kwargs.get("config") or {}
        if ails_jar is None or data_dir is None or warmstart_dir is None:
            _evolver_root = Path(__file__).parent.parent.parent
            _raw = Path(config.get("source_code_root", "../AILS"))
            _ails_root = _raw if _raw.is_absolute() else (_evolver_root / _raw).resolve()
            _dataset_dir = config.get("dataset_dir", "Vrp_Set_X")
            if ails_jar is None:
                ails_jar = str(_ails_root / "AILSII.jar")
            if data_dir is None:
                data_dir = str(_ails_root / "data" / _dataset_dir)
            if warmstart_dir is None:
                warmstart_dir = str(_ails_root / "warm_start" / _dataset_dir)

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

    @staticmethod
    def _extract_peak_heap_mb(output: str) -> float:
        """Extract peak heap usage from JVM GC log output."""
        post_gc_sizes = re.findall(r'->\s*(\d+)K\(', output)
        if post_gc_sizes:
            peak_kb = max(int(s) for s in post_gc_sizes)
            return peak_kb / 1024.0
        return 0.0

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        result = self._inner.smoke_test(
            jar_path=artifact_path, class_name=candidate_name, seed=self.seed)
        return SmokeTestResult(
            success=result["success"], output=result.get("output", ""),
            runtime=result.get("runtime", 0.0), exit_code=result.get("exit_code", 0))

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        raw_results = self._inner.evaluate_endgame_parallel(
            jar_path=artifact_path, class_name=candidate_name,
            instances=self.target_instances, seed=self.seed,
            iterations=self.iterations, timeout=self.timeout,
            max_workers=self.max_workers)

        eval_results = []
        for r in raw_results:
            output = r.get("output", "")
            peak_heap_mb = self._extract_peak_heap_mb(output)
            eval_results.append(EvalResult(
                instance=r.get("instance", "unknown"),
                success=r.get("success", False),
                scores={"accuracy": r.get("improvement", 0.0),
                        "memory_usage": peak_heap_mb},
                metadata={"initial_cost": r.get("initial_cost", float('inf')),
                          "final_cost": r.get("final_cost", float('inf')),
                          "runtime": r.get("runtime", 0.0),
                          "exit_code": r.get("exit_code")},
                error=r.get("error"),
            ))
        return eval_results

    def get_score_names(self) -> List[str]:
        return ["accuracy", "memory_usage"]

    def calculate_fitness(self, results: List[EvalResult]) -> None:
        return None
