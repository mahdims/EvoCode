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
| `resume` | false | Resume from existing candidates |
| `verbose` | true | Verbose output (false = reflections + best only) |
| `user_insight` | "" | User guidance string (future use) |

### Datasets

| Dataset | Nodes | Use Case |
|---------|-------|----------|
| `Vrp_Set_X` | 100-1000 | Quick testing |
| `XL` | 1000-10000+ | Production |

## Output

Each candidate stored in `candidates/gen_XXXX/`:

- `plugin.jar` - Compiled plugin
- `metadata.json` - Fitness, parent ID, evaluation results per instance

## References

- **ReEvo**: Ye et al., "Evolutionary Optimization of Heuristics with Large Language Models" (2024)
- **VRPAGENT**: Zhang et al., "Large Language Models as Hyper-Heuristics for Combinatorial Optimization" (2025)
