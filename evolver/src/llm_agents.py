"""
LLM Agents for Evolution

Handles:
- Initial seed generation
- Mutation of existing strategies
- Crossover between strategies
- Reflection (verbal gradients) from evaluation results

Uses Google Gemini API for code generation.
API key should be in .env file as GEMINI_API_KEY
"""

import os
from typing import Optional, Dict, List, Any

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    from pathlib import Path
    # Try to load .env from current dir or parent dir
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()  # Fall back to default behavior
except ImportError:
    pass  # dotenv is optional

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("[WARNING] google-genai not installed. Using template-based generation only.")
    print("Install with: pip install google-genai")


class LLMAgents:
    """LLM-powered agents for evolutionary operators."""

    def __init__(self, model: Optional[str] = None, use_llm: bool = True):
        """
        Initialize LLM agents.

        Args:
            model: Gemini model to use (defaults to gemini-2.0-flash-exp)
            use_llm: Whether to use LLM or template-based generation
        """
        self.use_llm = use_llm and GEMINI_AVAILABLE
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.client = None

        if self.use_llm:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("[WARNING] GEMINI_API_KEY not found in environment.")
                print("Set it with: export GEMINI_API_KEY=your-key-here")
                print("Falling back to template-based generation.")
                self.use_llm = False
            else:
                os.environ["GOOGLE_API_KEY"] = api_key  # New SDK uses GOOGLE_API_KEY
                self.client = genai.Client()
                print(f"[LLM] Using Gemini model: {self.model_name}")
        else:
            print("[LLM] Using template-based generation (no API calls)")

        # Constraints that ALL generated code must follow
        self.CONSTRAINTS = """
=== MANDATORY AILS ADAPTER CONTRACT ===
These requirements are NON-NEGOTIABLE. Violating any will cause runtime failure.

**PACKAGE & CLASS STRUCTURE:**
1. Package MUST be: package EvoDestroy;
2. Class MUST implement: DestroyStrategy interface
3. Class MUST have default constructor (no-arg): public ClassName() {}

**METHOD SIGNATURE (EXACT):**
Node[] selectNodesToRemove(int numToRemove, Route[] routes, int numRoutes,
                           Node[] nodes, Instance instance, Random rand)

**CRITICAL CONSTRAINTS:**
1. RETURN SIZE: Array size MUST be <= numToRemove (AILS will fail if more)
2. NODE VALIDATION: Only return nodes where:
   - node.nodeBelong == true (node is currently in a route)
   - node.name != 0 (never return depot)
3. NO DUPLICATES: Each node in returned array must be unique
4. USE PROVIDED RANDOM: Always use 'rand' parameter, NEVER create new Random()
5. NO I/O: No file operations, no System.out, no network calls
6. NO NEW DEPENDENCIES: Only use imports listed below
7. SINGLE CLASS: One class per file, no inner classes
8. DETERMINISTIC: Same seed must produce same selection

**REQUIRED IMPORTS:**
import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

**AVAILABLE DATA (read-only):**
- nodes[i]: Customer node (size = instance.getSize()-1, excludes depot)
  - node.name: int ID (1 to N, 0 is depot - never select!)
  - node.nodeBelong: boolean (true if currently assigned to route)
  - node.demand: int customer demand
  - node.knn[k]: k-th nearest neighbor node ID
  - node.route: parent Route object
  - node.next, node.prev: linked list pointers within route
- routes[i]: Route object (i < numRoutes)
  - route.first: depot Node (don't remove!)
  - route.first.next: first customer in route
  - route.totalDemand, route.fRoute (cost)
- instance.dist(i, j): distance between node IDs i and j

**SELECTION GUIDANCE:**
- numToRemove is adaptive (omega) - typically 5-50 nodes
- Prefer spatial clustering (nearby nodes) for better repair
- Mix deterministic and random selection (~70%/30%) for diversity
- Consider route structure when selecting

**CRITICAL: NO DUPLICATES**
You MUST ensure each node appears only ONCE in the returned array:
```java
// BAD - may contain duplicates
List<Node> selected = new ArrayList<>();
for (int i = 0; i < numToRemove; i++) {
    selected.add(candidates.get(rand.nextInt(candidates.size())));  // WRONG!
}

// GOOD - guaranteed unique nodes
List<Node> selected = new ArrayList<>();
Set<Integer> usedIds = new HashSet<>();
while (selected.size() < numToRemove && selected.size() < candidates.size()) {
    Node node = candidates.get(rand.nextInt(candidates.size()));
    if (usedIds.add(node.name)) {  // Returns false if already present
        selected.add(node);
    }
}
```
"""

    def generate_initial_seed(self, seed_id: int) -> tuple:
        """
        Generate initial seed strategy.

        Args:
            seed_id: Seed identifier (0, 1, 2, ...)

        Returns:
            (idea, code) tuple with idea description and Java source code
        """
        # Template-based seeds with companion ideas
        seed_ideas = [
            "Randomly selects nodes from valid candidates, providing baseline diversity without spatial structure.",
            "Removes nodes with highest cost contribution (distance to prev+next), targeting problematic nodes for reconstruction.",
            "Uses KNN-based spatial clustering to select geographically coherent node groups, improving repair efficiency through locality."
        ]

        seeds = [
            self._template_random_removal(),
            self._template_worst_removal(),
            self._template_clustered_removal()
        ]

        if seed_id < len(seeds):
            return seed_ideas[seed_id], seeds[seed_id]
        else:
            # Return random as fallback
            return seed_ideas[0], self._template_random_removal()

    def mutate(self,
               parent_code: str,
               parent_results: Optional[List[Dict[str, Any]]] = None,
               long_term_reflection: Optional[str] = None,
               mutation_strength: float = 0.3,
               mutation_type: Optional[str] = None,
               generation: int = 0,
               parent_idea: Optional[str] = None) -> tuple:
        """
        Mutate existing strategy with optional long-term reflection guidance.

        Enhanced with VRPAGENT typed mutations (ablation, extend, adjust_parameters, refactor).

        Args:
            parent_code: Java source code of parent strategy
            parent_results: Evaluation results for parent (required for typed mutations)
            long_term_reflection: Accumulated knowledge to guide mutation
            mutation_strength: How much to mutate (0.0-1.0)
            mutation_type: VRPAGENT mutation type (ablation/extend/adjust_parameters/refactor)
                          If None, uses basic reflection-guided mutation
            generation: Current generation (used to select mutation type if not specified)
            parent_idea: High-level idea/concept of parent strategy

        Returns:
            (idea, code) tuple with idea description and Java source code
        """
        from reflection_prompts import ReflectionPrompts
        from vrpagent_prompts import VRPAgentPrompts

        if mutation_type and parent_results:
            # VRPAGENT typed mutation with reflection
            prompt = VRPAgentPrompts.typed_mutation(
                elite_code=parent_code,
                elite_results=parent_results,
                mutation_type=mutation_type,
                long_term_reflection=long_term_reflection,
                mutation_strength=mutation_strength,
                parent_idea=parent_idea
            )
            print(f"[LLM MUTATION] Using VRPAGENT {mutation_type} mutation + reflection")
        elif long_term_reflection and parent_results:
            # ReEvo reflection-guided mutation
            prompt = ReflectionPrompts.mutation_with_long_term_reflection(
                elite_code=parent_code,
                elite_results=parent_results,
                long_term_knowledge=long_term_reflection,
                mutation_strength=mutation_strength,
                parent_idea=parent_idea
            )
            print(f"[LLM MUTATION] Using ReEvo long-term reflection-guided mutation")
        else:
            # Basic mutation prompt
            prompt = self._build_mutation_prompt(parent_code, long_term_reflection or "", mutation_strength)
            print(f"[LLM MUTATION] Using basic mutation (limited reflection)")

        print(f"[LLM MUTATION] Prompt length: {len(prompt)} chars")

        if self.use_llm:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                idea, code = self._extract_idea_and_code(response.text)
                if idea is None or code is None:
                    print("[LLM ERROR] Failed to parse IDEA and CODE sections")
                    print("[LLM] Falling back to template mutation")
                    fallback_idea = f"Mutated version of parent strategy ({mutation_type or 'generic'} mutation)."
                    return fallback_idea, self._add_mutation_comment(parent_code, "MUTATED")
                print(f"[LLM MUTATION] Generated idea ({len(idea)} chars) and code ({len(code)} chars)")
                return idea, code
            except Exception as e:
                print(f"[LLM ERROR] Mutation failed: {e}")
                print("[LLM] Falling back to template mutation")
                fallback_idea = "Mutated version of parent strategy."
                return fallback_idea, self._add_mutation_comment(parent_code, "MUTATED")
        else:
            # Placeholder: return parent code with comment
            fallback_idea = "Template-based mutation (LLM disabled)."
            return fallback_idea, self._add_mutation_comment(parent_code, "MUTATED")

    def crossover(self,
                  parent1_code: str,
                  parent2_code: str,
                  parent1_results: Optional[List[Dict[str, Any]]] = None,
                  parent2_results: Optional[List[Dict[str, Any]]] = None,
                  short_term_reflection: Optional[str] = None,
                  use_vrpagent_bias: bool = True,
                  elite_bias: float = 0.75,
                  parent1_idea: Optional[str] = None,
                  parent2_idea: Optional[str] = None) -> tuple:
        """
        Crossover between two strategies with optional reflection guidance.

        Enhanced with VRPAGENT biased crossover technique.

        Args:
            parent1_code: Java source code of first parent (better/elite)
            parent2_code: Java source code of second parent (worse/non-elite)
            parent1_results: Evaluation results for parent1 (needed for biased crossover)
            parent2_results: Evaluation results for parent2 (needed for biased crossover)
            short_term_reflection: Optional short-term reflection comparing the parents
            use_vrpagent_bias: Whether to use VRPAGENT biased crossover (default: True)
            elite_bias: Percentage to favor elite parent (default: 0.75)
            parent1_idea: High-level idea/concept of parent 1 (better)
            parent2_idea: High-level idea/concept of parent 2 (worse)

        Returns:
            (idea, code) tuple with idea description and Java source code
        """
        from reflection_prompts import ReflectionPrompts
        from vrpagent_prompts import VRPAgentPrompts

        if use_vrpagent_bias and parent1_results and parent2_results:
            # VRPAGENT biased crossover with reflection
            prompt = VRPAgentPrompts.biased_crossover(
                elite_code=parent1_code,
                elite_results=parent1_results,
                non_elite_code=parent2_code,
                non_elite_results=parent2_results,
                short_term_reflection=short_term_reflection,
                elite_bias=elite_bias,
                elite_idea=parent1_idea,
                non_elite_idea=parent2_idea
            )
            print(f"[LLM CROSSOVER] Using VRPAGENT biased crossover (bias={elite_bias:.0%}) + reflection")
        elif short_term_reflection:
            # ReEvo reflection-guided crossover
            prompt = ReflectionPrompts.crossover_with_short_term_reflection(
                better_code=parent1_code,
                worse_code=parent2_code,
                short_term_insight=short_term_reflection,
                parent1_idea=parent1_idea,
                parent2_idea=parent2_idea
            )
            print(f"[LLM CROSSOVER] Using ReEvo reflection-guided crossover")
        else:
            # Basic crossover prompt
            prompt = self._build_crossover_prompt(parent1_code, parent2_code)
            print(f"[LLM CROSSOVER] Using basic crossover (no reflection)")

        print(f"[LLM CROSSOVER] Prompt length: {len(prompt)} chars")

        if self.use_llm:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                idea, code = self._extract_idea_and_code(response.text)
                if idea is None or code is None:
                    print("[LLM ERROR] Failed to parse IDEA and CODE sections")
                    print("[LLM] Falling back to template crossover")
                    fallback_idea = "Crossover offspring combining features from both parents."
                    return fallback_idea, self._add_mutation_comment(parent1_code, "CROSSOVER")
                print(f"[LLM CROSSOVER] Generated idea ({len(idea)} chars) and code ({len(code)} chars)")
                return idea, code
            except Exception as e:
                print(f"[LLM ERROR] Crossover failed: {e}")
                print("[LLM] Falling back to template crossover")
                fallback_idea = "Crossover offspring from parents."
                return fallback_idea, self._add_mutation_comment(parent1_code, "CROSSOVER")
        else:
            # Placeholder: return parent1 with comment
            fallback_idea = "Template-based crossover (LLM disabled)."
            return fallback_idea, self._add_mutation_comment(parent1_code, "CROSSOVER")

    def generate_with_user_insight(self,
                                   insight_type: str,
                                   idea: str,
                                   related_candidates: Optional[List[Dict[str, Any]]] = None,
                                   long_term_reflection: Optional[str] = None) -> tuple:
        """
        Generate strategy guided by user insight.

        Supports three insight types:
        - "initialize": Create a new strategy from scratch based on user's idea (no related candidates)
        - "mutate": Modify a single existing strategy guided by user's idea (one related candidate)
        - "crossover": Combine features from multiple candidates based on user's idea (2+ related candidates)

        Args:
            insight_type: One of "initialize", "mutate", "crossover"
            idea: User's high-level idea/concept for the strategy
            related_candidates: List of candidate dicts:
                - None or empty for "initialize"
                - Single candidate for "mutate"
                - Multiple candidates for "crossover"
            long_term_reflection: Optional accumulated evolutionary knowledge

        Returns:
            (idea, code) tuple with generated idea description and Java source code
        """
        from vrpagent_prompts import VRPAgentPrompts

        prompt = VRPAgentPrompts.user_insight_generation(
            insight_type=insight_type,
            idea=idea,
            related_candidates=related_candidates,
            long_term_reflection=long_term_reflection
        )

        print(f"[LLM USER_INSIGHT] Type: {insight_type}")
        print(f"[LLM USER_INSIGHT] User idea: {idea[:100]}...")
        print(f"[LLM USER_INSIGHT] Prompt length: {len(prompt)} chars")

        if self.use_llm:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                generated_idea, code = self._extract_idea_and_code(response.text)
                if generated_idea is None or code is None:
                    print("[LLM ERROR] Failed to parse IDEA and CODE sections")
                    print("[LLM] Falling back to template generation")
                    fallback_idea = f"User-guided {insight_type} strategy: {idea[:50]}..."
                    return fallback_idea, self._template_random_removal()
                print(f"[LLM USER_INSIGHT] Generated idea ({len(generated_idea)} chars) and code ({len(code)} chars)")
                return generated_idea, code
            except Exception as e:
                print(f"[LLM ERROR] User insight generation failed: {e}")
                print("[LLM] Falling back to template generation")
                fallback_idea = f"User-guided strategy (fallback): {idea[:50]}..."
                return fallback_idea, self._template_random_removal()
        else:
            # Placeholder: return template with user idea as comment
            fallback_idea = f"Template-based strategy (LLM disabled). User idea: {idea}"
            return fallback_idea, self._template_random_removal()

    def reflect_short_term(self,
                           better_code: str,
                           better_results: List[Dict[str, Any]],
                           worse_code: str,
                           worse_results: List[Dict[str, Any]]) -> str:
        """
        Generate short-term reflection comparing two parents.

        Used to guide crossover by identifying why one strategy outperforms another.

        Args:
            better_code: Java source code of better-performing strategy
            better_results: Evaluation results for better strategy
            worse_code: Java source code of worse-performing strategy
            worse_results: Evaluation results for worse strategy

        Returns:
            Short-term reflection text analyzing the performance difference
        """
        from reflection_prompts import ReflectionPrompts

        prompt = ReflectionPrompts.short_term_reflection(
            better_code=better_code,
            better_results=better_results,
            worse_code=worse_code,
            worse_results=worse_results
        )

        if self.use_llm:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"[LLM ERROR] Short-term reflection failed: {e}")
                # Fall through to template

        # Template reflection as fallback
        better_avg = sum(r.get("improvement", 0) for r in better_results) / len(better_results)
        worse_avg = sum(r.get("improvement", 0) for r in worse_results) / len(worse_results)
        gap = (better_avg - worse_avg) * 100

        return f"""The better strategy outperforms the worse strategy by {gap:.3f} percentage points.
This likely stems from more effective node selection logic that better exploits route structure.
Consider combining the superior selection criteria with complementary diversification approaches."""

    def _truncate_reflection_sections(self, reflection: str, max_bullets: int = 12) -> str:
        """
        Truncate reflection sections to max_bullets per section.

        Enforces the reflection size cap: ≤12 bullets per section.

        Args:
            reflection: Raw reflection text with sections
            max_bullets: Maximum bullets per section (default 12)

        Returns:
            Truncated reflection with capped bullet counts
        """
        import re

        lines = reflection.split('\n')
        result_lines = []
        current_section_bullets = 0
        in_bullet_section = False

        for line in lines:
            stripped = line.strip()

            # Check if this is a section header (## or **SECTION**)
            is_header = stripped.startswith('##') or (stripped.startswith('**') and stripped.endswith('**'))

            # Check if this is a bullet point
            is_bullet = stripped.startswith('-') or stripped.startswith('*') or re.match(r'^\d+\.', stripped)

            if is_header:
                # Reset counter for new section
                current_section_bullets = 0
                in_bullet_section = True
                result_lines.append(line)
            elif is_bullet and in_bullet_section:
                # Count bullet points in current section
                if current_section_bullets < max_bullets:
                    result_lines.append(line)
                    current_section_bullets += 1
                # else: skip this bullet (over limit)
            elif stripped == '':
                # Empty line - preserve
                result_lines.append(line)
                in_bullet_section = False
            else:
                # Regular text (not header, not bullet)
                result_lines.append(line)
                in_bullet_section = False

        truncated = '\n'.join(result_lines)

        # Log if truncation occurred
        original_bullets = sum(1 for line in lines if line.strip().startswith('-') or line.strip().startswith('*'))
        truncated_bullets = sum(1 for line in result_lines if line.strip().startswith('-') or line.strip().startswith('*'))

        if truncated_bullets < original_bullets:
            print(f"[REFLECTION] Truncated reflection from {original_bullets} to {truncated_bullets} bullets (max {max_bullets} per section)")

        return truncated

    def reflect_long_term(self,
                         recent_short_term_reflections: List[str],
                         previous_long_term_reflection: Optional[str] = None,
                         generation: int = 0) -> str:
        """
        Generate long-term reflection synthesizing accumulated knowledge.

        Used to guide elitist mutation by maintaining a knowledge base of effective patterns.

        Args:
            recent_short_term_reflections: List of recent short-term reflections
            previous_long_term_reflection: Previous accumulated knowledge
            generation: Current generation number

        Returns:
            Long-term reflection text with accumulated knowledge (capped at 12 bullets per section)
        """
        from reflection_prompts import ReflectionPrompts

        prompt = ReflectionPrompts.long_term_reflection(
            recent_short_term_reflections=recent_short_term_reflections,
            previous_long_term_reflection=previous_long_term_reflection,
            generation=generation
        )

        reflection = None

        if self.use_llm:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                reflection = response.text
            except Exception as e:
                print(f"[LLM ERROR] Long-term reflection failed: {e}")
                # Fall through to template

        # Template reflection as fallback
        if reflection is None:
            reflection = f"""
## NODE SELECTION PRINCIPLES
- Spatial clustering using KNN improves repair efficiency
- Balance determinism with controlled randomness

## ROUTE INTERACTION PRINCIPLES
- Route-aware selection maintains solution structure
- Consider route demand and cost when selecting nodes

## DIVERSIFICATION PRINCIPLES
- Mix local intensification with global exploration
- Adapt selection strategy based on omega (numToRemove)

## AVOID (Anti-patterns)
- Pure random selection without structure
- Ignoring route boundaries entirely
"""

        # Enforce reflection size cap: truncate to ≤12 bullets per section
        return self._truncate_reflection_sections(reflection, max_bullets=12)

    def reflect(self,
                strategy_code: str,
                eval_results: List[Dict[str, Any]],
                parent_reflection: Optional[str] = None) -> str:
        """
        DEPRECATED: Use reflect_short_term() or reflect_long_term() instead.

        Generate reflection (verbal gradient) from evaluation results.

        Args:
            strategy_code: Java source code of evaluated strategy
            eval_results: List of evaluation results
            parent_reflection: Previous reflection (if available)

        Returns:
            Reflection text with analysis and suggestions
        """
        # Calculate stats
        avg_improvement = sum(r.get("improvement", 0) for r in eval_results) / len(eval_results)
        improvements = [r.get("improvement", 0) for r in eval_results]

        prompt = f"""
Analyze this VRP destroy strategy's performance and suggest improvements.

STRATEGY CODE:
{strategy_code}

PERFORMANCE:
- Average improvement: {avg_improvement*100:.2f}%
- Per instance: {[f"{imp*100:.2f}%" for imp in improvements]}

{f"PARENT REFLECTION: {parent_reflection}" if parent_reflection else ""}

Provide:
1. What this strategy does (2-3 sentences)
2. What likely worked well
3. What likely limited performance
4. 2-3 specific mutation suggestions to improve it

Keep it concise and actionable.
"""

        if self.use_llm:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"[LLM ERROR] Reflection failed: {e}")
                # Fall through to template

        # Template reflection as fallback
        reflection = f"""
REFLECTION:
- Average improvement: {avg_improvement*100:.2f}%
- This strategy shows {'positive' if avg_improvement > 0 else 'negative'} results
- Suggestions: Try different node selection criteria, consider route characteristics
"""
        return reflection

    def _build_mutation_prompt(self, parent_code: str, reflection: str, strength: float) -> str:
        """Build mutation prompt."""
        return f"""
You are evolving destroy operators for a Vehicle Routing Problem (VRP) solver.

TASK: Modify the destroy strategy to improve solution quality after 10,000 iterations.

CURRENT STRATEGY CODE:
```java
{parent_code}
```

REFLECTION (Verbal Gradient):
{reflection if reflection else "No reflection available"}

MUTATION STRENGTH: {strength}
- Low (0.0-0.3): Make small, targeted changes
- Medium (0.3-0.7): Make moderate changes to selection logic
- High (0.7-1.0): Significant restructuring

{self.CONSTRAINTS}

MUTATION GUIDANCE:
- Make minimal, targeted changes (this is mutation, not random generation)
- Focus on improving the node selection logic
- Consider using different route/node characteristics

Return only the complete Java class code, no explanations, no markdown.
"""

    def _build_crossover_prompt(self, parent1: str, parent2: str) -> str:
        """Build crossover prompt."""
        return f"""
You are evolving destroy operators for a Vehicle Routing Problem (VRP) solver.

TASK: Combine two parent strategies to create an offspring with characteristics from both.

PARENT 1 CODE:
```java
{parent1}
```

PARENT 2 CODE:
```java
{parent2}
```

{self.CONSTRAINTS}

CROSSOVER GUIDANCE:
- Combine the best aspects of both parents
- Ensure the logic is coherent (not just random splicing)
- The offspring should be a valid, working strategy

Return only the complete Java class code, no explanations, no markdown.
"""

    def _extract_idea_and_code(self, llm_response: str) -> tuple:
        """
        Extract both IDEA and CODE sections from LLM response.

        Handles the dual-section format where LLM provides both idea and code.

        Args:
            llm_response: Raw LLM response text

        Returns:
            (idea_text, code_text) or (None, None) if parsing fails
        """
        import re

        # Find ## IDEA section (just 1-2 sentences, not structured)
        idea_match = re.search(r'##\s*IDEA\s*[:\s]*(.*?)(?=##\s*CODE|\Z)', llm_response, re.DOTALL | re.IGNORECASE)

        # Find ## CODE section with java block
        code_match = re.search(r'##\s*CODE\s*\n```java\s*\n(.*?)\n```', llm_response, re.DOTALL | re.IGNORECASE)

        if not idea_match or not code_match:
            print("[PARSE ERROR] Missing IDEA or CODE section in LLM response")
            # Try fallback: maybe LLM only provided code
            code_fallback = self._extract_java_code(llm_response)
            if code_fallback and len(code_fallback) > 50:  # Valid code found
                print("[PARSE FALLBACK] Found code without IDEA section, using placeholder idea")
                return ("LLM-generated strategy without explicit idea description.", code_fallback)
            return None, None

        idea_text = idea_match.group(1).strip()
        code_text = code_match.group(1).strip()

        return idea_text, code_text

    def _extract_java_code(self, llm_response: str) -> str:
        """
        Extract Java code from LLM response.

        Handles cases where LLM wraps code in markdown blocks.

        Args:
            llm_response: Raw LLM response text

        Returns:
            Cleaned Java code
        """
        # Remove markdown code blocks if present
        if "```java" in llm_response:
            # Extract code between ```java and ```
            start = llm_response.find("```java") + 7
            end = llm_response.find("```", start)
            if end > start:
                return llm_response[start:end].strip()
        elif "```" in llm_response:
            # Generic code block
            start = llm_response.find("```") + 3
            end = llm_response.find("```", start)
            if end > start:
                return llm_response[start:end].strip()

        # No code blocks, return as-is
        return llm_response.strip()

    def _add_mutation_comment(self, code: str, mutation_type: str) -> str:
        """Add mutation comment to code (placeholder)."""
        lines = code.split('\n')
        # Find class declaration
        for i, line in enumerate(lines):
            if 'public class' in line:
                lines.insert(i, f'// {mutation_type} from parent')
                break
        return '\n'.join(lines)

    # Template-based seed strategies
    def _template_random_removal(self) -> str:
        """Template: Random removal strategy."""
        return """package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

/**
 * Random Removal Strategy
 * Randomly selects nodes to remove from the solution
 * Uses HashSet for guaranteed deduplication
 */
public class RandomRemoval implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        // Collect all valid nodes
        List<Node> validNodes = new ArrayList<>();
        for (Node node : nodes) {
            if (node != null && node.nodeBelong && node.name != 0) {
                validNodes.add(node);
            }
        }

        if (validNodes.isEmpty()) {
            return new Node[0];
        }

        // Randomly select with deduplication using HashSet
        List<Node> selected = new ArrayList<>();
        Set<Integer> usedIds = new HashSet<>();

        while (selected.size() < numToRemove && selected.size() < validNodes.size()) {
            Node node = validNodes.get(rand.nextInt(validNodes.size()));
            if (usedIds.add(node.name)) {
                selected.add(node);
            }
        }

        return selected.toArray(new Node[0]);
    }
}
"""

    def _template_worst_removal(self) -> str:
        """Template: Worst removal strategy."""
        return """package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

/**
 * Worst Removal Strategy
 * Removes nodes that contribute most to total distance
 * NO inner classes - computes cost inline
 */
public class WorstRemoval implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        // Collect valid nodes with inline cost calculation
        List<Node> validNodes = new ArrayList<>();
        List<Double> nodeCosts = new ArrayList<>();

        for (Node node : nodes) {
            if (node != null && node.nodeBelong && node.name != 0) {
                // Cost = distance to prev + distance to next
                double cost = instance.dist(node.prev.name, node.name) +
                             instance.dist(node.name, node.next.name);
                validNodes.add(node);
                nodeCosts.add(cost);
            }
        }

        if (validNodes.isEmpty()) {
            return new Node[0];
        }

        // Sort indices by cost (descending) using simple bubble sort
        List<Integer> indices = new ArrayList<>();
        for (int i = 0; i < validNodes.size(); i++) {
            indices.add(i);
        }

        for (int i = 0; i < indices.size() - 1; i++) {
            for (int j = 0; j < indices.size() - i - 1; j++) {
                if (nodeCosts.get(indices.get(j)) < nodeCosts.get(indices.get(j + 1))) {
                    int temp = indices.get(j);
                    indices.set(j, indices.get(j + 1));
                    indices.set(j + 1, temp);
                }
            }
        }

        // Select top numToRemove with deduplication
        List<Node> selected = new ArrayList<>();
        Set<Integer> usedIds = new HashSet<>();
        int count = Math.min(numToRemove, validNodes.size());

        for (int i = 0; i < indices.size() && selected.size() < count; i++) {
            Node node = validNodes.get(indices.get(i));
            if (usedIds.add(node.name)) {
                selected.add(node);
            }
        }

        return selected.toArray(new Node[0]);
    }
}
"""

    def _template_clustered_removal(self) -> str:
        """Template: Clustered removal strategy."""
        return """package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

/**
 * Clustered Removal Strategy
 * Removes geographically clustered nodes using KNN
 * Uses HashSet for guaranteed deduplication
 */
public class ClusteredRemoval implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        // Collect all valid nodes
        List<Node> validNodes = new ArrayList<>();
        for (Node node : nodes) {
            if (node != null && node.nodeBelong && node.name != 0) {
                validNodes.add(node);
            }
        }

        if (validNodes.isEmpty()) {
            return new Node[0];
        }

        // Select with deduplication using HashSet
        List<Node> selected = new ArrayList<>();
        Set<Integer> usedIds = new HashSet<>();

        // Pick random seed node
        Node seed = validNodes.get(rand.nextInt(validNodes.size()));
        selected.add(seed);
        usedIds.add(seed.name);

        // Expand cluster using KNN
        while (selected.size() < numToRemove && usedIds.size() < validNodes.size()) {
            // Pick from current cluster
            Node current = selected.get(rand.nextInt(selected.size()));

            // Find nearest neighbor not yet selected
            Node nearest = null;
            for (int i = 0; i < current.knn.length && nearest == null; i++) {
                int knnId = current.knn[i];
                if (!usedIds.contains(knnId)) {
                    // Find the node with this ID
                    for (Node candidate : validNodes) {
                        if (candidate.name == knnId) {
                            nearest = candidate;
                            break;
                        }
                    }
                }
            }

            if (nearest != null && usedIds.add(nearest.name)) {
                selected.add(nearest);
            } else {
                // No KNN neighbor found, pick random unselected node
                int attempts = 0;
                int maxAttempts = validNodes.size() * 2;
                while (attempts < maxAttempts && selected.size() < numToRemove) {
                    Node candidate = validNodes.get(rand.nextInt(validNodes.size()));
                    if (usedIds.add(candidate.name)) {
                        selected.add(candidate);
                        break;
                    }
                    attempts++;
                }
                if (attempts >= maxAttempts) {
                    break;
                }
            }
        }

        return selected.toArray(new Node[0]);
    }
}
"""
