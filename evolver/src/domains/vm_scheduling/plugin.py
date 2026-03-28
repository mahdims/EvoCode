"""
VM Scheduling Domain Plugin

Wires together VmSchedulingBuilder, VmSchedulingEvaluator, and templates
into a single domain plugin, and registers it as "vm_scheduling" in
the DomainPluginRegistry.
"""

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from core.base_domain_plugin import BaseDomainPlugin
from core.registry import DomainPluginRegistry
from .builder import VmSchedulingBuilder
from .evaluator import VmSchedulingEvaluator
from .templates import get_vm_initial_seeds


class VmSchedulingPlugin(BaseDomainPlugin):
    """Domain plugin for evolving TenantPlugin implementations.

    Config keys consumed:
        source_code_root  (str)  – path to applications/VM_Scheduling (relative or absolute)
        target_instances  (list) – instance names to evaluate on (without .json)
        smoke_test_instance (str)– instance name for smoke test (optional)
        seed              (int)  – random seed
        timeout           (int)  – per-instance solver timeout in seconds (default 120)
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}

        # Resolve VM Scheduling root
        evolver_root = Path(__file__).parent.parent.parent.parent
        raw = config.get("source_code_root", "../applications/VM_Scheduling")
        vm_root = Path(raw) if Path(raw).is_absolute() else (evolver_root / raw).resolve()

        vm_jar = str(vm_root / "target" / "vm-scheduling-1.0-SNAPSHOT.jar")
        data_dir = str(vm_root / "data")

        target_instances = config.get("target_instances", [])
        smoke_test_instance = config.get("smoke_test_instance", None)
        seed = config.get("seed", 42)
        timeout = config.get("timeout", 120)

        self._builder = VmSchedulingBuilder(vm_scheduling_jar=vm_jar)
        self._evaluator = VmSchedulingEvaluator(
            vm_scheduling_jar=vm_jar,
            data_dir=data_dir,
            target_instances=target_instances,
            smoke_test_instance=smoke_test_instance,
            seed=seed,
            timeout=timeout,
        )
        self._instances = target_instances

        logger.debug(
            f"[VM SCHEDULING PLUGIN] Initialized — "
            f"jar={vm_jar}, instances={target_instances}"
        )

    # ------------------------------------------------------------------
    # BaseDomainPlugin interface
    # ------------------------------------------------------------------

    def get_builder(self) -> VmSchedulingBuilder:
        return self._builder

    def get_evaluator(self) -> VmSchedulingEvaluator:
        return self._evaluator

    def get_llm_context(self) -> Dict[str, Any]:
        return self._builder.get_llm_context()

    def get_initial_seeds(self) -> List[tuple]:
        return get_vm_initial_seeds()

    def get_instances(self) -> List[str]:
        return self._instances


# Auto-register when this module is imported
DomainPluginRegistry.register("vm_scheduling", VmSchedulingPlugin)
