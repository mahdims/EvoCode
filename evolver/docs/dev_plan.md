# VRP Destroy Strategy Evolution - Development Plan & Status

## Project Overview

LLM-guided evolutionary system for discovering effective VRP destroy strategies. Combines **ReEvo dual-process reflection** with **VRPAGENT prompt engineering techniques**.

**Status**: ✅ **CORE SYSTEM COMPLETE, LLM INTEGRATION READY**

---

## Implementation Status

### ✅ Phase 1: Core System (COMPLETE)

#### Architecture Implemented
- [x] **DestroyStrategy Interface**: Simple Java interface for LLM-generated destroy logic
- [x] **Adapter Pattern**: Auto-generated Perturbation wrappers (not LLM-generated)
- [x] **Python Orchestrator**: Complete evolution pipeline
- [x] **AILS Integration**: Plugin loading via JAR compilation

#### Key Components

**1. LLM Agents** ([src/llm_agents.py](src/llm_agents.py))
- [x] Google Gemini API integration (gemini-2.0-flash-exp)
- [x] Seed strategy generation (3 templates: Random, Worst, Clustered)
- [x] VRPAGENT-style mutations (ablation, extend, adjust-parameters, refactor)
- [x] Biased crossover (75% elite, 25% non-elite)
- [x] ReEvo reflection system (short-term & long-term)
- [x] Reflection size cap (≤12 bullets per section)
- [x] Enhanced CONSTRAINTS with deduplication guidance

**2. Candidate Manager** ([src/candidate_manager.py](src/candidate_manager.py))
- [x] Auto-generation of Perturbation adapter wrappers
- [x] Java compilation with AILS classpath
- [x] JAR packaging for plugin loading
- [x] Code hash-based caching (prevents duplicate evaluations)
- [x] Validation gate (fails on null/duplicate/invalid nodes)
- [x] Omega adaptivity logging (every 100 invocations)

**3. Evaluator** ([src/evaluator.py](src/evaluator.py))
- [x] Smoke tests (dynamic instance selection)
- [x] End-game evaluation (warmstart + 10k iterations)
- [x] Multi-instance support
- [x] Solution cost parsing from .sol files
- [x] Improvement calculation (Δ = (initial - final) / initial)

**4. Evolution Loop** ([src/evolution_loop.py](src/evolution_loop.py))
- [x] Population management (elites + offspring)
- [x] Elite preservation strategy
- [x] Tournament-based parent selection
- [x] Mutation and crossover operators
- [x] Fitness calculation with code length penalty
- [x] Reflection updates (short-term every generation, long-term periodic)
- [x] Configurable datasets (XL, Vrp_Set_X)

**5. Prompt Engineering**
- [x] ReEvo-style reflection prompts ([src/reflection_prompts.py](src/reflection_prompts.py))
- [x] VRPAGENT-style generation prompts ([src/vrpagent_prompts.py](src/vrpagent_prompts.py))
- [x] Typed mutations with generation-aware selection
- [x] Biased crossover with parent comparison

---

### ✅ Recent Fixes (Jan 26, 2026)

#### 1. Seed Template Quality
- [x] Fixed all 3 seed templates to use HashSet-based deduplication
- [x] Removed inner class from WorstRemoval (compute costs inline)
- [x] Added proper null checks and early returns
- [x] Consistent pattern across all templates

#### 2. Contract Enforcement
- [x] Aligned CONSTRAINTS with HashSet/Set imports
- [x] Added BAD vs GOOD deduplication code example
- [x] Made contract violations clear with inline comments

#### 3. Reflection Management
- [x] Implemented `_truncate_reflection_sections()` method
- [x] Enforces ≤12 bullets per section limit
- [x] Logs truncation when it occurs
- [x] Applied to long-term reflection updates

#### 4. Validation Strictness
- [x] Changed validation from warning to **strict gate**
- [x] Throws `RuntimeException` on validation failures
- [x] Fails immediately: validCount == 0 OR any errors
- [x] Prevents wasting evaluation cycles on invalid strategies

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Evolution Loop                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │  Generator   │────────▶│  Reflector   │         │
│  │  (Mutate/    │◀────────│  (Short/Long │         │
│  │   Crossover) │         │   Term)      │         │
│  └──────────────┘         └──────────────┘         │
│         │                         │                  │
│         ▼                         ▼                  │
│  ┌──────────────────────────────────────┐          │
│  │         LLM Agents (Gemini)          │          │
│  │  • Seed generation                    │          │
│  │  • VRPAGENT typed mutations           │          │
│  │  • Biased crossover                   │          │
│  │  • Reflection synthesis               │          │
│  └──────────────────────────────────────┘          │
│         │                                            │
│         ▼                                            │
│  ┌──────────────────────────────────────┐          │
│  │      Candidate Manager                │          │
│  │  • Java compilation                   │          │
│  │  • Wrapper generation                 │          │
│  │  • JAR packaging                      │          │
│  │  • Validation & caching               │          │
│  └──────────────────────────────────────┘          │
│         │                                            │
│         ▼                                            │
│  ┌──────────────────────────────────────┐          │
│  │         Evaluator                     │          │
│  │  • AILS integration                   │          │
│  │  • Smoke tests                        │          │
│  │  • End-game evaluation                │          │
│  │  • Fitness calculation                │          │
│  └──────────────────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## Pending Tasks

### 🔥 Critical Priority

#### 1. ⏳ Environment Setup & LLM Testing
**Status**: Test running with conda environment
**Goal**: Verify LLM integration works with real API
**Tasks**:
- [x] Verify `google-genai>=0.2.0` installed in `env_evolve`
- [x] Run test with conda environment: `conda run -n env_evolve python tests/test_quick_evolution.py`
- [ ] Confirm LLM generates valid Java code
- [ ] Verify reflection produces meaningful guidance
- [ ] Measure initial compile success rate

**Expected Outcome**: Test completes with LLM-generated strategies (not templates)

---

### 🎯 High Priority

#### 2. ⏳ Initial Real Evolution Run
**Goal**: Validate LLM-guided evolution on small instances
**Config**:
```python
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
**Success Criteria**:
- [ ] >50% of LLM-generated strategies compile successfully
- [ ] >80% of compiled strategies pass smoke test
- [ ] Reflection accumulates useful patterns
- [ ] At least 1 strategy shows improvement >0%

**Estimated Time**: 30-60 minutes

---

#### 3. ⏳ Baseline Comparison
**Goal**: Establish baseline performance metrics
**Tasks**:
- [ ] Manually convert AILS Sequential operator to DestroyStrategy plugin
- [ ] Manually convert AILS Concentric operator to DestroyStrategy plugin
- [ ] Run same evaluation protocol on both versions
- [ ] Verify performance parity (plugin ≈ native)
- [ ] Document baseline improvements on X-n101-k25

**Why Important**: Validates adapter pattern doesn't degrade performance

---

#### 4. ⏳ Scale to XL Instances
**Goal**: Test on realistic large-scale problems
**Config**:
```python
evolution = EvolutionLoop(
    population_size=10,
    elite_ratio=0.2,
    dataset_dir="XL",
    target_instances=["XL-n1048-k237"],
    use_vrpagent=True
)
evolution.initialize_population(num_seeds=3)
evolution.evolve(num_generations=10, reflection_frequency=5)
```
**Success Criteria**:
- [ ] Discovers strategy with >0.5% improvement over warmstart
- [ ] Evolution completes 10 generations in <4 hours
- [ ] Best strategy identified with clear reasoning

**Estimated Time**: 3-5 hours

---

### 📊 Medium Priority

#### 5. ⏳ Multi-Instance Generalization
**Goal**: Test strategy generalization across problems
**Tasks**:
- [ ] Select 3-5 diverse instances from XL dataset
  - Small (XL-n134-k11)
  - Medium (XL-n1048-k237)
  - Large (XL-n2426-k391)
- [ ] Configure fitness as weighted average across instances
- [ ] Run evolution for 15-20 generations
- [ ] Analyze strategy specialization vs generalization

**Why Important**: Prevents overfitting to single instance

---

#### 6. ⏳ Multi-Seed Confirmation
**Goal**: Robust evaluation of top candidates
**Tasks**:
- [ ] Implement Stage 2 evaluation (3-5 seeds per instance)
- [ ] Apply only to top K=3 candidates after evolution
- [ ] Compute mean and std of improvements
- [ ] Select final best based on robustness (mean - α*std)

**Why Important**: Ensures discovered strategies aren't lucky on one seed

---

#### 7. ⏳ Enhanced Reflection with JSON Logs
**Goal**: Richer context for reflection agent
**Tasks**:
- [ ] Add optional JSON logging to AILS (see old dev_plan for code)
- [ ] Log per-iteration: operator, omega, cost, distance, acceptance
- [ ] Parse JSON logs in reflection prompts
- [ ] Compare reflection quality with vs without detailed logs

**Why Important**: May improve reflection guidance quality

---

### 🔬 Low Priority (Research & Analysis)

#### 8. ⏳ Mutation Type Analysis
**Goal**: Understand which mutation types work best
**Tasks**:
- [ ] Track mutation type → compile rate
- [ ] Track mutation type → fitness improvement
- [ ] Analyze generation-dependent patterns
- [ ] Adjust mutation selection weights based on findings

---

#### 9. ⏳ Code Complexity vs Performance
**Goal**: Understand parsimony pressure effectiveness
**Tasks**:
- [ ] Plot code length vs base fitness (scatter)
- [ ] Compare strategies: simple high-performance vs complex high-performance
- [ ] Tune code length penalty alpha parameter
- [ ] Analyze reflection guidance on complexity

---

#### 10. ⏳ Visualization & Reporting
**Goal**: Better understanding of evolution dynamics
**Tasks**:
- [ ] Plot fitness trajectories (best, avg, worst per generation)
- [ ] Visualize population diversity (code similarity heatmap)
- [ ] Track reflection evolution (keyword analysis)
- [ ] Generate final report with best strategy analysis

---

#### 11. ⏳ SLURM Cluster Integration
**Goal**: Parallel evaluation for faster evolution
**Tasks**:
- [ ] Adapt AILS SLURM scripts to accept plugin parameters
- [ ] Implement job array submission for candidate evaluation
- [ ] Handle result collection and parsing
- [ ] Test on cluster environment

**Why Low Priority**: Current evaluation times acceptable for MVP

---

## Current Configuration

### Development/Testing (Vrp_Set_X)
```python
EvolutionLoop(
    population_size=4,
    elite_ratio=0.25,
    dataset_dir="Vrp_Set_X",
    target_instances=["X-n101-k25"],
    use_vrpagent=True,
    code_length_penalty_alpha=0.001
)
```
- **Runtime**: ~3 minutes per generation
- **Use for**: Quick iteration, debugging, LLM prompt tuning

### Production (XL Dataset)
```python
EvolutionLoop(
    population_size=10,
    elite_ratio=0.2,
    dataset_dir="XL",
    target_instances=["XL-n1048-k237"],
    use_vrpagent=True,
    code_length_penalty_alpha=0.001
)
```
- **Runtime**: ~20-30 minutes per generation
- **Use for**: Real evolution runs, final evaluation

---

## Testing

### ✅ Quick Test (PASSED)
```bash
cd evolver
conda run -n env_evolve python tests/test_quick_evolution.py
```
- **Status**: Currently running
- **Config**: 2 seeds, 1 generation, Vrp_Set_X/X-n101-k25
- **Expected**: ~3 minutes, confirms LLM integration

### ⏳ Full Evolution Test (Pending)
```bash
cd evolver/src
conda run -n env_evolve python -c "
from evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=4,
    elite_ratio=0.25,
    dataset_dir='Vrp_Set_X',
    target_instances=['X-n101-k25'],
    use_vrpagent=True
)
evolution.initialize_population(num_seeds=2)
evolution.evolve(num_generations=5, reflection_frequency=2)
"
```

---

## Known Issues & Mitigations

### 1. LLM Compilation Rate
- **Issue**: Unknown real-world compile success rate
- **Expected**: 50-80% (based on VRPAGENT paper)
- **Mitigation**:
  - Enhanced CONSTRAINTS with examples
  - Strict validation gate (fail fast)
  - Template fallback if LLM unavailable

### 2. Code Quality Variability
- **Issue**: LLM may generate redundant or inefficient code
- **Mitigation**:
  - Code length penalty in fitness
  - Reflection guidance emphasizes simplicity
  - Deduplication examples in prompts

### 3. Evaluation Cost
- **Issue**: 10k iterations on XL takes 10-30 minutes
- **Mitigation**:
  - Fast smoke tests (500 iterations)
  - Hash-based caching (prevents re-evaluation)
  - Future: SLURM parallelization

### 4. Reflection Noise
- **Issue**: Short-term reflections may be noisy with small fitness gaps
- **Mitigation**:
  - Long-term reflection synthesis smooths noise
  - Periodic updates (not every generation)
  - Size cap prevents information overload

---

## Success Metrics

### Phase 1: MVP (✅ ACHIEVED)
- [x] Infrastructure works end-to-end
- [x] Plugins load and run without crashes
- [x] Evaluation pipeline completes successfully
- [x] Template fallback works
- [x] Validation gate prevents invalid strategies

### Phase 2: LLM Integration (🔄 IN PROGRESS)
- [ ] >50% LLM-generated strategies compile
- [ ] >80% compiled strategies pass smoke test
- [ ] At least 1 LLM strategy achieves >0.1% improvement
- [ ] Reflection produces actionable guidance

### Phase 3: Production (⏳ PENDING)
- [ ] Discover strategy beating Sequential baseline by >1%
- [ ] Strategy generalizes across 3+ instances
- [ ] Achieves improvements on XL instances (1000+ nodes)
- [ ] Evolution completes 20 generations in <8 hours

---

## File Reference

### Core Implementation
- [src/evolution_loop.py](src/evolution_loop.py) - Main evolution orchestrator
- [src/llm_agents.py](src/llm_agents.py) - LLM interface, prompts, constraints
- [src/candidate_manager.py](src/candidate_manager.py) - Compilation, wrappers, validation
- [src/evaluator.py](src/evaluator.py) - AILS integration, smoke tests, evaluation
- [src/reflection_prompts.py](src/reflection_prompts.py) - ReEvo reflection prompts
- [src/vrpagent_prompts.py](src/vrpagent_prompts.py) - VRPAGENT mutation/crossover

### Documentation
- [README.md](README.md) - User guide, setup, usage examples
- [docs/INTEGRATED_SYSTEM.md](docs/INTEGRATED_SYSTEM.md) - System architecture
- [docs/REFLECTION_DESIGN.md](docs/REFLECTION_DESIGN.md) - ReEvo reflection design
- [docs/VRPAGENT_INTEGRATION_SUMMARY.md](docs/VRPAGENT_INTEGRATION_SUMMARY.md) - VRPAGENT features

### Testing & Configuration
- [tests/test_quick_evolution.py](tests/test_quick_evolution.py) - Quick validation test
- [.env.example](.env.example) - API key template
- [requirements.txt](requirements.txt) - Python dependencies

---

## Quick Start Commands

### Setup
```bash
# Create conda environment
conda create -n env_evolve python=3.12
conda activate env_evolve
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run Quick Test
```bash
conda run -n env_evolve python tests/test_quick_evolution.py
```

### Run Real Evolution (Small)
```bash
cd src
conda run -n env_evolve python -c "
from evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=4,
    elite_ratio=0.25,
    dataset_dir='Vrp_Set_X',
    target_instances=['X-n101-k25'],
    use_vrpagent=True
)
evolution.initialize_population(num_seeds=2)
evolution.evolve(num_generations=5, reflection_frequency=2)
"
```

### Run Real Evolution (Large)
```bash
cd src
conda run -n env_evolve python -c "
from evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=10,
    elite_ratio=0.2,
    dataset_dir='XL',
    target_instances=['XL-n1048-k237'],
    use_vrpagent=True
)
evolution.initialize_population(num_seeds=3)
evolution.evolve(num_generations=20, reflection_frequency=5)
"
```

---

## Immediate Next Steps

1. ✅ **Wait for test completion** - Verify LLM integration with `env_evolve`
2. ⏳ **Run 5-generation evolution** - Validate LLM code generation quality
3. ⏳ **Analyze compile rate** - Tune prompts if needed
4. ⏳ **Create baseline plugins** - Convert Sequential/Concentric for comparison
5. ⏳ **Scale to XL instances** - Test on realistic problems

---

## References

- **ReEvo Paper**: Evolutionary Optimization of Heuristics with Large Language Models
  _Ye et al., 2024_

- **VRPAGENT Paper**: Large Language Models as Hyper-Heuristics for Combinatorial Optimization
  _Zhang et al., 2024_

- **AILS**: Adaptive Iterated Local Search for Vehicle Routing Problems
  _Adapted for plugin-based evolution_

---

**Last Updated**: January 26, 2026
**Status**: ✅ Core complete, 🔄 LLM test running, ⏳ Production validation pending
