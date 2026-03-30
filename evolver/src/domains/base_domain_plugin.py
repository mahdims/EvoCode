"""
Base Domain Plugin Interface

A DomainPlugin bundles everything that varies between problem domains:
  - How to build LLM-generated code (BaseBuilder)
  - How to evaluate built code (BaseEvaluator)
  - What the LLM should generate (context, seeds, constraints)

The EvolutionLoop holds one DomainPlugin and delegates all domain concerns
through it, keeping evolutionary logic (selection, reflection, diversity,
parallelism) completely domain-agnostic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from building.base_builder import BaseBuilder
from evaluation.base_evaluator import BaseEvaluator


class BaseDomainPlugin(ABC):
    """Abstract base class for domain plugins.

    Implement this to add a new problem domain to EvoCode without touching
    any of the evolutionary machinery.

    Example::

        class MyDomainPlugin(BaseDomainPlugin):
            def get_builder(self):    return MyBuilder()
            def get_evaluator(self):  return MyEvaluator()
            def get_llm_context(self): return {"language": "python", ...}
            def get_initial_seeds(self): return [("idea", "code"), ...]

        DomainPluginRegistry.register("my_domain", MyDomainPlugin)
    """

    @abstractmethod
    def get_builder(self) -> BaseBuilder:
        """Return the builder for this domain."""

    @abstractmethod
    def get_evaluator(self) -> BaseEvaluator:
        """Return the evaluator for this domain."""

    @abstractmethod
    def get_llm_context(self) -> Dict[str, Any]:
        """Return LLM prompt context for this domain.

        Keys consumed by LLMAgents (all optional):
            "constraints":          str  – mandatory code rules
            "problem_description":  str  – what problem is being solved
            "data_structures":      str  – available API / data structures
            "language":             str  – programming language (e.g. "java")
            "initial_seeds":        list – (idea: str, code: str) tuples
            "mutation_guidance":    str  – domain-specific mutation hints
            "crossover_guidance":   str  – domain-specific crossover hints
        """

    @abstractmethod
    def get_initial_seeds(self) -> List[tuple]:
        """Return (idea: str, code: str) pairs for seeding the initial population."""

    def get_instances(self) -> List[str]:
        """Return the list of evaluation instance names.

        Override to provide domain-specific instances from the plugin rather
        than requiring them to be listed in config.
        """
        return []
