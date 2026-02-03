---
name: evolve
description: Starts the EvoCode loop to evolve code components.
disable-model-invocation: true
---

# EvoCode Orchestrator

When this skill is invoked, follow these steps strictly to gather parameters.
When asking questions, **always** provide options as selectable widgets, instead of asking for a prompt based response.

## Step 1: Selection Phase
Ask the user to select or provide the following 4 parameters. **For each step, provide a list of common options and include an "Other" option for custom input.**

### 1. Evaluation Metric
Invoke the `evolve/evaluation-metric` subskill to gather the evaluation metric(s).

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

## Step 3: Confirmation & Execution
1. Present a **Summary Table** of the chosen parameters from Step 1.
2. Present a **Summary Table** of the "Evolution Loop" JSON parameter values from the file in Step 2.
3. Ask for a final "Confirm" before proceeding. Ask for confirmation by offering options for `Accept`, and a user-supplied input to `Update`.
4. Once confirmed, run: `python3 -u /app/evolver/evo_agent.py --verbose <JSON file from Step 2, if not default>` **CRITICAL: This is a long-running process. You MUST stay attached to the process and report progress updates as they appear in the logs. Do not background this task.**

### User Interrupts

If a user interrupts the execution of the `evo_agent.py` script, we should update the parameter file to set `"resume": true` and to update `user_insight` to contain the insight provided by the user after interrupting.

If the default parameters were used, create a copy of the `/app/evolver/config.json`, and make the corresponding updates there (i.e set `"resume": true` and `user_insight`). The user insight needs to be provided as JSON data:

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
