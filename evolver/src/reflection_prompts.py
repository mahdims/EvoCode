"""
Reflection Prompts for ReEvo-style Dual-Process Evolution

Following the ReEvo framework:
- Short-Term Reflection: Compares two parents to guide crossover
- Long-Term Reflection: Accumulates knowledge over generations to guide mutation

Adapted for VRP AILS Destroy Strategy Evolution
"""
from __future__ import annotations


class ReflectionPrompts:
    """Manages short-term and long-term reflection prompts."""

    @staticmethod
    def short_term_reflection(
        better_code: str,
        better_results: dict,
        worse_code: str,
        worse_results: dict,
        problem_context: str = "Vehicle Routing Problem (VRP) with AILS"
    ) -> str:
        """
        Short-Term Reflection Prompt

        Compares two parent strategies to identify what makes one better than the other.
        Used to guide crossover generation.

        Args:
            better_code: Java code of better-performing strategy
            better_results: Evaluation results for better strategy
            worse_code: Java code of worse-performing strategy
            worse_results: Evaluation results for worse strategy
            problem_context: Problem description

        Returns:
            Prompt string for LLM reflection
        """
        # Extract performance metrics (handle missing improvement key gracefully)
        better_improvements = [r.get("improvement", 0.0) for r in better_results if r.get("success", False)]
        better_avg_imp = sum(better_improvements) / len(better_improvements) if better_improvements else 0.0
        worse_improvements = [r.get("improvement", 0.0) for r in worse_results if r.get("success", False)]
        worse_avg_imp = sum(worse_improvements) / len(worse_improvements) if worse_improvements else 0.0

        better_class = ReflectionPrompts._extract_class_name(better_code)
        worse_class = ReflectionPrompts._extract_class_name(worse_code)

        prompt = f"""You are a heuristic expert analyzing destroy strategies for {problem_context}.

You have evaluated two different destroy strategies (Strategy A and Strategy B) on the same VRP instances with warmstart solutions.

=== STRATEGY A: {better_class} ===
```java
{better_code}
```

PERFORMANCE OF STRATEGY A:
- Average Improvement: {better_avg_imp * 100:.3f}%
- Per-instance results:
{ReflectionPrompts._format_results(better_results)}

=== STRATEGY B: {worse_class} ===
```java
{worse_code}
```

PERFORMANCE OF STRATEGY B:
- Average Improvement: {worse_avg_imp * 100:.3f}%
- Per-instance results:
{ReflectionPrompts._format_results(worse_results)}

=== PERFORMANCE COMPARISON ===
Strategy A has BETTER performance than Strategy B.
- Improvement gap: {(better_avg_imp - worse_avg_imp) * 100:.3f} percentage points

=== YOUR TASK ===
Analyze the differences in logic between Strategy A and Strategy B. Identify which specific logic components or design choices contribute to Strategy A's superior performance.

Consider these aspects:
1. **Node Selection Criteria**: How do they choose which nodes to remove?
   - Random selection vs structured selection
   - Use of KNN (K-nearest neighbors) for clustering
   - Use of distance metrics or route characteristics
   - Use of node demand or cost contributions

2. **Route Interaction**: How do they interact with routes?
   - Single route vs multi-route strategies
   - Route-based clustering vs global selection
   - Consideration of route cost or demand

3. **Diversification vs Intensification**:
   - Does the strategy explore diverse regions (remove scattered nodes)?
   - Does it intensify in problematic areas (remove clustered nodes)?
   - Balance between randomness and determinism

4. **Scalability Patterns**:
   - Does it adapt well to `numToRemove` (omega) parameter?
   - Does it handle large/small instances differently?

Provide a concise analysis (4-6 sentences) that:
- Explains the KEY DIFFERENCE in approach between A and B
- Identifies which specific logic or component leads to A's better performance
- Suggests how to combine or inherit A's strengths for creating an even better offspring

Keep your analysis technical, specific, and actionable for guiding crossover generation."""

        return prompt

    @staticmethod
    def long_term_reflection(
        recent_short_term_reflections: list[str],
        previous_long_term_reflection: str = None,
        generation: int = 0
    ) -> str:
        """
        Long-Term Reflection Prompt

        Synthesizes accumulated knowledge from multiple short-term reflections.
        Used to guide elitist mutation.

        Args:
            recent_short_term_reflections: List of recent short-term reflection outputs
            previous_long_term_reflection: Previous accumulated knowledge (if any)
            generation: Current generation number

        Returns:
            Prompt string for LLM reflection
        """
        prompt = f"""You are a heuristic expert observing the evolution of VRP destroy strategies over multiple generations.

You have been tracking the evolution for {generation} generations. Your goal is to maintain a concise yet comprehensive knowledge base of what makes destroy strategies effective for VRP end-game optimization (starting from warmstart solutions and improving over 10,000 iterations).

=== CURRENT ACCUMULATED KNOWLEDGE ===
{previous_long_term_reflection if previous_long_term_reflection else "No previous knowledge yet (this is generation 0)."}

=== RECENT SHORT-TERM REFLECTIONS ===
These are insights from comparing parent pairs in recent generations:

{ReflectionPrompts._format_short_term_list(recent_short_term_reflections)}

=== YOUR TASK ===
Update the Accumulated Knowledge by incorporating the Recent Short-Term Reflections.

Guidelines:
1. **Distill Patterns**: Identify recurring successful patterns across multiple reflections
   - What node selection strategies consistently work well?
   - What route interaction patterns are effective?
   - What balance of diversification vs intensification is optimal?

2. **Discard Obsolete Strategies**: Remove or downplay strategies that have been superseded
   - If a new approach consistently outperforms an old one, note that
   - If a pattern was thought useful but recent evidence contradicts it, update accordingly

3. **Maintain Conciseness**: Keep the knowledge base focused
   - Aim for 8-12 bullet points maximum
   - Each bullet should be specific and actionable
   - Avoid vague statements like "use good heuristics" - be concrete

4. **Organize by Theme**: Group insights into categories:
   - **Node Selection Principles**: How to choose nodes
   - **Route Interaction Principles**: How to work with routes
   - **Diversification Principles**: How to balance exploration
   - **Avoid**: Known anti-patterns or ineffective approaches

=== OUTPUT FORMAT ===
Return the updated Accumulated Knowledge in this structure:

## NODE SELECTION PRINCIPLES
- [Specific principle about node selection]
- [Another principle]

## ROUTE INTERACTION PRINCIPLES
- [Specific principle about route handling]
- [Another principle]

## DIVERSIFICATION PRINCIPLES
- [Specific principle about exploration/exploitation balance]
- [Another principle]

## AVOID (Anti-patterns)
- [Known ineffective approach]
- [Another anti-pattern]

Keep each principle concise (1-2 sentences) and directly actionable for guiding mutation of the current elite strategy."""

        return prompt

    @staticmethod
    def crossover_with_short_term_reflection(
        better_code: str,
        worse_code: str,
        short_term_insight: str,
        parent1_idea: str = None,
        parent2_idea: str = None
    ) -> str:
        """
        Crossover Prompt with Short-Term Reflection Guidance

        Used to generate offspring from two parents using insights from short-term reflection.

        Args:
            better_code: Better parent's code
            worse_code: Worse parent's code
            short_term_insight: Insight from short-term reflection comparing these parents
            parent1_idea: High-level idea/concept of parent 1 (better)
            parent2_idea: High-level idea/concept of parent 2 (worse)

        Returns:
            Prompt for LLM to generate crossover offspring
        """
        better_class = ReflectionPrompts._extract_class_name(better_code)
        worse_class = ReflectionPrompts._extract_class_name(worse_code)

        # Include parent ideas if available
        parent1_idea_section = f"\nPARENT 1 IDEA: {parent1_idea}\n" if parent1_idea else ""
        parent2_idea_section = f"\nPARENT 2 IDEA: {parent2_idea}\n" if parent2_idea else ""

        prompt = f"""You are evolving destroy operators for a Vehicle Routing Problem (VRP) solver.

TASK: Combine two parent strategies to create an offspring that inherits the strengths of both, guided by comparative analysis.

=== PARENT 1 (BETTER PERFORMER): {better_class} ==={parent1_idea_section}
```java
{better_code}
```

=== PARENT 2 (WORSE PERFORMER): {worse_class} ==={parent2_idea_section}
```java
{worse_code}
```

=== REFLECTION INSIGHT (Why Parent 1 > Parent 2) ===
{short_term_insight}

=== YOUR TASK ===
Create an offspring strategy that:
1. **Inherits the superior logic** from Parent 1 (as identified in the reflection)
2. **Considers useful diversity** from Parent 2 (if it has complementary strengths)
3. **Synthesizes coherently** - don't just splice code randomly; create a unified approach

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

CROSSOVER GUIDANCE:
- The reflection identified what makes Parent 1 better - make sure to preserve that
- Look for complementary logic in Parent 2 that could enhance Parent 1's approach
- Create a new class name (not same as either parent)
- Ensure the logic flows coherently

=== OUTPUT FORMAT ===
You MUST provide your response in TWO sections:

## IDEA
[1-2 concise sentences describing the offspring strategy approach and why it was chosen. Be specific but brief.]

Example: "Uses KNN-based clustering starting from high-cost nodes to select spatially coherent regions for removal, chosen because clustered removal improves repair efficiency while cost-based seeding targets problematic areas."

## CODE
```java
[Complete Java implementation]
```

Return your response exactly in this format with both IDEA and CODE sections."""

        return prompt

    @staticmethod
    def mutation_with_long_term_reflection(
        elite_code: str,
        elite_results: dict,
        long_term_knowledge: str,
        mutation_strength: float = 0.3,
        parent_idea: str = None
    ) -> str:
        """
        Mutation Prompt with Long-Term Reflection Guidance

        Used to mutate the elite strategy using accumulated knowledge.

        Args:
            elite_code: Current elite strategy code
            elite_results: Evaluation results for elite
            long_term_knowledge: Accumulated knowledge from long-term reflection
            mutation_strength: Mutation strength (0.0-1.0)
            parent_idea: High-level idea/concept of parent strategy

        Returns:
            Prompt for LLM to generate mutated strategy
        """
        elite_class = ReflectionPrompts._extract_class_name(elite_code)
        # Handle cases where improvement might not be present (e.g., evaluation failed)
        improvements = [r.get("improvement", 0.0) for r in elite_results if r.get("success", False)]
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0.0

        # Include parent idea if available
        parent_idea_section = f"\nPARENT IDEA: {parent_idea}\n" if parent_idea else ""

        prompt = f"""You are evolving destroy operators for a Vehicle Routing Problem (VRP) solver.

TASK: Mutate the current elite destroy strategy to improve solution quality, guided by accumulated evolutionary knowledge.

=== CURRENT ELITE STRATEGY: {elite_class} ==={parent_idea_section}
```java
{elite_code}
```

PERFORMANCE:
- Average Improvement: {avg_improvement * 100:.3f}%
- Per-instance results:
{ReflectionPrompts._format_results(elite_results)}

=== ACCUMULATED EVOLUTIONARY KNOWLEDGE ===
This knowledge base contains proven principles learned from {len(long_term_knowledge.split('- '))} previous generations:

{long_term_knowledge}

=== MUTATION GUIDANCE ===
Mutation Strength: {mutation_strength}
- Low (0.0-0.3): Make small, targeted refinements
- Medium (0.3-0.7): Moderate changes to selection logic
- High (0.7-1.0): Significant restructuring (use sparingly to avoid local optima)

Strategy:
1. **Apply Accumulated Knowledge**: Use the principles above to guide your mutation
   - If elite violates any principle, fix it
   - If elite could benefit from a proven pattern, incorporate it
   - Avoid known anti-patterns

2. **Make Targeted Changes**: Don't randomize - improve strategically
   - Focus on areas where elite shows weakness
   - Enhance what already works well
   - Scale changes according to mutation strength

3. **Maintain Coherence**: Ensure the mutated strategy makes logical sense
   - Don't break working logic
   - Keep the overall approach unified

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
[1-2 concise sentences describing the mutated strategy approach and why this mutation was chosen. Be specific but brief.]

Example: "Combines KNN-based clustering with adaptive cluster radius based on numToRemove, chosen to improve scalability while preserving the spatial locality that makes the parent effective."

## CODE
```java
[Complete Java implementation]
```

Return your response exactly in this format with both IDEA and CODE sections."""

        return prompt

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
    def _format_short_term_list(reflections: list[str]) -> str:
        """Format list of short-term reflections."""
        if not reflections:
            return "(No recent reflections yet)"

        formatted = []
        for i, reflection in enumerate(reflections, 1):
            formatted.append(f"--- Reflection {i} ---")
            formatted.append(reflection.strip())
            formatted.append("")
        return "\n".join(formatted)


# Example usage and testing
if __name__ == "__main__":
    print("=== SHORT-TERM REFLECTION PROMPT EXAMPLE ===\n")

    example_better_code = """package EvoDestroy;
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
        // Implementation using KNN clustering
        List<Node> toRemove = new ArrayList<>();
        // ... KNN-based selection ...
        return toRemove.toArray(new Node[0]);
    }
}"""

    example_worse_code = """package EvoDestroy;
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
        // Random selection
        List<Node> toRemove = new ArrayList<>();
        // ... random selection ...
        return toRemove.toArray(new Node[0]);
    }
}"""

    example_better_results = [
        {"instance": "XL-n1048-k237", "initial_cost": 380246.0, "final_cost": 375120.0, "improvement": 0.0135},
        {"instance": "XL-n2426-k391", "initial_cost": 852340.0, "final_cost": 843210.0, "improvement": 0.0107}
    ]

    example_worse_results = [
        {"instance": "XL-n1048-k237", "initial_cost": 380246.0, "final_cost": 378890.0, "improvement": 0.0036},
        {"instance": "XL-n2426-k391", "initial_cost": 852340.0, "final_cost": 849120.0, "improvement": 0.0038}
    ]

    prompt = ReflectionPrompts.short_term_reflection(
        example_better_code,
        example_better_results,
        example_worse_code,
        example_worse_results
    )

    print(prompt)
    print("\n" + "="*80 + "\n")

    print("=== LONG-TERM REFLECTION PROMPT EXAMPLE ===\n")

    example_short_term = [
        "Clustered removal using KNN outperforms random removal because it exploits spatial locality, allowing the repair phase to reconstruct routes more efficiently.",
        "Route-based selection performs better than global random selection because it maintains route structure and reduces cross-route dependencies."
    ]

    example_previous_knowledge = """
## NODE SELECTION PRINCIPLES
- KNN-based clustering helps maintain spatial locality
- Random selection provides poor guidance for repair phase

## ROUTE INTERACTION PRINCIPLES
- Working within single routes is more effective than global scattering
"""

    prompt = ReflectionPrompts.long_term_reflection(
        example_short_term,
        example_previous_knowledge,
        generation=5
    )

    print(prompt)
