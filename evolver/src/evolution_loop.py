"""
Evolution Loop with ReEvo-style Reflection

Implements dual-process evolutionary search:
- Generator: Produces new strategies via mutation/crossover
- Reflector: Provides verbal gradients via short-term and long-term reflection

Following ReEvo framework:
- Short-term reflection: Compares parent pairs, guides crossover
- Long-term reflection: Accumulates knowledge, guides elitist mutation
"""

import os
import json
import random
import sqlite3
import time
import networkx as nx
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from loguru import logger

from candidate_manager import CandidateManager
from llm_agents import LLMAgents
from diversity_checker import DiversityChecker
from evaluator import (
    BaseEvaluator,
    EvalResult,
    SmokeTestResult,
    FitnessAggregator,
    compute_candidate_score_vector,
    pareto_select,
    pareto_tournament,
)
from evaluator_loader import create_evaluator
from builder import BaseBuilder
from builder_loader import create_builder
from core.registry import DomainPluginRegistry
import domains  # noqa: F401 — triggers auto-registration of all domain plugins

# TODO: Where do we want this to go? Parameter? Static internal path? Configuration file?
DB_PATH = os.getenv("EVOCODE_DB_PATH", "/data/evolution.db")

def init_db() -> None:
    """Function to initialize empty database with empty tables"""
    # TODO: - We should allow this to be configured through parameters, but for now we will mostly hardcode behaviour
    #       - We also need to add support for resuming; presently we will just overwrite the same DB
    logger.debug(f"[DB INIT] Checking database at {DB_PATH}...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except:
            pass

        # Create table with new schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                generation INTEGER PRIMARY KEY,
                global_best REAL,
                avg_fitness REAL,
                viability_rate REAL,
                diversity REAL,
                timestamp REAL,
                additional_metrics TEXT
            )
        """)

        # Migration logic (safe to keep)
        try:
            conn.execute("SELECT additional_metrics FROM metrics LIMIT 1")
        except sqlite3.OperationalError:
            logger.debug("[DB INIT] Migrating DB: Adding additional_metrics column...")
            conn.execute("ALTER TABLE metrics ADD COLUMN additional_metrics TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                generation INTEGER PRIMARY KEY,
                genealogy_json TEXT,
                best_code_snippet TEXT,
                strategies_json TEXT,
                embeddings_json TEXT
            )
        """)

        # Global strategy table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                idea TEXT PRIMARY KEY,
                direction TEXT,
                status TEXT,
                impact TEXT,
                best_fit REAL
            )
        """)

        # Global reflection table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                generation INTEGER PRIMARY KEY,
                content TEXT,
                timestamp REAL
            )
        """)

    logger.debug("[DB INIT] Database initialized.")

@dataclass
class MultiObjectiveConfig:
    """Configuration for multi-objective optimization.

    Bundles all parameters related to multi-objective selection and
    fitness aggregation into a single object.

    Attributes:
        selection_mode: "scalar" (default) for fitness-based, "pareto" for multi-objective
        fitness_aggregation: Aggregation method ("mean", "weighted", "primary") when
                             evaluator doesn't provide calculate_fitness()
        score_weights: Weights per score name for "weighted" aggregation
        primary_score: Score name for "primary" aggregation
        maximize_scores: Dict mapping score name to whether to maximize (for Pareto selection)
    """
    selection_mode: str = "scalar"
    fitness_aggregation: str = "mean"
    score_weights: Optional[Dict[str, float]] = None
    primary_score: Optional[str] = None
    maximize_scores: Optional[Dict[str, bool]] = None


class EvolutionLoop:
    """Manages the evolutionary search loop with reflection."""

    def __init__(self,
                 population_size: int = 10,
                 elite_ratio: float = 0.2,
                 mutation_rate: float = 0.7,
                 crossover_rate: float = 0.3,
                 target_instances: List[str] = None,
                 seed: int = 42,
                 use_vrpagent: bool = True,
                 code_length_penalty_alpha: float = 0.001,
                 debug: bool = True,
                 user_insight: Optional[List[Dict[str, Any]]] = None,
                 num_workers: int = 2,
                 instance_workers: str | int = "auto",
                 max_parallel_evals: int = None,
                 evaluator: Optional[BaseEvaluator] = None,
                 builder: Optional[BaseBuilder] = None,
                 multi_objective: Optional[MultiObjectiveConfig] = None,
                 visualize: bool = False,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize evolution loop.

        Args:
            population_size: Number of candidates in population
            elite_ratio: Ratio of elites to preserve
            mutation_rate: Probability of mutation vs crossover
            crossover_rate: Probability of crossover (1 - mutation_rate)
            target_instances: List of instance names for evaluation. If None, taken from
                              the domain plugin (via evaluator.get_instances()).
            seed: Random seed
            use_vrpagent: Enable VRPAGENT techniques (biased crossover, typed mutations)
            code_length_penalty_alpha: VRPAGENT code length penalty coefficient
            debug: If True, show all output. If False, only show reflections and best candidate per generation
            user_insight: List of user-provided insights for guiding evolution. Each insight is a dict with:
                - type: "initialize" | "mutate" | "crossover"
                - idea: str describing the user's concept
                - related_population: list of candidate_ids (None for initialize, one for mutate, 2+ for crossover)
            num_workers: Concurrent candidate pipelines (default: 2)
            instance_workers: Parallel instance evaluations per candidate (default: "auto" = cpu_count // num_workers)
            max_parallel_evals: Maximum total parallel workers. If set, intelligently divides budget:
                               instance_workers = min(num_instances, max_parallel_evals)
                               num_workers = max(1, max_parallel_evals // instance_workers)
            evaluator: Optional pre-created BaseEvaluator instance. If None, created via domain plugin.
            builder: Optional pre-created BaseBuilder instance. If None, created via domain plugin.
            multi_objective: Multi-objective optimization config (selection mode, aggregation, etc.)
            config: Full application config dict. Used to select and configure the domain plugin
                    (config["domain"] defaults to "ails_vrp") and for evaluator_script / builder_script overrides.
        """
        mo = multi_objective or MultiObjectiveConfig()

        self.population_size = population_size
        self.elite_size = int(population_size * elite_ratio)
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.use_vrpagent = use_vrpagent
        self.code_length_penalty_alpha = code_length_penalty_alpha
        self.debug = debug
        self.user_insight = user_insight
        self.selection_mode = mo.selection_mode
        self.maximize_scores = mo.maximize_scores
        self.visualize = visualize

        # Compute paths relative to project root (parent of src/)
        project_root = Path(__file__).parent.parent
        self.candidates_dir = project_root / "candidates"

        # Lazily create the domain plugin only when builder/evaluator are not injected.
        # All domain-specific path resolution (AILS jar, data dirs, etc.) happens inside the plugin.
        _plugin = None
        def _get_plugin():
            nonlocal _plugin
            if _plugin is None:
                domain = (config or {}).get("domain", "ails_vrp")
                _plugin = DomainPluginRegistry.create(domain, config or {})
            return _plugin

        # --- Pluggable builder setup ---
        if builder is not None:
            self.builder = builder
        elif (config or {}).get("builder_script"):
            self.builder = create_builder(config)
        else:
            self.builder = _get_plugin().get_builder()

        self.candidate_manager = CandidateManager(
            candidates_dir=str(self.candidates_dir),
            builder=self.builder,
            cache_file=str(self.candidates_dir / "cache.json")
        )

        # --- Pluggable evaluator setup ---
        if evaluator is not None:
            self.evaluator = evaluator
        elif (config or {}).get("evaluator_script"):
            self.evaluator = create_evaluator(config)
        else:
            self.evaluator = _get_plugin().get_evaluator()

        # Target instances: explicit arg > evaluator's own list
        if target_instances is not None:
            self.target_instances = target_instances
        else:
            self.target_instances = self.evaluator.get_instances()

        # Handle max_parallel_evals: controls TOTAL parallelization budget
        if max_parallel_evals is not None:
            num_instances = len(self.target_instances)
            self.instance_workers = min(num_instances, max_parallel_evals)
            self.num_workers = max(1, max_parallel_evals // self.instance_workers)
        else:
            self.num_workers = num_workers
            self.instance_workers = instance_workers

        # Score names from evaluator
        self.score_names = self.evaluator.get_score_names()

        # Fitness aggregator (used when evaluator.calculate_fitness() returns None)
        self.fitness_aggregator = FitnessAggregator(
            method=mo.fitness_aggregation,
            score_weights=mo.score_weights,
            primary_score=mo.primary_score,
        )

        # Pass domain context from builder to LLM agents
        llm_context = self.builder.get_llm_context() if self.builder else {}
        self.llm = LLMAgents(use_llm=True, domain_context=llm_context)

        # Population tracking
        self.population: List[Dict[str, Any]] = []
        self.generation = 0
        self.candidate_counter = 0

        # Reflection tracking (ReEvo-style)
        self.short_term_reflections: List[str] = []  # Recent comparisons
        self.long_term_reflection: Optional[str] = None  # Accumulated knowledge

        # Diversity tracking (Idea-based)
        self.diversity_checker = DiversityChecker(similarity_threshold=0.80)

        # Strategy history tracking for interpretability
        from idea_history_tracker import IdeaHistoryTracker
        self.idea_history = IdeaHistoryTracker()
        self._prev_iteration_best = 0.0  # Track improvement trends
        self._generation_start_counter = 0  # Track candidates tested per generation

        random.seed(seed)

        # Extra DB data
        self.history = {}
        self.strategy_registry: Dict = {}

        if self.visualize:
            init_db()

    @staticmethod
    def _get_instance_workers_static(instance_workers, num_workers: int, num_instances: int) -> int:
        """Calculate instance workers without needing self (for use before __init__ completes)."""
        import os
        if instance_workers == "auto":
            cpu_count = max(1, os.cpu_count())
            workers = max(1, cpu_count // num_workers)
            return min(workers, num_instances)
        else:
            return min(int(instance_workers), num_instances)

    def _get_instance_workers(self) -> int:
        """Calculate number of parallel instance workers per candidate."""
        return self._get_instance_workers_static(
            self.instance_workers, self.num_workers, len(self.target_instances)
        )

    def _compute_fitness(self, eval_results_new: List[EvalResult]) -> float:
        """Compute scalar fitness from new-style EvalResults.

        Asks the evaluator first; falls back to the fitness aggregator.
        """
        fitness = self.evaluator.calculate_fitness(eval_results_new)
        if fitness is not None:
            return fitness
        return self.fitness_aggregator.aggregate(eval_results_new)

    def _compute_score_vector(self, eval_results_new: List[EvalResult]) -> Dict[str, float]:
        """Compute per-score mean vector from EvalResults."""
        return compute_candidate_score_vector(eval_results_new, self.score_names)

    def _eval_results_to_legacy(self, eval_results_new: List[EvalResult]) -> List[Dict]:
        """Convert new EvalResult list to legacy dict format.

        Flattens scores and metadata into a single dict per instance so that
        downstream code (reflection prompts, candidate_manager) sees the same
        keys as before (instance, improvement, initial_cost, final_cost, etc.).
        """
        legacy = []
        for r in eval_results_new:
            d = {
                "instance": r.instance,
                "success": r.success,
            }
            # Flatten scores into the dict
            d.update(r.scores)
            # Flatten metadata into the dict
            d.update(r.metadata)
            if r.error is not None:
                d["error"] = r.error
            legacy.append(d)
        return legacy

    def resume_from_candidates(self) -> bool:
        """
        Resume evolution from existing candidates folder.

        Loads population from saved metadata files, reconstructing the state
        from the last run.

        Returns:
            True if successfully resumed, False if no valid candidates found
        """
        logger.info("[RESUME] Scanning candidates folder for existing population...")

        candidates = []
        max_gen = 0
        max_id = -1

        # Scan all candidate directories
        for candidate_dir in sorted(self.candidates_dir.glob("gen_*")):
            metadata_file = candidate_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)

                # Check if evaluation data exists
                if "evaluation" not in metadata:
                    logger.debug(f"[RESUME] Skipping {candidate_dir.name}: no evaluation data")
                    continue

                # Load the source code via builder (domain-agnostic)
                code_file = None
                if self.builder is not None:
                    code_file = self.builder.get_source_path(candidate_dir, metadata)
                if code_file is None:
                    # Fallback: try legacy AILS path for backward compat
                    strategy_class = metadata.get("strategy_class", "Unknown")
                    code_file = candidate_dir / "src" / "EvoDestroy" / f"{strategy_class}.java"
                if not code_file or not code_file.exists():
                    logger.debug(f"[RESUME] Skipping {candidate_dir.name}: source file not found")
                    continue

                with open(code_file) as f:
                    code = f.read()

                # Reconstruct candidate entry
                eval_data = metadata["evaluation"]
                candidate = {
                    "candidate_id": metadata["candidate_id"],
                    "code": code,
                    "idea": metadata.get("idea"),  # None if missing (backward compat)
                    "metadata": metadata,
                    "eval_results": eval_data.get("instances", []),
                    "fitness": eval_data.get("fitness", 0),
                    "base_fitness": eval_data.get("base_fitness", 0),
                    "generation": eval_data.get("generation", 0),
                    "parent_id": metadata.get("parent_id"),
                    "mutation_type": metadata.get("mutation_type", "unknown"),
                    "score_vector": eval_data.get("score_vector", {}),
                }

                candidates.append(candidate)
                max_gen = max(max_gen, candidate["generation"])
                max_id = max(max_id, candidate["candidate_id"])

            except Exception as e:
                logger.debug(f"[RESUME] Error loading {candidate_dir.name}: {e}")
                continue

        if not candidates:
            logger.info("[RESUME] No valid candidates found to resume from")
            return False

        # Sort by fitness and keep top population_size
        candidates.sort(key=lambda x: x["fitness"], reverse=True)
        self.population = candidates[:self.population_size]
        self.generation = max_gen
        self.candidate_counter = max_id + 1

        logger.info(f"[RESUME] Loaded {len(self.population)} candidates from {len(candidates)} total")
        logger.info(f"[RESUME] Resuming from generation {self.generation}, next candidate ID: {self.candidate_counter}")
        logger.info(f"[RESUME] Best fitness: {self.population[0]['fitness']*100:.4f}%")

        # Rebuild idea history from loaded candidates
        if self.population:
            self._prev_iteration_best = max(c["fitness"] for c in self.population)

            for c in self.population:
                if c.get("idea"):
                    self.idea_history.record_strategy(
                        iteration=c.get("generation", 0),
                        idea=c["idea"],
                        performance=c.get("fitness", 0.0),
                        candidate_id=c["candidate_id"],
                        mutation_type=c.get("mutation_type", "unknown")
                    )

            logger.info(f"[RESUME] Rebuilt idea history with {len(self.idea_history.history)} strategies")

        return True

    def initialize_population(self, num_seeds: int = 3) -> None:
        """
        Initialize population with seed strategies.

        Args:
            num_seeds: Number of seed strategies to generate
        """
        logger.debug(f"[INIT] Generating {num_seeds} seed strategies...")

        for i in range(num_seeds):
            idea, strategy_code = self.llm.generate_initial_seed(i)

            # Build (compile + package)
            result = self.candidate_manager.build_candidate(
                source_code=strategy_code,
                candidate_id=self.candidate_counter,
                idea=idea,
                generation=self.generation,
                mutation_type="initial_seed"
            )

            if not result:
                logger.debug(f"[INIT] Seed {i} failed to build, skipping")
                continue

            # Smoke test
            smoke = self.evaluator.smoke_test(
                result["artifact_path"],
                result["entry_point"]
            )

            if not smoke.success:
                logger.debug(f"[INIT] Seed {i} failed smoke test, skipping")
                continue

            # Evaluate (via pluggable evaluator)
            eval_results_new = self.evaluator.evaluate(
                result["artifact_path"],
                result["entry_point"]
            )
            eval_results = self._eval_results_to_legacy(eval_results_new)
            score_vector = self._compute_score_vector(eval_results_new)

            # Calculate fitness with optional code length penalty
            base_fitness = self._compute_fitness(eval_results_new)
            fitness = self._calculate_fitness_with_penalty(strategy_code, base_fitness)

            # Save evaluation results to metadata
            self.candidate_manager.update_evaluation_results(
                candidate_id=self.candidate_counter,
                eval_results=eval_results,
                fitness=fitness,
                base_fitness=base_fitness,
                generation=0,
                score_vector=score_vector
            )

            self.population.append({
                "candidate_id": self.candidate_counter,
                "code": strategy_code,
                "idea": idea,
                "metadata": result,
                "eval_results": eval_results,
                "fitness": fitness,
                "base_fitness": base_fitness,
                "generation": 0,
                "parent_id": None,
                "mutation_type": "initial_seed",
                "score_vector": score_vector,
            })

            logger.debug(f"[INIT] Seed {i} (ID={self.candidate_counter}): fitness={fitness*100:.4f}%")
            logger.debug(f"[INIT] Idea: {idea[:100]}...")

            # Record strategy in history for interpretability reporting
            if idea and fitness is not None:
                self.idea_history.record_strategy(
                    iteration=self.generation,
                    idea=idea,
                    performance=fitness,
                    candidate_id=self.candidate_counter,
                    mutation_type="initial_seed"
                )
            self.candidate_counter += 1

        logger.debug(f"[INIT] Population size: {len(self.population)}")

    def select_parents(self, tournament_size: int = 3) -> Tuple[Dict, Dict]:
        """
        Select two parents using tournament selection.

        Returns better parent first, worse parent second (for reflection comparison).
        Uses Pareto tournament when selection_mode is "pareto".

        Args:
            tournament_size: Number of candidates in tournament

        Returns:
            Tuple of (better_parent, worse_parent)
        """
        # Adjust tournament size to population size (must be at least 2)
        actual_tournament_size = min(tournament_size, len(self.population))

        # Special case: if only 2 candidates, just return them
        if len(self.population) == 2:
            if self.population[0]["fitness"] >= self.population[1]["fitness"]:
                return self.population[0], self.population[1]
            else:
                return self.population[1], self.population[0]

        use_pareto = (self.selection_mode == "pareto"
                      and len(self.score_names) > 1
                      and any(c.get("score_vector") for c in self.population))

        if use_pareto:
            parent1 = pareto_tournament(
                self.population, actual_tournament_size,
                self.score_names, self.maximize_scores
            )
        else:
            parent1 = max(random.sample(self.population, actual_tournament_size),
                         key=lambda x: x["fitness"])

        # Select second parent, ensuring it's different (with retry limit)
        max_attempts = 20
        attempts = 0
        if use_pareto:
            parent2 = pareto_tournament(
                self.population, actual_tournament_size,
                self.score_names, self.maximize_scores
            )
        else:
            parent2 = max(random.sample(self.population, actual_tournament_size),
                         key=lambda x: x["fitness"])

        while parent1["candidate_id"] == parent2["candidate_id"] and attempts < max_attempts:
            if use_pareto:
                parent2 = pareto_tournament(
                    self.population, actual_tournament_size,
                    self.score_names, self.maximize_scores
                )
            else:
                parent2 = max(random.sample(self.population, actual_tournament_size),
                             key=lambda x: x["fitness"])
            attempts += 1

        # If we still got the same parent after max attempts, pick a different one directly
        if parent1["candidate_id"] == parent2["candidate_id"]:
            different_candidates = [c for c in self.population if c["candidate_id"] != parent1["candidate_id"]]
            if different_candidates:
                parent2 = random.choice(different_candidates)

        # Return better first, worse second (for reflection)
        if parent1["fitness"] >= parent2["fitness"]:
            return parent1, parent2
        else:
            return parent2, parent1

    def reproduce_with_reflection(self) -> Optional[Dict[str, Any]]:
        """
        Generate offspring using reflection-guided reproduction with diversity check.

        Following ReEvo framework:
        - For crossover: Use short-term reflection comparing two parents
        - For mutation: Use long-term reflection (accumulated knowledge)
        - Retry if offspring is not diverse enough (conceptual similarity)

        Returns:
            New candidate dict or None if reproduction failed
        """
        max_diversity_attempts = 3

        for attempt in range(max_diversity_attempts):
            # Decide: mutation or crossover
            use_crossover = random.random() < self.crossover_rate

            if use_crossover and len(self.population) >= 2:
                offspring = self._crossover_with_short_term_reflection()
            else:
                offspring = self._mutate_with_long_term_reflection()

            if offspring is None:
                continue  # Compilation failed, retry

            # CHECK DIVERSITY
            new_idea = offspring.get("idea")
            if new_idea is None:
                logger.debug("[DIVERSITY] No idea in offspring, skipping diversity check")
                return offspring

            population_ideas = [c.get("idea") for c in self.population if c.get("idea") is not None]

            if self.diversity_checker.is_diverse(new_idea, population_ideas):
                logger.debug(f"[DIVERSITY] Offspring is diverse (attempt {attempt+1})")
                return offspring
            else:
                similar = self.diversity_checker.find_most_similar(new_idea, population_ideas)
                if similar:
                    idx, score = similar
                    similar_id = self.population[idx]["candidate_id"]
                    logger.debug(f"[DIVERSITY] Offspring too similar to candidate {similar_id} "
                            f"(similarity={score:.2f}), retrying... (attempt {attempt+1})")
                continue

        logger.debug(f"[DIVERSITY] Failed to generate diverse offspring after {max_diversity_attempts} attempts")
        return None

    def _crossover_with_short_term_reflection(self) -> Optional[Dict[str, Any]]:
        """
        Crossover with short-term reflection guidance.

        ReEvo + VRPAGENT approach:
        1. Select two parents (better and worse)
        2. Generate short-term reflection comparing them
        3. Use reflection + VRPAGENT biased crossover to guide offspring generation
        """
        # Select parents
        better_parent, worse_parent = self.select_parents()

        logger.debug(f"[CROSSOVER] Parents: {better_parent['candidate_id']} (fit={better_parent['fitness']*100:.4f}%) "
              f"x {worse_parent['candidate_id']} (fit={worse_parent['fitness']*100:.4f}%)")

        # Generate short-term reflection
        logger.debug(f"[REFLECTION] Generating short-term reflection...")
        short_term_reflection = self.llm.reflect_short_term(
            better_code=better_parent["code"],
            better_results=better_parent["eval_results"],
            worse_code=worse_parent["code"],
            worse_results=worse_parent["eval_results"]
        )

        # Store for long-term accumulation
        self.short_term_reflections.append(short_term_reflection)
        logger.success(f"[REFLECTION] Short-term insight: {short_term_reflection[:200]}...")

        # Get parent ideas for context
        parent1_idea = better_parent.get("idea")
        parent2_idea = worse_parent.get("idea")

        # Generate offspring using reflection + optional VRPAGENT bias
        offspring_idea, offspring_code = self.llm.crossover(
            parent1_code=better_parent["code"],
            parent2_code=worse_parent["code"],
            parent1_results=better_parent["eval_results"],
            parent2_results=worse_parent["eval_results"],
            short_term_reflection=short_term_reflection,
            parent1_idea=parent1_idea,
            parent2_idea=parent2_idea,
            use_vrpagent_bias=self.use_vrpagent,
            elite_bias=0.75  # VRPAGENT: 75% from elite, 25% from non-elite
        )

        return self._compile_and_evaluate_offspring(
            offspring_code,
            offspring_idea,
            parent_id=better_parent["candidate_id"],
            mutation_type="crossover"
        )

    def _generate_with_user_insight(self) -> List[Dict[str, Any]]:
        """
        Generate offspring using user-provided insights.

        The user_insight should be a list of insight dicts, each with keys:
        - type: "initialize", "mutate", or "crossover"
        - idea: str describing the user's concept
        - related_population: list of candidate_ids (ignored for initialize,
          single for mutate, 2+ for crossover)

        This allows multiple operations in one call:
        - Initialize multiple new directions
        - Mutate different candidates with different ideas
        - Crossover between specific candidate groups

        Returns:
            List of new candidate dicts (may be empty if all generations failed)
        """
        if not self.user_insight:
            logger.debug("[USER_INSIGHT] No user insight provided")
            return []

        # Parse user_insight if it's a string (JSON)
        if isinstance(self.user_insight, str):
            try:
                insights = json.loads(self.user_insight)
            except json.JSONDecodeError as e:
                logger.debug(f"[USER_INSIGHT] Failed to parse user_insight as JSON: {e}")
                return []
        else:
            insights = self.user_insight

        # Ensure insights is a list
        if not isinstance(insights, list):
            logger.debug("[USER_INSIGHT] user_insight should be a list of insight dicts")
            return []

        if not insights:
            logger.debug("[USER_INSIGHT] Empty user_insight list")
            return []

        logger.debug(f"[USER_INSIGHT] Processing {len(insights)} user insights")

        # Build candidate lookup from population
        id_to_candidate = {c["candidate_id"]: c for c in self.population}

        offspring_list = []
        for i, insight in enumerate(insights):
            logger.debug(f"\n[USER_INSIGHT] Processing insight {i + 1}/{len(insights)}")

            # Validate required fields
            insight_type = insight.get("type")
            idea = insight.get("idea")

            if not insight_type:
                logger.debug(f"[USER_INSIGHT] Insight {i}: Missing 'type' field, skipping")
                continue
            if not idea:
                logger.debug(f"[USER_INSIGHT] Insight {i}: Missing 'idea' field, skipping")
                continue

            valid_types = ["initialize", "mutate", "crossover"]
            if insight_type not in valid_types:
                logger.debug(f"[USER_INSIGHT] Insight {i}: Invalid type '{insight_type}', skipping")
                continue

            # Get related population candidate IDs
            related_ids = insight.get("related_population", [])

            # Resolve related candidates from population
            related_candidates = []
            if related_ids:
                for cid in related_ids:
                    if cid in id_to_candidate:
                        related_candidates.append(id_to_candidate[cid])
                    else:
                        logger.debug(f"[USER_INSIGHT] Warning: candidate_id {cid} not found in population")

            # Validate related_candidates based on type
            if insight_type == "initialize":
                if related_candidates:
                    logger.debug(f"[USER_INSIGHT] Insight {i}: 'initialize' type ignores related_population")
                related_candidates = None
            elif insight_type == "mutate":
                if not related_candidates:
                    logger.debug(f"[USER_INSIGHT] Insight {i}: 'mutate' requires one candidate, skipping")
                    continue
                if len(related_candidates) > 1:
                    logger.debug(f"[USER_INSIGHT] Insight {i}: 'mutate' expects one candidate, using first")
                related_candidates = [related_candidates[0]]
            elif insight_type == "crossover":
                if len(related_candidates) < 2:
                    logger.debug(f"[USER_INSIGHT] Insight {i}: 'crossover' requires 2+ candidates, skipping")
                    continue

            logger.debug(f"[USER_INSIGHT] Insight {i}: type='{insight_type}', idea='{idea[:50]}...'")
            if related_candidates:
                logger.debug(f"[USER_INSIGHT] Insight {i}: Related candidates: {[c['candidate_id'] for c in related_candidates]}")

            # Generate using LLM with user insight
            try:
                offspring_idea, offspring_code = self.llm.generate_with_user_insight(
                    insight_type=insight_type,
                    idea=idea,
                    related_candidates=related_candidates,
                    long_term_reflection=self.long_term_reflection
                )

                # Determine parent_id for tracking
                parent_id = None
                if related_candidates:
                    parent_id = related_candidates[0]["candidate_id"]

                offspring = self._compile_and_evaluate_offspring(
                    offspring_code,
                    offspring_idea,
                    parent_id=parent_id,
                    mutation_type=f"user_insight_{insight_type}"
                )

                if offspring:
                    offspring_list.append(offspring)
                    logger.debug(f"[USER_INSIGHT] Insight {i}: Successfully generated candidate {offspring['candidate_id']}")
                else:
                    logger.debug(f"[USER_INSIGHT] Insight {i}: Failed to compile/evaluate offspring")

            except Exception as e:
                logger.debug(f"[USER_INSIGHT] Insight {i}: Error during generation: {e}")
                continue

        logger.debug(f"\n[USER_INSIGHT] Generated {len(offspring_list)} offspring from {len(insights)} insights")
        return offspring_list

    def _mutate_with_long_term_reflection(self) -> Optional[Dict[str, Any]]:
        """
        Elitist mutation with long-term reflection guidance.

        ReEvo + VRPAGENT approach:
        1. Select elite parent
        2. Select mutation type (VRPAGENT: ablation/extend/adjust_parameters/refactor)
        3. Use accumulated long-term reflection to guide typed mutation
        """
        # Select elite parent
        elite_parent = max(self.population, key=lambda x: x["fitness"])

        logger.debug(f"[MUTATION] Elite parent: {elite_parent['candidate_id']} (fit={elite_parent['fitness']*100:.4f}%)")

        # Select mutation type (VRPAGENT)
        if self.use_vrpagent:
            from vrpagent_prompts import VRPAgentPrompts
            mutation_type = VRPAgentPrompts.select_mutation_type(
                elite_code=elite_parent["code"],
                generation=self.generation,
                long_term_reflection=self.long_term_reflection
            )
            logger.debug(f"[MUTATION] Selected type: {mutation_type}")
        else:
            mutation_type = None

        # Get parent idea for context
        parent_idea = elite_parent.get("idea")

        # Generate offspring using long-term reflection + optional typed mutation
        offspring_idea, offspring_code = self.llm.mutate(
            parent_code=elite_parent["code"],
            parent_results=elite_parent["eval_results"],
            long_term_reflection=self.long_term_reflection,
            parent_idea=parent_idea,
            mutation_strength=0.3,
            mutation_type=mutation_type,
            generation=self.generation
        )

        return self._compile_and_evaluate_offspring(
            offspring_code,
            offspring_idea,
            parent_id=elite_parent["candidate_id"],
            mutation_type=mutation_type or "mutation"
        )

    def _compile_and_evaluate_offspring(self,
                                       offspring_code: str,
                                       offspring_idea: str,
                                       parent_id: int,
                                       mutation_type: str) -> Optional[Dict[str, Any]]:
        """Build and evaluate offspring."""
        # Build (compile + package)
        result = self.candidate_manager.build_candidate(
            source_code=offspring_code,
            candidate_id=self.candidate_counter,
            idea=offspring_idea,
            generation=self.generation,
            parent_id=parent_id,
            mutation_type=mutation_type
        )

        if not result:
            logger.debug(f"[OFFSPRING] Build failed")
            return None

        # Smoke test
        smoke = self.evaluator.smoke_test(
            result["artifact_path"],
            result["entry_point"]
        )

        if not smoke.success:
            logger.debug(f"[OFFSPRING] Smoke test failed")
            return None

        # Evaluate (via pluggable evaluator)
        eval_results_new = self.evaluator.evaluate(
            result["artifact_path"],
            result["entry_point"]
        )
        eval_results = self._eval_results_to_legacy(eval_results_new)
        score_vector = self._compute_score_vector(eval_results_new)

        # Calculate fitness with optional code length penalty
        base_fitness = self._compute_fitness(eval_results_new)
        fitness = self._calculate_fitness_with_penalty(offspring_code, base_fitness)

        # Save evaluation results to metadata
        self.candidate_manager.update_evaluation_results(
            candidate_id=self.candidate_counter,
            eval_results=eval_results,
            fitness=fitness,
            base_fitness=base_fitness,
            generation=self.generation,
            score_vector=score_vector
        )

        offspring = {
            "candidate_id": self.candidate_counter,
            "code": offspring_code,
            "idea": offspring_idea,
            "metadata": result,
            "eval_results": eval_results,
            "fitness": fitness,
            "base_fitness": base_fitness,
            "generation": self.generation,
            "parent_id": parent_id,
            "mutation_type": mutation_type,
            "score_vector": score_vector,
        }

        logger.debug(f"[OFFSPRING] ID={self.candidate_counter}: fitness={fitness*100:.4f}%")
        if offspring_idea:
            idea_preview = offspring_idea[:100] + "..." if len(offspring_idea) > 100 else offspring_idea
            logger.debug(f"[OFFSPRING] Idea: {idea_preview}")

        # Record strategy in history for interpretability reporting
        if offspring_idea and fitness is not None:
            self.idea_history.record_strategy(
                iteration=self.generation,
                idea=offspring_idea,
                performance=fitness,
                candidate_id=self.candidate_counter,
                mutation_type=mutation_type
            )
        self.candidate_counter += 1

        return offspring

    def update_long_term_reflection(self) -> None:
        """
        Update long-term reflection by synthesizing recent short-term reflections.

        Following ReEvo: Distill accumulated experiences into concise knowledge base.
        """
        if not self.short_term_reflections:
            logger.debug(f"[REFLECTION] No short-term reflections to synthesize yet")
            return

        logger.debug(f"[REFLECTION] Updating long-term knowledge (gen={self.generation})...")
        logger.debug(f"[REFLECTION] Synthesizing {len(self.short_term_reflections)} recent insights...")

        self.long_term_reflection = self.llm.reflect_long_term(
            recent_short_term_reflections=self.short_term_reflections,
            previous_long_term_reflection=self.long_term_reflection,
            generation=self.generation
        )

        # Display formatted reflection
        self._display_long_term_reflection()

        # Clear short-term buffer (already distilled into long-term)
        self.short_term_reflections = []

    def survival_selection(self) -> None:
        """
        Select survivors for next generation.

        Uses Pareto-based NSGA-II selection when selection_mode is "pareto"
        and multiple scores are available. Otherwise uses elitist scalar selection.
        """
        if (self.selection_mode == "pareto"
                and len(self.score_names) > 1
                and any(c.get("score_vector") for c in self.population)):
            self.population = pareto_select(
                self.population,
                self.population_size,
                self.score_names,
                self.maximize_scores,
            )
            # Sort by fitness for reporting
            self.population.sort(key=lambda x: x["fitness"], reverse=True)
        else:
            # Sort by fitness (descending)
            self.population.sort(key=lambda x: x["fitness"], reverse=True)
            # Keep top population_size
            self.population = self.population[:self.population_size]

        logger.debug(f"[SELECTION] Population after selection: {len(self.population)} candidates")
        logger.debug(f"[SELECTION] Top fitness: {self.population[0]['fitness']*100:.4f}%")
        logger.debug(f"[SELECTION] Worst fitness: {self.population[-1]['fitness']*100:.4f}%")

    def evolve(self, num_generations: int = 10, reflection_frequency: int = 3) -> None:
        """
        Run evolution loop with reflection.

        Args:
            num_generations: Number of generations to evolve
            reflection_frequency: How often to update long-term reflection
        """
        logger.info(f"{'='*80}")
        logger.info(f"STARTING EVOLUTION: {num_generations} generations")
        logger.debug(f"MODE: Work-stealing pipeline (workers={self.num_workers}, instance_workers={self._get_instance_workers()})")
        logger.info(f"{'='*80}")

        # Process user insights before main evolution loop
        if self.user_insight:
            logger.info(f"\n{'='*80}")
            logger.info(f"PROCESSING USER INSIGHTS")
            logger.info(f"{'='*80}")
            user_offspring = self._generate_with_user_insight()
            for offspring in user_offspring:
                self.population.append(offspring)
            logger.info(f"[USER_INSIGHT] Added {len(user_offspring)} candidates to population")
            # Apply survival selection if population exceeds limit
            if len(self.population) > self.population_size:
                self.survival_selection()

        for gen in range(num_generations):
            self.generation = gen + 1
            logger.info(f"{'='*80}")
            logger.info(f"GENERATION {self.generation}")
            logger.info(f"{'='*80}")

            # Track candidates at start of generation for statistics
            self._generation_start_counter = self.candidate_counter

            # Generate offspring using work-stealing pipeline
            num_offspring = self.population_size - self.elite_size
            offspring_list = self._evolve_generation_batch(num_offspring)
            for offspring in offspring_list:
                self.population.append(offspring)
            offspring_count = len(offspring_list)

            logger.debug(f"[GEN {self.generation}] Generated {offspring_count} valid offspring")

            # Survival selection
            self.survival_selection()

            if self.generation > 0:
                self._report_strategy_progress()

            # Update long-term reflection periodically
            if self.generation % reflection_frequency == 0:
                self.update_long_term_reflection()

            # Update DB
            if self.visualize:
                self._log_generation_to_db(offspring_list, num_offspring)

            # Report iteration statistics (always shown)
            self._report_iteration_statistics()

        # Final statistics
        self.print_final_statistics()

        # Save idea evolution log
        self.save_idea_evolution_log()

    def _log_generation_to_db(self, offspring_list: list, num_attempted: int):
        """
        Centralized DB logging: Updates Global Strategy Table + Snapshots.
        """
        DB_PATH = "/data/evolution.db"

        viability = len(offspring_list) / num_attempted if num_attempted > 0 else 0.0

        if not self.population:
            return

        fitnesses = [c["fitness"] for c in self.population]
        best_candidate = max(self.population, key=lambda x: x["fitness"])

        global_best = best_candidate["fitness"]
        avg_fitness = np.mean(fitnesses)
        diversity = np.var(fitnesses)

        # Geneaology tree
        for child in offspring_list:
            self.history[child['candidate_id']] = child

        for ind in self.population:
            if ind['candidate_id'] not in self.history:
                self.history[ind['candidate_id']] = ind

        G = nx.DiGraph()
        living_ids = {ind['candidate_id'] for ind in self.population}

        for cid, data in self.history.items():
            is_alive = cid in living_ids
            G.add_node(
                cid,
                fitness=data.get("fitness", 0),
                code=data.get("code", ""),
                label=str(cid),
                alive=is_alive,
                generation=data.get("generation", 0)
            )

            if data.get("parent_id") in self.history:
                G.add_edge(data.get("parent_id"), cid)

        genealogy_json = json.dumps(nx.node_link_data(G))

        # Directions Data
        for child in offspring_list:
            idea_key = child.get("idea")
            if not idea_key or len(idea_key) < 5:
                continue

            child_fitness = child.get("fitness", 0.0)
            mutation_type = child.get("mutation_type", "Evolution")

            # Initialize or Update
            if idea_key not in self.strategy_registry:
                status = "Succeeded" if child_fitness > avg_fitness else "Exploring"
                self.strategy_registry[idea_key] = {
                    "Direction": mutation_type,
                    "Idea": idea_key,
                    "Status": status,
                    "Impact": f"{child_fitness:.4f}",
                    "Best_Fit": child_fitness
                }
            else:
                entry = self.strategy_registry[idea_key]
                prev_best = entry.get("Best_Fit", -float('inf'))

                if child_fitness > prev_best:
                    entry["Best_Fit"] = child_fitness
                    entry["Impact"] = f"{child_fitness:.4f}"
                    if child_fitness > avg_fitness:
                        entry["Status"] = "Succeeded"

                if entry["Status"] == "Exploring" and child_fitness < (avg_fitness * 0.8):
                     entry["Status"] = "Abandoned"

        # Reflections
        reflection_content = getattr(self, "long_term_reflection", "")

        # Embeddings data
        embeddings = []
        for child in offspring_list:
            fitness = child.get("fitness", 0.0)
            score_dict = child.get("score_vector", {})

            if not isinstance(score_dict, dict): score_dict = {}

            clean_values = []
            for k in sorted(score_dict.keys()):
                val = score_dict[k]
                if val == float('inf') or val == -float('inf'): val = 0.0
                clean_values.append(val)

            if len(clean_values) >= 2:
                x_val, y_val = clean_values[0], clean_values[1]
            elif len(clean_values) == 1:
                x_val, y_val = clean_values[0], clean_values[0]
            else:
                x_val, y_val = 0.0, 0.0

            embeddings.append({
                "x": x_val, "y": y_val,
                "Strategy Cluster": str(child.get("mutation_type", "Initial")),
                "Fitness": fitness
            })
        embeddings_json = json.dumps(embeddings)

        # Put in DB now
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                except:
                    pass

                # Sync Registry to Global Table
                for s in self.strategy_registry.values():
                    conn.execute(
                        "INSERT OR REPLACE INTO strategies VALUES (?, ?, ?, ?, ?)",
                        (s["Idea"], s["Direction"], s["Status"], s["Impact"], s.get("Best_Fit", 0.0))
                    )

                # Insert Metrics
                conn.execute(
                    "INSERT OR REPLACE INTO metrics VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (self.generation, global_best, avg_fitness, viability, diversity, time.time(), "{}")
                )

                # Insert Snapshot
                # We still write 'strategies_json' here for backward compatibility with your current dashboard,
                # but the global 'strategies' table is now the source of truth.
                current_strategies_list = json.dumps(list(self.strategy_registry.values()))

                conn.execute(
                    "INSERT OR REPLACE INTO snapshots VALUES (?, ?, ?, ?, ?)",
                    (self.generation, genealogy_json, best_candidate.get("code", ""),
                     current_strategies_list, embeddings_json)
                )

                conn.execute(
                    "INSERT OR REPLACE INTO reflections VALUES (?, ?, ?)",
                    (self.generation, reflection_content, time.time())
                )

        except Exception as e:
            # Replace with logger.error if available
            print(f"[DB Error] Failed to log generation {self.generation}: {e}")

    def _evolve_generation_batch(self, num_offspring: int) -> List[Dict[str, Any]]:
        """
        Evolve one generation using work-stealing pipeline.

        Each worker handles a complete candidate: Generate → Compile → Smoke → Evaluate
        Workers pull tasks from a shared queue until all offspring are processed.
        """
        from queue import Queue
        from threading import Thread, Lock

        # Task queue: indices of offspring to generate
        task_queue = Queue()
        for i in range(num_offspring):
            task_queue.put(i)

        # Results collection
        results = []
        results_lock = Lock()

        # Track candidate IDs
        candidate_id_counter = [self.candidate_counter]
        candidate_id_lock = Lock()

        def get_next_candidate_id():
            with candidate_id_lock:
                cid = candidate_id_counter[0]
                candidate_id_counter[0] += 1
                return cid

        # Sentinel for stopping workers
        DONE = object()

        def worker(worker_id):
            """Process candidates end-to-end: Generate → Compile → Smoke → Evaluate."""
            while True:
                task = task_queue.get()
                if task is DONE:
                    task_queue.task_done()
                    break

                idx = task
                candidate_id = get_next_candidate_id()

                try:
                    # === Stage 1: Generate ===
                    use_crossover = random.random() < self.crossover_rate

                    if use_crossover and len(self.population) >= 2:
                        better_parent, worse_parent = self.select_parents()
                        logger.debug(f"[Worker{worker_id}] Generating offspring {idx+1}/{num_offspring}: Crossover {better_parent['candidate_id']} x {worse_parent['candidate_id']}")

                        short_term_reflection = self.llm.reflect_short_term(
                            better_code=better_parent["code"],
                            better_results=better_parent["eval_results"],
                            worse_code=worse_parent["code"],
                            worse_results=worse_parent["eval_results"]
                        )
                        with results_lock:
                            self.short_term_reflections.append(short_term_reflection)

                        # Get parent ideas for context
                        parent1_idea = better_parent.get("idea")
                        parent2_idea = worse_parent.get("idea")

                        offspring_idea, offspring_code = self.llm.crossover(
                            parent1_code=better_parent["code"],
                            parent2_code=worse_parent["code"],
                            parent1_results=better_parent["eval_results"],
                            parent2_results=worse_parent["eval_results"],
                            short_term_reflection=short_term_reflection,
                            parent1_idea=parent1_idea,
                            parent2_idea=parent2_idea,
                            use_vrpagent_bias=self.use_vrpagent,
                            elite_bias=0.75
                        )
                        parent_id = better_parent["candidate_id"]
                        mutation_type = "crossover"
                    else:
                        elite_parent = max(self.population, key=lambda x: x["fitness"])
                        logger.debug(f"[Worker{worker_id}] Generating offspring {idx+1}/{num_offspring}: Mutation from elite {elite_parent['candidate_id']}")

                        mutation_type = None
                        if self.use_vrpagent:
                            from vrpagent_prompts import VRPAgentPrompts
                            mutation_type = VRPAgentPrompts.select_mutation_type(
                                elite_code=elite_parent["code"],
                                generation=self.generation,
                                long_term_reflection=self.long_term_reflection
                            )

                        # Get parent idea for context
                        parent_idea = elite_parent.get("idea")

                        offspring_idea, offspring_code = self.llm.mutate(
                            parent_code=elite_parent["code"],
                            parent_results=elite_parent["eval_results"],
                            long_term_reflection=self.long_term_reflection,
                            parent_idea=parent_idea,
                            mutation_strength=0.3,
                            mutation_type=mutation_type,
                            generation=self.generation
                        )
                        parent_id = elite_parent["candidate_id"]
                        mutation_type = mutation_type or "mutation"

                    # === Stage 2: Build (compile + package) ===
                    compile_result = self.candidate_manager.build_candidate(
                        source_code=offspring_code,
                        candidate_id=candidate_id,
                        idea=offspring_idea,
                        generation=self.generation,
                        parent_id=parent_id,
                        mutation_type=mutation_type
                    )

                    if not compile_result:
                        logger.warning(f"[Worker{worker_id}] Candidate {candidate_id} failed to build")
                        continue

                    logger.debug(f"[Worker{worker_id}] Candidate {candidate_id} built")

                    # === Stage 3: Smoke Test ===
                    smoke_result = self.evaluator.smoke_test(
                        compile_result["artifact_path"],
                        compile_result["entry_point"]
                    )

                    if not smoke_result.success:
                        logger.warning(f"[Worker{worker_id}] Candidate {candidate_id} failed smoke test")
                        continue

                    logger.debug(f"[Worker{worker_id}] Candidate {candidate_id} passed smoke test")

                    # === Stage 4: Evaluate (via pluggable evaluator) ===
                    eval_results_new = self.evaluator.evaluate(
                        compile_result["artifact_path"],
                        compile_result["entry_point"]
                    )
                    eval_results = self._eval_results_to_legacy(eval_results_new)
                    score_vector = self._compute_score_vector(eval_results_new)

                    base_fitness = self._compute_fitness(eval_results_new)
                    fitness = self._calculate_fitness_with_penalty(offspring_code, base_fitness)

                    # Save evaluation results
                    self.candidate_manager.update_evaluation_results(
                        candidate_id=candidate_id,
                        eval_results=eval_results,
                        fitness=fitness,
                        base_fitness=base_fitness,
                        generation=self.generation,
                        score_vector=score_vector
                    )

                    offspring = {
                        "candidate_id": candidate_id,
                        "code": offspring_code,
                        "idea": offspring_idea,
                        "metadata": compile_result,
                        "eval_results": eval_results,
                        "fitness": fitness,
                        "base_fitness": base_fitness,
                        "generation": self.generation,
                        "parent_id": parent_id,
                        "mutation_type": mutation_type,
                        "score_vector": score_vector,
                    }

                    with results_lock:
                        results.append(offspring)

                    logger.info(f"[Worker{worker_id}] Candidate {candidate_id} complete: fitness={fitness*100:.4f}%")

                except Exception as e:
                    logger.error(f"[Worker{worker_id}] Candidate {candidate_id} failed with error: {e}")

                finally:
                    task_queue.task_done()

        # === Start Workers ===
        actual_workers = min(self.num_workers, num_offspring)
        logger.debug(f"[PIPELINE] Starting {actual_workers} workers for {num_offspring} offspring")

        workers = [Thread(target=worker, args=(i,), daemon=True) for i in range(actual_workers)]
        for w in workers:
            w.start()

        # Wait for all tasks to complete
        task_queue.join()

        # Signal workers to stop
        for _ in range(actual_workers):
            task_queue.put(DONE)

        # Wait for workers to finish
        for w in workers:
            w.join(timeout=1)

        # Update candidate counter
        self.candidate_counter = candidate_id_counter[0]

        logger.debug(f"[PIPELINE] Complete: {len(results)}/{num_offspring} offspring evaluated")
        return results

    def _calculate_fitness_with_penalty(self, code: str, base_fitness: float) -> float:
        """
        Calculate fitness with optional VRPAGENT code length penalty.

        Args:
            code: Java source code
            base_fitness: Base fitness from evaluator

        Returns:
            Penalized fitness (lower is worse due to penalty)
        """
        if not self.use_vrpagent or self.code_length_penalty_alpha == 0:
            return base_fitness

        from vrpagent_prompts import VRPAgentPrompts
        penalty = VRPAgentPrompts.calculate_code_length_penalty(
            code, alpha=self.code_length_penalty_alpha
        )

        # Penalized fitness = base_fitness - penalty
        # (Higher base fitness is better, penalty reduces it)
        penalized_fitness = base_fitness - penalty

        return penalized_fitness

    def _display_long_term_reflection(self) -> None:
        """Format and display long-term reflection in a clean, readable format."""
        if not self.long_term_reflection:
            return

        # Parse the reflection into sections
        lines = self.long_term_reflection.strip().split('\n')

        # Print header
        logger.info("")
        logger.info("=" * 80)
        logger.info("CUMULATIVE KNOWLEDGE - Strategic Insights")
        logger.info("=" * 80)

        current_section = None
        section_items = []

        for line in lines:
            stripped = line.strip()

            # Detect section headers (lines starting with ##)
            if stripped.startswith('##'):
                # Print previous section if exists
                if current_section and section_items:
                    logger.info(f" ")
                    logger.info(f"{current_section}")
                    logger.info("-" * 60)
                    for item in section_items:
                        logger.info(f"  {item}")
                    section_items = []

                # Start new section
                current_section = stripped.replace('##', '').strip()

            # Detect bullet points
            elif stripped.startswith('-') or stripped.startswith('*'):
                # Clean up bullet and extract content
                content = stripped.lstrip('-*').strip()
                # Handle bold markdown **text**
                content = content.replace('**', '')
                section_items.append(f"• {content}")

            # Handle non-empty lines that aren't headers or bullets
            elif stripped and not stripped.startswith('='):
                section_items.append(f"  {stripped}")

        # Print final section
        if current_section and section_items:
            logger.info(f" ")
            logger.info(f"{current_section}")
            logger.info("-" * 60)
            for item in section_items:
                logger.info(f"  {item}")

        logger.info("")
        logger.info("=" * 80)

    def _report_iteration_statistics(self) -> None:
        """Report comprehensive statistics for current iteration."""
        # Calculate fitness statistics
        fitnesses = [c["fitness"] for c in self.population]
        best = max(self.population, key=lambda x: x["fitness"])
        worst = min(self.population, key=lambda x: x["fitness"])
        avg_fitness = sum(fitnesses) / len(fitnesses)

        # Count variations tested
        # This generation: calculate from candidate_counter difference
        gen_tested = self.candidate_counter - self._generation_start_counter

        # Total tested: all candidates created so far
        total_tested = self.candidate_counter

        # Report using logger.info
        logger.info("")
        logger.info("-" * 80)
        logger.info(f"Generation {self.generation} - Statistics Summary")
        logger.info("-" * 80)
        logger.info(f"  Candidates tested this generation: {gen_tested}")
        logger.info(f"  Total candidates tested: {total_tested}")
        logger.info(f"  Best solution: ID={best['candidate_id']}, fitness={best['fitness']*100:.4f}%")

        # Show best idea on new line
        best_idea = best.get('idea', 'N/A')
        if len(best_idea) > 120:
            best_idea = best_idea[:117] + "..."
        logger.info(f"  Best idea: {best_idea}")

        logger.info(f"  Worst solution: ID={worst['candidate_id']}, fitness={worst['fitness']*100:.4f}%")
        logger.info(f"  Average population fitness: {avg_fitness*100:.4f}%")
        logger.info("-" * 80)

    def _report_strategy_progress(self) -> None:
        """Generate and display strategy progress report for user interpretability."""

        # Gather current strategies with performance
        current_strategies = [
            {
                "idea": c.get("idea"),
                "performance": c.get("fitness", 0.0),
                "candidate_id": c.get("candidate_id")
            }
            for c in self.population
            if c.get("idea") is not None
        ]

        # Skip if no ideas
        if not current_strategies:
            return

        # Get historical context (limit to recent for manageable prompt size)
        historical_ideas = self.idea_history.get_historical_ideas_with_performance(limit=15)

        # Performance metrics
        fitnesses = [c["fitness"] for c in self.population]
        perf_summary = self.idea_history.get_performance_summary()

        performance_metrics = {
            "best": max(fitnesses),
            "average": sum(fitnesses) / len(fitnesses),
            "total_tested": perf_summary.get("total_tested", 0),
            "improvement": 0.0
        }

        # Calculate improvement from previous iteration
        if hasattr(self, '_prev_iteration_best'):
            performance_metrics["improvement"] = performance_metrics["best"] - self._prev_iteration_best

        self._prev_iteration_best = performance_metrics["best"]

        # Call LLM for analysis
        analysis = self.llm.analyze_strategy_directions(
            current_strategies=current_strategies,
            historical_ideas=historical_ideas,
            long_term_reflection=self.long_term_reflection,
            iteration=self.generation,
            performance_metrics=performance_metrics
        )

        # Display to user (always visible using reflection logging)
        logger.info(
            f"\n{'='*70}\n"
            f"EXPOLRATION STRATEGIES - Iteration {self.generation}\n"
            f"{'='*70}\n"
            f"{analysis}\n"
            f"{'='*70}\n"
        )

    def print_final_statistics(self) -> None:
        """Print final evolution statistics (always shown)."""
        best = max(self.population, key=lambda x: x["fitness"])

        logger.info(f"{'='*80}")
        logger.info(f"FINAL STATISTICS")
        logger.info(f"{'='*80}")
        logger.info(f"Total candidates evaluated: {self.candidate_counter}")
        logger.info(f"Final population size: {len(self.population)}")
        logger.info(f"Best candidate ID: {best['candidate_id']}")
        logger.info(f"Best fitness: {best['fitness']*100:.4f}%")
        if self.use_vrpagent and "base_fitness" in best:
            logger.info(f"Best base fitness (no penalty): {best['base_fitness']*100:.4f}%")
        logger.info(f"Best generation: {best['generation']}")

        # Show best candidate's idea
        if best.get("idea"):
            logger.info(f"")
            logger.info(f"Best candidate idea:")
            logger.info(f"  {best['idea']}")

        logger.info(f"Best candidate performance:")
        for result in best["eval_results"]:
            instance_name = result.get('instance', result.get('name', 'unknown'))
            improvement = result.get('improvement', result.get('improvement_pct', 0) / 100)
            logger.info(f"  {instance_name}: {improvement*100:.3f}% improvement")

        # Code length statistics
        if self.use_vrpagent:
            code_lines = len([l for l in best["code"].split('\n')
                            if l.strip() and not l.strip().startswith('//')
                            and not l.strip().startswith('package')
                            and not l.strip().startswith('import')])
            logger.info(f"Best candidate code length: {code_lines} lines")

        logger.info(f"\n{'='*80}\n")

    def save_idea_evolution_log(self, log_file: str = None) -> None:
        """Save evolution history of ideas for analysis."""
        if log_file is None:
            log_file = str(self.candidates_dir / "idea_evolution.md")

        with open(log_file, 'w') as f:
            f.write("# Idea Evolution Log\n\n")
            f.write(f"Generated from {len(self.population)} candidates\n\n")

            # Sort by generation
            sorted_pop = sorted(self.population, key=lambda x: x.get("generation", 0))

            for candidate in sorted_pop:
                f.write(f"## Generation {candidate.get('generation', 0)} - "
                       f"Candidate {candidate['candidate_id']}\n\n")
                f.write(f"**Fitness:** {candidate['fitness']*100:.4f}%\n\n")
                f.write(f"**Mutation Type:** {candidate.get('mutation_type', 'unknown')}\n\n")

                if candidate.get("parent_id") is not None:
                    f.write(f"**Parent ID:** {candidate['parent_id']}\n\n")

                if candidate.get("idea"):
                    f.write("### Idea\n\n")
                    f.write(candidate["idea"])
                    f.write("\n\n")
                else:
                    f.write("*[No idea available - legacy candidate]*\n\n")

                f.write("---\n\n")

        logger.info(f"[LOG] Saved idea evolution to {log_file}")


# Example usage
if __name__ == "__main__":
    logger.debug("="*80)
    logger.debug("ReEvo-style Evolution Loop for VRP Destroy Strategies")
    logger.debug("="*80)

    # Create evolution loop
    evolution = EvolutionLoop(
        population_size=20,
        elite_ratio=0.2,
        mutation_rate=0.7,
        crossover_rate=0.3,
        seed=42
    )

    # Initialize population with seeds
    evolution.initialize_population(num_seeds=3)

    # Run evolution
    evolution.evolve(
        num_generations=10,
        reflection_frequency=3  # Update long-term reflection every 3 generations
    )
