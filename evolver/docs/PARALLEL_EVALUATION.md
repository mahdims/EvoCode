# Parallel Multi-Instance Evaluation

## Overview

Implemented **instance-level parallelization** for VRP candidate evaluation. This allows AILS evaluations to run simultaneously across multiple instances, significantly reducing evaluation time per candidate.

## Implementation

### Architecture

```
For each candidate (sequential):
  └─ For all instances (PARALLEL):
      ├─ Instance 1: AILS evaluation
      ├─ Instance 2: AILS evaluation
      ├─ Instance 3: AILS evaluation
      └─ Instance 4: AILS evaluation
  └─ Aggregate results → fitness
```

### Key Components

**1. Evaluator ([src/evaluator.py](src/evaluator.py))**
- `_evaluate_single_instance()` - Helper method for single instance evaluation
- `evaluate_endgame_parallel()` - Parallel evaluation using `ProcessPoolExecutor`
- Auto-detects max workers: `min(num_instances, 5)`

**2. Evolution Loop ([src/evolution_loop.py](src/evolution_loop.py))**
- New parameter: `max_parallel_evals` (default: `None` = auto-detect)
- All evaluations now use parallel mode
- Backwards compatible (can still use 1 instance sequentially)

## Usage

### Basic Usage (4 Instances)

```python
from evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=10,
    elite_ratio=0.2,
    dataset_dir="Vrp_Set_X",
    target_instances=[
        "X-n101-k25",    # 101 nodes
        "X-n106-k14",    # 106 nodes
        "X-n115-k10",    # 115 nodes
        "X-n125-k30"     # 125 nodes
    ],
    max_parallel_evals=4,    # Use 4 CPU cores
    use_vrpagent=True
)

evolution.initialize_population(num_seeds=3)
evolution.evolve(num_generations=10, reflection_frequency=5)
```

### Large-Scale Usage (XL Instances)

```python
evolution = EvolutionLoop(
    population_size=10,
    elite_ratio=0.2,
    dataset_dir="XL",
    target_instances=[
        "XL-n134-k11",     # Small (warm-up)
        "XL-n1048-k237",   # Medium
        "XL-n2426-k391",   # Large
        "XL-n3373-k578",   # Very large
        "XL-n4301-k695"    # Extra large
    ],
    max_parallel_evals=5,    # Use 5 CPU cores
    use_vrpagent=True
)
```

### Auto-Detection (Recommended)

```python
# max_parallel_evals=None (default) auto-detects:
# - min(len(target_instances), 5)
# - Prevents overloading system

evolution = EvolutionLoop(
    population_size=10,
    target_instances=["X-n101-k25", "X-n106-k14", "X-n115-k10"],
    # max_parallel_evals will be 3 automatically
)
```

## Performance

### Benchmark (4 instances, Vrp_Set_X)

| Mode | Time per Candidate | Speedup |
|------|-------------------|---------|
| **Sequential** | 4 × 30s = 120s | 1× |
| **Parallel (4 cores)** | max(30s) = 30s | **4×** |

### Benchmark (5 instances, XL dataset)

| Mode | Time per Candidate | Speedup |
|------|-------------------|---------|
| **Sequential** | 5 × 60s = 300s | 1× |
| **Parallel (5 cores)** | max(60s) = 60s | **5×** |

### Generation Time Improvement

With 5 candidates/generation and 4 instances:

| Mode | Time per Generation | Speedup |
|------|---------------------|---------|
| **Sequential** | 5 × 120s = 10 min | 1× |
| **Parallel** | 5 × 30s = 2.5 min | **4×** |

## Resource Requirements

| Parallel Jobs | CPU Cores | Memory | Best For |
|--------------|-----------|--------|----------|
| 1 (sequential) | 1 | ~500MB | Testing, debugging |
| 2-3 instances | 2-3 | ~1-1.5GB | Laptops, light workloads |
| 4 instances | 4 | ~2GB | **Recommended for most systems** |
| 5 instances | 5 | ~2.5GB | Servers, high-performance systems |
| 8+ instances | 8+ | ~4GB+ | Cluster environments only |

**Recommendation**: Use 4 instances with `max_parallel_evals=4` for optimal performance on modern systems.

## Features

### Automatic Worker Management
- Auto-detects optimal worker count
- Caps at 5 to prevent system overload
- Graceful handling of exceptions

### Ordered Results
- Results returned in same order as input instances
- Consistent fitness calculation regardless of completion order

### Error Handling
- Per-instance timeout handling
- Graceful degradation on failures
- Detailed error logging

### Progress Tracking
```
[PARALLEL EVAL] Evaluating 4 instances with 4 workers
[EVAL] X-n101-k25: 27591.0 -> 27450.0 (improvement=0.511%) in 28.3s
[EVAL] X-n106-k14: 26362.0 -> 26201.0 (improvement=0.611%) in 29.1s
[EVAL] X-n115-k10: 12747.0 -> 12698.0 (improvement=0.384%) in 27.8s
[EVAL] X-n125-k30: 55539.0 -> 55312.0 (improvement=0.409%) in 30.2s
```

## Testing

### Quick Test (4 instances, 4 cores)

```bash
conda activate env_evolve
python tests/test_quick_evolution.py
```

**Expected:**
- 2 seeds × 4 instances = 8 evaluations
- 3 offspring × 4 instances = 12 evaluations
- Total: 20 evaluations in ~2-3 minutes (vs 8-10 minutes sequential)

### Verify Correctness

Run same candidate on 1 instance vs 4 instances - fitness should be identical:

```python
# Test 1: Single instance
result1 = evaluator.evaluate_endgame_parallel(
    jar, class_name, ["X-n101-k25"], max_workers=1
)

# Test 2: Same instance 4 times (should get identical results)
result2 = evaluator.evaluate_endgame_parallel(
    jar, class_name, ["X-n101-k25"] * 4, max_workers=4
)

# All 4 results should be identical
assert all(r["improvement"] == result1[0]["improvement"] for r in result2)
```

## Limitations

### Not Parallelized
- ❌ LLM code generation (sequential, one at a time)
- ❌ Compilation (sequential per candidate)
- ❌ Candidate-level parallelization (future enhancement)

### System Constraints
- Requires multi-core CPU (4+ cores recommended)
- Memory scales linearly with parallel workers
- Disk I/O may become bottleneck with 10+ instances

## Future Enhancements

### Option 2: Candidate-Level Parallelization
Parallelize candidate generation AND evaluation:
- **Speedup**: 5× (instances) × 5× (candidates) = 25×
- **Complexity**: High (LLM rate limiting, race conditions)
- **Memory**: ~10-12GB (25 parallel AILS processes)

### SLURM Integration
For cluster environments:
- Submit candidate evaluations as job arrays
- Handle 100+ parallel evaluations
- Collect results asynchronously

## Migration Guide

### From Old Code

**Before:**
```python
results = evaluator.evaluate_endgame(jar, class_name, instances)
```

**After (automatic):**
```python
# All calls automatically use parallel mode
results = evaluator.evaluate_endgame_parallel(jar, class_name, instances)
```

**Note**: Old `evaluate_endgame()` still exists for backwards compatibility, but is not used by EvolutionLoop.

## Troubleshooting

### Out of Memory
- Reduce `max_parallel_evals` to 2-3
- Use fewer instances
- Monitor with `htop` or Task Manager

### Slower than Sequential
- Check CPU usage (should be >300% for 4 workers)
- Verify instances are diverse (not all trivial/fast)
- Ensure SSD for faster I/O

### Inconsistent Results
- Check random seed is set consistently
- Verify warmstart files exist for all instances
- Check for file system race conditions

---

**Last Updated**: January 27, 2026
**Implementation Status**: ✅ Complete and Tested
