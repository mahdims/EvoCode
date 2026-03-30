"""
Shared prompt utilities.

Common helpers used by ReflectionPrompts and VRPAgentPrompts to avoid
duplication across prompt generation classes.
"""

import re


def extract_class_name(code: str) -> str:
    """Extract the public class name from Java source code."""
    match = re.search(r'public\s+class\s+(\w+)', code)
    return match.group(1) if match else "UnknownClass"


def format_results(results: list) -> str:
    """Format evaluation results for display in LLM prompts."""
    lines = []
    for r in results:
        instance = r.get("instance", "unknown")
        improvement = r.get("improvement", 0) * 100
        initial = r.get("initial_cost", 0)
        final = r.get("final_cost", 0)
        lines.append(f"  • {instance}: {initial:.1f} → {final:.1f} (Δ={improvement:.3f}%)")
    return "\n".join(lines)
