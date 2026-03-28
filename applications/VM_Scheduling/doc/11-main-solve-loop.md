# 11 — Main Solve Loop (AlnsMigrationSolver)

The top-level class and its `solve()` method that orchestrates all components.

---

## Class Definition (Confirmed Source)

```java
@Accessors(fluent = true)
public class AlnsMigrationSolver implements MigrationSolver {
    private final MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher;
    private final SplittableRandom random;

    @Setter private AcceptanceCriteria acceptanceCriteria =
        new LateAcceptanceHillClimbingAcceptanceCriteria(10);
    @Setter private int numMaxRuinHost = 5;
    @Setter private int maxSteps = 50000;
    @Setter private int maxStagnationSteps = 500;
    @Setter private Duration timeLimit = Duration.ofSeconds(5);
    @Setter private boolean useChainOptimizer = true;

    private List<List<Placement>> allPlacements;

    public AlnsMigrationSolver(MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher,
                                SplittableRandom random) {
        this.hostVmsFetcher = hostVmsFetcher;
        this.random = random;
    }
}
```

### Configurable Defaults

| Field | Default | Purpose |
|---|---|---|
| `acceptanceCriteria` | LAHC(10) | Late Acceptance Hill Climbing, buffer length 10 |
| `numMaxRuinHost` | 5 | Upper bound of adaptive numRuinHost dimension |
| `maxSteps` | 50,000 | Maximum total iterations |
| `maxStagnationSteps` | 500 | Iterations without global best → terminate |
| `timeLimit` | 5 seconds | Wall-clock time budget |
| `useChainOptimizer` | true | Post-recreate chain optimization |

All fields use Lombok `@Setter` with fluent accessors for configuration.

---

## solve() — Complete Source (Confirmed)

```java
@Override
public MigrationSolution solve(Problem problem) {
    Instant endTime = Instant.now().plus(timeLimit);
    MigrationSolution solution = new MigrationSolution(problem);
    if (problem.getHosts().isEmpty() || problem.getVms().isEmpty()) {
        return solution;
    }
    allPlacements = MigrationSolver.calculateAllPlacements(problem);  // File 05
    AdaptiveMaintainer adaptiveMaintainer = new AdaptiveMaintainer(numMaxRuinHost);  // File 06
    int steps = 0;
    int stagnationSteps = 0;
    Value value = problem.getMigrationObjective().calculate(problem, solution);
    MigrationSolution bestSolution = new MigrationSolution(solution, false);
    Value bestValue = value;
    acceptanceCriteria.init(value);  // File 10
    OptimizationTrackData optimizationTrackData = new OptimizationTrackData();
    optimizationTrackData.addOptimizationTrackDataItem(Collections.emptyList(), value);

    while (steps < maxSteps && stagnationSteps < maxStagnationSteps
            && Instant.now().isBefore(endTime)) {
        ++steps;
        ++stagnationSteps;

        // ── STEP 1: SELECT OPERATORS ──────────────────────────── File 06
        int numRuinHost = adaptiveMaintainer.rollNumRuinHost(random);
        HostSorterType hostSorterType = adaptiveMaintainer.rollHostSorterType(random);
        VmSorterType vmSorterType = adaptiveMaintainer.rollVmSorterType(random);
        RecreateType recreateType = adaptiveMaintainer.rollRecreateType(random);

        // ── STEP 2: RUIN ─────────────────────────────────────── File 08
        List<Host> ruinHosts = getRuinHosts(problem, solution, numRuinHost, hostSorterType);
        MigrationSolution newSolution = new MigrationSolution(solution);  // DEEP COPY
        List<Vm> ruinVms = getRuinVms(problem, newSolution, ruinHosts, vmSorterType);

        // ── STEP 3: RECREATE ─────────────────────────────────── File 09
        List<RecreateDelta> recreateDeltas = new ArrayList<>();
        if (Objects.isNull(ruinVms)
            || !recreate(problem, newSolution, ruinVms, recreateDeltas,
                         vmSorterType, recreateType)) {
            continue;  // ruin found no improvement or recreate failed
        }

        // ── STEP 4: EVALUATE ─────────────────────────────────── File 04
        Value newValue = problem.getMigrationObjective().calculate(problem, newSolution);
        if (useChainOptimizer) {
            newValue = MigrationOptimizer.optimizeChain(problem, newSolution, newValue,
                hostVmsFetcher, ruinVms, recreateDeltas);
        }

        // ── STEP 5: GLOBAL BEST CHECK ────────────────────────── File 06
        if (newValue.compareTo(bestValue) < 0) {       // LOWER IS BETTER
            bestValue = newValue;
            bestSolution = new MigrationSolution(newSolution, false);  // shallow copy
            stagnationSteps = 0;                        // reset stagnation
            adaptiveMaintainer.updateWeights(ruinHosts.size(), vmSorterType,
                hostSorterType, recreateType, 1.0);     // reward operators
        }

        // ── STEP 6: ACCEPT / REJECT (LAHC) ──────────────────── File 10
        if (acceptanceCriteria.accept(value, newValue, random, stagnationSteps)) {
            value = newValue;
            solution = newSolution;  // adopt the candidate
            optimizationTrackData.addOptimizationTrackDataItem(recreateDeltas, value);
        } else {
            // newSolution is simply discarded — NO rollback needed
            optimizationTrackData.addOptimizationTrackDataItem(Collections.emptyList(), value);
        }
    }
    bestSolution.setOptimizationTrackData(optimizationTrackData);
    bestSolution.updateMigrationVariables(problem);  // full recompute before returning
    return bestSolution;
}
```

---

## Stopping Criteria

The loop terminates when **any** of three conditions is met:

| Condition | Default | Meaning |
|---|---|---|
| `steps ≥ maxSteps` | 50,000 | Maximum total iterations |
| `stagnationSteps ≥ maxStagnationSteps` | 500 | Iterations without global best improvement |
| `time ≥ endTime` | 5 seconds | Wall-clock limit |

Stagnation increments **every** iteration (`++stagnationSteps`) and resets to 0 **only** when a new global best is found — not on mere LAHC acceptance.

---

## Copy-on-Write Pattern

```
solution (working)  ──────────────────────────────────────────►
                         │
                    deep copy
                         │
                         ▼
                    newSolution ──► ruin ──► recreate ──► evaluate
                         │                                   │
                         │                          accepted?│
                         │                    ┌──────────────┤
                         │                    │ YES          │ NO
                         │                    ▼              ▼
                    solution = newSolution    discard (GC)
```

The original `solution` is **never** mutated. `new MigrationSolution(solution)` creates a full deep copy (including variable state). If rejected, the copy is simply garbage-collected.

For the global best, a **shallow** copy is used: `new MigrationSolution(newSolution, false)` copies only the placement array. Variables are fully recomputed once at the end via `bestSolution.updateMigrationVariables(problem)`.

---

## MigrationOptimizer.optimizeChain()

An undocumented post-processing step that performs targeted local optimization after recreate:

```java
if (useChainOptimizer) {
    newValue = MigrationOptimizer.optimizeChain(problem, newSolution, newValue,
        hostVmsFetcher, ruinVms, recreateDeltas);
}
```

Takes the ruined VMs and recreate deltas, attempts chain swaps for further improvement. May modify `newSolution` and return an updated `newValue`. Enabled by default.

---

## Weight Update Detail

```java
adaptiveMaintainer.updateWeights(
    ruinHosts.size(),  // NOTE: actual count, not rolled numRuinHost
    vmSorterType,
    hostSorterType,
    recreateType,
    1.0                // fixed reward
);
```

The first argument is `ruinHosts.size()` (the actual host count after HostSorterType processing), not the originally rolled `numRuinHost`. The adaptive mechanism rewards the actual outcome.

---

## Initialization Summary

```
1. MigrationSolution(problem)              → all VMs at initial placements
2. calculateAllPlacements(problem)          → pre-build all structural placements (File 05)
3. AdaptiveMaintainer(numMaxRuinHost=5)     → all weights init to 1.0 (File 06)
4. LAHC.init(startingObjectiveValue)        → fill buffer with starting value (File 10)
5. bestSolution = shallow copy              → initial state is the baseline
```
