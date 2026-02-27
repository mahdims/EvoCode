"""
AILS VRP Domain Plugin

Wires together AILSBuilder, AILSEvaluator, and AILS templates into a single
domain plugin, and registers it as "ails_vrp" in the DomainPluginRegistry.
"""

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from core.base_domain_plugin import BaseDomainPlugin
from core.registry import DomainPluginRegistry
from .builder import AILSBuilder
from .evaluator import AILSEvaluator
from .templates import get_ails_initial_seeds


class AILSVRPPlugin(BaseDomainPlugin):
    """Domain plugin for the AILS VRP destroy-strategy evolution problem.

    Reads all domain-specific parameters from ``config``:
        ails_jar        (str)  – path to AILSII.jar
        dataset_dir     (str)  – directory containing .vrp instance files
        target_instances (list)– instance names to evaluate on
        seed            (int)  – random seed for AILS
        max_parallel_evals (int) – max parallel evaluation workers
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}

        # Resolve AILS root: config["source_code_root"] is the single source of truth.
        # Relative paths are resolved against evolver_root so they work regardless of CWD.
        # Falls back to <evolver_root>/AILS for backward compatibility.
        evolver_root = Path(__file__).parent.parent.parent.parent
        if config.get("source_code_root"):
            _raw = Path(config["source_code_root"])
            ails_root = _raw if _raw.is_absolute() else (evolver_root / _raw).resolve()
        else:
            ails_root = evolver_root / "AILS"

        ails_jar = config.get("ails_jar", str(ails_root / "AILSII.jar"))
        dataset_dir = config.get("dataset_dir", "Vrp_Set_X")
        target_instances = config.get("target_instances", [])
        seed = config.get("seed", 42)
        max_workers = config.get("max_parallel_evals")

        data_dir = str(ails_root / "data" / dataset_dir)
        warmstart_dir = str(ails_root / "warm_start" / dataset_dir)

        self._builder = AILSBuilder(ails_jar=ails_jar)
        self._evaluator = AILSEvaluator(
            ails_jar=ails_jar,
            data_dir=data_dir,
            warmstart_dir=warmstart_dir,
            target_instances=target_instances,
            max_workers=max_workers,
            seed=seed,
        )
        self._instances = target_instances

        logger.debug(f"[AILS VRP PLUGIN] Initialized — "
                     f"jar={ails_jar}, dataset={dataset_dir}, "
                     f"instances={target_instances}")

    # ------------------------------------------------------------------
    # BaseDomainPlugin interface
    # ------------------------------------------------------------------

    def get_builder(self) -> AILSBuilder:
        return self._builder

    def get_evaluator(self) -> AILSEvaluator:
        return self._evaluator

    def get_llm_context(self) -> Dict[str, Any]:
        return self._builder.get_llm_context()

    def get_initial_seeds(self) -> List[tuple]:
        return get_ails_initial_seeds()

    def get_instances(self) -> List[str]:
        return self._instances


# Auto-register when this module is imported
DomainPluginRegistry.register("ails_vrp", AILSVRPPlugin)
