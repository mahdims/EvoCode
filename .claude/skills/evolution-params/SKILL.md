---
name: evolve/evolution-params
description: Gathers evolution loop parameters for the EvoCode process.
---

# Evolution Loop Parameters

When this subskill is invoked, gather the parameters for the evolution script.

## Input (from calling skill)

The calling skill may pass evaluator information:
- `evaluator_script`: Custom evaluator spec in `path:ClassName` format (if not using default)
- `selection_mode`: "scalar" or "pareto"
- `fitness_aggregation`: "mean", "weighted", or "primary"
- `score_weights`: Dict of weights per metric
- `primary_score`: Primary metric name
- `maximize_scores`: Dict mapping metric to maximize (true/false)

## Step 1: Parameter Source

Offer the following options:
- `Use default` - Use `/app/evolver/config.json` as base
- `Path to parameter file` - User provides path to existing JSON
- `Configure manually` - Ask for key parameters interactively

## Step 2: Parameter Configuration

### If `Use default` or `Path to parameter file`:
- Load the base config
- Merge in any evaluator settings passed from calling skill
- Show the merged config to user for review

### If `Configure manually`:
Ask for these key parameters (provide sensible defaults):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `population_size` | 10 | Candidates per generation |
| `num_generations` | 10 | Generations to evolve |
| `num_seeds` | 3 | Initial seed strategies |
| `elite_ratio` | 0.2 | Fraction preserved as elites |
| `mutation_rate` | 0.7 | Probability of mutation vs crossover |
| `target_instances` | varies | Test instances for evaluation |

## Step 3: Incorporate Evaluator Settings

If a custom evaluator or multi-metric settings were passed, add them to the config:

### Custom Evaluator (minimal)
```json
{
    "evaluator_script": "path/to/evaluator.py:MyEvaluator"
}
```

### Custom Evaluator with Settings
```json
{
    "evaluator_script": "path/to/evaluator.py:MyEvaluator",
    "evaluator_config": {
        "custom_param": value
    }
}
```

### Multi-Objective (Pareto)
```json
{
    "evaluator_script": "path/to/evaluator.py:MyEvaluator",
    "selection_mode": "pareto",
    "maximize_scores": {"accuracy": true, "latency": false}
}
```

### Weighted Aggregation
```json
{
    "evaluator_script": "path/to/evaluator.py:MyEvaluator",
    "selection_mode": "scalar",
    "fitness_aggregation": "weighted",
    "score_weights": {"accuracy": 2.0, "latency": 1.0}
}
```

### Primary Metric
```json
{
    "evaluator_script": "path/to/evaluator.py:MyEvaluator",
    "selection_mode": "scalar",
    "fitness_aggregation": "primary",
    "primary_score": "accuracy"
}
```

## Step 4: Save Config

- If using defaults with modifications, create a temp file: `/tmp/evo_config_<random>.json`
- If user provided a path, validate it exists
- Save the final merged config

## Output

Return to the calling skill:
- `config_path`: Path to the config JSON file (or `null` if using unmodified default)
- `config_summary`: Dict of key parameters for display
