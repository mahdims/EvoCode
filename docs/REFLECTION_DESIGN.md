# ReEvo-style Reflection Design for VRP Evolution

## Overview

This document describes the **Reflection** mechanism integrated into the VRP destroy strategy evolution system, following the **ReEvo framework** (Reflective Evolution).

Reflection provides "verbal gradients" that guide the LLM's evolutionary search, replacing blind exploration with reasoned improvement.

---

## The Dual-Process Architecture

Following ReEvo, our system implements two coupled processes:

### 1. Generator (Evolution)
- **Mutation**: Modifies elite strategies
- **Crossover**: Combines parent strategies
- **Goal**: Explore the strategy space

### 2. Reflector (Reasoning)
- **Short-Term Reflection**: Analyzes parent pairs
- **Long-Term Reflection**: Accumulates knowledge
- **Goal**: Guide exploration with insights

---

## Short-Term Reflection (Guiding Crossover)

### Purpose
Understand **WHY** one strategy outperforms another by comparing a pair of parents.

### When It Occurs
- During **crossover** operation
- Compares the **better parent** vs **worse parent** selected for reproduction

### What It Analyzes
```
Input:
  - Better Parent Code
  - Better Parent Results (improvement %, per-instance costs)
  - Worse Parent Code
  - Worse Parent Results

Output:
  - Comparative analysis explaining the performance gap
  - Identification of superior logic components
  - Guidance for synthesizing offspring
```

### Example

**Better Parent (ClusteredKNNRemoval):**
```java
// Uses KNN to select clustered nodes
Node seed = validNodes.get(rand.nextInt(validNodes.size()));
for (int i = 0; i < seed.knn.length; i++) {
    toRemove.add(nodes[seed.knn[i]]);
}
```
- Improvement: **1.35%**

**Worse Parent (RandomRemoval):**
```java
// Random selection
int idx = rand.nextInt(validNodes.size());
toRemove.add(validNodes.remove(idx));
```
- Improvement: **0.36%**

**Short-Term Reflection Output:**
> "The better strategy (ClusteredKNNRemoval) outperforms random removal by 0.99 percentage points. The key difference is **spatial clustering using KNN**, which maintains locality and allows the greedy repair phase to reconstruct routes more efficiently. Random removal scatters nodes globally, forcing repair to create suboptimal long-distance connections. For crossover, preserve the KNN-based clustering approach while potentially adding diversity through adaptive cluster sizing."

### How It's Used
This reflection is passed to the **crossover prompt**, guiding the LLM to:
1. Preserve the superior logic (KNN clustering)
2. Consider complementary strengths from the worse parent
3. Create a coherent synthesis

---

## Long-Term Reflection (Guiding Mutation)

### Purpose
Accumulate **general principles** learned across multiple generations to guide elitist mutation.

### When It Occurs
- Updated every N generations (e.g., every 3 generations)
- Synthesizes all recent short-term reflections
- Maintains a **concise knowledge base** (prevents memory blowup)

### What It Synthesizes
```
Input:
  - List of recent short-term reflections (from last N crossovers)
  - Previous long-term reflection (accumulated knowledge)
  - Current generation number

Output:
  - Updated knowledge base organized by themes:
    * Node Selection Principles
    * Route Interaction Principles
    * Diversification Principles
    * Anti-patterns to Avoid
```

### Example Evolution

**Generation 3 - First Long-Term Reflection:**
```
## NODE SELECTION PRINCIPLES
- KNN-based clustering improves repair efficiency
- Random selection provides poor guidance

## ROUTE INTERACTION PRINCIPLES
- Working within single routes maintains structure
```

**Generation 6 - Updated Long-Term Reflection:**
```
## NODE SELECTION PRINCIPLES
- KNN-based clustering consistently outperforms random selection
- Adaptive cluster radius (based on omega) scales better than fixed radius
- Combining KNN with cost-based filtering yields best results

## ROUTE INTERACTION PRINCIPLES
- Route-aware selection maintains solution structure
- Cross-route removal enables global optimization but requires careful balance
- Consider route demand saturation when selecting nodes

## DIVERSIFICATION PRINCIPLES
- Pure exploitation (always best nodes) leads to local optima
- Mix 70% deterministic (KNN/cost) with 30% random for exploration

## AVOID (Anti-patterns)
- Pure random selection (no structure)
- Ignoring omega parameter (not adaptive)
- Removing only from one route (too greedy)
```

### How It's Used
This knowledge base is passed to the **mutation prompt** when mutating the **elite** strategy, guiding the LLM to:
1. Apply proven principles
2. Avoid known anti-patterns
3. Make strategic improvements (not random changes)

---

## Implementation Details

### File Structure

```
src/
├── reflection_prompts.py       # Prompt templates for both reflection types
├── llm_agents.py              # LLM interface with reflection methods
├── evolution_loop.py          # Main evolution loop with reflection integration
├── candidate_manager.py       # Compilation and caching
└── evaluator.py              # Performance evaluation
```

### Key Methods

#### In `llm_agents.py`:

```python
# Short-term reflection
short_term_insight = llm.reflect_short_term(
    better_code=parent1_code,
    better_results=parent1_results,
    worse_code=parent2_code,
    worse_results=parent2_results
)

# Long-term reflection
long_term_knowledge = llm.reflect_long_term(
    recent_short_term_reflections=reflections_list,
    previous_long_term_reflection=old_knowledge,
    generation=current_gen
)

# Crossover with short-term reflection
offspring_code = llm.crossover(
    parent1_code=better_code,
    parent2_code=worse_code,
    short_term_reflection=short_term_insight
)

# Mutation with long-term reflection
mutant_code = llm.mutate(
    parent_code=elite_code,
    parent_results=elite_results,
    long_term_reflection=long_term_knowledge,
    mutation_strength=0.3
)
```

#### In `evolution_loop.py`:

```python
# During crossover
better, worse = select_parents()
reflection = llm.reflect_short_term(better, worse)
short_term_reflections.append(reflection)  # Store for later
offspring = llm.crossover(better, worse, reflection)

# Every N generations
if generation % 3 == 0:
    long_term_knowledge = llm.reflect_long_term(
        short_term_reflections,
        long_term_knowledge
    )
    short_term_reflections.clear()  # Reset buffer

# During mutation
elite = get_best_candidate()
mutant = llm.mutate(elite, long_term_knowledge)
```

---

## Comparison: With vs Without Reflection

### Without Reflection (Blind Evolution)

**Crossover:**
```
Prompt: "Combine these two parent strategies."
```
- LLM doesn't know why parents have different performance
- Random feature mixing
- No clear guidance

**Mutation:**
```
Prompt: "Mutate this strategy."
```
- LLM has no context about what works
- Changes may break working logic
- Exploration is random

### With Reflection (Guided Evolution)

**Crossover:**
```
Prompt: "Parent A uses KNN clustering (1.35% improvement).
        Parent B uses random selection (0.36% improvement).

        Reflection: KNN clustering maintains spatial locality,
        enabling more efficient repair. Random selection scatters
        nodes and forces suboptimal long-distance connections.

        Create offspring that preserves KNN clustering strength."
```
- LLM understands performance difference
- Targeted feature inheritance
- Clear improvement direction

**Mutation:**
```
Prompt: "Elite strategy achieves 1.42% improvement.

        Accumulated Knowledge:
        - KNN clustering consistently works best
        - Adaptive cluster radius scales better
        - Mix 70% deterministic with 30% random
        - AVOID: pure random selection

        Mutate elite to apply these proven principles."
```
- LLM has learned patterns from evolution history
- Strategic improvements
- Avoids repeating past mistakes

---

## Benefits of This Design

### 1. **Sample Efficiency**
- Reflection provides "verbal gradients" that guide search
- Fewer random trials needed
- Faster convergence to good strategies

### 2. **Interpretability**
- Reflections explain **why** strategies work
- Human-readable evolution log
- Easier debugging and analysis

### 3. **Knowledge Accumulation**
- Long-term reflection builds a knowledge base
- Later generations benefit from early insights
- Prevents "forgetting" successful patterns

### 4. **Avoids Local Optima**
- Explicit anti-pattern tracking
- Diversification principles prevent premature convergence
- Balance exploitation (proven patterns) and exploration (mutation)

---

## Customization for Your Problem

The reflection prompts in `reflection_prompts.py` are **specifically tailored** for VRP destroy strategies:

### Domain-Specific Analysis Points

**Short-Term Reflection asks:**
- How do they select nodes? (KNN, random, cost-based?)
- How do they interact with routes? (single-route, cross-route?)
- What's the diversification strategy? (clustered, scattered?)
- Does it scale with omega (numToRemove)?

**Long-Term Reflection organizes:**
- **Node Selection Principles**: What selection criteria work best
- **Route Interaction Principles**: How to work with route structure
- **Diversification Principles**: Balance exploration vs exploitation
- **Anti-patterns**: What consistently fails

### To Adapt for Other Problems

If you extend beyond VRP destroy strategies, modify:
1. **Analysis dimensions** in short-term prompt (what to compare)
2. **Knowledge categories** in long-term prompt (how to organize)
3. **Available data structures** documented in mutation/crossover prompts

---

## Usage Example

```python
from evolution_loop import EvolutionLoop

# Create evolution loop with reflection
evolution = EvolutionLoop(
    population_size=20,
    elite_ratio=0.2,
    mutation_rate=0.7,
    crossover_rate=0.3
)

# Initialize with seed strategies
evolution.initialize_population(num_seeds=3)

# Run evolution (reflection happens automatically)
evolution.evolve(
    num_generations=10,
    reflection_frequency=3  # Update long-term every 3 gens
)

# Access final knowledge base
print(evolution.long_term_reflection)
```

---

## Advanced: Reflection Frequency Tuning

### Short-Term Reflection
- **Frequency**: Every crossover operation
- **Cost**: 1 LLM call per crossover
- **Buffer**: Stores 3-10 recent reflections before distilling

### Long-Term Reflection
- **Frequency**: Every N generations (configurable)
- **Cost**: 1 LLM call per update
- **Tradeoff**:
  - Too frequent: Expensive, knowledge doesn't change much
  - Too rare: Mutation lacks up-to-date guidance
  - **Recommended**: Every 3-5 generations

### Budget Optimization

If LLM calls are expensive:
1. **Reduce short-term reflection frequency**: Only reflect when parents differ significantly
2. **Batch short-term reflections**: Accumulate more before synthesizing
3. **Cache reflections**: Reuse reflection for same parent pair

---

## Monitoring Reflection Quality

### Short-Term Reflection Checklist
- [ ] Identifies specific logic differences between parents
- [ ] Explains performance gap quantitatively
- [ ] Provides actionable guidance for crossover
- [ ] Stays technical (not vague like "use better heuristics")

### Long-Term Reflection Checklist
- [ ] Organized into clear categories
- [ ] Each principle is specific and actionable
- [ ] Removes obsolete/contradicted patterns
- [ ] Maintains conciseness (8-12 bullet points)
- [ ] Includes anti-patterns to avoid

### Red Flags
⚠️ Reflection is too generic ("try to improve node selection")
⚠️ No quantitative analysis ("A is better than B")
⚠️ Long-term reflection growing unbounded (>20 bullets)
⚠️ Contradictory principles not resolved

---

## Future Enhancements

### 1. **Multi-Instance Reflection**
Currently: Reflection uses average improvement
Enhancement: Analyze per-instance patterns
- "KNN works better on large instances"
- "Random selection competitive on small instances"

### 2. **Hierarchical Knowledge Base**
Currently: Flat bullet-point list
Enhancement: Structured hierarchy
- Top-level: General principles
- Mid-level: Context-specific rules
- Low-level: Concrete implementation patterns

### 3. **Reflection-Guided Selection**
Currently: Tournament selection ignores reflection
Enhancement: Select parents that maximize learning
- Pick parents with large performance gaps (more to learn)
- Pick parents with different approaches (diverse insights)

### 4. **Meta-Reflection**
Reflect on reflection quality itself:
- "Which reflections led to successful offspring?"
- "Which principles in knowledge base are most valuable?"
- Prune ineffective patterns automatically

---

## References

- **ReEvo Paper**: "Large Language Models as Evolutionary Optimizers"
- **Key Idea**: Verbal gradients > Random mutation
- **Adaptation**: VRP-specific analysis dimensions and knowledge organization

---

## Summary

The reflection mechanism transforms **blind evolution** into **guided search**:

1. **Short-Term Reflection**: Compare parents → Guide crossover
2. **Long-Term Reflection**: Accumulate knowledge → Guide mutation
3. **Result**: Faster convergence, better strategies, interpretable process

The prompts are specifically designed for **VRP destroy strategies**, analyzing:
- Node selection logic
- Route interaction patterns
- Diversification strategies
- Known anti-patterns

This creates a self-improving system where later generations benefit from accumulated evolutionary experience.
