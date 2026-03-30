"""
Diversity Checker for Idea-Based Conceptual Diversity

Prevents re-exploring duplicate conceptual approaches using keyword-based similarity.
"""

from typing import List, Set, Optional
import re


class DiversityChecker:
    """Checks conceptual diversity of strategy ideas using keyword similarity."""

    def __init__(self, similarity_threshold: float = 0.80):
        """
        Args:
            similarity_threshold: Reject ideas with similarity above this (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def extract_keywords(self, idea_text: str) -> Set[str]:
        """
        Extract key concept words from idea text.

        Focuses on technical terms, ignores common words.

        Args:
            idea_text: Idea description text

        Returns:
            Set of extracted keywords
        """
        if not idea_text:
            return set()

        # Lowercase and extract words (4+ characters)
        words = re.findall(r'\b[a-z]{4,}\b', idea_text.lower())

        # Filter stopwords - common words that don't indicate concept
        stopwords = {
            'this', 'that', 'with', 'from', 'have', 'will', 'would',
            'could', 'should', 'nodes', 'node', 'remove', 'strategy', 'destroy',
            'removal', 'select', 'selection', 'chosen', 'because', 'approach',
            'uses', 'using', 'based', 'provides', 'providing', 'improves',
            'improving', 'targets', 'targeting', 'allows', 'enabling'
        }

        # Extract meaningful keywords
        keywords = {w for w in words if w not in stopwords}

        return keywords

    def compute_similarity(self, idea1: str, idea2: str) -> float:
        """
        Compute Jaccard similarity between two ideas.

        Jaccard similarity = |intersection| / |union|

        Args:
            idea1: First idea text
            idea2: Second idea text

        Returns:
            Similarity score 0.0-1.0 (1.0 = identical concepts)
        """
        keywords1 = self.extract_keywords(idea1)
        keywords2 = self.extract_keywords(idea2)

        if not keywords1 or not keywords2:
            return 0.0

        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def is_diverse(self, new_idea: str, population_ideas: List[str]) -> bool:
        """
        Check if new idea is sufficiently diverse from population.

        Args:
            new_idea: Idea text to check
            population_ideas: List of existing ideas in population

        Returns:
            True if diverse enough, False if too similar to existing idea
        """
        if not population_ideas:
            return True  # First idea is always diverse

        for existing_idea in population_ideas:
            if existing_idea is None:
                continue  # Skip legacy candidates without ideas

            similarity = self.compute_similarity(new_idea, existing_idea)

            if similarity > self.similarity_threshold:
                return False  # Too similar, reject

        return True  # Sufficiently diverse

    def find_most_similar(self, new_idea: str, population_ideas: List[str]) -> Optional[tuple]:
        """
        Find most similar idea in population.

        Args:
            new_idea: Idea text to check
            population_ideas: List of existing ideas in population

        Returns:
            (index, similarity_score) or None if population empty
        """
        if not population_ideas:
            return None

        max_similarity = -1
        max_index = -1

        for i, existing_idea in enumerate(population_ideas):
            if existing_idea is None:
                continue

            similarity = self.compute_similarity(new_idea, existing_idea)

            if similarity > max_similarity:
                max_similarity = similarity
                max_index = i

        if max_index == -1:
            return None

        return (max_index, max_similarity)
