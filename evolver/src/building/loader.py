"""
Builder Loader

Dynamically loads builder implementations from user-provided scripts,
or delegates to the domain plugin registry for the default builder.

Mirrors the design of evaluator_loader.py.
"""

import importlib.util
import inspect
import sys
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from building import BaseBuilder
from domains.registry import DomainPluginRegistry
import domains  # noqa: F401 — triggers auto-registration of all domain plugins


def _parse_builder_spec(spec: str) -> Tuple[str, Optional[str]]:
    """Parse a builder specification into (script_path, class_name).

    Supports formats:
        "path/to/builder.py:ClassName"  -> explicit class
        "path/to/builder.py"            -> auto-detect first BaseBuilder subclass

    Handles Windows drive letters by checking that the part after the last
    colon is a valid Python identifier.

    Returns:
        (script_path, class_name_or_None)
    """
    if ":" in spec:
        script_path, candidate = spec.rsplit(":", 1)
        candidate = candidate.strip()
        if candidate.isidentifier():
            return script_path.strip(), candidate
    return spec.strip(), None


from utils.path_utils import resolve_script_path as _resolve_script_path


def load_builder_from_script(builder_spec: str,
                              builder_config: Dict[str, Any] = None) -> BaseBuilder:
    """Load a BaseBuilder subclass from a Python script.

    Args:
        builder_spec: Builder specification:
            - "path/to/builder.py:ClassName"  (explicit class)
            - "path/to/builder.py"            (auto-detect)
        builder_config: Keyword arguments passed to the builder constructor

    Returns:
        An instance of the BaseBuilder subclass

    Raises:
        FileNotFoundError: If the script does not exist
        ValueError: If no suitable class is found
    """
    script_path, class_name = _parse_builder_spec(builder_spec)
    builder_config = builder_config or {}

    path = _resolve_script_path(script_path)
    if not path.exists():
        raise FileNotFoundError(f"Builder script not found: {path}")

    logger.info(f"[BUILDER] Loading builder from: {path}"
                + (f" (class: {class_name})" if class_name else ""))

    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    spec = importlib.util.spec_from_file_location("custom_builder", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    builder_cls = None
    if class_name:
        builder_cls = getattr(module, class_name, None)
        if builder_cls is None:
            raise ValueError(
                f"Class '{class_name}' not found in {path}. "
                f"Available: {[n for n, _ in inspect.getmembers(module, inspect.isclass)]}"
            )
        if not (inspect.isclass(builder_cls)
                and issubclass(builder_cls, BaseBuilder)
                and builder_cls is not BaseBuilder):
            raise ValueError(f"'{class_name}' in {path} is not a BaseBuilder subclass")
    else:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseBuilder) and obj is not BaseBuilder:
                builder_cls = obj
                break
        if builder_cls is None:
            raise ValueError(f"No BaseBuilder subclass found in {path}")

    logger.info(f"[BUILDER] Found builder class: {builder_cls.__name__}")
    instance = builder_cls(**builder_config)
    logger.info(f"[BUILDER] Instantiated {builder_cls.__name__} with config: "
                f"{list(builder_config.keys()) or '(none)'}")
    return instance


def create_builder(config: Dict[str, Any]) -> BaseBuilder:
    """Create a builder based on configuration.

    If config["builder_script"] is set, loads a custom builder from that
    specification. The value can be:
        - "path/to/builder.py:ClassName"  (explicit class)
        - "path/to/builder.py"            (auto-detect)

    Otherwise delegates to the domain plugin registry
    (config["domain"] defaults to "ails_vrp").

    Args:
        config: Full application configuration dict

    Returns:
        A BaseBuilder instance
    """
    builder_spec = config.get("builder_script")

    if builder_spec:
        builder_config = config.get("builder_config", {})
        return load_builder_from_script(builder_spec, builder_config)

    # Default: delegate to domain plugin registry
    domain = config.get("domain", "ails_vrp")
    return DomainPluginRegistry.create(domain, config).get_builder()
