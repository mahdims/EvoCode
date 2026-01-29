# LLM-Guided Evolution for AILS Setup Guide

## Overview

This project implements LLM-guided evolutionary search to evolve destroy operators for the AILS-II CVRP solver using Google Gemini.

## Prerequisites

- Java JDK 8+ (for compiling AILS and plugins)
- Python 3.8+ (for evolution orchestrator)
- Google Gemini API key

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:

- `google`: Google Gemini API client
- `python-dotenv`: Environment variable management

### 2. Configure Gemini API

1. Copy the example environment file:

```bash
cp .env.example .env
```

1. Edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your-actual-api-key-here
GEMINI_MODEL=gemini-1.5-flash
```

Get your API key from: <https://makersuite.google.com/app/apikey>

### 3. Build AILS

The AILS solver must be compiled before running evolution:

```bash
cd AILS/scripts
./build_jar.bat  # Windows
# or
./build_jar.sh   # Linux/Mac
```

This creates `AILS/AILSII.jar`

## Project Structure

```
evolver/
├── AILS/                      # AILS-II solver
│   ├── src/                   # Java source code
│   │   ├── EvoDestroy/        # DestroyStrategy interface (for LLM)
│   │   ├── Perturbation/      # Adapter wrappers
│   │   └── ...
│   ├── data/XL/               # CVRP instances
│   ├── warm_start/XL/         # Warmstart solutions
│   └── AILSII.jar             # Compiled solver
├── src/                       # Python evolution orchestrator
│   ├── candidate_manager.py   # Compilation & caching
│   ├── evaluator.py           # Evaluation harness
│   ├── llm_agents.py          # LLM-powered agents
│   ├── test_infrastructure.py # Infrastructure test
│   └── test_llm_seeds.py      # LLM seed generation test
├── candidates/                # Generated plugins
├── temp/                      # Temporary outputs
├── .env                       # API keys (git-ignored)
├── .env.example               # Template
└── requirements.txt           # Python dependencies
```

## Quick Test

### Test Infrastructure (No LLM Required)

```bash
cd src
python test_infrastructure.py
```

This tests:

- Plugin compilation
- AILS evaluation
- Cache system

### Test LLM Seed Generation

```bash
cd src
python test_llm_seeds.py
```

Without Gemini API (uses templates):

- Generates 3 template-based seed strategies
- Compiles them into plugin JARs
- Runs smoke test on first seed

With Gemini API (in .env):

- Can generate novel strategies via LLM

## Usage

### Template-Based Mode (No API Required)

```python
from llm_agents import LLMAgents

# Initialize without LLM
llm = LLMAgents(use_llm=False)

# Generate template seeds
code = llm.generate_initial_seed(0)  # RandomRemoval
```

### LLM-Powered Mode (Requires API Key)

```python
from llm_agents import LLMAgents

# Initialize with Gemini
llm = LLMAgents(use_llm=True)

# Mutate existing strategy
mutated_code = llm.mutate(
    parent_code=parent_strategy,
    reflection="Strategy is too random, needs more structure",
    mutation_strength=0.5
)

# Crossover two strategies
offspring_code = llm.crossover(parent1_code, parent2_code)

# Generate reflection
reflection = llm.reflect(
    strategy_code=code,
    eval_results=[
        {"instance": "XL-n1048-k237", "improvement": 0.025, "success": True}
    ]
)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | (required for LLM mode) |
| `GEMINI_MODEL` | Gemini model to use | `gemini-1.5-flash` |

Available models:

- `gemini-1.5-flash` (fast, recommended)
- `gemini-1.5-pro` (more capable)
- `gemini-2.0-flash-exp` (experimental)

## Troubleshooting

### "Module not found: dotenv"

```bash
pip install python-dotenv
```

### "Module not found: google.generativeai"

```bash
pip install google-generativeai
```

### "GEMINI_API_KEY not found"

- Check `.env` file exists in project root
- Verify API key is set correctly
- Fallback: System will use template-based generation

### "IllegalAccessError" when running plugin

- Rebuild AILS: `cd AILS/scripts && ./build_jar.bat`
- Recompile plugins: `rm -rf candidates && python test_llm_seeds.py`

## Next Steps

- See `FINALIZED IMPLEMENTATION PLAN` in plan file for Phase 1-2 roadmap
- Implement evolution loop with selection/reproduction
- Add multi-seed confirmation
- Scale to full evaluation protocol
