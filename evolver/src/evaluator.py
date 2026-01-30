"""
Evaluation Harness for Plugin Candidates

Handles:
- Stage 0: Smoke test on small instance
- Stage 1: End-game evaluation on target instances with warmstart
- Stage 2: Multi-seed confirmation for top candidates
- Solution file parsing
- Fitness calculation
"""

import utils
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


class Evaluator:
    """Evaluates plugin candidates using AILS."""

    def __init__(self,
                 ails_jar: str = "AILS/AILSII.jar",
                 data_dir: str = "AILS/data/XL",
                 warmstart_dir: str = "AILS/warm_start/XL",
                 temp_dir: str = "temp"):
        """
        Initialize evaluator.

        Args:
            ails_jar: Path to AILS JAR
            data_dir: Directory containing instance files
            warmstart_dir: Directory containing warmstart solutions
            temp_dir: Directory for temporary output files
        """
        self.ails_jar = Path(ails_jar)
        self.data_dir = Path(data_dir)
        self.warmstart_dir = Path(warmstart_dir)
        self.temp_dir = Path(temp_dir)

        # Create temp directory
        self.temp_dir.mkdir(exist_ok=True)

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
            utils.log(f"[PARSE ERROR] Failed to parse {sol_file}: {e}")

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
                   timeout: int = 120) -> Dict[str, Any]:
        """
        Run smoke test on smallest instance.

        Args:
            jar_path: Path to plugin JAR
            class_name: Plugin class name
            seed: Random seed
            iterations: Number of iterations
            timeout: Timeout in seconds

        Returns:
            Dictionary with smoke test results
        """
        # Use smallest available instance in the data directory
        # Look for instances and pick the smallest one by file size (proxy for instance size)
        vrp_files = list(self.data_dir.glob("*.vrp"))
        if not vrp_files:
            utils.log(f"[SMOKE TEST ERROR] No .vrp files found in {self.data_dir}")
            return {
                "success": False,
                "runtime": 0.0,
                "output": f"No VRP instances found in {self.data_dir}",
                "exit_code": -1
            }

        # Pick smallest instance by file size (smaller files = fewer nodes)
        instance_file = min(vrp_files, key=lambda f: f.stat().st_size)
        utils.log(f"[SMOKE TEST] Using instance: {instance_file.name}", level="debug")

        output_sol = self.temp_dir / "smoke_test.sol"

        # Remove old output
        if output_sol.exists():
            output_sol.unlink()

        # Run AILS
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
            utils.log(f"[SMOKE TEST TIMEOUT] {class_name} exceeded {timeout}s")
            return {
                "success": False,
                "runtime": timeout,
                "output": "TIMEOUT",
                "exit_code": -1
            }

        except Exception as e:
            utils.log(f"[SMOKE TEST ERROR] {class_name}: {e}")
            return {
                "success": False,
                "runtime": 0.0,
                "output": str(e),
                "exit_code": -1
            }

    def evaluate_endgame(self,
                        jar_path: str,
                        class_name: str,
                        instances: List[str],
                        seed: int = 42,
                        iterations: int = 10000,
                        timeout: int = 3600) -> List[Dict[str, Any]]:
        """
        Evaluate on target instances with warmstart.

        Args:
            jar_path: Path to plugin JAR
            class_name: Plugin class name
            instances: List of instance names (e.g., ["XL-n1048-k237", "XL-n2426-k391"])
            seed: Random seed
            iterations: Number of iterations
            timeout: Timeout in seconds per instance

        Returns:
            List of evaluation results (one per instance)
        """
        results = []

        for instance_name in instances:
            instance_file = self.data_dir / f"{instance_name}.vrp"
            warmstart_file = self.warmstart_dir / f"{instance_name}.sol"
            output_sol = self.temp_dir / f"{instance_name}_{class_name}.sol"

            # Check files exist
            if not instance_file.exists():
                utils.log(f"[EVAL ERROR] Instance not found: {instance_file}")
                results.append({
                    "instance": instance_name,
                    "success": False,
                    "error": "Instance file not found"
                })
                continue

            if not warmstart_file.exists():
                utils.log(f"[EVAL WARNING] Warmstart not found: {warmstart_file}")
                warmstart_file = None

            # Parse initial cost
            initial_cost = self.parse_solution_cost(warmstart_file) if warmstart_file else float('inf')

            # Remove old output
            if output_sol.exists():
                output_sol.unlink()

            # Run AILS
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

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                # Parse final cost
                final_cost = self.parse_solution_cost(output_sol)

                # Calculate improvement
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

                utils.log(f"[EVAL] {instance_name}: {initial_cost:.1f} -> {final_cost:.1f} "
                      f"(improvement={improvement*100:.3f}%) in {runtime:.1f}s", level="debug")

            except subprocess.TimeoutExpired:
                utils.log(f"[EVAL TIMEOUT] {instance_name} exceeded {timeout}s")
                results.append({
                    "instance": instance_name,
                    "initial_cost": initial_cost,
                    "final_cost": initial_cost,
                    "improvement": 0.0,
                    "runtime": timeout,
                    "success": False,
                    "exit_code": -1
                })

            except Exception as e:
                utils.log(f"[EVAL ERROR] {instance_name}: {e}")
                results.append({
                    "instance": instance_name,
                    "initial_cost": initial_cost,
                    "final_cost": initial_cost,
                    "improvement": 0.0,
                    "runtime": 0.0,
                    "success": False,
                    "error": str(e)
                })

        return results

    def _evaluate_single_instance(self,
                                  jar_path: str,
                                  class_name: str,
                                  instance_name: str,
                                  seed: int,
                                  iterations: int,
                                  timeout: int) -> Dict[str, Any]:
        """
        Evaluate a single instance (helper for parallel execution).

        Args:
            jar_path: Path to plugin JAR
            class_name: Plugin class name
            instance_name: Instance name (e.g., "XL-n1048-k237")
            seed: Random seed
            iterations: Number of iterations
            timeout: Timeout in seconds

        Returns:
            Evaluation result dictionary
        """
        instance_file = self.data_dir / f"{instance_name}.vrp"
        warmstart_file = self.warmstart_dir / f"{instance_name}.sol"
        output_sol = self.temp_dir / f"{instance_name}_{class_name}_{seed}.sol"

        # Check files exist
        if not instance_file.exists():
            return {
                "instance": instance_name,
                "success": False,
                "error": "Instance file not found",
                "initial_cost": float('inf'),
                "final_cost": float('inf'),
                "improvement": 0.0,
                "runtime": 0.0
            }

        if not warmstart_file.exists():
            warmstart_file = None

        # Parse initial cost
        initial_cost = self.parse_solution_cost(warmstart_file) if warmstart_file else float('inf')

        # Remove old output
        if output_sol.exists():
            output_sol.unlink()

        # Run AILS
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

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Parse final cost
            final_cost = self.parse_solution_cost(output_sol)

            # Calculate improvement
            improvement = (initial_cost - final_cost) / initial_cost if initial_cost > 0 else 0.0

            runtime = self.extract_runtime(result.stdout + result.stderr)

            return {
                "instance": instance_name,
                "initial_cost": initial_cost,
                "final_cost": final_cost,
                "improvement": improvement,
                "runtime": runtime,
                "success": result.returncode == 0,
                "exit_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "instance": instance_name,
                "initial_cost": initial_cost,
                "final_cost": initial_cost,
                "improvement": 0.0,
                "runtime": timeout,
                "success": False,
                "exit_code": -1
            }

        except Exception as e:
            return {
                "instance": instance_name,
                "initial_cost": initial_cost,
                "final_cost": initial_cost,
                "improvement": 0.0,
                "runtime": 0.0,
                "success": False,
                "error": str(e)
            }

    def evaluate_endgame_parallel(self,
                                  jar_path: str,
                                  class_name: str,
                                  instances: List[str],
                                  seed: int = 42,
                                  iterations: int = 10000,
                                  timeout: int = 3600,
                                  max_workers: int = None) -> List[Dict[str, Any]]:
        """
        Evaluate on target instances with PARALLEL execution.

        Runs AILS evaluations in parallel across instances for faster evaluation.

        Args:
            jar_path: Path to plugin JAR
            class_name: Plugin class name
            instances: List of instance names (e.g., ["XL-n1048-k237", "XL-n2426-k391"])
            seed: Random seed
            iterations: Number of iterations
            timeout: Timeout in seconds per instance
            max_workers: Number of parallel processes (default: min(len(instances), 5))

        Returns:
            List of evaluation results (one per instance)
        """
        # Auto-detect max workers if not specified
        if max_workers is None:
            max_workers = min(len(instances), 5)  # Cap at 5 to avoid overload

        utils.log(f"[PARALLEL EVAL] Evaluating {len(instances)} instances with {max_workers} workers", level="debug")

        results = []

        # Parallel execution using ThreadPoolExecutor (better for I/O-bound subprocess calls)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all instance evaluations
            future_to_instance = {
                executor.submit(
                    self._evaluate_single_instance,
                    jar_path, class_name, inst, seed, iterations, timeout
                ): inst
                for inst in instances
            }

            # Collect results as they complete
            for future in as_completed(future_to_instance):
                instance_name = future_to_instance[future]
                try:
                    result = future.result(timeout=timeout + 10)  # Add buffer to timeout
                    results.append(result)

                    # Log result
                    if result["success"]:
                        utils.log(f"[EVAL] {instance_name}: {result['initial_cost']:.1f} -> "
                              f"{result['final_cost']:.1f} (improvement={result['improvement']*100:.3f}%) "
                              f"in {result['runtime']:.1f}s", level="debug")
                    else:
                        utils.log(f"[EVAL ERROR] {instance_name}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    utils.log(f"[EVAL EXCEPTION] {instance_name}: {e}")
                    results.append({
                        "instance": instance_name,
                        "success": False,
                        "error": str(e),
                        "initial_cost": float('inf'),
                        "final_cost": float('inf'),
                        "improvement": 0.0,
                        "runtime": 0.0
                    })

        # Sort results to match input order
        instance_order = {name: i for i, name in enumerate(instances)}
        results.sort(key=lambda x: instance_order.get(x["instance"], 999))

        return results

    def calculate_fitness(self, eval_results: List[Dict[str, Any]]) -> float:
        """
        Calculate fitness from evaluation results.

        Args:
            eval_results: List of evaluation results

        Returns:
            Fitness score (higher is better)
        """
        if not eval_results:
            return -float('inf')

        # Simple average improvement across instances
        successful_results = [r for r in eval_results if r.get("success", False)]

        if not successful_results:
            return -float('inf')

        total_improvement = sum(r["improvement"] for r in successful_results)
        return total_improvement / len(eval_results)

    def confirm_elite(self,
                     jar_path: str,
                     class_name: str,
                     instances: List[str],
                     seeds: List[int] = [42, 123, 456],
                     iterations: int = 10000,
                     timeout: int = 3600) -> Dict[str, Any]:
        """
        Run multi-seed confirmation for elite candidates.

        Args:
            jar_path: Path to plugin JAR
            class_name: Plugin class name
            instances: List of instance names
            seeds: List of random seeds
            iterations: Number of iterations per run
            timeout: Timeout per instance

        Returns:
            Aggregated results across seeds
        """
        all_runs = []

        for seed in seeds:
            results = self.evaluate_endgame(
                jar_path, class_name, instances,
                seed=seed, iterations=iterations, timeout=timeout
            )
            all_runs.append(results)

        # Calculate mean and std of improvements
        fitness_per_seed = [self.calculate_fitness(results) for results in all_runs]

        import statistics
        avg_fitness = statistics.mean(fitness_per_seed)
        std_fitness = statistics.stdev(fitness_per_seed) if len(fitness_per_seed) > 1 else 0.0

        return {
            "avg_fitness": avg_fitness,
            "std_fitness": std_fitness,
            "fitness_per_seed": fitness_per_seed,
            "all_runs": all_runs
        }
