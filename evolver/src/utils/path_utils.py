"""
Shared path resolution utilities.

Used by builder_loader and evaluator_loader to locate user-provided scripts
from a set of well-known base directories.
"""

from pathlib import Path


def resolve_script_path(script_path: str) -> Path:
    """Resolve a script path, trying multiple base directories.

    Tries in order:
        1. Absolute / CWD-relative
        2. Relative to evolver/      (parent of src/)
        3. Relative to repo root     (parent of evolver/)
        4. Relative to src/ directory

    Args:
        script_path: Absolute or relative path to a Python script.

    Returns:
        Resolved Path (may not exist — caller must check).
    """
    path = Path(script_path)

    if path.is_absolute():
        return path.resolve()

    search_bases = [
        Path.cwd(),
        Path(__file__).parent.parent.parent,   # evolver/
        Path(__file__).parent.parent.parent.parent,  # repo root
        Path(__file__).parent.parent,          # evolver/src/
    ]
    for base in search_bases:
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate

    # Fall back to CWD-relative (will trigger FileNotFoundError in caller)
    return (Path.cwd() / path).resolve()
