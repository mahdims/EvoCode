"""
Abstract base class for prompt generation strategies.

Implement this to plug in a new prompt style (ReEvo, VRPAGENT, custom, etc.)
without modifying LLMAgents. Pass an instance to LLMAgents(prompt_generator=...).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BasePromptGenerator(ABC):
    """Contract for LLM prompt generation strategies."""

    @abstractmethod
    def short_term_reflection_prompt(
        self,
        better_code: str,
        better_results: list,
        worse_code: str,
        worse_results: list,
        problem_context: str,
        language: str,
    ) -> str:
        """Build a prompt that compares two parents to explain the performance gap."""

    @abstractmethod
    def long_term_reflection_prompt(
        self,
        recent_reflections: List[str],
        previous_reflection: Optional[str],
        generation: int,
        problem_context: str,
    ) -> str:
        """Build a prompt that distills accumulated knowledge from many generations."""

    @abstractmethod
    def crossover_prompt(
        self,
        better_code: str,
        worse_code: str,
        short_term_insight: Optional[str],
        parent1_idea: Optional[str],
        parent2_idea: Optional[str],
        language: str,
        constraints: Optional[str],
        better_results: Optional[list] = None,
        worse_results: Optional[list] = None,
        elite_bias: float = 0.75,
    ) -> str:
        """Build a prompt that generates a crossover offspring from two parents."""

    @abstractmethod
    def mutation_prompt(
        self,
        elite_code: str,
        elite_results: list,
        long_term_reflection: Optional[str],
        mutation_strength: float,
        parent_idea: Optional[str],
        language: str,
        constraints: Optional[str],
        mutation_type: Optional[str] = None,
        generation: int = 0,
    ) -> str:
        """Build a prompt that mutates the elite strategy."""
