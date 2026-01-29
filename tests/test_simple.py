"""Minimal test to verify LLM-guided evolution works"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from evolution_loop import EvolutionLoop
import shutil

# Clean up
project_root = Path(__file__).parent
for d in [project_root / "candidates", project_root / "temp"]:
    if d.exists():
        shutil.rmtree(d)

print("="*80)
print("MINIMAL LLM EVOLUTION TEST")
print("="*80)
print("Config: 2 candidates, 1 seed, no generations")
print("Goal: Verify LLM seed generation works")
print("="*80)

# Minimal config - just test seed generation
evolution = EvolutionLoop(
    population_size=2,
    elite_ratio=0.5,
    dataset_dir="Vrp_Set_X",
    target_instances=["X-n101-k25"],
    use_vrpagent=True
)

print("\n[TEST] Generating 1 LLM seed...")
evolution.initialize_population(num_seeds=1)

print("\n" + "="*80)
print("TEST RESULTS")
print("="*80)
print(f"Population size: {len(evolution.population)}")
if evolution.population:
    seed = evolution.population[0]
    print(f"Seed ID: {seed['candidate_id']}")
    print(f"Seed fitness: {seed['fitness']:.6f}")
    print(f"Code length: {seed['code_length']} lines")
    print("\nSUCCESS: LLM seed generation works!")
else:
    print("FAILED: No seeds generated")
print("="*80)
