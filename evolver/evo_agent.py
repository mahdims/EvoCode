#!/usr/bin/env python3
"""
EvoAgent - Main Entry Point for EvoCode

LLM-guided evolution of code components. The problem being solved is chosen
by the "domain" key in the config file (see src/domains/); the evolutionary
machinery itself is domain-agnostic.

Usage:
    python evo_agent.py                          # Use default configs/default.json
    python evo_agent.py configs/quick_test.json  # Use specified config file
    python evo_agent.py --config myexp.json      # Use specified config file
    python evo_agent.py --resume                 # Resume from existing candidates
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from evolution_loop import EvolutionLoop, MultiObjectiveConfig

from loguru import logger


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file. If None, looks for configs/default.json in script directory.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent / "configs" / "default.json"
    else:
        config_path = Path(config_path)
        # If the given path is relative and doesn't exist from CWD, try:
        #   1. Relative to evo_agent.py directory (e.g. "configs/quick_test.json")
        #   2. Relative to evo_agent.py's configs/ subdirectory (e.g. just "quick_test.json")
        if not config_path.is_absolute() and not config_path.exists():
            script_dir = Path(__file__).parent
            for candidate in [script_dir / config_path, script_dir / "configs" / config_path]:
                if candidate.exists():
                    config_path = candidate
                    break

    if not config_path.exists():
        logger.warning(f"[CONFIG] Config file not found: {config_path}")
        logger.warning(f"[CONFIG] Using default configuration")
        return get_default_config()

    with open(config_path) as f:
        config = json.load(f)

    logger.info(f"[CONFIG] Loaded configuration from: {config_path}")
    return config


def get_default_config() -> dict:
    """Return default configuration."""
    return {
        "experiment_name": "default_run",

        # Evolution parameters
        "population_size": 4,
        "elite_ratio": 0.25,
        "mutation_rate": 0.7,
        "crossover_rate": 0.3,
        "num_generations": 5,
        "num_seeds": 2,
        "reflection_frequency": 2,

        # Dataset configuration
        "dataset_dir": "Vrp_Set_X",
        "smoke_test_instance": None,
        "target_instances": ["X-n101-k25", "X-n106-k14"],

        # VRPAGENT settings
        "use_vrpagent": True,
        "code_length_penalty_alpha": 0.0,

        # Execution settings
        "seed": 42,
        "max_parallel_evals": None,

        # Pluggable evaluator settings
        "evaluator_script": None,
        "evaluator_config": {},

        # Pluggable builder settings
        # Set "builder_script" to a Python file path to use a custom builder.
        # Example: "builder_script": "my_domain/builder.py:MyBuilder"
        # When not set, defaults to AILSBuilder (backward-compatible).
        "builder_script": None,
        "builder_config": {},

        "selection_mode": "scalar",
        "fitness_aggregation": "mean",
        "score_weights": None,
        "primary_score": None,
        "maximize_scores": None,

        # New settings
        "resume": False,
        "debug": True,
        "user_insight": ""
    }


def print_config(config: dict):
    """Print configuration summary."""
    # Minimal output when debug is off
    logger.info(f"[CONFIG] {config.get('experiment_name', 'unnamed')} | "
            f"{config['num_generations']} gens | "
            f"resume={config.get('resume', False)}")

    logger.debug("="*80)
    logger.debug("EVOLUTION CONFIGURATION")
    logger.debug("="*80)
    logger.debug(f"  Experiment: {config.get('experiment_name', 'unnamed')}")
    if config.get('dataset_dir'):
        logger.debug(f"  Dataset: {config['dataset_dir']}")
    if config.get('source_code_root'):
        logger.debug(f"  Source root: {config['source_code_root']}")
    if config.get('target_instances'):
        logger.debug(f"  Instances: {config['target_instances']}")
    logger.debug(f"  Population: {config['population_size']} (elite ratio: {config['elite_ratio']})")
    logger.debug(f"  Generations: {config['num_generations']} (seeds: {config['num_seeds']})")
    logger.debug(f"  Mutation/Crossover: {config['mutation_rate']:.0%}/{config['crossover_rate']:.0%}")
    if config.get('use_vrpagent') is not None:
        logger.debug(f"  VRPAGENT: {config['use_vrpagent']} (penalty α={config.get('code_length_penalty_alpha', 0.0)})")
    logger.debug(f"  Domain: {config.get('domain', 'ails_vrp')}")
    logger.debug(f"  Random seed: {config['seed']}")
    logger.debug(f"  Resume: {config.get('resume', False)}")
    logger.debug(f"  Debug output: {config.get('debug', True)}")
    if config.get('user_insight'):
        logger.debug(f"  User insight: {config['user_insight'][:50]}...")
    if config.get('evaluator_script'):
        logger.debug(f"  Evaluator script: {config['evaluator_script']}")
        logger.debug(f"  Evaluator config: {config.get('evaluator_config', {})}")
    logger.debug(f"  Selection mode: {config.get('selection_mode', 'scalar')}")
    if config.get('selection_mode') == 'pareto':
        logger.debug(f"  Maximize scores: {config.get('maximize_scores')}")
    if config.get('fitness_aggregation', 'mean') != 'mean':
        logger.debug(f"  Fitness aggregation: {config['fitness_aggregation']}")
    logger.debug("="*80)


def clean_candidates_folder(candidates_dir: Path):
    """Remove existing candidates folder for fresh start."""
    if candidates_dir.exists():
        logger.debug(f"[CLEAN] Removing existing candidates folder: {candidates_dir}")
        shutil.rmtree(candidates_dir)
    candidates_dir.mkdir(exist_ok=True)


def run_evolution(config: dict, visualize: bool = False):
    """
    Run evolution with given configuration.

    Args:
        config: Configuration dictionary
    """
    resume = config.get("resume", False)
    debug = config.get("debug", True)
    user_insight = config.get("user_insight", "")

    print_config(config)

    # Determine candidates directory
    project_root = Path(__file__).parent
    candidates_dir = project_root / "candidates"

    # Handle resume vs fresh start
    if not resume:
        clean_candidates_folder(candidates_dir)

    # Build multi-objective config
    mo_config = MultiObjectiveConfig(
        selection_mode=config.get("selection_mode", "scalar"),
        fitness_aggregation=config.get("fitness_aggregation", "mean"),
        score_weights=config.get("score_weights"),
        primary_score=config.get("primary_score"),
        maximize_scores=config.get("maximize_scores"),
    )

    # Create evolution loop — scalar params (population_size, seed, code_length_penalty_alpha, …)
    # are read directly from config inside EvolutionLoop via the 3-level priority chain:
    #   explicit constructor arg (not None) → config dict value → hardcoded default
    evolution = EvolutionLoop(
        user_insight=user_insight,
        multi_objective=mo_config,
        visualize=visualize,
        config=config,
    )

    # Initialize or resume population
    if resume:
        logger.debug(f"[PHASE 1] Attempting to resume from existing candidates...")
        resumed = evolution.resume_from_candidates()
        if not resumed:
            logger.debug(f"[PHASE 1] Resume failed, initializing fresh population with {config['num_seeds']} seeds...")
            evolution.initialize_population(num_seeds=config["num_seeds"])
    else:
        if debug:
            logger.debug(f"[PHASE 1] Initializing population with {config['num_seeds']} seeds...")
        evolution.initialize_population(num_seeds=config["num_seeds"])

    # Run evolution
    if debug:
        logger.debug(f"[PHASE 2] Running {config['num_generations']} generations...")
    evolution.evolve(
        num_generations=config["num_generations"],
        reflection_frequency=config["reflection_frequency"]
    )

    return evolution


def main():
    parser = argparse.ArgumentParser(
        description="EvoAgent - LLM-guided evolution of code components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python evo_agent.py                           # Use configs/default.json
    python evo_agent.py configs/quick_test.json   # Use named preset
    python evo_agent.py -c experiments/exp1.json
    python evo_agent.py --resume             # Resume from existing candidates
    python evo_agent.py --no-debug           # Minimal output (reflections + best only)
    python evo_agent.py -v/-vv               # Enable verbose/extra-verbose logs
    python evo_agent.py --log_path log.out   # Path for writing log file
        """
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to JSON config file (default: configs/default.json)"
    )
    parser.add_argument(
        "-c", "--config",
        dest="config_flag",
        default=None,
        help="Path to JSON config file (alternative syntax)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing candidates (overrides config)"
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Minimal output: only reflections and best candidate per generation"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count", default=0,
        help="Verbosity level ('-v' == DEBUG, '-vv' == TRACE)"
    )
    parser.add_argument(
        "--log_path",
        action="store",
        help="Path to log file. If empty, no log file is generated.",
        type=str
    )
    parser.add_argument(
        "--novisual",
        action="store_true",
        help="Generate data for platform visualization."
    )
    args = parser.parse_args()

    # Determine config path
    config_path = args.config_flag or args.config

    # Load config
    config = load_config(config_path)

    # Remove default logger and add a customized one
    logger.remove()

    # Determine verbosity: command-line args take precedence over config
    verbosity = args.verbose if args.verbose > 0 else config.get("verbose", 0)

    log_level = "INFO"
    if verbosity == 1:
        log_level = "DEBUG"
    elif verbosity >= 2:
        log_level = "TRACE"

    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <level>{message}</level>",
        level=log_level
    )
    if args.log_path is not None:
        logger.add(args.log_path,
            format="<level>{level: <8}</level> | <level>{message}</level>",
            rotation="10 MB"
        )

    # Command line overrides
    if args.resume:
        config["resume"] = True
    if args.no_debug:
        config["debug"] = False

    try:
        evolution = run_evolution(config, not args.novisual)
        logger.success("[DONE] Evolution completed successfully!")
        return 0
    except KeyboardInterrupt:
        logger.warning("[INTERRUPTED] Evolution stopped by user")
        return 1
    except Exception as e:
        logger.error(f"[ERROR] Evolution failed: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
