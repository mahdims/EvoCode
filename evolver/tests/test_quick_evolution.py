"""Quick test of evolution loop with minimal settings"""
import sys
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from evolution_loop import EvolutionLoop
import shutil

# Clean up
candidates_dir = project_root / "candidates"
if candidates_dir.exists():
    shutil.rmtree(candidates_dir)
temp_dir = project_root / "temp"
if temp_dir.exists():
    shutil.rmtree(temp_dir)

print("="*80)
print("QUICK EVOLUTION TEST - PARALLEL MULTI-INSTANCE EVALUATION")
print("="*80)
print("Using Vrp_Set_X dataset with small instances for fast testing")
print("Instances: 4 instances with parallel evaluation (4 cores)")
print("="*80)

# Small, fast configuration using Vrp_Set_X dataset
evolution = EvolutionLoop(
    population_size=4,                   # Small population
    elite_ratio=0.25,                    # Keep 1 elite
    mutation_rate=0.7,
    crossover_rate=0.3,
    dataset_dir="Vrp_Set_X",            # Use small test instances
    target_instances=[                   # Multiple instances for parallel eval
        "X-n101-k25",                    # 101 nodes, 25 vehicles
        "X-n106-k14",                    # 106 nodes, 14 vehicles
        "X-n115-k10",                    # 115 nodes, 10 vehicles
        "X-n125-k30"                     # 125 nodes, 30 vehicles
    ],
    use_vrpagent=True,
    code_length_penalty_alpha=0.00,
    max_parallel_evals=4                 # Parallel evaluation on 4 cores
)

print(f"Target instances: {evolution.target_instances}")
print(f"Population size: {evolution.population_size}")
print(f"Elite size: {evolution.elite_size}")
print("="*80)

# Initialize with 2 seeds
print("\n[PHASE 1] Initializing population with 2 seeds...")
evolution.initialize_population(num_seeds=2)

# Run 1 generation
print("\n[PHASE 2] Running 1 generation...")
evolution.evolve(
    num_generations=1,
    reflection_frequency=2
)

print("\n" + "="*80)
print("QUICK TEST COMPLETED")
print("="*80)
