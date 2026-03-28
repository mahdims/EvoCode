"""
VM Scheduling Evaluator

Runs the VM Scheduling solver (Main.java) with a candidate TenantPlugin
and parses structured penalty output to compute a fitness score.

Fitness = mean violation reduction across all target instances:
  reduction = (total_initial - total_final) / max(1, total_initial)
  where total = penalty_A + penalty_B + penalty_C
"""

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from core.base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult


_KEY_FIELDS = [
    "INITIAL_PENALTY_A", "INITIAL_PENALTY_B", "INITIAL_PENALTY_C",
    "FINAL_PENALTY_A",   "FINAL_PENALTY_B",   "FINAL_PENALTY_C",
    "EMPTY_HOSTS_INITIAL", "EMPTY_HOSTS_FINAL",
    "MIGRATIONS", "RUNTIME_MS",
]


def _parse_output(stdout: str) -> Optional[Dict[str, int]]:
    """Parse key=value lines from Main.java structured output."""
    result = {}
    for line in stdout.splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("["):
            key, _, val = line.partition("=")
            key = key.strip()
            if key in _KEY_FIELDS:
                try:
                    result[key] = int(val.strip())
                except ValueError:
                    pass
    # Return only if we have at least the basic penalty fields
    required = {"INITIAL_PENALTY_A", "FINAL_PENALTY_A"}
    return result if required.issubset(result) else None


def _run_instance(
    vm_jar: str,
    candidate_jar: str,
    instance_path: str,
    class_name: str,
    seed: int,
    timeout: int,
) -> Dict[str, Any]:
    """Run Main.java on one instance; return parsed results dict."""
    classpath = f"{candidate_jar}{';' if '\\\\' in candidate_jar or ':' not in candidate_jar else ':'}{vm_jar}"
    # Windows uses semicolon, Linux/Mac uses colon
    import os
    sep = ";" if os.name == "nt" else ":"
    classpath = f"{candidate_jar}{sep}{vm_jar}"

    cmd = [
        "java",
        "-cp", classpath,
        "com.vmscheduling.Main",
        instance_path,
        str(seed),
        class_name,
    ]

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - t0
        parsed = _parse_output(proc.stdout)
        if proc.returncode != 0 or parsed is None:
            return {
                "success": False,
                "error": f"Exit {proc.returncode}: {proc.stderr[:500]}",
                "runtime": elapsed,
                "stdout": proc.stdout[:2000],
            }
        return {
            "success": True,
            "runtime": elapsed,
            **parsed,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "runtime": timeout}
    except Exception as e:
        return {"success": False, "error": str(e), "runtime": 0.0}


def _compute_reduction(result: Dict[str, Any]) -> float:
    """Compute violation reduction ratio from parsed result."""
    if not result.get("success"):
        return 0.0
    initial = (result.get("INITIAL_PENALTY_A", 0)
               + result.get("INITIAL_PENALTY_B", 0)
               + result.get("INITIAL_PENALTY_C", 0))
    final = (result.get("FINAL_PENALTY_A", 0)
             + result.get("FINAL_PENALTY_B", 0)
             + result.get("FINAL_PENALTY_C", 0))
    return (initial - final) / max(1, initial)


class VmSchedulingEvaluator(BaseEvaluator):
    """Evaluates TenantPlugin JARs by running the VM Scheduling ALNS solver."""

    def __init__(
        self,
        vm_scheduling_jar: str,
        data_dir: str,
        target_instances: List[str] = None,
        smoke_test_instance: Optional[str] = None,
        seed: int = 42,
        timeout: int = 120,
    ):
        self.vm_jar = vm_scheduling_jar
        self.data_dir = Path(data_dir)
        self.target_instances = target_instances or []
        self.smoke_test_instance = smoke_test_instance
        self.seed = seed
        self.timeout = timeout

    def _resolve_instance(self, name: str) -> Optional[Path]:
        """Resolve instance name to .json file path."""
        for suffix in ["", ".json"]:
            p = self.data_dir / f"{name}{suffix}"
            if p.exists():
                return p
        return None

    def smoke_test(self, artifact_path: str, candidate_name: str) -> SmokeTestResult:
        """Quick validation — run on one small instance, check output format."""
        # Pick smoke test instance
        instance_name = self.smoke_test_instance
        if not instance_name:
            # Auto-select smallest JSON file in data_dir
            jsons = list(self.data_dir.glob("*.json"))
            if not jsons:
                return SmokeTestResult(success=False, output="No JSON instances found")
            instance_name = min(jsons, key=lambda f: f.stat().st_size).stem

        instance_path = self._resolve_instance(instance_name)
        if instance_path is None:
            return SmokeTestResult(
                success=False,
                output=f"Smoke test instance not found: {instance_name}"
            )

        logger.debug(f"[VM SMOKE] Using instance: {instance_path.name}")
        result = _run_instance(
            vm_jar=self.vm_jar,
            candidate_jar=artifact_path,
            instance_path=str(instance_path),
            class_name=candidate_name,
            seed=self.seed,
            timeout=min(self.timeout, 60),
        )

        output = result.get("stdout", result.get("error", ""))
        return SmokeTestResult(
            success=result["success"],
            output=output,
            runtime=result.get("runtime", 0.0),
            exit_code=0 if result["success"] else 1,
        )

    def evaluate(self, artifact_path: str, candidate_name: str) -> List[EvalResult]:
        """Evaluate on all target instances."""
        eval_results = []
        for instance_name in self.target_instances:
            instance_path = self._resolve_instance(instance_name)
            if instance_path is None:
                logger.warning(f"[VM EVAL] Instance not found: {instance_name}")
                eval_results.append(EvalResult(
                    instance=instance_name,
                    success=False,
                    scores={"reduction": 0.0},
                    error=f"Instance file not found: {instance_name}",
                ))
                continue

            result = _run_instance(
                vm_jar=self.vm_jar,
                candidate_jar=artifact_path,
                instance_path=str(instance_path),
                class_name=candidate_name,
                seed=self.seed,
                timeout=self.timeout,
            )

            reduction = _compute_reduction(result)
            initial_total = (result.get("INITIAL_PENALTY_A", 0)
                             + result.get("INITIAL_PENALTY_B", 0)
                             + result.get("INITIAL_PENALTY_C", 0))
            final_total = (result.get("FINAL_PENALTY_A", 0)
                           + result.get("FINAL_PENALTY_B", 0)
                           + result.get("FINAL_PENALTY_C", 0))

            eval_results.append(EvalResult(
                instance=instance_name,
                success=result["success"],
                scores={"reduction": reduction},
                metadata={
                    "initial_penalty_A": result.get("INITIAL_PENALTY_A", 0),
                    "initial_penalty_B": result.get("INITIAL_PENALTY_B", 0),
                    "initial_penalty_C": result.get("INITIAL_PENALTY_C", 0),
                    "final_penalty_A":   result.get("FINAL_PENALTY_A",   0),
                    "final_penalty_B":   result.get("FINAL_PENALTY_B",   0),
                    "final_penalty_C":   result.get("FINAL_PENALTY_C",   0),
                    "initial_total": initial_total,
                    "final_total": final_total,
                    "empty_hosts_initial": result.get("EMPTY_HOSTS_INITIAL", 0),
                    "empty_hosts_final":   result.get("EMPTY_HOSTS_FINAL",   0),
                    "migrations":  result.get("MIGRATIONS",  0),
                    "runtime_ms":  result.get("RUNTIME_MS",  0),
                    "runtime":     result.get("runtime",     0.0),
                },
                error=result.get("error"),
            ))

        return eval_results

    def get_score_names(self) -> List[str]:
        return ["reduction"]

    def get_instances(self) -> List[str]:
        return self.target_instances

    def calculate_fitness(self, results: List[EvalResult]) -> Optional[float]:
        """Mean reduction across all successful results (0 if none succeed)."""
        if not results:
            return -float("inf")
        successful = [r for r in results if r.success]
        if not successful:
            return -float("inf")
        total = sum(r.scores.get("reduction", 0.0) for r in successful)
        return total / len(results)  # penalise failures by dividing by all, not just successful
