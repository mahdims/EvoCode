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

from .base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult


class MockMultiScoreEvaluator(BaseEvaluator):
    """Mock evaluator returning accuracy and memory_efficiency scores."""

    def __init__(self,
                 target_instances: List[str] = None,
                 seed: int = 42,
                 base_accuracy: float = 0.7,
                 base_memory: float = 0.8,
                 **kwargs):
        """Initialize mock evaluator.

        Args:
            target_instances: List of instance names to "evaluate"
            seed: Random seed for reproducibility
            base_accuracy: Base accuracy score (0-1)
            base_memory: Base memory efficiency score (0-1)
            **kwargs: Ignored (for compatibility with evaluator_loader)
        """
        self.target_instances = target_instances or ["instance_1", "instance_2"]
        self.seed = seed
        self.base_accuracy = base_accuracy
        self.base_memory = base_memory
        self._rng = random.Random(seed)

    def _analyze_code(self, artifact_path: str) -> dict:
        """Analyze code to generate deterministic but varied scores.

        Uses code hash and simple heuristics to generate scores that:
        - Are deterministic for the same code
        - Vary between different candidates
        - Have some trade-off between accuracy and memory
        """
        # Use artifact path hash for deterministic randomness
        path_hash = hashlib.md5(artifact_path.encode()).hexdigest()
        hash_val = int(path_hash[:8], 16) / (16 ** 8)  # 0-1 range

        # Read JAR path to estimate code complexity (if accessible)
        # For mock purposes, use hash to simulate variation
        complexity_factor = hash_val

        # Simulate trade-off: more complex code = higher accuracy but worse memory
        accuracy_boost = complexity_factor * 0.3  # Up to +0.3 accuracy
        memory_penalty = complexity_factor * 0.2  # Up to -0.2 memory efficiency

        return {
            "accuracy_modifier": accuracy_boost,
            "memory_modifier": -memory_penalty,
            "hash_val": hash_val,
        }

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Mock smoke test - always passes unless candidate_name contains 'FAIL'."""
        if "FAIL" in candidate_name.upper():
            return SmokeTestResult(
                success=False,
                output="Mock failure: candidate name contains FAIL",
                runtime=0.1,
                exit_code=1
            )

        return SmokeTestResult(
            success=True,
            output=f"Mock smoke test passed for {candidate_name}",
            runtime=0.5,
            exit_code=0
        )

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        """Evaluate candidate on all target instances.

        Returns synthetic accuracy and memory_efficiency scores.
        """
        analysis = self._analyze_code(artifact_path)
        results = []

        for i, instance in enumerate(self.target_instances):
            # Add per-instance variation using instance index
            instance_seed = hash(f"{artifact_path}_{instance}") % 10000
            instance_rng = random.Random(instance_seed)

            # Calculate scores with some randomness
            accuracy = self.base_accuracy + analysis["accuracy_modifier"]
            accuracy += instance_rng.gauss(0, 0.05)  # Add noise
            accuracy = max(0.0, min(1.0, accuracy))  # Clamp to [0, 1]

            memory_eff = self.base_memory + analysis["memory_modifier"]
            memory_eff += instance_rng.gauss(0, 0.03)  # Add noise
            memory_eff = max(0.0, min(1.0, memory_eff))  # Clamp to [0, 1]

            results.append(EvalResult(
                instance=instance,
                success=True,
                scores={
                    "accuracy": accuracy,
                    "memory_efficiency": memory_eff,
                },
                metadata={
                    "candidate_name": candidate_name,
                    "instance_index": i,
                    "hash_val": analysis["hash_val"],
                }
            ))

        return results

    def get_score_names(self) -> List[str]:
        """Return the two score names this evaluator produces."""
        return ["accuracy", "memory_efficiency"]

    def calculate_fitness(self, results: List[EvalResult]) -> None:
        """Return None to delegate to FitnessAggregator.

        This allows testing different aggregation methods (mean, weighted, primary).
        """
        return None
