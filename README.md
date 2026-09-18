# EvoCode

**An LLM-guided evolutionary framework for evolving code components.**

EvoCode takes a component of an existing program — a heuristic, a scheduling policy, a selection rule, a scoring function — and evolves better implementations of it. An LLM acts as the variation operator (mutation and crossover), your own evaluator provides the fitness signal, and the evolutionary loop does the rest.

The framework itself is **domain-agnostic**. Everything problem-specific — what language the LLM writes, how source becomes a runnable artifact, how that artifact is plugged into your solver, and how quality is measured — lives behind a `BaseDomainPlugin`. Two domains ship as reference implementations: `ails_vrp` (destroy strategies for a VRP solver) and `vm_scheduling` (tenant placement policies).

The search combines **ReEvo dual-process reflection** (verbal gradients from comparing candidates) with **VRPAgent operators** (biased crossover, typed mutations, code-length regularization).

---

## Architecture

```
                              EVOLUTIONARY LOOP  (domain-agnostic)
    ┌────────────────────────────────────────────────────────────────────┐
    │                                                                    │
    │   ┌─────────────┐        ┌─────────────────────────────────┐      │
    │   │  GENERATOR  │        │          REFLECTOR              │      │
    │   │             │        │                                 │      │
    │   │  Crossover  │◄──────►│  Short-term: compare 2 parents  │      │
    │   │             │        │  "Why does A outperform B?"     │      │
    │   │  Mutation   │        │                                 │      │
    │   │  (4 types)  │◄──────►│  Long-term: accumulated wisdom  │      │
    │   └──────┬──────┘        │  "What patterns work well?"     │      │
    │          │               └─────────────────────────────────┘      │
    │          ▼                                                         │
    │   ┌────────────────────────────────────────────────────────────┐  │
    │   │  LLM  (Gemini by default; OpenAI-compatible / ModelArts)   │  │
    │   │  parent code + reflection  →  new candidate source         │  │
    │   └────────────────────────┬───────────────────────────────────┘  │
    │                            ▼                                       │
    │   ┌────────────────────────────────────────────────────────────┐  │
    │   │  BUILDER  (domain)   source → runnable artifact            │  │
    │   │  e.g. javac → plugin JAR, or a .py file, or a binary       │  │
    │   └────────────────────────┬───────────────────────────────────┘  │
    │                            ▼                                       │
    │   ┌────────────────────────────────────────────────────────────┐  │
    │   │  EVALUATOR (domain)  smoke test → run instances → scores   │  │
    │   └────────────────────────┬───────────────────────────────────┘  │
    │                            ▼                                       │
    │   ┌────────────────────────────────────────────────────────────┐  │
    │   │  POPULATION  idea-diversity check · embedding novelty ·    │  │
    │   │              idea-history tracking                         │  │
    │   └────────────────────────┬───────────────────────────────────┘  │
    │                            ▼                                       │
    │   ┌────────────────────────────────────────────────────────────┐  │
    │   │  SELECTION  elitist (scalar fitness) or NSGA-II (Pareto)   │  │
    │   └────────────────────────┬───────────────────────────────────┘  │
    └────────────────────────────┼───────────────────────────────────────┘
                                 ▼
                    SQLite log  →  Streamlit dashboard
```

### What the framework provides

- **Dual-process reflection (ReEvo)** — short-term reflections compare parent pairs and guide crossover; long-term reflections accumulate across generations and guide mutation.
- **Typed operators (VRPAgent)** — biased crossover (75/25 elite bias) and four mutation types: `ablation`, `extend`, `adjust_parameters`, `refactor`. Optional code-length penalty for parsimony.
- **Diversity management** — textual idea-similarity checking plus optional embedding-based novelty in code space.
- **Multi-objective support** — evaluators may return several named scores; select with scalar aggregation or NSGA-II Pareto fronts.
- **Parallel pipeline** — work-stealing workers process candidates end-to-end (generate → build → smoke → evaluate) with a configurable total parallelism budget.
- **Live dashboard** — fitness, diversity, viability, genealogy tree, code diffs, reflections, and an embedding map of the search space.

---

## Built-in domains

| Domain | What it evolves | Target program | Config |
|--------|-----------------|----------------|--------|
| `ails_vrp` *(default)* | Destroy strategies (Java) for the AILS-II Vehicle Routing Problem solver | [`applications/AILS/`](applications/AILS) | [`evolver/configs/default.json`](evolver/configs/default.json) |
| `vm_scheduling` | `TenantPlugin` placement policies (Java) for a VM scheduling solver | [`applications/VM_Scheduling/`](applications/VM_Scheduling) | [`evolver/configs/vm_scheduling.json`](evolver/configs/vm_scheduling.json) |

Select one with `"domain": "<name>"` in your config. See [Extending to new domains](#extending-to-new-domains) to add your own.

**`ails_vrp` datasets** (under `applications/AILS/data/`):

| Dataset | Nodes | Use case |
|---------|-------|----------|
| `Vrp_Set_X` | 100–1000 | Quick testing |
| `XL` | 1000–10000+ | Production runs |

---

## Setup

**Prerequisites**

- Python 3.12+
- JDK 21 — only needed for the built-in Java domains (`ails_vrp`, `vm_scheduling`)
- An LLM API key (Gemini by default)

```bash
python -m venv ~/envs/evolver && source ~/envs/evolver/bin/activate
pip install -r evolver/requirements.txt

cp .env.example evolver/.env   # then add your API key
```

> `.env` must live in `evolver/` — `python-dotenv` loads it from the working directory the run starts in.

**Environment variables**

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | LLM API key (required for real generation; without it the loop falls back to templates) |
| `GEMINI_MODEL` | Model name (default `gemini-2.0-flash-exp`) |
| `GOOGLE_API_KEY` | Enables the code-embedding service for novelty/visualization (optional) |
| `MODELARTS_API_KEY`, `MODELARTS_MODEL` | Credentials for the ModelArts / OpenAI-compatible adapter |
| `EVOCODE_DB_PATH` | SQLite path the dashboard reads (default `/data/evolution.db`) |

The provider adapters live in [`evolver/src/operators/llm_agents.py`](evolver/src/operators/llm_agents.py) (`gemini`, `openai`, `modelarts`). The loop currently instantiates the Gemini adapter; to use another, construct `LLMAgents(provider="...")` directly.

---

## Usage

```bash
cd evolver
python evo_agent.py                          # uses configs/default.json
python evo_agent.py configs/vm_scheduling.json
python evo_agent.py -c /path/to/my_experiment.json
python evo_agent.py --resume                 # continue from existing candidates/
```

| Flag | Effect |
|------|--------|
| `--resume` | Resume from the existing `candidates/` folder instead of starting fresh |
| `--no-debug` | Minimal output — reflections and best candidate per generation only |
| `-v` / `-vv` | Log level DEBUG / TRACE |
| `--log_path PATH` | Also write logs to a rotating file |
| `--novisual` | Skip writing the SQLite database the dashboard reads |

A config path given as a bare filename is resolved against the working directory, then `evolver/`, then `evolver/configs/`.

### Dashboard

```bash
cd ui/frontend
pip install -r requirements.txt
streamlit run src/dashboard.py --server.address=localhost
```

Opens at `http://localhost:8501` and refreshes as the run progresses. Do not pass `--novisual` to the evolution run, or there will be no data to show. Full tab-by-tab guide: [`ui/frontend/README.md`](ui/frontend/README.md).

### Docker

```bash
docker compose up -d
```

Starts `litellm` (port 4000), `frontend` (port 8501), and a `claude-code` container. The shared `evo_data` volume mounted at `/data` holds `evolution.db`.

### SLURM cluster

```bash
bash scripts/setup.sh                                   # one-time: venv + deps
sbatch scripts/run_evolution.sh                         # uses configs/default.json
sbatch scripts/run_evolution.sh configs/quick_test.json
```

See [`scripts/README.md`](scripts/README.md) for account and walltime settings.

---

## Configuration

Everything is driven by a single JSON config. The easiest start is copying [`evolver/configs/default.json`](evolver/configs/default.json) or [`evolver/configs/vm_scheduling.json`](evolver/configs/vm_scheduling.json).

```json
{
    "experiment_name": "my_experiment",
    "domain": "vm_scheduling",
    "population_size": 4,
    "elite_ratio": 0.25,
    "mutation_rate": 0.7,
    "crossover_rate": 0.3,
    "num_generations": 5,
    "num_seeds": 2,
    "reflection_frequency": 2,
    "target_instances": ["tenant_h10_v8_s1", "tenant_h15_v10_s1"],
    "max_parallel_evals": 6,
    "seed": 42,
    "resume": false,
    "verbose": 1
}
```

### Required keys

These are read directly and must be present in any config file you write:

| Parameter | Description |
|-----------|-------------|
| `population_size` | Candidates per generation |
| `elite_ratio` | Fraction preserved as elites (`elite_size = population_size * elite_ratio`) |
| `mutation_rate` | Probability of mutation |
| `crossover_rate` | Probability of crossover |
| `num_generations` | Generations to evolve |
| `num_seeds` | Initial seed strategies drawn from the domain's seed templates |
| `reflection_frequency` | Generations between long-term reflections |
| `seed` | Random seed |

### Optional keys

| Parameter | Default | Description |
|-----------|---------|-------------|
| `experiment_name` | `"unnamed"` | Label for the run |
| `domain` | `"ails_vrp"` | Registered domain plugin name |
| `source_code_root` | per-domain | Path to the target application (relative to the repo root, or absolute) |
| `target_instances` | `[]` | Evaluation instances; falls back to the evaluator's own list when omitted |
| `smoke_test_instance` | `null` | Instance used for the fast pre-evaluation sanity check |
| `dataset_dir` | `"Vrp_Set_X"` | Dataset folder under `applications/AILS/data/` (`ails_vrp` only; `default.json` sets `"XL"`) |
| `timeout` | `120` | Per-instance solver timeout in seconds (`vm_scheduling` only) |
| `max_parallel_evals` | `null` | Total parallelism budget; split into `instance_workers = min(num_instances, budget)` and `num_workers = max(1, budget // instance_workers)` |
| `use_vrpagent` | `true` | Enable biased crossover and typed mutations |
| `code_length_penalty_alpha` | `0.0` | Parsimony coefficient (`0` = disabled) |
| `embedding_diversity_threshold` | `0.90` | Cosine similarity above which a candidate counts as a duplicate |
| `resume` | `false` | Resume from existing candidates |
| `debug` | `true` | Verbose progress output |
| `verbose` | `0` | Log level: `0` = INFO, `1` = DEBUG, `2` = TRACE |
| `user_insight` | `""` | Domain knowledge injected into the loop — see [User insight](#user-insight) |
| `builder_script` | `null` | Custom builder as `"path/to/file.py:ClassName"` |
| `builder_config` | `{}` | Extra kwargs for the custom builder |
| `evaluator_script` | `null` | Custom evaluator as `"path/to/file.py:ClassName"` |
| `evaluator_config` | `{}` | Extra kwargs for the custom evaluator |
| `selection_mode` | `"scalar"` | `"scalar"` (fitness-based) or `"pareto"` (NSGA-II) |
| `fitness_aggregation` | `"mean"` | Multi-score aggregation: `"mean"`, `"weighted"`, or `"primary"` |
| `score_weights` | `null` | Per-score weights for `"weighted"`, e.g. `{"accuracy": 2, "speed": 1}` |
| `primary_score` | `null` | Score name for `"primary"` aggregation |
| `maximize_scores` | `null` | Per-score direction for Pareto, e.g. `{"accuracy": true, "runtime": false}` |

When `builder_script` or `evaluator_script` is set, it overrides the corresponding component from the domain plugin — so you can keep a domain's build pipeline while swapping in your own fitness measurement, or vice versa.

### Multi-objective selection

When an evaluator declares multiple scores via `get_score_names()` and `selection_mode` is `"pareto"`, NSGA-II is used:

- Non-dominated sorting ranks candidates into Pareto fronts
- Crowding distance preserves diversity within a front
- Tournament selection uses Pareto dominance

Otherwise the scores are collapsed to a scalar by `FitnessAggregator` using `fitness_aggregation`, unless the evaluator's own `calculate_fitness()` returns a value.

### User insight

Inject domain knowledge into the search by listing insight objects. They are applied at the start of evolution, before the main loop — which makes them a natural way to steer a `--resume` run after watching the dashboard.

```json
{
    "user_insight": [
        {
            "type": "initialize",
            "idea": "Use demand-based clustering to remove high-demand nodes together"
        },
        {
            "type": "mutate",
            "idea": "Add an adaptive threshold based on omega size",
            "related_population": [0]
        },
        {
            "type": "crossover",
            "idea": "Combine KNN clustering from the first parent with cost-based selection from the second",
            "related_population": [0, 1]
        }
    ]
}
```

| Type | Description | `related_population` |
|------|-------------|---------------------|
| `initialize` | Create a new candidate from scratch | Not used |
| `mutate` | Modify an existing candidate | One candidate ID |
| `crossover` | Combine several candidates | 2+ candidate IDs |

---

## Extending to new domains

All evolutionary machinery is domain-agnostic; `EvolutionLoop` has zero knowledge of your problem. Four layers define a domain, and all four are owned by one plugin object:

| Layer | Interface | What it controls |
|-------|-----------|------------------|
| LLM context | `BaseBuilder.get_llm_context()` | Language, constraints, API description, and seed examples the LLM must follow |
| Build pipeline | `BaseBuilder.build()` | How generated source becomes a runnable artifact |
| Injection | `BaseEvaluator.smoke_test()` / `evaluate()` | How the artifact is plugged into the target program and invoked |
| Fitness signal | `BaseEvaluator.calculate_fitness()` | How result quality is measured |

There are three ways to extend, in increasing scope.

### Option A — Custom evaluator only

Use when the build step stays the same but you want different metrics or a different solver for measuring fitness.

```python
# my_evaluator.py
from evaluation import BaseEvaluator, EvalResult, SmokeTestResult
from typing import List, Optional


class MyEvaluator(BaseEvaluator):
    def __init__(self, target_instances=None, my_param=0.5, **kwargs):
        # Accept **kwargs — the loader also passes max_workers and the full config.
        # target_instances arrives empty here; EvolutionLoop assigns the resolved
        # list to self.target_instances after construction, so read it at call time.
        self.target_instances = target_instances or []
        self.my_param = my_param

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        return SmokeTestResult(success=True, output="OK", runtime=0.1, exit_code=0)

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        return [
            EvalResult(
                instance=inst,
                success=True,
                scores={"accuracy": 0.95, "memory_efficiency": 0.80},
                metadata={"artifact": artifact_path},
            )
            for inst in self.target_instances
        ]

    def get_instances(self) -> List[str]:
        return self.target_instances

    def get_score_names(self) -> List[str]:
        return ["accuracy", "memory_efficiency"]

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        # Return None to delegate to fitness_aggregation from config
        return None
```

```json
{
    "target_instances": ["inst1", "inst2"],
    "evaluator_script": "path/to/my_evaluator.py:MyEvaluator",
    "evaluator_config": {"my_param": 0.7},
    "selection_mode": "pareto",
    "maximize_scores": {"accuracy": true, "memory_efficiency": true}
}
```

The `evaluator_script` format is `"path/to/file.py:ClassName"`. Omit the class name to auto-detect the first `BaseEvaluator` subclass in the file. A relative path is resolved against the working directory, then `evolver/`, then the repo root, then `evolver/src/`.

The loader always passes `target_instances`, `max_workers`, and `config` (the full config dict) to the constructor, then merges in `evaluator_config` — which takes precedence. Accept `**kwargs` so you are not broken by keys you do not use. Note that `target_instances` arrives **empty** at construction time: `EvolutionLoop` resolves the instance list and assigns it to `evaluator.target_instances` immediately after, so read the attribute when you evaluate rather than caching a copy.

The same spec format and path resolution apply to `builder_script`, but a custom builder receives only `builder_config` — no common parameters.

### Option B — Custom builder only

Use when the generated source compiles differently — Python scripts instead of JARs, C++ binaries, and so on.

```python
# my_builder.py
from building import BaseBuilder
from pathlib import Path
from typing import Any, Dict, Optional
import re


class MyBuilder(BaseBuilder):
    def extract_entry_point(self, source_code: str) -> Optional[str]:
        """Extract the callable name from generated source."""
        m = re.search(r"def (\w+)", source_code)
        return m.group(1) if m else None

    def build(self, source_code: str, candidate_id: int,
              candidate_dir: str) -> Optional[Dict[str, Any]]:
        """Write source to disk. Return artifact_path + entry_point, or None on failure."""
        out = Path(candidate_dir)
        out.mkdir(parents=True, exist_ok=True)
        script = out / "strategy.py"
        script.write_text(source_code)
        return {
            "artifact_path": str(script),
            "entry_point": self.extract_entry_point(source_code),
        }

    def get_llm_context(self) -> Dict[str, Any]:
        """Tell the LLM what it must produce."""
        return {
            "language": "python",
            "constraints": "Must define a function with this exact signature: ...",
            "problem_description": "...",
            "initial_seeds": [
                ("idea description", "def my_strategy(...):\n    pass"),
            ],
        }
```

```json
{
    "builder_script": "path/to/my_builder.py:MyBuilder",
    "builder_config": {}
}
```

### Option C — Full domain plugin

Recommended for a genuinely new problem. This bundles builder, evaluator, LLM context, and seed templates into one registered plugin selected by `"domain": "my_domain"`.

**Layout** — under `evolver/src/domains/`, mirroring `ails_vrp/` and `vm_scheduling/`:

```
evolver/src/domains/my_domain/
├── __init__.py    # imports .plugin so registration runs
├── plugin.py      # BaseDomainPlugin subclass + registration call
├── builder.py     # BaseBuilder subclass (as in Option B)
├── evaluator.py   # BaseEvaluator subclass (as in Option A)
└── templates.py   # constraints, problem description, seed code
```

**`templates.py`**

```python
def get_initial_seeds():
    """Return (idea, source_code) pairs for seeding the initial population."""
    return [
        ("First strategy idea", "def my_strategy(...):\n    # implementation 1"),
        ("Second strategy idea", "def my_strategy(...):\n    # implementation 2"),
    ]
```

**`plugin.py`**

```python
from typing import Any, Dict, List

from domains.base_domain_plugin import BaseDomainPlugin
from domains.registry import DomainPluginRegistry
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

    def get_builder(self) -> MyBuilder:          return self._builder
    def get_evaluator(self) -> MyEvaluator:      return self._evaluator
    def get_llm_context(self) -> Dict[str, Any]: return self._builder.get_llm_context()
    def get_initial_seeds(self) -> List[tuple]:  return get_initial_seeds()
    def get_instances(self) -> List[str]:        return self._evaluator.get_instances()


# Auto-register on import
DomainPluginRegistry.register("my_domain", MyDomainPlugin)
```

**Enable it** — add one line to [`evolver/src/domains/__init__.py`](evolver/src/domains/__init__.py):

```python
from . import ails_vrp        # existing
from . import vm_scheduling   # existing
from . import my_domain       # add this
```

**Run it**

```json
{
    "domain": "my_domain",
    "target_instances": ["instance_a", "instance_b"],
    "population_size": 4,
    "elite_ratio": 0.25,
    "mutation_rate": 0.7,
    "crossover_rate": 0.3,
    "num_generations": 10,
    "num_seeds": 2,
    "reflection_frequency": 2,
    "seed": 42
}
```

Config keys belonging to other domains are simply ignored — each plugin reads only what it needs from the config dict it is handed.

### Interface reference

| Class | Location | Abstract methods |
|-------|----------|------------------|
| `BaseBuilder` | [`evolver/src/building/base_builder.py`](evolver/src/building/base_builder.py) | `build()`, `extract_entry_point()` |
| `BaseEvaluator` | [`evolver/src/evaluation/base_evaluator.py`](evolver/src/evaluation/base_evaluator.py) | `smoke_test()`, `evaluate()` |
| `BaseDomainPlugin` | [`evolver/src/domains/base_domain_plugin.py`](evolver/src/domains/base_domain_plugin.py) | `get_builder()`, `get_evaluator()`, `get_llm_context()`, `get_initial_seeds()` |

Optional override hooks: `get_source_path()` and `get_llm_context()` on the builder; `calculate_fitness()`, `get_score_names()`, and `get_instances()` on the evaluator; `get_instances()` on the plugin.

The registry ([`evolver/src/domains/registry.py`](evolver/src/domains/registry.py)) maps domain names to plugin classes via `DomainPluginRegistry.register(name, cls)` / `.create(name, config)` / `.list_domains()`.

`ails_vrp` ([`evolver/src/domains/ails_vrp/`](evolver/src/domains/ails_vrp)) is the reference implementation; `vm_scheduling` ([`evolver/src/domains/vm_scheduling/`](evolver/src/domains/vm_scheduling)) is a second, leaner example of the same pattern.

---

## Guided setup with Claude Code

The repo ships a `/evolve` skill ([`.claude/skills/evolve/`](.claude/skills/evolve)) that walks through setting up a run interactively: choosing evaluation metrics and selection mode, generating a custom evaluator when needed, picking the component to evolve and the search direction, filling in the evolution parameters, and launching both the run and the dashboard. Supporting subskills handle metric selection, evaluator generation, and loop parameters.

---

## Output

Each candidate is written to `evolver/candidates/gen_XXXX/` (numbered by candidate ID):

| File | Contents |
|------|----------|
| builder artifact | Whatever `build()` produced — e.g. `plugin.jar` for the Java domains |
| `metadata.json` | Candidate ID, parent ID, mutation type, idea, artifact path, entry point, code hash, timestamp, plus domain-specific fields |
| `idea_genXXXX.md` | The idea behind the candidate, tagged with the generation that produced it |

The candidates folder also holds `cache.json` (build cache keyed by source hash) and `embedding_cache.json`. Per-generation metrics, genealogy, strategies, and reflections go to the SQLite database at `EVOCODE_DB_PATH` (default `/data/evolution.db`), which the dashboard reads.

---

## Repository layout

| Path | Purpose |
|------|---------|
| [`evolver/evo_agent.py`](evolver/evo_agent.py) | Entry point — config loading, logging, run orchestration |
| [`evolver/src/evolution_loop.py`](evolver/src/evolution_loop.py) | Core loop: reflection, variation, selection, parallel pipeline |
| [`evolver/src/domains/`](evolver/src/domains) | Domain plugins and the registry |
| [`evolver/src/building/`](evolver/src/building) | Builder interface and dynamic loader |
| [`evolver/src/evaluation/`](evolver/src/evaluation) | Evaluator interface, fitness aggregation, Pareto selection |
| [`evolver/src/operators/`](evolver/src/operators) | LLM adapters and ReEvo / VRPAgent prompt generators |
| [`evolver/src/population/`](evolver/src/population) | Candidate management, diversity, embeddings, survival, idea history |
| [`evolver/src/persistence/`](evolver/src/persistence) | SQLite logging and reporting |
| [`evolver/configs/`](evolver/configs) | Ready-to-run example configs |
| [`evolver/docs/`](evolver/docs) | Design notes on reflection and the VRPAgent integration |
| [`ui/frontend/`](ui/frontend) | Streamlit dashboard |
| [`applications/`](applications) | Target programs the built-in domains evolve code for |
| [`scripts/`](scripts) | Cluster setup and SLURM job scripts |

---

## References

- **ReEvo** — Ye et al., *ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution*, NeurIPS 2024. Source of the dual-process (short-term / long-term) reflection design.
- **VRPAgent** (2025) — source of the biased crossover, typed mutation operators, and code-length regularization.

Design notes for both are in [`evolver/docs/`](evolver/docs).
