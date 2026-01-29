# Documentation

This directory contains detailed design documentation for the VRP Destroy Strategy Evolution system.

## Files

### Architecture & Integration

- **[INTEGRATED_SYSTEM.md](INTEGRATED_SYSTEM.md)**: Complete system architecture showing how ReEvo reflection and VRPAGENT techniques are integrated
  - Overall design
  - Component interactions
  - Prompt engineering details

### ReEvo Framework

- **[REFLECTION_DESIGN.md](REFLECTION_DESIGN.md)**: Detailed design of the ReEvo dual-process reflection system
  - Short-term reflection (parent comparison)
  - Long-term reflection (knowledge accumulation)
  - Prompt structures

- **[REFLECTION_SUMMARY.md](REFLECTION_SUMMARY.md)**: Summary of ReEvo concepts and implementation
  - Key concepts
  - Verbal gradients
  - Reflection synthesis

### VRPAGENT Techniques

- **[VRPAGENT_INTEGRATION_SUMMARY.md](VRPAGENT_INTEGRATION_SUMMARY.md)**: Integration of VRPAGENT prompt engineering techniques
  - Biased crossover (75/25)
  - Typed mutations (ablation, extend, adjust-parameters, refactor)
  - Code length penalty
  - Generation-aware mutation selection

## Quick Navigation

**For understanding the system:**
1. Start with [INTEGRATED_SYSTEM.md](INTEGRATED_SYSTEM.md) for overall architecture
2. Read [REFLECTION_DESIGN.md](REFLECTION_DESIGN.md) to understand the reflection mechanism
3. See [VRPAGENT_INTEGRATION_SUMMARY.md](VRPAGENT_INTEGRATION_SUMMARY.md) for advanced features

**For implementation details:**
- See the main [README.md](../README.md) for usage and setup
- Check source code docstrings in `src/` for technical details
