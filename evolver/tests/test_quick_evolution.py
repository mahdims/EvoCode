"""Quick test of evolution loop with minimal settings"""
import json
import sys
from pathlib import Path
from loguru import logger

# Add src directory to path
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
logger.debug("QUICK EVOLUTION TEST - PARALLEL MULTI-INSTANCE EVALUATION")
logger.debug("="*80)
logger.debug("Using Vrp_Set_X dataset with small instances for fast testing")
logger.debug("Instances: 4 instances with parallel evaluation (4 cores)")
logger.debug("="*80)

# Small, fast configuration using Vrp_Set_X dataset
evolution = EvolutionLoop(
    population_size=4,                   # Small population
    elite_ratio=0.25,                    # Keep 1 elite
    mutation_rate=0.7,
    crossover_rate=0.3,
    target_instances=[                   # Multiple instances for parallel eval
        "X-n101-k25",                    # 101 nodes, 25 vehicles
        "X-n106-k14",                    # 106 nodes, 14 vehicles
        "X-n115-k10",                    # 115 nodes, 10 vehicles
        "X-n125-k30"                     # 125 nodes, 30 vehicles
    ],
    use_vrpagent=True,
    code_length_penalty_alpha=0.00,
    max_parallel_evals=4,                # Parallel evaluation on 4 cores
    config=config
)

logger.debug(f"Target instances: {evolution.target_instances}")
logger.debug(f"Population size: {evolution.population_size}")
logger.debug(f"Elite size: {evolution.elite_size}")
logger.debug("="*80)

# Initialize with 2 seeds
logger.debug("\n[PHASE 1] Initializing population with 2 seeds...")
evolution.initialize_population(num_seeds=2)

# Run 1 generation
logger.debug("\n[PHASE 2] Running 1 generation...")
evolution.evolve(
    num_generations=1,
    reflection_frequency=2
)

logger.debug("\n" + "="*80)
logger.debug("QUICK TEST COMPLETED")
logger.debug("="*80)
