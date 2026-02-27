"""Minimal test to verify LLM-guided evolution works"""
import json
import sys
from pathlib import Path
from loguru import logger

# Add src to path
evolver_root = Path(__file__).parent.parent
sys.path.insert(0, str(evolver_root / "src"))

from dotenv import load_dotenv
load_dotenv(evolver_root.parent / ".env")

from evolution_loop import EvolutionLoop
import shutil

# Load config (provides source_code_root and other settings)
config_path = evolver_root / "config.json"
with open(config_path) as f:
    config = json.load(f)

# Clean up
candidates_dir = evolver_root / "candidates"
if candidates_dir.exists():
    shutil.rmtree(candidates_dir)

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
    target_instances=["X-n101-k25"],
    use_vrpagent=True,
    config=config
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
    logger.debug("\nSUCCESS: LLM seed generation works!")
else:
    logger.debug("FAILED: No seeds generated")
logger.debug("="*80)
