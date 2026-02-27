---
name: evolve
description: Starts the EvoCode loop to evolve code components.
---

# EvoCode Orchestrator

When this skill is invoked, follow these steps strictly to gather parameters.
When asking questions, **always** provide options as selectable widgets, instead of asking for a prompt based response.

## Step 1: Selection Phase

Ask the user to select or provide the following 4 parameters. **For each step, provide a list of common options and include an "Other" option for custom input.**

### 1. Evaluation Metric

Invoke the `evolve/evaluation-metric` subskill to gather the evaluation metric(s).

The subskill returns:
- `metrics`: List of metric names
- `selection_mode`: "scalar" or "pareto"
- `fitness_aggregation`, `score_weights`, `primary_score`, `maximize_scores` (as applicable)
- `evaluator_spec`: (if user provided existing evaluator, in `path:ClassName` format)

**Evaluator Decision:**
- If `metrics` is `["accuracy"]` only → use default AILSEvaluator (no `evaluator_script` needed)
- If `evaluator_spec` is provided → use that as `evaluator_script`
- Otherwise → invoke `evolve/evaluation-generate` subskill, passing `metrics` and `selection_mode`, to generate a custom evaluator. Show the generated evaluator to the user.

### 2. Initial Code

Ask for one of the following options:
- File path
- A code snippet
- Template

### 3. Direction

Offer these choices, allow multiple selections:
- `Neighborhood Search Improvement`
- `Ruin-and-Recreate`
- `Capacity Constraint Speedup`
- `Metaheuristic Tuning`
- `Other` (User provides custom direction)

### 4. Component

Ask the user to identify the function, class, or specific line range.

## Step 2: Get "Evolution Loop" Parameters

Invoke the `evolve/evolution-params` subskill to gather the evolution loop parameters.

**Important:** Pass the evaluator information from Step 1 to this subskill:
- If custom evaluator generated/provided: include `evaluator_script` in `path:ClassName` format
- If multi-metric: include `selection_mode`, `fitness_aggregation`, `score_weights`, `primary_score`, `maximize_scores` as applicable

The subskill will incorporate these into the config JSON.

## Step 3: Confirmation & Execution

1. Present a **Summary Table** of the chosen parameters from Step 1:

| Parameter | Value |
|-----------|-------|
| Metrics | {metrics} |
| Selection Mode | {selection_mode} |
| Evaluator | {default / path:ClassName} |
| Initial Code | {source} |
| Direction | {directions} |
| Component | {component} |

2. Present a **Summary Table** of the "Evolution Loop" JSON parameter values from Step 2.

3. Ask for a final "Confirm" before proceeding. Offer options: `Accept` or `Update` (user provides changes).

4. Once confirmed, run:
   ```bash
   python3 -u evolver/evo_agent.py --verbose <JSON file from Step 2, if not default>
   ```

   **CRITICAL:** This is a long-running process. You MUST stay attached to the process and report progress updates as they appear in the logs. Do not background this task.

## User Interrupts

If a user interrupts the execution of the `evo_agent.py` script, update the parameter file:
- Set `"resume": true`
- Add `user_insight` containing the insight provided by the user

If the default parameters were used, create a copy of the `/app/evolver/config.json` and make the updates there.

### User Insight Format

```json
{
    "user_insight": [
        {
            "type": "initialize",
            "idea": "Use demand-based clustering to remove high-demand nodes together"
        },
        {
            "type": "mutate",
            "idea": "Add adaptive threshold based on omega size",
            "related_population": [0]
        },
        {
            "type": "crossover",
            "idea": "Combine KNN clustering from first parent with cost-based selection from second",
            "related_population": [0, 1]
        }
    ]
}
```

| Type | Description | `related_population` |
|------|-------------|---------------------|
| `initialize` | Create a new strategy from scratch | Not used |
| `mutate` | Modify an existing candidate | Single candidate ID |
| `crossover` | Combine multiple candidates | 2+ candidate IDs |
