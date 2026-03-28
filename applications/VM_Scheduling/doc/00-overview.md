# ALNS Migration Solver — Implementation Plan

## What This Is

These files describe the complete implementation of the **Adaptive Large Neighborhood Search (ALNS) Migration Solver** used in the Server Consolidation V2 system. The solver finds near-optimal VM-to-host placements in a data center by iteratively destroying (ruining) parts of the current solution and rebuilding (recreating) them using adaptive operator selection.

## File Index

| # | File | What It Covers |
|---|------|---------------|
| 01 | `01-data-structures.md` | Model layer: Rack, Host, NumaGroup, Numa, Vm, Placement, Problem, MigrationSolution, Value types |
| 02 | `02-incremental-evaluation.md` | Variable layer, delta objects (RuinDelta/RecreateDelta), fetcher pattern, CpuMemVariable example |
| **02a** | **`02a-unified-interface-contract.md`** | **The three parallel interfaces (Variable/Constraint/Objective), how they wire through Problem, every call site in the ALNS loop, data flow diagram, extension pattern** |
| 03 | `03-constraints.md` | MigrationConstraint interface, hierarchical composition, all hard/soft constraints |
| 04 | `04-objectives.md` | MigrationObjective interface, lexicographic hierarchy, Value polarity, all objectives |
| 05 | `05-placement-precomputation.md` | NumaGroup.addNuma() combinatorial generation, calculateAllPlacements() |
| 06 | `06-adaptive-maintainer.md` | AdaptiveMaintainer: four operator dimensions, roulette wheel, weight update |
| 07 | `07-operator-types.md` | VmSorterType, HostSorterType, RecreateType — full enum source code |
| 08 | `08-ruin-phase.md` | getRuinHosts(), getRuinVms(), sortVmsByType() — guided ruin |
| 09 | `09-recreate-phase.md` | getBestRecreate(), getRandomRecreate(), getFirstFitRecreate(), recreate() dispatch |
| 10 | `10-acceptance-criterion.md` | Late Acceptance Hill Climbing (LAHC) — buffer, accept logic, configuration |
| 11 | `11-main-solve-loop.md` | AlnsMigrationSolver class, solve() complete source, stopping criteria, copy-on-write |
| 12 | `12-iteration-walkthrough.md` | One full ALNS iteration step-by-step with concrete values |

## Algorithm at a Glance

```
solve(problem):
  solution ← initial placements (all VMs at current hosts)
  allPlacements ← precompute all structural placements partitioned by NUMA count
  adaptiveMaintainer ← init all operator weights to 1.0
  LAHC ← init circular buffer of length 10

  while steps < 50000 AND stagnation < 500 AND time < 5s:
    operators ← adaptiveMaintainer.roll(random)           [File 06]
    ruinHosts ← select + sort hosts for ruin               [File 08]
    newSolution ← deep copy of solution                    [File 01]
    ruinVms ← guided per-VM ruin on newSolution            [File 08]
    if ruinVms == null: skip                               [File 08]
    success ← recreate(ruinVms, operators.recreateType)    [File 09]
    if !success: skip
    newValue ← evaluate objective                          [File 04]
    if newValue < bestValue: update best, reward operators [File 06]
    if LAHC.accept(value, newValue): adopt newSolution     [File 10]
    else: discard newSolution (no rollback needed)

  return bestSolution
```

## Key Invariants

1. **Lower values are always better.** `compareTo < 0` means the left operand is strictly better. `compareToZero() <= 0` means "non-worsening."

2. **Copy-on-write, not rollback.** Each iteration deep-copies the working solution before mutating it. Rejected candidates are simply discarded — the original is never touched.

3. **Ruin is guided, not blind.** VMs are removed one at a time with per-VM constraint checking and objective projection. The iteration is skipped entirely if no improving removal is found.

4. **Weights never decay.** The AdaptiveMaintainer monotonically increases weights; operators that succeed early permanently dominate.

5. **Stagnation tracks global best only.** The counter increments every iteration and resets only when a new global best is found — not on mere LAHC acceptance.
