"""
AILS Evaluation Harness

Core low-level AILS runner. Handles:
- Stage 0: Smoke test on small instance
- Stage 1: End-game evaluation on target instances with warmstart
- Stage 2: Multi-seed confirmation for top candidates
- Solution file parsing
- Fitness calculation
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger


class Evaluator:
    """Evaluates plugin candidates using AILS."""

    def __init__(self,
                 ails_jar: str = "AILS/AILSII.jar",
                 data_dir: str = "AILS/data/XL",
                 warmstart_dir: str = "AILS/warm_start/XL",
                 temp_dir: str = None):
        """
        Initialize evaluator.

        Args:
            ails_jar: Path to AILS JAR
            data_dir: Directory containing instance files
            warmstart_dir: Directory containing warmstart solutions
            temp_dir: Directory for temporary output files. If None, a system
                      temp directory is created automatically and cleaned up
                      when the Evaluator is garbage-collected.
        """
        self.ails_jar = Path(ails_jar)
        self.data_dir = Path(data_dir)
        self.warmstart_dir = Path(warmstart_dir)

        if temp_dir is not None:
            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(exist_ok=True)
            self._temp_dir_obj = None  # caller-managed
        else:
            self._temp_dir_obj = tempfile.TemporaryDirectory(prefix="ails_eval_")
            self.temp_dir = Path(self._temp_dir_obj.name)

    def __del__(self):
        if self._temp_dir_obj is not None:
            try:
                self._temp_dir_obj.cleanup()
            except Exception:
                pass

    def parse_solution_cost(self, sol_file: Path) -> float:
        """
        Extract cost from .sol file.

        Args:
            sol_file: Path to solution file

        Returns:
            Solution cost or infinity if parsing fails
        """
        if not sol_file.exists():
            return float('inf')

        try:
            with open(sol_file) as f:
                lines = f.readlines()
                # Cost is on last line: "Cost XXXXX"
                for line in reversed(lines):
                    if line.startswith("Cost"):
                        return float(line.split()[1])
        except Exception as e:
            logger.error(f"[PARSE ERROR] Failed to parse {sol_file}: {e}")

        return float('inf')

    def extract_runtime(self, ails_output: str) -> float:
        """
        Extract runtime from AILS console output.

        Args:
            ails_output: AILS stdout/stderr

        Returns:
            Runtime in seconds or 0.0 if not found
        """
        # Look for final save line: "time: X.XXXs"
        match = re.search(r'time:\s+([\d.]+)s', ails_output)
        if match:
            return float(match.group(1))
        return 0.0

    def smoke_test(self,
                   jar_path: str,
                   class_name: str,
                   seed: int = 42,
                   iterations: int = 500,
                   timeout: int = 120,
                   instance: str = None) -> Dict[str, Any]:
        """
        Run smoke test on a single instance.

        Args:
            jar_path: Path to plugin JAR
            class_name: Plugin class name
            seed: Random seed
            iterations: Number of iterations
            timeout: Timeout in seconds
            instance: Instance name (without .vrp). If None, uses the smallest
                      available instance by file size.

        Returns:
            Dictionary with smoke test results
        """
        vrp_files = list(self.data_dir.glob("*.vrp"))
        if not vrp_files:
            logger.error(f"[SMOKE TEST ERROR] No .vrp files found in {self.data_dir}")
            return {
                "success": False,
                "runtime": 0.0,
                "output": f"No VRP instances found in {self.data_dir}",
                "exit_code": -1
            }

        if instance:
            name = instance if instance.endswith(".vrp") else f"{instance}.vrp"
            instance_file = self.data_dir / name
            if not instance_file.exists():
                logger.warning(f"[SMOKE TEST] Configured instance {name} not found in "
                               f"{self.data_dir}, falling back to smallest")
                instance_file = min(vrp_files, key=lambda f: f.stat().st_size)
        else:
            # Pick smallest instance by file size (smaller files = fewer nodes)
            instance_file = min(vrp_files, key=lambda f: f.stat().st_size)
        logger.debug(f"[SMOKE TEST] Using instance: {instance_file.name}")

        output_sol = self.temp_dir / f"smoke_test_{class_name}.sol"

        if output_sol.exists():
            try:
                output_sol.unlink()
            except OSError:
                pass

        try:
            result = subprocess.run([
                "java", "-jar", str(self.ails_jar),
                "-file", str(instance_file.resolve()),
                "-destroyPlugin", str(Path(jar_path).resolve()),
                "-destroyClass", class_name,
                "-seed", str(seed),
                "-limit", str(iterations),
                "-stoppingCriterion", "Iteration",
                "-solOutput", str(output_sol.resolve()),
                "-rounded", "true",
                "-best", "0"
            ], capture_output=True, text=True, timeout=timeout)

            success = result.returncode == 0 and output_sol.exists()
            runtime = self.extract_runtime(result.stdout + result.stderr)

            return {
                "success": success,
                "runtime": runtime,
                "output": result.stdout + result.stderr,
                "exit_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error(f"[SMOKE TEST TIMEOUT] {class_name} exceeded {timeout}s")
            return {"success": False, "runtime": timeout, "output": "TIMEOUT", "exit_code": -1}

        except Exception as e:
            logger.error(f"[SMOKE TEST ERROR] {class_name}: {e}")
            return {"success": False, "runtime": 0.0, "output": str(e), "exit_code": -1}

    def evaluate_endgame(self,
                         jar_path: str,
                         class_name: str,
                         instances: List[str],
                         seed: int = 42,
                         iterations: int = 500,
                         timeout: int = 3600) -> List[Dict[str, Any]]:
        """Evaluate on target instances with warmstart (sequential)."""
        results = []

        for instance_name in instances:
            instance_file = self.data_dir / f"{instance_name}.vrp"
            warmstart_file = self.warmstart_dir / f"{instance_name}.sol"
            output_sol = self.temp_dir / f"{instance_name}_{class_name}.sol"

            if not instance_file.exists():
                logger.error(f"[EVAL ERROR] Instance not found: {instance_file}")
                results.append({"instance": instance_name, "success": False,
                                 "error": "Instance file not found"})
                continue

            if not warmstart_file.exists():
                logger.warning(f"[EVAL WARNING] Warmstart not found: {warmstart_file}")
                warmstart_file = None

            initial_cost = self.parse_solution_cost(warmstart_file) if warmstart_file else float('inf')

            if output_sol.exists():
                output_sol.unlink()

            try:
                cmd = [
                    "java", "-jar", str(self.ails_jar),
                    "-file", str(instance_file.resolve()),
                    "-destroyPlugin", str(Path(jar_path).resolve()),
                    "-destroyClass", class_name,
                    "-seed", str(seed),
                    "-limit", str(iterations),
                    "-stoppingCriterion", "Iteration",
                    "-solOutput", str(output_sol.resolve()),
                    "-rounded", "true",
                    "-best", "0"
                ]
                if warmstart_file:
                    cmd.extend(["-warmStart", str(warmstart_file.resolve())])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                final_cost = self.parse_solution_cost(output_sol)
                improvement = (initial_cost - final_cost) / initial_cost if initial_cost > 0 else 0.0
                runtime = self.extract_runtime(result.stdout + result.stderr)

                results.append({
                    "instance": instance_name,
                    "initial_cost": initial_cost,
                    "final_cost": final_cost,
                    "improvement": improvement,
                    "runtime": runtime,
                    "success": result.returncode == 0,
                    "exit_code": result.returncode
                })

                logger.debug(f"[EVAL] {instance_name}: {initial_cost:.1f} -> {final_cost:.1f} "
                             f"(improvement={improvement*100:.3f}%) in {runtime:.1f}s")

            except subprocess.TimeoutExpired:
                logger.error(f"[EVAL TIMEOUT] {instance_name} exceeded {timeout}s")
                results.append({"instance": instance_name, "initial_cost": initial_cost,
                                 "final_cost": initial_cost, "improvement": 0.0,
                                 "runtime": timeout, "success": False, "exit_code": -1})

            except Exception as e:
                logger.error(f"[EVAL ERROR] {instance_name}: {e}")
                results.append({"instance": instance_name, "initial_cost": initial_cost,
                                 "final_cost": initial_cost, "improvement": 0.0,
                                 "runtime": 0.0, "success": False, "error": str(e)})

        return results

    def _evaluate_single_instance(self,
                                   jar_path: str,
                                   class_name: str,
                                   instance_name: str,
                                   seed: int,
                                   iterations: int,
                                   timeout: int) -> Dict[str, Any]:
        """Evaluate a single instance (helper for parallel execution)."""
        instance_file = self.data_dir / f"{instance_name}.vrp"
        warmstart_file = self.warmstart_dir / f"{instance_name}.sol"
        output_sol = self.temp_dir / f"{instance_name}_{class_name}_{seed}.sol"

        if not instance_file.exists():
            return {"instance": instance_name, "success": False,
                    "error": "Instance file not found", "initial_cost": float('inf'),
                    "final_cost": float('inf'), "improvement": 0.0, "runtime": 0.0}

        if not warmstart_file.exists():
            warmstart_file = None

        initial_cost = self.parse_solution_cost(warmstart_file) if warmstart_file else float('inf')

        if output_sol.exists():
            output_sol.unlink()

        try:
            cmd = [
                "java", "-jar", str(self.ails_jar),
                "-file", str(instance_file.resolve()),
                "-destroyPlugin", str(Path(jar_path).resolve()),
                "-destroyClass", class_name,
                "-seed", str(seed),
                "-limit", str(iterations),
                "-stoppingCriterion", "Iteration",
                "-solOutput", str(output_sol.resolve()),
                "-rounded", "true",
                "-best", "0"
            ]
            if warmstart_file:
                cmd.extend(["-warmStart", str(warmstart_file.resolve())])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            final_cost = self.parse_solution_cost(output_sol)
            improvement = (initial_cost - final_cost) / initial_cost if initial_cost > 0 else 0.0
            runtime = self.extract_runtime(result.stdout + result.stderr)

            return {"instance": instance_name, "initial_cost": initial_cost,
                    "final_cost": final_cost, "improvement": improvement,
                    "runtime": runtime, "success": result.returncode == 0,
                    "exit_code": result.returncode}

        except subprocess.TimeoutExpired:
            return {"instance": instance_name, "initial_cost": initial_cost,
                    "final_cost": initial_cost, "improvement": 0.0,
                    "runtime": timeout, "success": False, "exit_code": -1}

        except Exception as e:
            return {"instance": instance_name, "initial_cost": initial_cost,
                    "final_cost": initial_cost, "improvement": 0.0,
                    "runtime": 0.0, "success": False, "error": str(e)}

    def evaluate_endgame_parallel(self,
                                   jar_path: str,
                                   class_name: str,
                                   instances: List[str],
                                   seed: int = 42,
                                   iterations: int = 500,
                                   timeout: int = 3600,
                                   max_workers: int = None) -> List[Dict[str, Any]]:
        """Evaluate on target instances with parallel execution."""
        if max_workers is None:
            max_workers = min(len(instances), 5)

        logger.debug(f"[PARALLEL EVAL] {len(instances)} instances with {max_workers} workers")

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_instance = {
                executor.submit(
                    self._evaluate_single_instance,
                    jar_path, class_name, inst, seed, iterations, timeout
                ): inst
                for inst in instances
            }

            for future in as_completed(future_to_instance):
                instance_name = future_to_instance[future]
                try:
                    result = future.result(timeout=timeout + 10)
                    results.append(result)
                    if result["success"]:
                        logger.debug(f"[EVAL] {instance_name}: {result['initial_cost']:.1f} -> "
                                     f"{result['final_cost']:.1f} "
                                     f"(improvement={result['improvement']*100:.3f}%) "
                                     f"in {result['runtime']:.1f}s")
                    else:
                        logger.error(f"[EVAL ERROR] {instance_name}: "
                                     f"{result.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"[EVAL EXCEPTION] {instance_name}: {e}")
                    results.append({"instance": instance_name, "success": False,
                                    "error": str(e), "initial_cost": float('inf'),
                                    "final_cost": float('inf'), "improvement": 0.0,
                                    "runtime": 0.0})

        instance_order = {name: i for i, name in enumerate(instances)}
        results.sort(key=lambda x: instance_order.get(x["instance"], 999))
        return results

    def evaluate_candidates_parallel(self,
                                      candidates: List[Dict[str, Any]],
                                      instances: List[str],
                                      seed: int = 42,
                                      iterations: int = 500,
                                      timeout: int = 3600,
                                      max_candidate_workers: int = 3,
                                      max_instance_workers: int = 4) -> List[List[Dict[str, Any]]]:
        """2-level parallel evaluation for multiple candidates × instances."""
        if not candidates:
            return []

        actual_candidate_workers = min(max_candidate_workers, len(candidates))
        logger.debug(f"[2-LEVEL PARALLEL] {len(candidates)} candidates × {len(instances)} instances, "
                     f"workers: {actual_candidate_workers} × {max_instance_workers}")

        results = [None] * len(candidates)
        with ThreadPoolExecutor(max_workers=actual_candidate_workers) as executor:
            future_to_idx = {
                executor.submit(
                    self.evaluate_endgame_parallel,
                    c["jar_path"], c["class_name"], instances,
                    seed, iterations, timeout, max_instance_workers
                ): i
                for i, c in enumerate(candidates)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result(timeout=timeout * len(instances) + 60)
                    results[idx] = result
                    successful = [r for r in result if r.get("success", False)]
                    if successful:
                        avg_imp = sum(r["improvement"] for r in successful) / len(successful)
                        logger.debug(f"[2-LEVEL PARALLEL] Candidate {idx}: "
                                     f"{len(successful)}/{len(instances)} instances, "
                                     f"avg_improvement={avg_imp*100:.3f}%")
                    else:
                        logger.debug(f"[2-LEVEL PARALLEL] Candidate {idx}: all instances failed")
                except Exception as e:
                    logger.debug(f"[2-LEVEL PARALLEL ERROR] Candidate {idx}: {e}")
                    results[idx] = [
                        {"instance": inst, "success": False, "error": str(e),
                         "initial_cost": float('inf'), "final_cost": float('inf'),
                         "improvement": 0.0, "runtime": 0.0}
                        for inst in instances
                    ]

        return results

    def calculate_fitness(self, eval_results: List[Dict[str, Any]]) -> float:
        """Calculate fitness as average improvement across instances."""
        if not eval_results:
            return -float('inf')
        successful = [r for r in eval_results if r.get("success", False)]
        if not successful:
            return -float('inf')
        return sum(r["improvement"] for r in successful) / len(eval_results)

    def confirm_elite(self,
                      jar_path: str,
                      class_name: str,
                      instances: List[str],
                      seeds: List[int] = None,
                      iterations: int = 500,
                      timeout: int = 3600) -> Dict[str, Any]:
        """Multi-seed confirmation for elite candidates."""
        if seeds is None:
            seeds = [42, 123, 456]
        all_runs = [
            self.evaluate_endgame(jar_path, class_name, instances,
                                  seed=s, iterations=iterations, timeout=timeout)
            for s in seeds
        ]
        fitness_per_seed = [self.calculate_fitness(r) for r in all_runs]
        import statistics
        return {
            "avg_fitness": statistics.mean(fitness_per_seed),
            "std_fitness": statistics.stdev(fitness_per_seed) if len(fitness_per_seed) > 1 else 0.0,
            "fitness_per_seed": fitness_per_seed,
            "all_runs": all_runs,
        }
