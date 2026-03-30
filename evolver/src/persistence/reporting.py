"""
Reporting and statistics display for the evolution loop.

Pure display functions — no evolutionary state is mutated here.
Each function takes the data it needs as parameters rather than
reading from an EvolutionLoop instance, keeping concerns separated.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


def display_long_term_reflection(reflection: str) -> None:
    """Format and display long-term reflection in a clean, readable format."""
    if not reflection:
        return

    lines = reflection.strip().split('\n')

    logger.info("")
    logger.info("=" * 80)
    logger.info("CUMULATIVE KNOWLEDGE - Strategic Insights")
    logger.info("=" * 80)

    current_section = None
    section_items = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('##'):
            if current_section and section_items:
                logger.info(f" ")
                logger.info(f"{current_section}")
                logger.info("-" * 60)
                for item in section_items:
                    logger.info(f"  {item}")
                section_items = []
            current_section = stripped.replace('##', '').strip()

        elif stripped.startswith('-') or stripped.startswith('*'):
            content = stripped.lstrip('-*').strip().replace('**', '')
            section_items.append(f"• {content}")

        elif stripped and not stripped.startswith('='):
            section_items.append(f"  {stripped}")

    if current_section and section_items:
        logger.info(f" ")
        logger.info(f"{current_section}")
        logger.info("-" * 60)
        for item in section_items:
            logger.info(f"  {item}")

    logger.info("")
    logger.info("=" * 80)


def report_iteration_statistics(
    generation: int,
    candidate_counter: int,
    generation_start_counter: int,
    population: List[Dict[str, Any]],
) -> None:
    """Report comprehensive statistics for the current generation."""
    fitnesses = [c["fitness"] for c in population]
    best = max(population, key=lambda x: x["fitness"])
    worst = min(population, key=lambda x: x["fitness"])
    avg_fitness = sum(fitnesses) / len(fitnesses)

    gen_tested = candidate_counter - generation_start_counter
    total_tested = candidate_counter

    logger.info("")
    logger.info("-" * 80)
    logger.info(f"Generation {generation} - Statistics Summary")
    logger.info("-" * 80)
    logger.info(f"  Candidates tested this generation: {gen_tested}")
    logger.info(f"  Total candidates tested: {total_tested}")
    logger.info(f"  Best solution: ID={best['candidate_id']}, fitness={best['fitness']*100:.4f}%")

    best_idea = best.get('idea', 'N/A')
    if len(best_idea) > 120:
        best_idea = best_idea[:117] + "..."
    logger.info(f"  Best idea: {best_idea}")
    logger.info(f"  Worst solution: ID={worst['candidate_id']}, fitness={worst['fitness']*100:.4f}%")
    logger.info(f"  Average population fitness: {avg_fitness*100:.4f}%")
    logger.info("-" * 80)


def report_strategy_progress(
    generation: int,
    population: List[Dict[str, Any]],
    idea_history,
    llm,
    long_term_reflection: Optional[str],
    prev_iteration_best: Optional[float],
) -> float:
    """Generate and display strategy progress analysis.

    Returns the updated prev_iteration_best value for the caller to store.
    """
    current_strategies = [
        {
            "idea": c.get("idea"),
            "performance": c.get("fitness", 0.0),
            "candidate_id": c.get("candidate_id"),
        }
        for c in population
        if c.get("idea") is not None
    ]

    if not current_strategies:
        return prev_iteration_best or 0.0

    historical_ideas = idea_history.get_historical_ideas_with_performance(limit=15)
    fitnesses = [c["fitness"] for c in population]
    perf_summary = idea_history.get_performance_summary()

    best_fitness = max(fitnesses)
    performance_metrics = {
        "best": best_fitness,
        "average": sum(fitnesses) / len(fitnesses),
        "total_tested": perf_summary.get("total_tested", 0),
        "improvement": best_fitness - prev_iteration_best if prev_iteration_best is not None else 0.0,
    }

    analysis = llm.analyze_strategy_directions(
        current_strategies=current_strategies,
        historical_ideas=historical_ideas,
        long_term_reflection=long_term_reflection,
        iteration=generation,
        performance_metrics=performance_metrics,
    )

    logger.info(
        f"\n{'='*70}\n"
        f"EXPOLRATION STRATEGIES - Iteration {generation}\n"
        f"{'='*70}\n"
        f"{analysis}\n"
        f"{'='*70}\n"
    )

    return best_fitness


def print_final_statistics(
    population: List[Dict[str, Any]],
    candidate_counter: int,
    use_vrpagent: bool,
) -> None:
    """Print final evolution statistics."""
    best = max(population, key=lambda x: x["fitness"])

    logger.info(f"{'='*80}")
    logger.info(f"FINAL STATISTICS")
    logger.info(f"{'='*80}")
    logger.info(f"Total candidates evaluated: {candidate_counter}")
    logger.info(f"Final population size: {len(population)}")
    logger.info(f"Best candidate ID: {best['candidate_id']}")
    logger.info(f"Best fitness: {best['fitness']*100:.4f}%")
    if use_vrpagent and "base_fitness" in best:
        logger.info(f"Best base fitness (no penalty): {best['base_fitness']*100:.4f}%")
    logger.info(f"Best generation: {best['generation']}")

    if best.get("idea"):
        logger.info(f"")
        logger.info(f"Best candidate idea:")
        logger.info(f"  {best['idea']}")

    logger.info(f"Best candidate performance:")
    for result in best["eval_results"]:
        instance_name = result.get('instance', result.get('name', 'unknown'))
        improvement = result.get('improvement', result.get('improvement_pct', 0) / 100)
        logger.info(f"  {instance_name}: {improvement*100:.3f}% improvement")

    if use_vrpagent:
        code_lines = len([
            line for line in best["code"].split('\n')
            if line.strip()
            and not line.strip().startswith('//')
            and not line.strip().startswith('package')
            and not line.strip().startswith('import')
        ])
        logger.info(f"Best candidate code length: {code_lines} lines")

    logger.info(f"\n{'='*80}\n")


def save_idea_evolution_log(
    population: List[Dict[str, Any]],
    candidates_dir: Path,
    log_file: Optional[str] = None,
) -> None:
    """Save evolution history of ideas to a Markdown file for analysis."""
    if log_file is None:
        log_file = str(candidates_dir / "idea_evolution.md")

    with open(log_file, 'w') as f:
        f.write("# Idea Evolution Log\n\n")
        f.write(f"Generated from {len(population)} candidates\n\n")

        for candidate in sorted(population, key=lambda x: x.get("generation", 0)):
            f.write(
                f"## Generation {candidate.get('generation', 0)} - "
                f"Candidate {candidate['candidate_id']}\n\n"
            )
            f.write(f"**Fitness:** {candidate['fitness']*100:.4f}%\n\n")
            f.write(f"**Mutation Type:** {candidate.get('mutation_type', 'unknown')}\n\n")

            if candidate.get("parent_id") is not None:
                f.write(f"**Parent ID:** {candidate['parent_id']}\n\n")

            if candidate.get("idea"):
                f.write("### Idea\n\n")
                f.write(candidate["idea"])
                f.write("\n\n")
            else:
                f.write("*[No idea available - legacy candidate]*\n\n")

            f.write("---\n\n")

    logger.info(f"[LOG] Saved idea evolution to {log_file}")
