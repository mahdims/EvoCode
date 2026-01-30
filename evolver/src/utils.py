"""
Utility functions for the evolution system.
"""

# Global verbose flag
_VERBOSE = True


def set_verbose(verbose: bool):
    """Set global verbose flag."""
    global _VERBOSE
    _VERBOSE = verbose


def log(message: str, level: str = "info"):
    """
    Log a message respecting verbose flag.

    Args:
        message: Message to log
        level: 'debug' (only if verbose=True) or 'info' (always shown)
    """
    global _VERBOSE
    if level == "info" or _VERBOSE:
        print(message)
