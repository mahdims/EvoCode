"""Minimal test to verify LLM-guided evolution works"""
import sys
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from evolution_loop import EvolutionLoop
import shutil

# Clean up
project_root = Path(__file__).parent
for d in [project_root / "candidates", project_root / "temp"]:
    if d.exists():
        shutil.rmtree(d)

logger.debug("="*80)
logger.debug("MINIMAL LLM EVOLUTION TEST")
logger.debug("="*80)
logger.debug("Config: 2 candidates, 1 seed, no generations")
logger.debug("Goal: Verify LLM seed generation works")
logger.debug("="*80)

# Minimal config - just test seed generation
evolution = EvolutionLoop(
    population_size=2,
    elite_ratio=0.5,
    dataset_dir="Vrp_Set_X",
    target_instances=["X-n101-k25"],
    use_vrpagent=True
)

logger.debug("\n[TEST] Generating 1 LLM seed...")
evolution.initialize_population(num_seeds=1)

logger.debug("\n" + "="*80)
logger.debug("TEST RESULTS")
logger.debug("="*80)
logger.debug(f"Population size: {len(evolution.population)}")
if evolution.population:
    seed = evolution.population[0]
    logger.debug(f"Seed ID: {seed['candidate_id']}")
    logger.debug(f"Seed fitness: {seed['fitness']:.6f}")
    logger.debug(f"Code length: {seed['code_length']} lines")
    logger.debug("\nSUCCESS: LLM seed generation works!")
else:
    logger.debug("FAILED: No seeds generated")
logger.debug("="*80)
