"""
Core — Domain-Agnostic Abstractions

Re-exports the four fundamental contracts that every domain must satisfy.
"""

from .base_builder import BaseBuilder
from .base_evaluator import BaseEvaluator, EvalResult, SmokeTestResult
from .base_domain_plugin import BaseDomainPlugin
from .registry import DomainPluginRegistry
