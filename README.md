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
    │   │  EVALUATOR (Pluggable): Smoke test → Eval → Scores      │ │
    │   └────────────────────────┬────────────────────────────────┘ │
    │                            ▼                                   │
    │   ┌─────────────────────────────────────────────────────────┐ │
    │   │  SELECTION: Elitist (scalar) or NSGA-II (Pareto)        │ │
    │   └─────────────────────────────────────────────────────────┘ │
    └────────────────────────────────────────────────────────────────┘
```

### Key Features

- **Dual-Process Reflection (ReEvo)**: Short-term reflections guide crossover; long-term reflections accumulate knowledge for mutation
- **VRPAGENT Techniques**: Biased crossover (75/25 elite bias), typed mutations (ablation, extend, adjust, refactor), code length penalty
- **Pluggable Evaluators**: Custom evaluators for different domains; multi-score outputs with Pareto selection
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
| `evaluator_script` | null | Custom evaluator as `"path/to/file.py:ClassName"` (see [Pluggable Evaluators](#pluggable-evaluators)) |
| `evaluator_config` | {} | Evaluator-specific config passed to custom evaluator constructor |
| `selection_mode` | "scalar" | Selection mode: "scalar" (fitness-based) or "pareto" (multi-objective NSGA-II) |
| `fitness_aggregation` | "mean" | Multi-score aggregation: "mean", "weighted", or "primary" |
| `score_weights` | null | Weights per score for "weighted" aggregation, e.g. `{"accuracy": 2, "speed": 1}` |
| `primary_score` | null | Score name for "primary" aggregation |
| `maximize_scores` | null | Dict mapping score names to maximize (true) or minimize (false) for Pareto |

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

### Pluggable Evaluators

The system supports custom evaluators for different optimization domains or metrics. By default, it uses `AILSEvaluator` for VRP problems.

**Creating a Custom Evaluator:**

```python
# my_evaluator.py
from evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from typing import List, Optional

class MyEvaluator(BaseEvaluator):
    def __init__(self, target_instances=None, my_param=0.5, **kwargs):
        # target_instances is automatically passed from main config
        self.target_instances = target_instances or []
        self.my_param = my_param

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        # Quick validation test
        return SmokeTestResult(success=True, output="OK", runtime=0.1, exit_code=0)

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        # Evaluate on each instance, return named scores
        results = []
        for inst in self.target_instances:
            results.append(EvalResult(
                instance=inst,
                success=True,
                scores={"accuracy": 0.95, "memory_efficiency": 0.80},
                metadata={"artifact": artifact_path}
            ))
        return results

    def get_score_names(self) -> List[str]:
        return ["accuracy", "memory_efficiency"]

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        # Optional: return None to use fitness_aggregation from config
        return None
```

**Config for custom evaluator:**

```json
{
    "target_instances": ["inst1", "inst2"],
    "evaluator_script": "path/to/my_evaluator.py:MyEvaluator",
    "evaluator_config": {"my_param": 0.7},
    "selection_mode": "pareto",
    "maximize_scores": {"accuracy": true, "memory_efficiency": true}
}
```

The `evaluator_script` format is `"path/to/file.py:ClassName"`. You can also omit the class name (`"path/to/file.py"`) to auto-detect the first `BaseEvaluator` subclass in the file. The path is resolved relative to the CWD, project root, or repo root.

Common parameters (`target_instances`, `max_workers`, etc.) are automatically passed to custom evaluators. Use `evaluator_config` only for evaluator-specific settings.

**Multi-Objective Selection:**

When `selection_mode` is `"pareto"` and the evaluator returns multiple scores, NSGA-II selection is used:
- Non-dominated sorting ranks candidates into Pareto fronts
- Crowding distance preserves diversity within fronts
- Tournament selection uses Pareto dominance

## Extending to New Domains

EvoCode uses a domain plugin architecture that keeps all evolutionary machinery completely domain-agnostic. Everything that is specific to a problem — what the LLM produces, how it is compiled, how it runs, how quality is measured — lives inside a `BaseDomainPlugin` subclass.

### What defines a domain

To evolve a different component, all four of these layers must change together:

| Layer | Interface | What it controls |
| - | - | - |
| LLM context | `BaseBuilder.get_llm_context()` | Code language, constraints, and seed examples the LLM must follow |
| Build pipeline | `BaseBuilder.build()` | How LLM-generated source is turned into a runnable artifact |
| Injection | `BaseEvaluator.smoke_test()` / `evaluate()` | How the artifact is plugged into the solver and invoked |
| Fitness signal | `BaseEvaluator.calculate_fitness()` | How result quality is measured and returned |

All four are owned by a single `BaseDomainPlugin` object. `EvolutionLoop` has zero knowledge of any of them.

### Extension options

There are three ways to extend the system, in increasing scope:

---

#### Option A — Custom evaluator only

Already documented in [Pluggable Evaluators](#pluggable-evaluators).

Use this when the build step (e.g. Java compilation) stays the same but you want different metrics or a different solver for fitness measurement.

Config: `"evaluator_script": "path/to/my_evaluator.py:MyEvaluator"`

---

#### Option B — Custom builder only

Use this when the source code compiles differently (e.g. Python scripts instead of JARs, or C++ binaries).

```python
# my_builder.py
from builder import BaseBuilder  # evolver/src/builder/__init__.py re-export
from pathlib import Path
from typing import Optional, Dict, Any
import re

class MyBuilder(BaseBuilder):
    def extract_entry_point(self, source_code: str) -> Optional[str]:
        """Extract the callable name from generated source code."""
        m = re.search(r'def (\w+)', source_code)
        return m.group(1) if m else None

    def build(self, source_code: str, candidate_id: int,
              candidate_dir: str) -> Optional[Dict[str, Any]]:
        """Write source to disk. Return artifact_path + entry_point."""
        out = Path(candidate_dir)
        out.mkdir(parents=True, exist_ok=True)
        entry = self.extract_entry_point(source_code)
        script = out / "strategy.py"
        script.write_text(source_code)
        return {"artifact_path": str(script), "entry_point": entry}

    def get_llm_context(self) -> Dict[str, Any]:
        """Tell the LLM what it must produce."""
        return {
            "language": "python",
            "constraints": "Must define a function with this exact signature: ...",
            "initial_seeds": [
                ("idea description", "def my_strategy(...):\n    pass"),
            ],
        }
```

Config:
```json
{
    "builder_script": "path/to/my_builder.py:MyBuilder",
    "builder_config": {}
}
```

---

#### Option C — Full domain plugin

Recommended when you are adding a completely new problem domain.
This bundles a builder, evaluator, LLM context, and seed templates into a single registered plugin.

**Directory layout** (place under `evolver/src/domains/` or anywhere on the Python path):

```
evolver/src/domains/my_domain/
├── __init__.py    # empty, or re-exports
├── plugin.py      # BaseDomainPlugin subclass + registration call
├── builder.py     # BaseBuilder subclass (same as Option B)
├── evaluator.py   # BaseEvaluator subclass
└── templates.py   # constraints string + seed code examples
```

**`evaluator.py`:**

```python
from core.base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from typing import List, Optional

class MyEvaluator(BaseEvaluator):
    def __init__(self, target_instances=None, max_workers=None, **kwargs):
        self.target_instances = target_instances or []
        self.max_workers = max_workers

    def get_instances(self) -> List[str]:
        return self.target_instances

    def get_score_names(self) -> List[str]:
        return ["my_score"]

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Quick sanity-check: can the artifact be loaded and invoked?"""
        # run a fast check here; return success=False to skip full evaluation
        return SmokeTestResult(success=True, runtime=0.1)

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        """Run the artifact on every instance and return named scores."""
        results = []
        for inst in self.target_instances:
            score = run_my_solver(artifact_path, candidate_name, inst)
            results.append(EvalResult(
                instance=inst,
                success=True,
                scores={"my_score": score},
            ))
        return results

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        """Return a scalar fitness, or None to use fitness_aggregation from config."""
        successful = [r for r in results if r.success]
        if not successful:
            return -float("inf")
        return sum(r.scores["my_score"] for r in successful) / len(results)
```

**`templates.py`:**

```python
def get_initial_seeds():
    """Return (idea, source_code) pairs for seeding the initial population."""
    return [
        ("First strategy idea", "def my_strategy(...):\n    # implementation 1"),
        ("Second strategy idea", "def my_strategy(...):\n    # implementation 2"),
    ]
```

**`plugin.py`:**

```python
from typing import Dict, Any, List
from core.base_domain_plugin import BaseDomainPlugin
from core.registry import DomainPluginRegistry
from .builder import MyBuilder
from .evaluator import MyEvaluator
from .templates import get_initial_seeds

class MyDomainPlugin(BaseDomainPlugin):
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        self._builder = MyBuilder()
        self._evaluator = MyEvaluator(
            target_instances=config.get("target_instances", []),
            max_workers=config.get("max_parallel_evals"),
        )

    def get_builder(self) -> MyBuilder:        return self._builder
    def get_evaluator(self) -> MyEvaluator:    return self._evaluator
    def get_llm_context(self) -> Dict:         return self._builder.get_llm_context()
    def get_initial_seeds(self) -> List[tuple]: return get_initial_seeds()
    def get_instances(self) -> List[str]:      return self._evaluator.target_instances

# Auto-register when this module is imported
DomainPluginRegistry.register("my_domain", MyDomainPlugin)
```

**Enable the plugin** — add one line to `evolver/src/domains/__init__.py`:

```python
from . import ails_vrp   # existing
from . import my_domain  # add this line
```

**Config:**

```json
{
    "domain": "my_domain",
    "target_instances": ["instance_a", "instance_b"],
    "population_size": 4,
    "num_generations": 10
}
```

All AILS-specific config keys (`source_code_root`, `dataset_dir`, etc.) are simply ignored when `"domain"` is not `"ails_vrp"`.

### ABCs reference

| Class | Location | Abstract methods |
|-------|----------|-----------------|
| `BaseBuilder` | `evolver/src/core/base_builder.py` | `build()`, `extract_entry_point()` |
| `BaseEvaluator` | `evolver/src/core/base_evaluator.py` | `smoke_test()`, `evaluate()` |
| `BaseDomainPlugin` | `evolver/src/core/base_domain_plugin.py` | `get_builder()`, `get_evaluator()`, `get_llm_context()`, `get_initial_seeds()` |

All three ABCs have optional override hooks (`get_source_path()` on builder, `calculate_fitness()` and `get_score_names()` on evaluator, `get_instances()` on both plugin and evaluator).

The `DomainPluginRegistry` (`evolver/src/core/registry.py`) maps domain name strings to plugin classes: `DomainPluginRegistry.register("my_domain", MyDomainPlugin)` and `DomainPluginRegistry.create("my_domain", config)`.

The built-in AILS VRP plugin (`evolver/src/domains/ails_vrp/`) is the reference implementation.

## Output

Each candidate stored in `candidates/gen_XXXX/`:

- `plugin.jar` - Compiled plugin
- `metadata.json` - Fitness, parent ID, evaluation results per instance

## References

- **ReEvo**: Ye et al., "Evolutionary Optimization of Heuristics with Large Language Models" (2024)
- **VRPAGENT**: Zhang et al., "Large Language Models as Hyper-Heuristics for Combinatorial Optimization" (2025)
