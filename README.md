# VRP Destroy Strategy Evolution

LLM-guided evolutionary system for discovering effective destroy strategies for Vehicle Routing Problem (VRP) solvers. Combines **ReEvo dual-process reflection** with **VRPAGENT prompt engineering**.

## Algorithm Overview

This system evolves Java destroy strategies for the AILS-II (Adaptive Iterated Local Search) VRP solver using an LLM as a hyper-heuristic.

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
    │   │                                                         │ │
    │   │  Inputs:                    Outputs:                    │ │
    │   │  - Parent code              - New Java strategy         │ │
    │   │  - Reflection guidance      - Implements DestroyStrategy│ │
    │   │  - Mutation type            - Compiles to plugin JAR    │ │
    │   │  - Constraints doc                                      │ │
    │   └────────────────────────┬────────────────────────────────┘ │
    │                            │                                   │
    │                            ▼                                   │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │              CANDIDATE MANAGER                          │ │
    │   │                                                         │ │
    │   │  1. Extract Java code from LLM response                 │ │
    │   │  2. Generate validation wrapper (Perturbation adapter)  │ │
    │   │  3. Compile with javac                                  │ │
    │   │  4. Package into plugin.jar                             │ │
    │   │  5. Cache by code hash (avoid re-evaluation)            │ │
    │   └────────────────────────┬────────────────────────────────┘ │
    │                            │                                   │
    │                            ▼                                   │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │                    EVALUATOR                            │ │
    │   │                                                         │ │
    │   │  1. Smoke test (500 iterations, smallest instance)      │ │
    │   │  2. End-game eval (10K iterations + warmstart)          │ │
    │   │  3. Parse solution cost from .sol files                 │ │
    │   │  4. Fitness = improvement% - code_length_penalty        │ │
    │   └────────────────────────┬────────────────────────────────┘ │
    │                            │                                   │
    │                            ▼                                   │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │              SURVIVAL SELECTION                         │ │
    │   │                                                         │ │
    │   │  Keep top N candidates by fitness (elitist)             │ │
    │   │  Repeat for num_generations                             │ │
    │   └─────────────────────────────────────────────────────────┘ │
    │                                                                │
    └────────────────────────────────────────────────────────────────┘
```

## Key Algorithm Features

### 1. Dual-Process Reflection (ReEvo)

The system maintains two types of reflection to guide evolution:

| Reflection Type | When Updated | Purpose |
|----------------|--------------|---------|
| **Short-term** | Every crossover | Compares two parents: "Why does strategy A outperform B?" |
| **Long-term** | Every N generations | Synthesizes accumulated knowledge into actionable patterns |

Short-term reflections feed into crossover decisions. Long-term reflections guide elitist mutation by providing a "knowledge base" of what works.

### 2. VRPAGENT Techniques

**Biased Crossover (75/25):**
- Elite parent contributes 75% of offspring characteristics
- Non-elite parent contributes 25% for diversity
- Guided by short-term reflection

**Typed Mutations:**
| Type | When Used | Description |
|------|-----------|-------------|
| `ablation` | Early generations | Simplify by removing components |
| `extend` | Mid generations | Add new mechanisms |
| `adjust_parameters` | Any generation | Tune existing parameters |
| `refactor` | Late generations | Optimize structure without changing behavior |

**Code Length Penalty:**
```
fitness = base_improvement - α × code_length
```
Encourages parsimony (simpler strategies preferred when performance is equal).

### 3. Validation Gate

The adapter wrapper enforces strict constraints:
- No null nodes
- No depot nodes (node.name != 0)
- No duplicates (HashSet-based deduplication)
- Return size ≤ numToRemove
- Throws `RuntimeException` on any violation (fail fast)

### 4. Tournament Selection

Parent selection uses tournament selection (k=3):
1. Sample k random candidates
2. Select the fittest as parent
3. Better parent is always first (for biased crossover)

## Project Structure

```
evolver/
├── src/                    # Core evolution system
│   ├── evolution_loop.py   # Main orchestrator
│   ├── llm_agents.py       # LLM interface (Gemini)
│   ├── candidate_manager.py# Compilation & JAR packaging
│   ├── evaluator.py        # AILS integration
│   ├── reflection_prompts.py
│   └── vrpagent_prompts.py
├── tests/                  # Test scripts
├── scripts/                # SLURM scripts for cluster
├── AILS/                   # AILS-II VRP solver
│   ├── AILSII.jar
│   ├── data/               # VRP instances
│   └── warm_start/         # Initial solutions
├── docs/                   # Documentation
├── .env.example            # API key template
└── requirements.txt
```

## Setup

### Prerequisites
- Python 3.12+
- Java JDK 11+
- Google Gemini API key

### Installation

```bash
# Create environment
conda create -n env_evolve python=3.12
conda activate env_evolve
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
```

### Verify Setup

```bash
python tests/test_llm.py      # Test API connectivity
python tests/test_simple.py   # Quick evolution test
```

## Usage

### Quick Test (Small Instances)

```python
from src.evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=4,
    elite_ratio=0.25,
    dataset_dir="Vrp_Set_X",
    target_instances=["X-n101-k25"],
    use_vrpagent=True
)

evolution.initialize_population(num_seeds=2)
evolution.evolve(num_generations=5, reflection_frequency=2)
```

### Full Evolution (Large Instances)

```python
evolution = EvolutionLoop(
    population_size=10,
    elite_ratio=0.2,
    dataset_dir="XL",
    target_instances=["XL-n1048-k237"],
    use_vrpagent=True,
    code_length_penalty_alpha=0.001
)

evolution.initialize_population(num_seeds=3)
evolution.evolve(num_generations=20, reflection_frequency=5)
```

### Running on Compute Canada (Nibi)

```bash
# One-time setup
bash scripts/setup.sh

# Submit jobs
sbatch scripts/run_evolution.sh      # Single run
sbatch scripts/run_array.sh          # Multiple parallel runs
```

See [scripts/README.md](scripts/README.md) for details.

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `population_size` | 10 | Number of candidates per generation |
| `elite_ratio` | 0.2 | Fraction of population preserved as elites |
| `mutation_rate` | 0.7 | Probability of mutation (vs crossover) |
| `crossover_rate` | 0.3 | Probability of crossover |
| `code_length_penalty_alpha` | 0.001 | Parsimony pressure coefficient |
| `reflection_frequency` | 3 | Generations between long-term reflection updates |

## Datasets

| Dataset | Instances | Nodes | Use Case |
|---------|-----------|-------|----------|
| `Vrp_Set_X` | 44 | 100-1000 | Quick testing, debugging |
| `XL` | 8 | 1000-10000+ | Production evaluation |

## Output

Each candidate is stored in `candidates/gen_XXXX/`:
- `plugin.jar` - Compiled plugin
- `src/EvoDestroy/*.java` - Generated strategy
- `src/Perturbation/*.java` - Validation wrapper
- `metadata.json` - Parent IDs, timestamps, mutation type

## References

- **ReEvo**: Ye et al., "Evolutionary Optimization of Heuristics with Large Language Models" (2024)
- **VRPAGENT**: Zhang et al., "Large Language Models as Hyper-Heuristics for Combinatorial Optimization" (2024)
- **AILS-II**: Adaptive Iterated Local Search for Vehicle Routing Problems
