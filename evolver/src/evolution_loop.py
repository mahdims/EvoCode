"""
Evolution Loop with ReEvo-style Reflection

Implements dual-process evolutionary search:
- Generator: Produces new strategies via mutation/crossover
- Reflector: Provides verbal gradients via short-term and long-term reflection

Following ReEvo framework:
- Short-term reflection: Compares parent pairs, guides crossover
- Long-term reflection: Accumulates knowledge, guides elitist mutation
"""

import json
import random
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from candidate_manager import CandidateManager
from evaluator import Evaluator
from llm_agents import LLMAgents


class EvolutionLoop:
    """Manages the evolutionary search loop with reflection."""

    def __init__(self,
                 population_size: int = 10,
                 elite_ratio: float = 0.2,
                 mutation_rate: float = 0.7,
                 crossover_rate: float = 0.3,
                 target_instances: List[str] = None,
                 dataset_dir: str = "XL",
                 seed: int = 42,
                 use_vrpagent: bool = True,
                 code_length_penalty_alpha: float = 0.001,
                 max_parallel_evals: int = None,
                 debug: bool = True,
                 user_insight: str = "",
                 max_parallel_candidates: int = 3,
                 use_batch_evaluation: bool = True):
        """
        Initialize evolution loop.

        Args:
            population_size: Number of candidates in population
            elite_ratio: Ratio of elites to preserve
            mutation_rate: Probability of mutation vs crossover
            crossover_rate: Probability of crossover (1 - mutation_rate)
            target_instances: List of instance names for evaluation (without .vrp extension)
            dataset_dir: Dataset directory name (e.g., "XL", "Vrp_Set_X")
            seed: Random seed
            use_vrpagent: Enable VRPAGENT techniques (biased crossover, typed mutations)
            code_length_penalty_alpha: VRPAGENT code length penalty coefficient
            debug: If True, show all output. If False, only show reflections and best candidate per generation
            user_insight: User-provided insight string for guiding evolution (reserved for future use)
            max_parallel_evals: Max parallel instance evaluations per candidate (default: min(num_instances, 5))
            max_parallel_candidates: Max parallel candidate evaluations (Level 1, default: 3)
            use_batch_evaluation: Enable 2-level parallel batch evaluation (default: True)
        """
        self.population_size = population_size
        self.elite_size = int(population_size * elite_ratio)
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.use_vrpagent = use_vrpagent
        self.code_length_penalty_alpha = code_length_penalty_alpha
        self.dataset_dir = dataset_dir
        self.max_parallel_evals = max_parallel_evals
        self.debug = debug
        self.user_insight = user_insight
        self.max_parallel_candidates = max_parallel_candidates
        self.use_batch_evaluation = use_batch_evaluation

        # Compute paths relative to project root (parent of src/)
        project_root = Path(__file__).parent.parent
        self.candidates_dir = project_root / "candidates"
        ails_jar = project_root / "AILS" / "AILSII.jar"

        self.candidate_manager = CandidateManager(
            candidates_dir=str(self.candidates_dir),
            ails_jar=str(ails_jar),
            cache_file=str(self.candidates_dir / "cache.json")
        )
        self.evaluator = Evaluator(
            ails_jar=str(ails_jar),
            data_dir=str(project_root / "AILS" / "data" / dataset_dir),
            warmstart_dir=str(project_root / "AILS" / "warm_start" / dataset_dir),
            temp_dir=str(project_root / "temp")
        )
        self.llm = LLMAgents(use_llm=True)

        # Set default instances based on dataset
        if target_instances is None:
            if dataset_dir == "Vrp_Set_X":
                # Use two smallest instances for fast testing
                self.target_instances = ["X-n101-k25", "X-n106-k14"]
            else:
                # Default to XL smallest instance
                self.target_instances = ["XL-n1048-k237"]
        else:
            self.target_instances = target_instances

        # Population tracking
        self.population: List[Dict[str, Any]] = []
        self.generation = 0
        self.candidate_counter = 0

        # Reflection tracking (ReEvo-style)
        self.short_term_reflections: List[str] = []  # Recent comparisons
        self.long_term_reflection: Optional[str] = None  # Accumulated knowledge

        random.seed(seed)

    def _log(self, message: str, level: str = "debug") -> None:
        """
        Log a message respecting debug flag.

        Args:
            message: Message to log
            level: 'debug' (only if debug=True) or 'info' (always shown)
        """
        if level == "info" or self.debug:
            print(message)

    def _log_reflection(self, message: str) -> None:
        """Log reflection-related messages (always shown)."""
        print(message)

    def resume_from_candidates(self) -> bool:
        """
        Resume evolution from existing candidates folder.

        Loads population from saved metadata files, reconstructing the state
        from the last run.

        Returns:
            True if successfully resumed, False if no valid candidates found
        """
        self._log("[RESUME] Scanning candidates folder for existing population...", "info")

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
                    self._log(f"[RESUME] Skipping {candidate_dir.name}: no evaluation data", "debug")
                    continue

                # Load the source code
                strategy_class = metadata.get("strategy_class", "Unknown")
                code_file = candidate_dir / "src" / "EvoDestroy" / f"{strategy_class}.java"
                if not code_file.exists():
                    self._log(f"[RESUME] Skipping {candidate_dir.name}: source file not found", "debug")
                    continue

                with open(code_file) as f:
                    code = f.read()

                # Reconstruct candidate entry
                eval_data = metadata["evaluation"]
                candidate = {
                    "candidate_id": metadata["candidate_id"],
                    "code": code,
                    "metadata": metadata,
                    "eval_results": eval_data.get("instances", []),
                    "fitness": eval_data.get("fitness", 0),
                    "base_fitness": eval_data.get("base_fitness", 0),
                    "generation": eval_data.get("generation", 0),
                    "parent_id": metadata.get("parent_id"),
                    "mutation_type": metadata.get("mutation_type", "unknown")
                }

                candidates.append(candidate)
                max_gen = max(max_gen, candidate["generation"])
                max_id = max(max_id, candidate["candidate_id"])

            except Exception as e:
                self._log(f"[RESUME] Error loading {candidate_dir.name}: {e}", "debug")
                continue

        if not candidates:
            self._log("[RESUME] No valid candidates found to resume from", "info")
            return False

        # Sort by fitness and keep top population_size
        candidates.sort(key=lambda x: x["fitness"], reverse=True)
        self.population = candidates[:self.population_size]
        self.generation = max_gen
        self.candidate_counter = max_id + 1

        self._log(f"[RESUME] Loaded {len(self.population)} candidates from {len(candidates)} total", "info")
        self._log(f"[RESUME] Resuming from generation {self.generation}, next candidate ID: {self.candidate_counter}", "info")
        self._log(f"[RESUME] Best fitness: {self.population[0]['fitness']*100:.4f}%", "info")

        return True

    def initialize_population(self, num_seeds: int = 3) -> None:
        """
        Initialize population with seed strategies.

        Args:
            num_seeds: Number of seed strategies to generate
        """
        self._log(f"[INIT] Generating {num_seeds} seed strategies...")

        for i in range(num_seeds):
            strategy_code = self.llm.generate_initial_seed(i)

            # Compile
            result = self.candidate_manager.compile_candidate(
                strategy_code=strategy_code,
                candidate_id=self.candidate_counter,
                mutation_type="initial_seed"
            )

            if not result:
                self._log(f"[INIT] Seed {i} failed to compile, skipping")
                continue

            # Smoke test
            smoke = self.evaluator.smoke_test(
                result["jar_path"],
                result["wrapper_class"]
            )

            if not smoke["success"]:
                self._log(f"[INIT] Seed {i} failed smoke test, skipping")
                continue

            # Evaluate (parallel across instances)
            eval_results = self.evaluator.evaluate_endgame_parallel(
                result["jar_path"],
                result["wrapper_class"],
                self.target_instances,
                max_workers=self.max_parallel_evals
            )

            # Calculate fitness with optional code length penalty
            base_fitness = self.evaluator.calculate_fitness(eval_results)
            fitness = self._calculate_fitness_with_penalty(strategy_code, base_fitness)

            # Save evaluation results to metadata
            self.candidate_manager.update_evaluation_results(
                candidate_id=self.candidate_counter,
                eval_results=eval_results,
                fitness=fitness,
                base_fitness=base_fitness,
                generation=0
            )

            self.population.append({
                "candidate_id": self.candidate_counter,
                "code": strategy_code,
                "metadata": result,
                "eval_results": eval_results,
                "fitness": fitness,
                "base_fitness": base_fitness,
                "generation": 0
            })

            self._log(f"[INIT] Seed {i} (ID={self.candidate_counter}): fitness={fitness*100:.4f}%")
            self.candidate_counter += 1

        self._log(f"[INIT] Population size: {len(self.population)}")

    def select_parents(self, tournament_size: int = 3) -> Tuple[Dict, Dict]:
        """
        Select two parents using tournament selection.

        Returns better parent first, worse parent second (for reflection comparison).

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

        # Tournament selection for two parents
        parent1 = max(random.sample(self.population, actual_tournament_size),
                     key=lambda x: x["fitness"])

        # Select second parent, ensuring it's different (with retry limit to prevent infinite loop)
        max_attempts = 20
        attempts = 0
        parent2 = max(random.sample(self.population, actual_tournament_size),
                     key=lambda x: x["fitness"])

        while parent1["candidate_id"] == parent2["candidate_id"] and attempts < max_attempts:
            parent2 = max(random.sample(self.population, actual_tournament_size),
                         key=lambda x: x["fitness"])
            attempts += 1

        # If we still got the same parent after max attempts, just pick a different one directly
        if parent1["candidate_id"] == parent2["candidate_id"]:
            # Fallback: pick any different candidate
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
        Generate offspring using reflection-guided reproduction.

        Following ReEvo framework:
        - For crossover: Use short-term reflection comparing two parents
        - For mutation: Use long-term reflection (accumulated knowledge)

        Returns:
            New candidate dict or None if reproduction failed
        """
        # Decide: mutation or crossover
        use_crossover = random.random() < self.crossover_rate

        if use_crossover and len(self.population) >= 2:
            return self._crossover_with_short_term_reflection()
        else:
            return self._mutate_with_long_term_reflection()

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

        self._log(f"[CROSSOVER] Parents: {better_parent['candidate_id']} (fit={better_parent['fitness']*100:.4f}%) "
              f"x {worse_parent['candidate_id']} (fit={worse_parent['fitness']*100:.4f}%)")

        # Generate short-term reflection
        self._log(f"[REFLECTION] Generating short-term reflection...")
        short_term_reflection = self.llm.reflect_short_term(
            better_code=better_parent["code"],
            better_results=better_parent["eval_results"],
            worse_code=worse_parent["code"],
            worse_results=worse_parent["eval_results"]
        )

        # Store for long-term accumulation
        self.short_term_reflections.append(short_term_reflection)
        self._log_reflection(f"[REFLECTION] Short-term insight: {short_term_reflection[:200]}...")

        # Generate offspring using reflection + optional VRPAGENT bias
        offspring_code = self.llm.crossover(
            parent1_code=better_parent["code"],
            parent2_code=worse_parent["code"],
            parent1_results=better_parent["eval_results"],
            parent2_results=worse_parent["eval_results"],
            short_term_reflection=short_term_reflection,
            use_vrpagent_bias=self.use_vrpagent,
            elite_bias=0.75  # VRPAGENT: 75% from elite, 25% from non-elite
        )

        return self._compile_and_evaluate_offspring(
            offspring_code,
            parent_id=better_parent["candidate_id"],
            mutation_type="crossover"
        )

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

        self._log(f"[MUTATION] Elite parent: {elite_parent['candidate_id']} (fit={elite_parent['fitness']*100:.4f}%)")

        # Select mutation type (VRPAGENT)
        if self.use_vrpagent:
            from vrpagent_prompts import VRPAgentPrompts
            mutation_type = VRPAgentPrompts.select_mutation_type(
                elite_code=elite_parent["code"],
                generation=self.generation,
                long_term_reflection=self.long_term_reflection
            )
            self._log(f"[MUTATION] Selected type: {mutation_type}")
        else:
            mutation_type = None

        # Generate offspring using long-term reflection + optional typed mutation
        offspring_code = self.llm.mutate(
            parent_code=elite_parent["code"],
            parent_results=elite_parent["eval_results"],
            long_term_reflection=self.long_term_reflection,
            mutation_strength=0.3,
            mutation_type=mutation_type,
            generation=self.generation
        )

        return self._compile_and_evaluate_offspring(
            offspring_code,
            parent_id=elite_parent["candidate_id"],
            mutation_type=mutation_type or "mutation"
        )

    def _compile_and_evaluate_offspring(self,
                                       offspring_code: str,
                                       parent_id: int,
                                       mutation_type: str) -> Optional[Dict[str, Any]]:
        """Compile and evaluate offspring."""
        # Compile
        result = self.candidate_manager.compile_candidate(
            strategy_code=offspring_code,
            candidate_id=self.candidate_counter,
            parent_id=parent_id,
            mutation_type=mutation_type
        )

        if not result:
            self._log(f"[OFFSPRING] Compilation failed")
            return None

        # Smoke test
        smoke = self.evaluator.smoke_test(
            result["jar_path"],
            result["wrapper_class"]
        )

        if not smoke["success"]:
            self._log(f"[OFFSPRING] Smoke test failed")
            return None

        # Evaluate (parallel across instances)
        eval_results = self.evaluator.evaluate_endgame_parallel(
            result["jar_path"],
            result["wrapper_class"],
            self.target_instances,
            max_workers=self.max_parallel_evals
        )

        # Calculate fitness with optional code length penalty
        base_fitness = self.evaluator.calculate_fitness(eval_results)
        fitness = self._calculate_fitness_with_penalty(offspring_code, base_fitness)

        # Save evaluation results to metadata
        self.candidate_manager.update_evaluation_results(
            candidate_id=self.candidate_counter,
            eval_results=eval_results,
            fitness=fitness,
            base_fitness=base_fitness,
            generation=self.generation
        )

        offspring = {
            "candidate_id": self.candidate_counter,
            "code": offspring_code,
            "metadata": result,
            "eval_results": eval_results,
            "fitness": fitness,
            "base_fitness": base_fitness,
            "generation": self.generation,
            "parent_id": parent_id,
            "mutation_type": mutation_type
        }

        self._log(f"[OFFSPRING] ID={self.candidate_counter}: fitness={fitness*100:.4f}%")
        self.candidate_counter += 1

        return offspring

    def _generate_offspring_batch(self, num_offspring: int) -> List[Dict[str, Any]]:
        """Generate multiple offspring codes (sequential due to LLM rate limits)."""
        offspring_specs = []

        for i in range(num_offspring):
            use_crossover = random.random() < self.crossover_rate

            if use_crossover and len(self.population) >= 2:
                better_parent, worse_parent = self.select_parents()
                print(f"[BATCH GEN {i+1}/{num_offspring}] Crossover: {better_parent['candidate_id']} x {worse_parent['candidate_id']}")

                short_term_reflection = self.llm.reflect_short_term(
                    better_code=better_parent["code"],
                    better_results=better_parent["eval_results"],
                    worse_code=worse_parent["code"],
                    worse_results=worse_parent["eval_results"]
                )
                self.short_term_reflections.append(short_term_reflection)

                offspring_code = self.llm.crossover(
                    parent1_code=better_parent["code"],
                    parent2_code=worse_parent["code"],
                    parent1_results=better_parent["eval_results"],
                    parent2_results=worse_parent["eval_results"],
                    short_term_reflection=short_term_reflection,
                    use_vrpagent_bias=self.use_vrpagent,
                    elite_bias=0.75
                )

                offspring_specs.append({
                    "code": offspring_code,
                    "parent_id": better_parent["candidate_id"],
                    "mutation_type": "crossover"
                })
            else:
                elite_parent = max(self.population, key=lambda x: x["fitness"])
                print(f"[BATCH GEN {i+1}/{num_offspring}] Mutation from elite: {elite_parent['candidate_id']}")

                mutation_type = None
                if self.use_vrpagent:
                    from vrpagent_prompts import VRPAgentPrompts
                    mutation_type = VRPAgentPrompts.select_mutation_type(
                        elite_code=elite_parent["code"],
                        generation=self.generation,
                        long_term_reflection=self.long_term_reflection
                    )

                offspring_code = self.llm.mutate(
                    parent_code=elite_parent["code"],
                    parent_results=elite_parent["eval_results"],
                    long_term_reflection=self.long_term_reflection,
                    mutation_strength=0.3,
                    mutation_type=mutation_type,
                    generation=self.generation
                )

                offspring_specs.append({
                    "code": offspring_code,
                    "parent_id": elite_parent["candidate_id"],
                    "mutation_type": mutation_type or "mutation"
                })

        return offspring_specs

    def _compile_batch_parallel(self, offspring_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compile multiple offspring in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def compile_one(spec, candidate_id):
            result = self.candidate_manager.compile_candidate(
                strategy_code=spec["code"],
                candidate_id=candidate_id,
                parent_id=spec["parent_id"],
                mutation_type=spec["mutation_type"]
            )
            if result:
                return {
                    **spec,
                    "candidate_id": candidate_id,
                    "jar_path": result["jar_path"],
                    "class_name": result["wrapper_class"],
                    "metadata": result
                }
            return None

        candidate_ids = list(range(self.candidate_counter, self.candidate_counter + len(offspring_specs)))

        with ThreadPoolExecutor(max_workers=min(len(offspring_specs), 4)) as executor:
            futures = {
                executor.submit(compile_one, spec, cid): i
                for i, (spec, cid) in enumerate(zip(offspring_specs, candidate_ids))
            }

            results = [None] * len(offspring_specs)
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    print(f"[COMPILE ERROR] Offspring {idx}: {e}")

        compiled = [r for r in results if r is not None]
        print(f"[BATCH COMPILE] {len(compiled)}/{len(offspring_specs)} compiled successfully")
        return compiled

    def _smoke_test_batch_parallel(self, compiled_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run smoke tests on multiple candidates in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def smoke_test_one(candidate):
            result = self.evaluator.smoke_test(candidate["jar_path"], candidate["class_name"])
            return candidate if result["success"] else None

        passed = []
        with ThreadPoolExecutor(max_workers=min(len(compiled_candidates), 4)) as executor:
            futures = {executor.submit(smoke_test_one, c): i for i, c in enumerate(compiled_candidates)}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        passed.append(result)
                except Exception as e:
                    print(f"[SMOKE TEST ERROR] {e}")

        print(f"[BATCH SMOKE TEST] {len(passed)}/{len(compiled_candidates)} passed")
        return passed

    def _evaluate_batch_parallel(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate multiple candidates using 2-level parallelization."""
        if not candidates:
            return []

        eval_candidates = [
            {"jar_path": c["jar_path"], "class_name": c["class_name"], "candidate_id": c["candidate_id"]}
            for c in candidates
        ]

        all_results = self.evaluator.evaluate_candidates_parallel(
            eval_candidates,
            self.target_instances,
            max_candidate_workers=self.max_parallel_candidates,
            max_instance_workers=self.max_parallel_evals or min(len(self.target_instances), 5)
        )

        offspring_list = []
        for candidate, eval_results in zip(candidates, all_results):
            base_fitness = self.evaluator.calculate_fitness(eval_results)
            fitness = self._calculate_fitness_with_penalty(candidate["code"], base_fitness)

            offspring = {
                "candidate_id": candidate["candidate_id"],
                "code": candidate["code"],
                "metadata": candidate["metadata"],
                "eval_results": eval_results,
                "fitness": fitness,
                "base_fitness": base_fitness,
                "generation": self.generation,
                "parent_id": candidate["parent_id"],
                "mutation_type": candidate["mutation_type"]
            }
            offspring_list.append(offspring)
            print(f"[BATCH EVAL] ID={candidate['candidate_id']}: fitness={fitness:.6f}")

        if candidates:
            self.candidate_counter = max(c["candidate_id"] for c in candidates) + 1

        return offspring_list

    def update_long_term_reflection(self) -> None:
        """
        Update long-term reflection by synthesizing recent short-term reflections.

        Following ReEvo: Distill accumulated experiences into concise knowledge base.
        """
        if not self.short_term_reflections:
            self._log(f"[REFLECTION] No short-term reflections to synthesize yet")
            return

        self._log(f"[REFLECTION] Updating long-term knowledge (gen={self.generation})...")
        self._log(f"[REFLECTION] Synthesizing {len(self.short_term_reflections)} recent insights...")

        self.long_term_reflection = self.llm.reflect_long_term(
            recent_short_term_reflections=self.short_term_reflections,
            previous_long_term_reflection=self.long_term_reflection,
            generation=self.generation
        )

        self._log_reflection(f"[REFLECTION] Long-term knowledge updated:")
        self._log_reflection(self.long_term_reflection[:400] + "...")

        # Clear short-term buffer (already distilled into long-term)
        self.short_term_reflections = []

    def survival_selection(self) -> None:
        """
        Select survivors for next generation.

        Strategy: Elitist - keep top N by fitness.
        """
        # Sort by fitness (descending)
        self.population.sort(key=lambda x: x["fitness"], reverse=True)

        # Keep top population_size
        self.population = self.population[:self.population_size]

        self._log(f"[SELECTION] Population after selection: {len(self.population)} candidates")
        self._log(f"[SELECTION] Top fitness: {self.population[0]['fitness']*100:.4f}%")
        self._log(f"[SELECTION] Worst fitness: {self.population[-1]['fitness']*100:.4f}%")

    def evolve(self, num_generations: int = 10, reflection_frequency: int = 3) -> None:
        """
        Run evolution loop with reflection.

        Args:
            num_generations: Number of generations to evolve
            reflection_frequency: How often to update long-term reflection
        """
        self._log(f"\n{'='*80}", "info")
        self._log(f"STARTING EVOLUTION: {num_generations} generations", "info")
        self._log(f"{'='*80}\n", "info")

        for gen in range(num_generations):
            self.generation = gen + 1
            self._log(f"\n{'='*80}")
            self._log(f"GENERATION {self.generation}")
            self._log(f"{'='*80}")

            # Generate offspring
            num_offspring = self.population_size - self.elite_size

            if self.use_batch_evaluation:
                offspring_list = self._evolve_generation_batch(num_offspring)
                for offspring in offspring_list:
                    self.population.append(offspring)
                offspring_count = len(offspring_list)
            else:
                offspring_count = 0
                for i in range(num_offspring):
                    offspring = self.reproduce_with_reflection()
                    if offspring:
                        self.population.append(offspring)
                        offspring_count += 1

            self._log(f"\n[GEN {self.generation}] Generated {offspring_count} valid offspring")

            # Survival selection
            self.survival_selection()

            # Update long-term reflection periodically
            if self.generation % reflection_frequency == 0:
                self.update_long_term_reflection()

            # Report best (always shown)
            best = max(self.population, key=lambda x: x["fitness"])
            self._log(f"\n[GEN {self.generation}] BEST: ID={best['candidate_id']}, fitness={best['fitness']*100:.4f}%", "info")

        self._log(f"\n{'='*80}", "info")
        self._log(f"EVOLUTION COMPLETE", "info")
        self._log(f"{'='*80}\n", "info")

        # Final statistics
        self.print_final_statistics()

    def _evolve_generation_batch(self, num_offspring: int) -> List[Dict[str, Any]]:
        """Evolve one generation using 2-level parallel batch evaluation."""
        print(f"\n[BATCH] Phase 1: Generating {num_offspring} offspring codes...")
        offspring_specs = self._generate_offspring_batch(num_offspring)
        if not offspring_specs:
            return []

        print(f"\n[BATCH] Phase 2: Compiling {len(offspring_specs)} candidates...")
        compiled = self._compile_batch_parallel(offspring_specs)
        if not compiled:
            return []

        print(f"\n[BATCH] Phase 3: Smoke testing {len(compiled)} candidates...")
        passed_smoke = self._smoke_test_batch_parallel(compiled)
        if not passed_smoke:
            return []

        print(f"\n[BATCH] Phase 4: 2-level parallel evaluation of {len(passed_smoke)} candidates...")
        return self._evaluate_batch_parallel(passed_smoke)

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

    def print_final_statistics(self) -> None:
        """Print final evolution statistics (always shown)."""
        best = max(self.population, key=lambda x: x["fitness"])

        self._log(f"\n{'='*80}", "info")
        self._log(f"FINAL STATISTICS", "info")
        self._log(f"{'='*80}", "info")
        self._log(f"Total candidates evaluated: {self.candidate_counter}", "info")
        self._log(f"Final population size: {len(self.population)}", "info")
        self._log(f"Best candidate ID: {best['candidate_id']}", "info")
        self._log(f"Best fitness: {best['fitness']*100:.4f}%", "info")
        if self.use_vrpagent and "base_fitness" in best:
            self._log(f"Best base fitness (no penalty): {best['base_fitness']*100:.4f}%", "info")
        self._log(f"Best generation: {best['generation']}", "info")
        self._log(f"\nBest candidate performance:", "info")
        for result in best["eval_results"]:
            instance_name = result.get('instance', result.get('name', 'unknown'))
            improvement = result.get('improvement', result.get('improvement_pct', 0) / 100)
            self._log(f"  {instance_name}: {improvement*100:.3f}% improvement", "info")

        # Code length statistics
        if self.use_vrpagent:
            code_lines = len([l for l in best["code"].split('\n')
                            if l.strip() and not l.strip().startswith('//')
                            and not l.strip().startswith('package')
                            and not l.strip().startswith('import')])
            self._log(f"\nBest candidate code length: {code_lines} lines", "info")

        self._log(f"\n{'='*80}\n", "info")


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("ReEvo-style Evolution Loop for VRP Destroy Strategies")
    print("="*80)

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
