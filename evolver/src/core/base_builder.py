"""
Base Builder Interface

Defines the abstract interface for compiling/preparing LLM-generated source code
into runnable artifacts that the Evaluator can invoke.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class BaseBuilder(ABC):
    """Abstract base class for candidate builders.

    Subclasses know how to turn LLM-generated source code into a runnable
    artifact (a JAR, a Python script, a binary, etc.) and how to find the
    callable entry point within that artifact.

    The artifact_path / entry_point pair returned by build() is passed
    directly to BaseEvaluator.smoke_test() and BaseEvaluator.evaluate().
    """

    @abstractmethod
    def build(self,
              source_code: str,
              candidate_id: int,
              candidate_dir: str) -> Optional[Dict[str, Any]]:
        """Compile or prepare source code into a runnable artifact.

        Args:
            source_code: Raw source code from the LLM
            candidate_id: Unique integer ID for this candidate
            candidate_dir: Directory where candidate files should be stored

        Returns:
            Dict with at minimum:
                "artifact_path": str  – path to the runnable artifact
                "entry_point":   str  – name used to invoke the artifact
                                         (e.g., Java class name, Python function name)
            May include extra domain-specific keys.
            Returns None if the build fails.
        """

    @abstractmethod
    def extract_entry_point(self, source_code: str) -> Optional[str]:
        """Extract the callable entry point name from source code.

        Args:
            source_code: Raw source code from the LLM

        Returns:
            Entry point name, or None if it cannot be determined.
        """

    def get_source_path(self,
                        candidate_dir: Path,
                        metadata: Dict[str, Any]) -> Optional[Path]:
        """Return the path to the source file for a given candidate.

        Used by EvolutionLoop.resume_from_candidates() to reload source code.
        Override this in subclasses that persist source files.

        Args:
            candidate_dir: Path to the candidate's directory
            metadata: The candidate's metadata dict (loaded from metadata.json)

        Returns:
            Path to the source file, or None if not applicable.
        """
        return None

    def get_llm_context(self) -> Dict[str, Any]:
        """Return domain-specific context injected into LLM prompts.

        Override to provide constraints, available data structures, language,
        initial seed templates, etc.

        Keys used by LLMAgents (all optional):
            "constraints":          str  – mandatory code rules
            "problem_description":  str  – what problem is being solved
            "data_structures":      str  – available API / data structures
            "language":             str  – programming language (e.g. "java")
            "initial_seeds":        list – (idea: str, code: str) tuples
            "mutation_guidance":    str  – domain-specific mutation hints
            "crossover_guidance":   str  – domain-specific crossover hints

        Returns:
            Empty dict by default (LLMAgents falls back to built-in AILS defaults).
        """
        return {}
