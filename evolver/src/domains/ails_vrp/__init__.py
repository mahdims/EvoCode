"""
AILS VRP Domain

Re-exports key classes for convenient imports.
Importing this package auto-registers AILSVRPPlugin with DomainPluginRegistry.
"""

from .builder import AILSBuilder
from .evaluator import AILSEvaluator
from .templates import get_ails_initial_seeds, AILS_CONSTRAINTS
from .plugin import AILSVRPPlugin
