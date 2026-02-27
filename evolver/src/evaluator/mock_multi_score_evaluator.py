"""
Mock Multi-Score Evaluator

A demonstration evaluator that returns two scores:
- accuracy: simulated solution quality (higher is better)
- memory_efficiency: simulated memory usage score (higher is better, i.e., less memory)

This evaluator is for testing the pluggable evaluator system with multi-objective optimization.
It does NOT run actual AILS - it generates synthetic scores based on code analysis.
"""

import hashlib
import random
import re
from typing import List

from core.base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult


class MockMultiScoreEvaluator(BaseEvaluator):
    """Mock evaluator returning accuracy and memory_efficiency scores."""

    def __init__(self,
                 target_instances: List[str] = None,
                 seed: int = 42,
                 base_accuracy: float = 0.7,
                 base_memory: float = 0.8,
                 **kwargs):
        self.target_instances = target_instances or ["instance_1", "instance_2"]
        self.seed = seed
        self.base_accuracy = base_accuracy
        self.base_memory = base_memory
        self._rng = random.Random(seed)

    def _analyze_code(self, artifact_path: str) -> dict:
        path_hash = hashlib.md5(artifact_path.encode()).hexdigest()
        hash_val = int(path_hash[:8], 16) / (16 ** 8)
        complexity_factor = hash_val
        return {
            "accuracy_modifier": complexity_factor * 0.3,
            "memory_modifier": -complexity_factor * 0.2,
            "hash_val": hash_val,
        }

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        if "FAIL" in candidate_name.upper():
            return SmokeTestResult(success=False,
                                   output="Mock failure: candidate name contains FAIL",
                                   runtime=0.1, exit_code=1)
        return SmokeTestResult(success=True,
                               output=f"Mock smoke test passed for {candidate_name}",
                               runtime=0.5, exit_code=0)

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        analysis = self._analyze_code(artifact_path)
        results = []
        for i, instance in enumerate(self.target_instances):
            instance_seed = hash(f"{artifact_path}_{instance}") % 10000
            instance_rng = random.Random(instance_seed)
            accuracy = max(0.0, min(1.0, self.base_accuracy + analysis["accuracy_modifier"]
                                    + instance_rng.gauss(0, 0.05)))
            memory_eff = max(0.0, min(1.0, self.base_memory + analysis["memory_modifier"]
                                      + instance_rng.gauss(0, 0.03)))
            results.append(EvalResult(
                instance=instance,
                success=True,
                scores={"accuracy": accuracy, "memory_efficiency": memory_eff},
                metadata={"candidate_name": candidate_name, "instance_index": i,
                          "hash_val": analysis["hash_val"]},
            ))
        return results

    def get_score_names(self) -> List[str]:
        return ["accuracy", "memory_efficiency"]

    def calculate_fitness(self, results: List[EvalResult]) -> None:
        return None
