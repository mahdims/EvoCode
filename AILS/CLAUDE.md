# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AILS-II is an Adaptive Iterated Local Search metaheuristic for solving the Large-scale Capacitated Vehicle Routing Problem (CVRP). The implementation is in Java with no external dependencies.

## Build and Run Commands

### Build the JAR file

**Linux/macOS/Git Bash:**

```bash
./scripts/build_jar.sh
```

**Windows (CMD/PowerShell):**

```cmd
scripts\build_jar.bat
```

Both scripts compile all Java sources in `src/` and create `AILSII.jar` with main class `SearchMethod.AILSII`.

### Run the algorithm

```bash
java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -rounded true -best 0 -limit 30 -stoppingCriterion Time
```

**Parameters:**

- `-file` : Path to .vrp instance file
- `-rounded` : Whether distances are rounded (true/false)
- `-stoppingCriterion` : `Time` (seconds) or `Iteration`
- `-limit` : Timeout in seconds or iteration count
- `-best` : Known optimal/BKS value for gap calculation
- `-varphi` : KNN neighborhood size (default: 40)
- `-gamma` : Iterations between omega adjustments (default: 30)
- `-dMax`/`-dMin` : Reference distance bounds (default: 30/15)

### Run on SLURM cluster

```bash
./scripts/run_dataset.sh Vrp_Set_XL_T
```

## Architecture

### Package Structure

**SearchMethod** - Main algorithm loop

- `AILSII.java` - Entry point. Implements the ILS loop: construct → local search → (perturb → feasibility → local search → accept) repeat
- `Config.java` - Algorithm parameters (eta, omega, gamma, dMin, dMax)
- `InputParameters.java` - CLI argument parsing

**Solution** - Solution representation

- `Solution.java` - Complete CVRP solution as array of Routes
- `Route.java` - Single vehicle route (circular doubly-linked list of Nodes)
- `Node.java` - Customer/depot vertex with demand, coordinates, KNN neighbors

**Improvement** - Local search operators

- `LocalSearch.java` - Inter-route operators: SHIFT, SWAP*, Cross, CrossInverted (best improvement strategy)
- `IntraLocalSearch.java` - Intra-route 2-opt and Or-opt moves
- `FeasibilityPhase.java` - Makes infeasible solutions feasible

**Perturbation** - Diversification operators

- `Perturbation.java` - Abstract base with insertion heuristics
- `Sequential.java` - Sequential removal perturbation
- `Concentric.java` - Concentric removal perturbation

**DiversityControl** - Adaptive parameter tuning

- `OmegaAdjustment.java` - Perturbation degree adaptation
- `AcceptanceCriterion.java` - Solution acceptance (eta parameter)
- `DistAdjustment.java` - Reference distance adaptation
- `IdealDist.java` - Target distance tracking

**Evaluators** - Move evaluation

- `CostEvaluation.java` - Delta cost calculations for moves
- `FeasibilityEvaluation.java` - Capacity feasibility checks
- `ExecuteMovement.java` - Apply accepted moves to solution

**Data** - Problem instance

- `Instance.java` - Parses .vrp files (TSPLIB format), builds distance matrix and KNN

### Key Algorithm Flow

1. `ConstructSolution` creates initial solution using nearest neighbor
2. `FeasibilityPhase` repairs capacity violations
3. `LocalSearch` applies inter-route moves (SHIFT, SWAP*, Cross)
4. Main loop in `AILSII.search()`:
   - Clone reference solution
   - Apply random perturbation (Sequential or Concentric)
   - Make feasible
   - Apply local search
   - Update best if improved
   - Accept/reject based on `AcceptanceCriterion`
   - Adjust omega (perturbation degree) every `gamma` iterations

### Instance Format

Uses TSPLIB .vrp format with sections: DIMENSION, CAPACITY, NODE_COORD_SECTION, DEMAND_SECTION, DEPOT_SECTION.

## Data Directories

- `data/` - VRP benchmark instances (.vrp files) and best known solutions (.sol files)
- `results/` - Experimental result tables and figures
- `warm_start/` - Pre-computed solutions for warm starting
