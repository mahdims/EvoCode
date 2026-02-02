"""
Idea History Tracker for Strategy Progress Reporting

Tracks all tested strategy ideas and their performance impact to enable
interpretability reporting showing what worked vs what didn't.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StrategyRecord:
    """Record of a tested strategy and its performance."""
    iteration: int
    idea: str
    performance: float  # 0.0-1.0 (normalized fitness)
    candidate_id: int
    timestamp: str
    mutation_type: str


class IdeaHistoryTracker:
    """Tracks all tested strategy ideas and their performance impact."""

    def __init__(self):
        self.history: List[StrategyRecord] = []
        self._best_performance_so_far = 0.0

    def record_strategy(self,
                       iteration: int,
                       idea: str,
                       performance: float,
                       candidate_id: int,
                       mutation_type: str = "unknown") -> None:
        """Record a tested strategy with its performance."""
        record = StrategyRecord(
            iteration=iteration,
            idea=idea,
            performance=performance,
            candidate_id=candidate_id,
            timestamp=datetime.now().isoformat(),
            mutation_type=mutation_type
        )
        self.history.append(record)

        # Track best performance
        if performance > self._best_performance_so_far:
            self._best_performance_so_far = performance

    def get_performance_summary(self) -> Dict[str, any]:
        """Get summary of historical performance."""
        if not self.history:
            return {}

        recent_window = 10  # Last N strategies
        recent = self.history[-recent_window:]

        return {
            "total_tested": len(self.history),
            "best_ever": self._best_performance_so_far,
            "recent_best": max(r.performance for r in recent),
            "recent_avg": sum(r.performance for r in recent) / len(recent),
            "improvement_count": sum(1 for r in self.history if r.performance > self._best_performance_so_far * 0.95)
        }

    def get_historical_ideas_with_performance(self, limit: int = 20) -> List[Dict[str, any]]:
        """Get recent tested ideas with their performance for analysis."""
        recent = self.history[-limit:]
        return [
            {
                "iteration": r.iteration,
                "idea": r.idea,
                "performance": r.performance,
                "improved": r.performance > self._best_performance_so_far * 0.95
            }
            for r in recent
        ]
