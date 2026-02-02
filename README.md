# VRP Destroy Strategy Evolution

LLM-guided evolutionary system for discovering effective destroy strategies for Vehicle Routing Problem (VRP) solvers. Combines **ReEvo dual-process reflection** with **VRPAGENT prompt engineering**.

## Algorithm Overview

```
                              EVOLUTIONARY LOOP
    ┌────────────────────────────────────────────────────────────────┐
    │                                                                │
    │   ┌─────────────┐        ┌─────────────────────────────────┐  │
    │   │  GENERATOR  │        │          REFLECTOR              │  │
    │   │             │        │                                 │  │
    │   │  Crossover  │◄──────►│  Short-term: Compare 2 parents  │  │
    │   │  (30%)      │        │  "Why does A outperform B?"     │  │
    │   │             │        │                                 │  │
    │   │  Mutation   │◄──────►│  Long-term: Accumulated wisdom  │  │
    │   │  (70%)      │        │  "What patterns work well?"     │  │
    │   └──────┬──────┘        └─────────────────────────────────┘  │
    │          │                                                     │
    │          ▼                                                     │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │                    LLM (Gemini)                         │ │
    │   │  - Parent code + Reflection → New Java strategy         │ │
    │   │  - Compiles to plugin JAR                               │ │
    │   └────────────────────────┬────────────────────────────────┘ │
    │                            ▼                                   │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │  EVALUATOR: Smoke test → End-game eval → Fitness score  │ │
    │   └────────────────────────┬────────────────────────────────┘ │
    │                            ▼                                   │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │  SELECTION: Keep top N candidates (elitist)             │ │
    │   └─────────────────────────────────────────────────────────┘ │
    └────────────────────────────────────────────────────────────────┘
```

### Key Features

- **Dual-Process Reflection (ReEvo)**: Short-term reflections guide crossover; long-term reflections accumulate knowledge for mutation
- **VRPAGENT Techniques**: Biased crossover (75/25 elite bias), typed mutations (ablation, extend, adjust, refactor), code length penalty
- **Validation Gate**: Strict constraints on generated code (no nulls, no depot nodes, no duplicates)

## Setup

**Prerequisites:** Python 3.12+, Java JDK 11+, Google Gemini API key

```bash
conda create -n env_evolve python=3.12 && conda activate env_evolve
pip install -r requirements.txt
cp .env.example .env  # Add GEMINI_API_KEY
```

## Usage

All parameters are specified in a JSON config file. Run with default `config.json` or provide a path to any config file:

```bash
python evo_agent.py                          # Uses config.json in project root
python evo_agent.py configs/full_small.json  # Uses specified config file
python evo_agent.py --resume                 # Resume from existing candidates
python evo_agent.py --no-verbose             # Minimal output (reflections + best only)
```

### Cluster

```bash
bash scripts/setup.sh                        # One-time setup
sbatch scripts/run_evolution.sh              # Single run
sbatch scripts/run_array.sh                  # 5 parallel runs (different seeds)
```

## Configuration

Example `config.json`:

```json
{
    "experiment_name": "my_experiment",
    "population_size": 10,
    "num_generations": 15,
    "num_seeds": 3,
    "dataset_dir": "Vrp_Set_X",
    "target_instances": ["X-n101-k25", "X-n106-k14"],
    "resume": false,
    "verbose": true
}
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `population_size` | 10 | Candidates per generation |
| `elite_ratio` | 0.2 | Fraction preserved as elites |
| `mutation_rate` | 0.7 | Probability of mutation (vs crossover) |
| `num_generations` | 10 | Generations to evolve |
| `num_seeds` | 3 | Initial seed strategies |
| `reflection_frequency` | 3 | Generations between long-term reflection |
| `use_vrpagent` | true | Enable VRPAGENT techniques |
| `code_length_penalty_alpha` | 0.0 | Parsimony coefficient (0 = disabled) |
| `num_workers` | 2 | Concurrent candidate pipelines |
| `instance_workers` | "auto" | Parallel instances per candidate ("auto" = (cpu_count-1) / num_workers) |
| `resume` | false | Resume from existing candidates |
| `verbose` | true | Verbose output (false = reflections + best only) |
| `user_insight` | null | List of user insights to guide evolution (see [User Insight](#user-insight)) |

### Datasets

| Dataset | Nodes | Use Case |
|---------|-------|----------|
| `Vrp_Set_X` | 100-1000 | Quick testing |
| `XL` | 1000-10000+ | Production |

### Parallelization

Work-stealing pipeline where each worker handles a candidate end-to-end:

```
Worker 1: Generate → Compile → Smoke → Evaluate → (pick next task)
Worker 2: Generate → Compile → Smoke → Evaluate → (pick next task)
```

- `num_workers`: How many candidates processed in parallel
- `instance_workers`: Parallel VRP instances per candidate evaluation
  - `"auto"`: Distributes cores fairly: `(cpu_count - 1) / num_workers`
  - Or set explicit number

### User Insight

Inject domain knowledge into the evolutionary process by providing a list of insight objects:

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
| `initialize` | Create a new strategy from scratch based on the idea | Not used |
| `mutate` | Modify an existing candidate guided by the idea | Single candidate ID |
| `crossover` | Combine multiple candidates according to the idea | 2+ candidate IDs |

User insights are processed at the start of evolution, before the main loop.

## Output

Each candidate stored in `candidates/gen_XXXX/`:

- `plugin.jar` - Compiled plugin
- `metadata.json` - Fitness, parent ID, evaluation results per instance

## References

- **ReEvo**: Ye et al., "Evolutionary Optimization of Heuristics with Large Language Models" (2024)
- **VRPAGENT**: Zhang et al., "Large Language Models as Hyper-Heuristics for Combinatorial Optimization" (2025)
