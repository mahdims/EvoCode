---
name: evolve-evaluation-generate
description: Generate evaluator for the evolve-loop
---

# Evaluator Generator

When this subskill is invoked, generate a custom evaluator based on the selected evaluation metrics.

## Input
- `metrics`: List of metric names (e.g., ["latency", "memory_usage"])
- `selection_mode`: "scalar" or "pareto" (from evaluation-metric)

## Template

Generate an evaluator following this template based on `evolver/src/evaluator/base_evaluator.py`:

```python
"""
Custom Evaluator for: {metrics}
Auto-generated for EvoCode evolution loop.
"""

from typing import List
from evaluator import BaseEvaluator, EvalResult, SmokeTestResult


class CustomEvaluator(BaseEvaluator):
    """Evaluator measuring: {metrics}"""

    def __init__(self, target_instances=None, **kwargs):
        # target_instances is automatically passed from main config
        self.target_instances = target_instances or []
        # Add any custom initialization here

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Quick validation test - verify candidate can run."""
        # TODO: Implement smoke test logic
        # Return SmokeTestResult(success=True/False, output="...", runtime=0.0, exit_code=0)
        pass

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        """Evaluate candidate on all target instances."""
        results = []
        for instance in self.target_instances:
            # TODO: Run actual evaluation and measure metrics
            scores = {
                # Add one entry per metric, e.g.:
                # "latency": measured_latency,
                # "memory_usage": measured_memory,
            }
            results.append(EvalResult(
                instance=instance,
                success=True,  # Set False if evaluation failed
                scores=scores,
                metadata={}  # Optional: add extra info
            ))
        return results

    def get_score_names(self) -> List[str]:
        """Return the metric names this evaluator produces."""
        return [{metric_list}]  # e.g., ["latency", "memory_usage"]

    def calculate_fitness(self, results: List[EvalResult]) -> float:
        """Optional: Return None to use fitness_aggregation from config."""
        return None
```

## Generation Steps

1. **Understand the metrics**: For each metric, determine how to measure it:
   - `latency` → measure execution time
   - `memory_usage` → measure peak memory consumption
   - `accuracy` → measure correctness/test pass rate
   - Custom metrics → ask user for measurement approach

2. **Implement smoke_test()**: Quick check that the candidate can execute without errors

3. **Implement evaluate()**:
   - Run the candidate on each target instance
   - Measure all requested metrics
   - Return EvalResult with scores dict containing all metrics

4. **Set get_score_names()**: Return list of all metric names (must match keys in scores dict)

5. **Save the evaluator**: Save to `evolver/src/evaluator/custom_evaluator.py`

## Test

Create a simple test to verify the evaluator works:

```python
# Test the custom evaluator
from evaluator.custom_evaluator import CustomEvaluator

evaluator = CustomEvaluator(target_instances=["test_instance"])
print(f"Score names: {evaluator.get_score_names()}")

# Test smoke test
smoke = evaluator.smoke_test("/path/to/artifact", "TestCandidate")
print(f"Smoke test: success={smoke.success}")

# Test evaluate
results = evaluator.evaluate("/path/to/artifact", "TestCandidate")
for r in results:
    print(f"  {r.instance}: {r.scores}")
```

## Output

Return to the calling skill:
- `evaluator_spec`: Evaluator specification in `path:ClassName` format (e.g., `evolver/src/evaluator/custom_evaluator.py:CustomEvaluator`)
- `score_names`: List of metric names the evaluator produces
- `description`: Brief description of what the evaluator measures
