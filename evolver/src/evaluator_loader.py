"""
Evaluator Loader

Dynamically loads evaluator implementations from user-provided scripts
or delegates to the domain plugin registry for the default evaluator.
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from loguru import logger

from evaluator import BaseEvaluator
from core.registry import DomainPluginRegistry
import domains  # noqa: F401 — triggers auto-registration of all domain plugins


def _parse_evaluator_spec(spec: str) -> Tuple[str, str | None]:
    """Parse an evaluator specification into (script_path, class_name).

    Supports formats:
        "path/to/evaluator.py:ClassName"  -> explicit class
        "path/to/evaluator.py"            -> auto-detect first BaseEvaluator subclass

    Handles Windows drive letters (e.g. "D:/path/file.py") by checking that
    the part after the last colon looks like a Python identifier.

    Returns:
        (script_path, class_name_or_None)
    """
    if ":" in spec:
        script_path, candidate = spec.rsplit(":", 1)
        candidate = candidate.strip()
        # A class name is a valid Python identifier (no slashes or dots)
        if candidate.isidentifier():
            return script_path.strip(), candidate
    return spec.strip(), None


def _resolve_script_path(script_path: str) -> Path:
    """Resolve a script path, trying multiple base directories.

    Tries in order:
        1. Absolute / CWD-relative
        2. Relative to project root  (evolver/)
        3. Relative to repo root     (parent of evolver/)
        4. Relative to src/ directory (evolver/src/)
    """
    path = Path(script_path)

    if path.is_absolute():
        return path.resolve()

    search_bases = [
        Path.cwd(),
        Path(__file__).parent.parent,          # evolver/
        Path(__file__).parent.parent.parent,   # repo root
        Path(__file__).parent,                 # evolver/src/
    ]
    for base in search_bases:
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate

    # Fall back to CWD-relative (will trigger FileNotFoundError later)
    return (Path.cwd() / path).resolve()


def load_evaluator_from_script(evaluator_spec: str,
                                evaluator_config: Dict[str, Any] = None,
                                common_params: Dict[str, Any] = None) -> BaseEvaluator:
    """Load a BaseEvaluator subclass from a Python script.

    Args:
        evaluator_spec: Evaluator specification in one of two formats:
            - "path/to/evaluator.py:ClassName"  (explicit class)
            - "path/to/evaluator.py"            (auto-detect first BaseEvaluator subclass)
        evaluator_config: Evaluator-specific keyword arguments
        common_params: Common parameters (target_instances, max_workers, etc.)
                      that are merged into evaluator_config

    Returns:
        An instance of the BaseEvaluator subclass

    Raises:
        FileNotFoundError: If the script does not exist
        ValueError: If the specified class is not found or no BaseEvaluator subclass exists
    """
    script_path, class_name = _parse_evaluator_spec(evaluator_spec)

    # Merge common params with evaluator-specific config
    # evaluator_config takes precedence (user can override common params)
    merged_config = {}
    if common_params:
        merged_config.update(common_params)
    if evaluator_config:
        merged_config.update(evaluator_config)
    evaluator_config = merged_config

    path = _resolve_script_path(script_path)

    if not path.exists():
        raise FileNotFoundError(f"Evaluator script not found: {path}")

    logger.info(f"[EVALUATOR] Loading evaluator from: {path}"
                + (f" (class: {class_name})" if class_name else ""))

    # Ensure the script's directory is in sys.path so its imports resolve
    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Load module from file
    spec = importlib.util.spec_from_file_location("custom_evaluator", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the evaluator class
    evaluator_cls = None

    if class_name:
        # Explicit class name provided - look it up directly
        evaluator_cls = getattr(module, class_name, None)
        if evaluator_cls is None:
            raise ValueError(
                f"Class '{class_name}' not found in {path}. "
                f"Available names: {[n for n, _ in inspect.getmembers(module, inspect.isclass)]}"
            )
        if not (inspect.isclass(evaluator_cls)
                and issubclass(evaluator_cls, BaseEvaluator)
                and evaluator_cls is not BaseEvaluator):
            raise ValueError(
                f"'{class_name}' in {path} is not a BaseEvaluator subclass"
            )
    else:
        # Auto-detect first BaseEvaluator subclass
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseEvaluator) and obj is not BaseEvaluator:
                evaluator_cls = obj
                break
        if evaluator_cls is None:
            raise ValueError(f"No BaseEvaluator subclass found in {path}")

    logger.info(f"[EVALUATOR] Found evaluator class: {evaluator_cls.__name__}")

    instance = evaluator_cls(**evaluator_config)
    logger.info(f"[EVALUATOR] Instantiated {evaluator_cls.__name__} with config: "
                f"{list(evaluator_config.keys()) or '(none)'}")
    return instance


def create_evaluator(config: Dict[str, Any],
                     target_instances=None,
                     max_workers=None) -> BaseEvaluator:
    """Create an evaluator based on configuration.

    If config["evaluator_script"] is set, loads a custom evaluator from that
    specification. The value can be:
        - "path/to/evaluator.py:ClassName"  (explicit class)
        - "path/to/evaluator.py"            (auto-detect)

    Otherwise delegates to the domain plugin registry
    (config["domain"] defaults to "ails_vrp").

    Common parameters (target_instances, max_workers, config) are automatically
    passed to custom evaluators, so users don't need to duplicate them in
    evaluator_config.

    Args:
        config: Full application configuration dict
        target_instances: List of instance names (passed to custom evaluators)
        max_workers: Max parallel workers (passed to custom evaluators)

    Returns:
        A BaseEvaluator instance
    """
    evaluator_spec = config.get("evaluator_script")

    if evaluator_spec:
        evaluator_config = config.get("evaluator_config", {})
        # Common params that custom evaluators might need
        common_params = {
            "target_instances": target_instances or [],
            "max_workers": max_workers,
            "config": config,
        }
        return load_evaluator_from_script(evaluator_spec, evaluator_config, common_params)

    # Default: delegate to domain plugin registry
    domain = config.get("domain", "ails_vrp")
    return DomainPluginRegistry.create(domain, config).get_evaluator()
