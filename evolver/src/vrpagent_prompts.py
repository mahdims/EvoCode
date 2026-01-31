"""
VRPAGENT Prompt Techniques integrated with ReEvo Reflection

Combines:
- VRPAGENT: Biased crossover, typed mutations, code length penalty
- ReEvo: Short-term and long-term reflection for guidance

Key additions from VRPAGENT:
1. Biased Crossover: Explicit percentage bias toward elite parent
2. Four Mutation Types: Ablation, Extend, Adjust-Parameters, Refactor
3. Code Length Regularization: Prefer concise implementations
"""

from typing import Optional, Dict, List, Any
import random


class VRPAgentPrompts:
    """VRPAGENT-style prompts enhanced with ReEvo reflection."""

    # Mutation types from VRPAGENT
    MUTATION_TYPES = ["ablation", "extend", "adjust_parameters", "refactor"]

    @staticmethod
    def biased_crossover(
        elite_code: str,
        elite_results: Dict[str, Any],
        non_elite_code: str,
        non_elite_results: Dict[str, Any],
        short_term_reflection: Optional[str] = None,
        elite_bias: float = 0.75,
        elite_idea: str = None,
        non_elite_idea: str = None
    ) -> str:
        """
        VRPAGENT Biased Crossover + ReEvo Short-Term Reflection

        Combines VRPAGENT's explicit bias with ReEvo's comparative analysis.

        Args:
            elite_code: Better performing parent code
            elite_results: Elite's evaluation results
            non_elite_code: Worse performing parent code
            non_elite_results: Non-elite's evaluation results
            short_term_reflection: Optional ReEvo reflection comparing the parents
            elite_bias: Percentage to take from elite (default: 75%)
            elite_idea: High-level idea/concept of elite parent
            non_elite_idea: High-level idea/concept of non-elite parent

        Returns:
            Prompt for biased crossover with reflection guidance
        """
        elite_class = VRPAgentPrompts._extract_class_name(elite_code)
        non_elite_class = VRPAgentPrompts._extract_class_name(non_elite_code)

        # Handle cases where improvement might not be present (e.g., evaluation failed)
        elite_improvements = [r.get("improvement", 0.0) for r in elite_results if r.get("success", False)]
        elite_avg = sum(elite_improvements) / len(elite_improvements) if elite_improvements else 0.0
        non_elite_improvements = [r.get("improvement", 0.0) for r in non_elite_results if r.get("success", False)]
        non_elite_avg = sum(non_elite_improvements) / len(non_elite_improvements) if non_elite_improvements else 0.0

        non_elite_percentage = int((1 - elite_bias) * 100)
        elite_percentage = int(elite_bias * 100)

        # Include parent ideas if available
        elite_idea_section = f"\nELITE IDEA: {elite_idea}\n" if elite_idea else ""
        non_elite_idea_section = f"\nNON-ELITE IDEA: {non_elite_idea}\n" if non_elite_idea else ""

        prompt = f"""You are evolving destroy operators for a Vehicle Routing Problem (VRP) solver.

TASK: Perform BIASED CROSSOVER to create an offspring that inherits primarily from the elite parent.

=== ELITE PARENT: {elite_class} (BETTER) ==={elite_idea_section}
```java
{elite_code}
```

PERFORMANCE:
- Average Improvement: {elite_avg * 100:.3f}%
- Per-instance results:
{VRPAgentPrompts._format_results(elite_results)}

=== NON-ELITE PARENT: {non_elite_class} (WORSE) ==={non_elite_idea_section}
```java
{non_elite_code}
```

PERFORMANCE:
- Average Improvement: {non_elite_avg * 100:.3f}%
- Per-instance results:
{VRPAgentPrompts._format_results(non_elite_results)}

Performance Gap: {(elite_avg - non_elite_avg) * 100:.3f} percentage points

{"=== REFLECTION INSIGHT ===" if short_term_reflection else ""}
{short_term_reflection if short_term_reflection else ""}

=== CROSSOVER INSTRUCTION (VRPAGENT BIASED STRATEGY) ===

**CRITICAL: This is a BIASED crossover favoring exploitation over exploration.**

1. **Take {elite_percentage}% of ideas and logic from the ELITE parent**
   - Preserve the core mechanism that makes it successful
   - Keep the main selection strategy
   - Maintain the effective node/route interaction patterns

2. **Incorporate only {non_elite_percentage}% of ideas from the NON-ELITE parent**
   - Add small variations or complementary features
   - Introduce minor diversity elements
   - Test if specific small features provide benefit

3. **Ensure coherent integration**
   - The offspring must compile and run correctly
   - The logic must flow naturally (not just code splicing)
   - The {non_elite_percentage}% from non-elite should enhance, not disrupt the elite's core logic

{"4. **Use reflection insight to guide selection**" if short_term_reflection else ""}
{("   - Focus on preserving the aspects identified as superior in the reflection" if short_term_reflection else "")}
{("   - Consider whether non-elite's features address any weaknesses mentioned" if short_term_reflection else "")}

CONSTRAINTS - MUST FOLLOW:
1. Package: EvoDestroy
2. Implements: DestroyStrategy interface
3. Method signature:
   Node[] selectNodesToRemove(int numToRemove, Route[] routes, int numRoutes,
                              Node[] nodes, Instance instance, Random rand)
4. Return array size <= numToRemove
5. Only select nodes where: node.nodeBelong == true AND node.name != 0
6. Use provided Random instance (rand), do not create new Random()
7. No file I/O, no external libraries, no System.out
8. Single class only
9. Deterministic for same seed
10. **Keep code CONCISE** - aim for under 80 lines (prefer quality over verbosity)

AVAILABLE DATA STRUCTURES:
- routes[i]: Route object with first (depot), totalDemand, fRoute (cost)
- nodes[i]: Node object with name (ID), demand, knn[] (nearest neighbors), route (parent)
- instance.dist(i, j): Distance between nodes i and j
- node.knn[k]: k-th nearest neighbor ID
- route.first.next: First customer in route
- node.next, node.prev: Linked list pointers

IMPORTS REQUIRED:
import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;

=== OUTPUT FORMAT ===
You MUST provide your response in TWO sections:

## IDEA
[1-2 concise sentences describing the offspring strategy approach and why it was chosen. Be specific but brief.]

Example: "Uses KNN-based clustering with {elite_percentage}% emphasis on the elite's cost-based seeding approach, chosen to preserve proven efficiency while adding minor diversity from non-elite's adaptive selection."

## CODE
```java
[Complete Java implementation]
```

Return your response exactly in this format with both IDEA and CODE sections."""

        return prompt

    @staticmethod
    def typed_mutation(
        elite_code: str,
        elite_results: List[Dict[str, Any]],
        mutation_type: str,
        long_term_reflection: Optional[str] = None,
        mutation_strength: float = 0.3,
        parent_idea: str = None
    ) -> str:
        """
        VRPAGENT Typed Mutation + ReEvo Long-Term Reflection

        Four mutation types from VRPAGENT, guided by ReEvo's accumulated knowledge.

        Args:
            elite_code: Elite strategy code
            elite_results: Elite's evaluation results
            mutation_type: One of ["ablation", "extend", "adjust_parameters", "refactor"]
            long_term_reflection: Optional accumulated knowledge from ReEvo
            mutation_strength: Mutation strength (0.0-1.0)
            parent_idea: High-level idea/concept of parent strategy

        Returns:
            Prompt for typed mutation with reflection guidance
        """
        if mutation_type not in VRPAgentPrompts.MUTATION_TYPES:
            raise ValueError(f"Invalid mutation type: {mutation_type}. Must be one of {VRPAgentPrompts.MUTATION_TYPES}")

        elite_class = VRPAgentPrompts._extract_class_name(elite_code)
        # Handle cases where improvement might not be present (e.g., evaluation failed)
        improvements = [r.get("improvement", 0.0) for r in elite_results if r.get("success", False)]
        elite_avg = sum(improvements) / len(improvements) if improvements else 0.0

        # Include parent idea if available
        parent_idea_section = f"\nPARENT IDEA: {parent_idea}\n" if parent_idea else ""

        # Type-specific instructions
        type_instructions = {
            "ablation": """
=== MUTATION TYPE: ABLATION (Simplification) ===

**Goal:** Remove a mechanism or component to simplify the strategy.

**Instructions:**
1. Identify a mechanic, feature, or code block that may be unnecessary
2. Remove it cleanly (don't break the remaining logic)
3. Simplify the strategy to its essential elements
4. The resulting code should be more concise and potentially more robust

**What to consider removing:**
- Complex filtering logic that may not add value
- Redundant checks or conditions
- Over-engineered components
- Features that contradict accumulated knowledge (if available)

**Strength guidance:**
- Low (0.0-0.3): Remove minor features or optimizations
- Medium (0.3-0.7): Remove significant components
- High (0.7-1.0): Aggressive simplification (use carefully)
""",
            "extend": """
=== MUTATION TYPE: EXTEND (Enhancement) ===

**Goal:** Add a new mechanism or component to enhance the strategy.

**Instructions:**
1. Identify where the current strategy could be improved
2. Add a new feature, heuristic, or logic component
3. Ensure the addition integrates smoothly with existing logic
4. The enhancement should address a weakness or add capability

**What to consider adding:**
- Adaptive behavior based on omega or instance characteristics
- Additional node selection criteria
- Route-aware improvements
- Features recommended in accumulated knowledge (if available)

**Strength guidance:**
- Low (0.0-0.3): Add small enhancements or tweaks
- Medium (0.3-0.7): Add significant new logic
- High (0.7-1.0): Major feature addition (use carefully)
""",
            "adjust_parameters": """
=== MUTATION TYPE: ADJUST-PARAMETERS (Tuning) ===

**Goal:** Modify hyperparameters, thresholds, or configuration values.

**Instructions:**
1. Identify parameters in the code (loop bounds, thresholds, ratios, etc.)
2. Adjust their values to tune the strategy's behavior
3. Keep the core logic structure unchanged
4. Focus on numerical values that control behavior

**What to consider adjusting:**
- KNN neighbor counts (e.g., current.knn[i] loop bounds)
- Selection probabilities or ratios
- Cluster sizes or radius parameters
- Thresholds for filtering nodes
- Balance between deterministic and random elements

**Strength guidance:**
- Low (0.0-0.3): Small parameter tweaks (e.g., 5 → 6 neighbors)
- Medium (0.3-0.7): Moderate adjustments (e.g., 5 → 8 neighbors)
- High (0.7-1.0): Major parameter changes (e.g., 5 → 15 neighbors)
""",
            "refactor": """
=== MUTATION TYPE: REFACTOR (Optimization) ===

**Goal:** Improve code efficiency and runtime performance.

**Instructions:**
1. Identify computational inefficiencies in the current implementation
2. Refactor to reduce time complexity or unnecessary operations
3. Maintain the same algorithmic behavior (same output for same input)
4. Focus on performance, not changing the strategy logic

**What to consider refactoring:**
- Redundant distance calculations (cache results)
- Inefficient data structure access patterns
- Repeated loops that could be combined
- Unnecessary object creations in hot paths
- Early termination opportunities

**Strength guidance:**
- Low (0.0-0.3): Minor efficiency improvements
- Medium (0.3-0.7): Significant algorithmic optimizations
- High (0.7-1.0): Major restructuring for performance
"""
        }

        prompt = f"""You are evolving destroy operators for a Vehicle Routing Problem (VRP) solver.

TASK: Apply {mutation_type.upper()} mutation to the elite destroy strategy.

=== ELITE STRATEGY: {elite_class} ==={parent_idea_section}
```java
{elite_code}
```

PERFORMANCE:
- Average Improvement: {elite_avg * 100:.3f}%
- Per-instance results:
{VRPAgentPrompts._format_results(elite_results)}

{type_instructions[mutation_type]}

Current Mutation Strength: {mutation_strength} ({VRPAgentPrompts._strength_label(mutation_strength)})

{"=== ACCUMULATED EVOLUTIONARY KNOWLEDGE ===" if long_term_reflection else ""}
{long_term_reflection if long_term_reflection else ""}
{("**Use this knowledge to guide your mutation:**" if long_term_reflection else "")}
{("- Apply proven principles when extending or adjusting" if long_term_reflection else "")}
{("- Remove components that violate known good practices (ablation)" if long_term_reflection else "")}
{("- Avoid introducing known anti-patterns" if long_term_reflection else "")}

CONSTRAINTS - MUST FOLLOW:
1. Package: EvoDestroy
2. Implements: DestroyStrategy interface
3. Method signature:
   Node[] selectNodesToRemove(int numToRemove, Route[] routes, int numRoutes,
                              Node[] nodes, Instance instance, Random rand)
4. Return array size <= numToRemove
5. Only select nodes where: node.nodeBelong == true AND node.name != 0
6. Use provided Random instance (rand), do not create new Random()
7. No file I/O, no external libraries, no System.out
8. Single class only
9. Deterministic for same seed
10. **Keep code CONCISE** - favor shorter, clearer code over verbose implementations

AVAILABLE DATA STRUCTURES:
- routes[i]: Route object with first (depot), totalDemand, fRoute (cost)
- nodes[i]: Node object with name (ID), demand, knn[] (nearest neighbors), route (parent)
- instance.dist(i, j): Distance between nodes i and j
- node.knn[k]: k-th nearest neighbor ID
- route.first.next: First customer in route
- node.next, node.prev: Linked list pointers

IMPORTS REQUIRED:
import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;

=== OUTPUT FORMAT ===
You MUST provide your response in TWO sections:

## IDEA
[1-2 concise sentences describing the mutated strategy approach and why this {mutation_type} mutation was chosen. Be specific but brief.]

Example: "Reduces KNN neighbor count from 10 to 6 and adds early termination when cluster reaches target size, chosen to improve efficiency while maintaining spatial coherence."

## CODE
```java
[Complete Java implementation]
```

Return your response exactly in this format with both IDEA and CODE sections."""

        return prompt

    @staticmethod
    def select_mutation_type(
        elite_code: str,
        generation: int,
        long_term_reflection: Optional[str] = None
    ) -> str:
        """
        Intelligently select mutation type based on context.

        Can be random (VRPAGENT style) or guided by reflection.

        Args:
            elite_code: Elite strategy code
            generation: Current generation number
            long_term_reflection: Accumulated knowledge

        Returns:
            Mutation type string
        """
        # Simple heuristic: early generations explore more, later generations refine
        if generation < 5:
            # Early: favor extension and adjustment
            weights = {
                "ablation": 0.1,
                "extend": 0.5,
                "adjust_parameters": 0.3,
                "refactor": 0.1
            }
        elif generation < 15:
            # Mid: balanced
            weights = {
                "ablation": 0.25,
                "extend": 0.25,
                "adjust_parameters": 0.25,
                "refactor": 0.25
            }
        else:
            # Late: favor refinement
            weights = {
                "ablation": 0.3,
                "extend": 0.1,
                "adjust_parameters": 0.3,
                "refactor": 0.3
            }

        # TODO: Could use long_term_reflection to further bias selection
        # e.g., if knowledge says "strategies are too complex", favor ablation

        types = list(weights.keys())
        probs = list(weights.values())
        return random.choices(types, weights=probs)[0]

    @staticmethod
    def calculate_code_length_penalty(code: str, alpha: float = 0.001) -> float:
        """
        VRPAGENT Code Length Penalty

        Fitness penalty to encourage concise implementations.

        Args:
            code: Java source code
            alpha: Penalty coefficient (default: 0.001)

        Returns:
            Penalty value (higher = worse)
        """
        # Count non-empty, non-comment lines
        lines = [
            line.strip()
            for line in code.split('\n')
            if line.strip() and not line.strip().startswith('//')
        ]

        # Filter out imports, package declarations
        code_lines = [
            line for line in lines
            if not line.startswith('package') and not line.startswith('import')
        ]

        num_lines = len(code_lines)

        # Penalty: alpha * num_lines
        penalty = alpha * num_lines

        return penalty

    # Helper methods

    @staticmethod
    def _extract_class_name(code: str) -> str:
        """Extract class name from Java code."""
        import re
        match = re.search(r'public\s+class\s+(\w+)', code)
        return match.group(1) if match else "UnknownClass"

    @staticmethod
    def _format_results(results: list) -> str:
        """Format evaluation results for display."""
        lines = []
        for r in results:
            instance = r.get("instance", "unknown")
            improvement = r.get("improvement", 0) * 100
            initial = r.get("initial_cost", 0)
            final = r.get("final_cost", 0)
            lines.append(f"  • {instance}: {initial:.1f} → {final:.1f} (Δ={improvement:.3f}%)")
        return "\n".join(lines)

    @staticmethod
    def _strength_label(strength: float) -> str:
        """Convert strength to label."""
        if strength < 0.3:
            return "Low - Minor changes"
        elif strength < 0.7:
            return "Medium - Moderate changes"
        else:
            return "High - Significant changes"


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("VRPAGENT Prompts + ReEvo Reflection")
    print("="*80)

    example_elite_code = """package EvoDestroy;
import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;

public class ClusteredKNNRemoval implements DestroyStrategy {
    @Override
    public Node[] selectNodesToRemove(int numToRemove, Route[] routes, int numRoutes,
                                     Node[] nodes, Instance instance, Random rand) {
        List<Node> toRemove = new ArrayList<>();
        // ... KNN-based clustering implementation ...
        return toRemove.toArray(new Node[0]);
    }
}"""

    example_non_elite_code = """package EvoDestroy;
import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;

public class RandomRemoval implements DestroyStrategy {
    @Override
    public Node[] selectNodesToRemove(int numToRemove, Route[] routes, int numRoutes,
                                     Node[] nodes, Instance instance, Random rand) {
        List<Node> toRemove = new ArrayList<>();
        // ... random selection ...
        return toRemove.toArray(new Node[0]);
    }
}"""

    elite_results = [
        {"instance": "XL-n1048-k237", "initial_cost": 380246.0, "final_cost": 375120.0, "improvement": 0.0135},
        {"instance": "XL-n2426-k391", "initial_cost": 852340.0, "final_cost": 843210.0, "improvement": 0.0107}
    ]

    non_elite_results = [
        {"instance": "XL-n1048-k237", "initial_cost": 380246.0, "final_cost": 378890.0, "improvement": 0.0036},
        {"instance": "XL-n2426-k391", "initial_cost": 852340.0, "final_cost": 849120.0, "improvement": 0.0038}
    ]

    reflection = "KNN clustering maintains spatial locality better than random selection."

    print("\n=== BIASED CROSSOVER PROMPT ===\n")
    prompt = VRPAgentPrompts.biased_crossover(
        example_elite_code, elite_results,
        example_non_elite_code, non_elite_results,
        reflection, elite_bias=0.75
    )
    print(prompt[:800] + "...\n")

    print("="*80)
    print("\n=== ABLATION MUTATION PROMPT ===\n")
    prompt = VRPAgentPrompts.typed_mutation(
        example_elite_code, elite_results,
        "ablation", reflection
    )
    print(prompt[:800] + "...\n")

    print("="*80)
    print("\n=== CODE LENGTH PENALTY ===\n")
    penalty = VRPAgentPrompts.calculate_code_length_penalty(example_elite_code)
    print(f"Code has {len(example_elite_code.split(chr(10)))} lines")
    print(f"Penalty: {penalty:.6f}")
