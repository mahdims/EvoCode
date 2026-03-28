---
name: evolve-evaluation-metric
description: Gathers evaluation metric(s) for the EvoCode evolution process.
---

# Evaluation Metric Selection

When this subskill is invoked, ask the user to select one or more evaluation metrics.

## Step 1: Metric Selection

Offer these choices, **allow multiple selections**:
- `accuracy` (Improve solution quality / test pass rate)
- `latency` (Optimize for speed / execution time)
- `memory_usage` (Reduce memory footprint)
- `Other` (User provides custom metric name)
- `Path to evaluator` (User provides path to existing custom evaluator)

## Step 2: Selection Mode (Multi-Metric Only)

**If multiple metrics are selected**, ask how to handle them:

| Option | Description |
|--------|-------------|
| `pareto` | **Multi-objective optimization (NSGA-II)** - Maintains Pareto-optimal solutions that trade off between metrics. Best when metrics conflict (e.g., speed vs accuracy). |
| `weighted` | **Weighted average** - Combines metrics into single score. Ask user for weights (e.g., accuracy:2, latency:1). |
| `primary` | **Primary metric** - Optimize mainly for one metric, others are secondary. Ask which is primary. |

### If `weighted` selected:
Ask for weights per metric, e.g.:
```
Enter weight for accuracy (default 1.0): 2.0
Enter weight for latency (default 1.0): 1.0
```

### If `primary` selected:
Ask which metric is the primary optimization target.

### If `pareto` selected:
Ask for each metric whether to maximize or minimize:
```
accuracy: maximize (higher is better)
latency: minimize (lower is better)
memory_usage: minimize (lower is better)
```

## Step 3: Path to Evaluator (if selected)

If user selects "Path to evaluator":
- Ask for the evaluator specification in `path/to/file.py:ClassName` format
- Validate the file exists
- Read the file to extract `get_score_names()` return value from the specified class
- Use those as the metrics

## Output

Return to the calling skill:
- `metrics`: List of selected metric names (e.g., `["accuracy", "latency"]`)
- `selection_mode`: `"scalar"` (single metric or aggregated) or `"pareto"` (multi-objective)
- `fitness_aggregation`: `"mean"`, `"weighted"`, or `"primary"` (only if scalar mode with multiple metrics)
- `score_weights`: Dict of weights (only if weighted aggregation)
- `primary_score`: Primary metric name (only if primary aggregation)
- `maximize_scores`: Dict mapping metric to true (maximize) or false (minimize) - for Pareto mode
- `evaluator_spec`: Evaluator specification in `path:ClassName` format (only if "Path to evaluator" was selected, e.g., `evolver/src/my_evaluator.py:MyEvaluator`)

### Examples

**Single metric (accuracy):**
```json
{
  "metrics": ["accuracy"],
  "selection_mode": "scalar"
}
```

**Multiple metrics with Pareto:**
```json
{
  "metrics": ["accuracy", "latency"],
  "selection_mode": "pareto",
  "maximize_scores": {"accuracy": true, "latency": false}
}
```

**Multiple metrics with weighted aggregation:**
```json
{
  "metrics": ["accuracy", "latency"],
  "selection_mode": "scalar",
  "fitness_aggregation": "weighted",
  "score_weights": {"accuracy": 2.0, "latency": 1.0}
}
```
