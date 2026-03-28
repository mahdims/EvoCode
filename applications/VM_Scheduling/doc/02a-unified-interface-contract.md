# 02a — Unified Interface Contract

The entire system's extensibility rests on three interfaces that share a mirrored method signature pattern around **the same two delta types**. Every new rule added to the system is expressed as an implementation of one or more of these interfaces — no existing code is modified.

---

## The Three Interfaces

### MigrationVariable — State Aggregator

```java
public interface MigrationVariable {

    /** Full recompute from the entire solution — O(n). Called at initialization. */
    void update(Problem problem, MigrationSolution solution);

    /** Incremental update after VMs are removed — O(k). */
    void update(Problem problem, MigrationSolution solution, RuinDelta delta);

    /** Incremental update after one VM is placed — O(1). */
    void update(Problem problem, MigrationSolution solution, RecreateDelta delta);

    /** Deep copy of internal state — used for copy-on-write in ALNS loop. */
    MigrationVariable copy();
}
```

### MigrationConstraint — Feasibility Predicate

```java
public interface MigrationConstraint {

    /** Full feasibility check of the entire solution — O(n). */
    boolean satisfy(Problem problem, MigrationSolution solution);

    /** Projection: would this ruin violate feasibility? No state change. */
    boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta);

    /** Projection: would this placement violate feasibility? No state change. */
    boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
```

### MigrationObjective — Quality Measure

```java
public interface MigrationObjective<T extends Value> {

    /** Full evaluation of the entire solution — O(n) or O(1) if reading from Variable. */
    T calculate(Problem problem, MigrationSolution solution);

    /** Projection: what would the marginal cost of this ruin be? No state change. */
    T calculate(Problem problem, MigrationSolution solution, RuinDelta delta);

    /** Projection: what would the marginal cost of this placement be? No state change. */
    T calculate(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
```

---

## The Shared Pattern

All three interfaces have **exactly the same overload structure**:

| Method | Variable | Constraint | Objective |
|--------|----------|------------|-----------|
| Full solution | `update(problem, solution)` | `satisfy(problem, solution)` | `calculate(problem, solution)` |
| + RuinDelta | `update(problem, solution, ruinDelta)` | `satisfy(problem, solution, ruinDelta)` | `calculate(problem, solution, ruinDelta)` |
| + RecreateDelta | `update(problem, solution, recreateDelta)` | `satisfy(problem, solution, recreateDelta)` | `calculate(problem, solution, recreateDelta)` |
| Copy state | `copy()` | — | — |

The delta overloads on Constraint and Objective are **projections** — they evaluate the delta's effect without mutating the solution. The delta overloads on Variable are **mutations** — they apply the change to the variable's internal state.

This asymmetry is deliberate: Variable.update(delta) runs **once** to change the world state, and then any number of Constraint.satisfy(delta) and Objective.calculate(delta) can read from the updated Variable cheaply.

---

## The Two Delta Types

Both delta types carry the minimal information needed for incremental operations:

```java
class RuinDelta {
    private final Vm[] vms;                                      // VMs being removed
    public RuinDelta(Vm[] vms) { this.vms = vms; }
    public Vm[] getVms() { return vms; }
    public void update(Problem problem, MigrationSolution solution) { ... }  // self-applying
}

class RecreateDelta {
    private final Vm vm;                                         // VM being placed
    private final Placement placement;                           // target placement
    public RecreateDelta(Vm vm, Placement placement) { ... }
    public Vm getVm() { return vm; }
    public Placement getPlacement() { return placement; }        // target (new)
    // Old placement read from solution.getPlacement(vm) at apply time
    public void update(Problem problem, MigrationSolution solution) { ... }  // self-applying
}
```

Both deltas are **self-applying**: `delta.update(problem, solution)` commits the change AND triggers `variable.update(problem, solution, delta)` on every registered variable. This is the propagation mechanism — the delta fans out to all variables automatically.

---

## Wiring: How the Interfaces Connect Through Problem

`Problem` is the registry that wires everything together:

```java
public class Problem {
    // ── Variable Registry ──
    private List<Supplier<? extends MigrationVariable>> migrationVariableSuppliers;

    public <T extends MigrationVariable> MigrationFetcher<T> addMigrationVariable(
            Supplier<T> supplier) {
        migrationVariableSuppliers.add(supplier);
        return new MigrationFetcher<>(migrationVariableSuppliers.size() - 1);
    }

    // ── Constraint Tree ──
    private MigrationConstraint migrationConstraint;  // single root (composite)

    public void setMigrationConstraint(MigrationConstraint c) {
        this.migrationConstraint = c;
    }

    // ── Objective Tree ──
    private MigrationObjective migrationObjective;    // single root (composite)

    public void setMigrationObjective(MigrationObjective o) {
        this.migrationObjective = o;
    }
}
```

### Assembly Example — Full Wiring

```java
// 1. Register variables — get fetchers back
MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher =
    problem.addMigrationVariable(CpuMemMigrationVariable::new);
MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
    problem.addMigrationVariable(HostVmsMigrationVariable::new);
MigrationFetcher<EmptyHostMigrationVariable> emptyHostFetcher =
    problem.addMigrationVariable(EmptyHostMigrationVariable::new);
MigrationFetcher<AntiAffinityMigrationVariable> aaFetcher =
    problem.addMigrationVariable(AntiAffinityMigrationVariable::new);
MigrationFetcher<MigrationCostMigrationVariable> costFetcher =
    problem.addMigrationVariable(MigrationCostMigrationVariable::new);
MigrationFetcher<LoadVariable> loadFetcher =
    problem.addMigrationVariable(LoadVariable::new);

// 2. Build constraint tree — each constraint holds a fetcher to its variable
problem.setMigrationConstraint(
    HierarchicalMigrationConstraint.builder()
        .constraint(new CpuMemMigrationConstraint(cpuMemFetcher))
        .constraint(new IntraHostMigrationConstraint())
        .constraint(new AntiAffinityMigrationConstraint(aaFetcher))
        .constraint(new BudgetLimitMigrationConstraint(costFetcher, 1000))
        .build()
);

// 3. Build objective tree — each objective holds a fetcher to its variable
problem.setMigrationObjective(
    HierarchicalMigrationObjective.builder()
        .objective(new EmptyHostMigrationObjective(emptyHostFetcher))
        .objective(new MinLoadBalancingObjective(loadFetcher))
        .minorObjective(new MigrationCostMigrationObjective(costFetcher), true)
        .build()
);

// 4. Create solver — needs hostVmsFetcher for ruin phase
AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom());
MigrationSolution result = solver.solve(problem);
```

The resulting object graph:

```
Problem
 ├── migrationVariableSuppliers: [CpuMem::new, HostVms::new, EmptyHost::new, AA::new, Cost::new, Load::new]
 │                                  slot 0        slot 1       slot 2       slot 3    slot 4     slot 5
 │
 ├── migrationConstraint (HierarchicalMigrationConstraint)
 │    ├── CpuMemMigrationConstraint ──── fetcher(index=0) ──► reads CpuMemVariable
 │    ├── IntraHostMigrationConstraint   (stateless, no fetcher)
 │    ├── AntiAffinityConstraint ──────── fetcher(index=3) ──► reads AAVariable
 │    └── BudgetLimitConstraint ─────── fetcher(index=4) ──► reads CostVariable
 │
 └── migrationObjective (HierarchicalMigrationObjective)
      ├── EmptyHostObjective ──────────── fetcher(index=2) ──► reads EmptyHostVariable
      ├── MinLoadBalancingObjective ──── fetcher(index=5) ──► reads LoadVariable
      └── MigrationCostObjective ──────── fetcher(index=4) ──► reads CostVariable (SHARED)
```

Note: `CostVariable` at slot 4 is read by **both** `BudgetLimitConstraint` and `MigrationCostObjective`. Computation happens once; both consumers read the same updated state.

---

## How the ALNS Loop Calls Each Interface

Here is every call site in one iteration, showing which interface method is invoked and why:

### Phase: Initialization (once)

```java
MigrationSolution solution = new MigrationSolution(problem);
// → for each supplier: variable = supplier.get()
// → for each variable: variable.update(problem, solution)     ← Variable.update(full)
// → all variables now reflect the initial placement state

Value value = problem.getMigrationObjective()
    .calculate(problem, solution);                              ← Objective.calculate(full)
```

### Phase: Copy-on-Write

```java
MigrationSolution newSolution = new MigrationSolution(solution);
// → placements = Arrays.copyOf(...)
// → for each variable: newVariable = variable.copy()           ← Variable.copy()
```

### Phase: Guided Ruin (for each VM on each ruin host)

```java
RuinDelta ruinDelta = new RuinDelta(new Vm[] {vm});

// 1. Constraint projection — can we remove this VM?
problem.getMigrationConstraint()
    .satisfy(problem, newSolution, ruinDelta);                  ← Constraint.satisfy(RuinDelta)

// 2. Objective projection — does removing this VM improve things?
problem.getMigrationObjective()
    .calculate(problem, newSolution, ruinDelta)
    .compareToZero();                                           ← Objective.calculate(RuinDelta)

// 3. Apply — commit the ruin (updates all variables via fan-out)
ruinDelta.update(problem, newSolution);
// internally calls for each registered variable:
//   variable.update(problem, newSolution, ruinDelta)           ← Variable.update(RuinDelta)
```

### Phase: Recreate (for each candidate placement of each VM)

```java
RecreateDelta recreateDelta = new RecreateDelta(vm, candidatePlacement);

// 1. Constraint projection — is this placement feasible?
problem.getMigrationConstraint()
    .satisfy(problem, newSolution, recreateDelta);              ← Constraint.satisfy(RecreateDelta)

// 2. Objective projection — what's the marginal cost?
problem.getMigrationObjective()
    .calculate(problem, newSolution, recreateDelta)
    .compareToZero();                                           ← Objective.calculate(RecreateDelta)

// 3. Apply (only the winning delta) — commit the placement
bestDelta.update(problem, newSolution);
// internally calls for each registered variable:
//   variable.update(problem, newSolution, recreateDelta)       ← Variable.update(RecreateDelta)
```

### Phase: Full Evaluation (once per iteration, after all placements committed)

```java
Value newValue = problem.getMigrationObjective()
    .calculate(problem, newSolution);                           ← Objective.calculate(full)
```

### Phase: Final Recompute (once, before returning best solution)

```java
bestSolution.updateMigrationVariables(problem);
// → for each variable: variable.update(problem, bestSolution)  ← Variable.update(full)
```

---

## Data Flow Diagram — One Ruin + One Recreate

```
                           RuinDelta(vm)
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
          Constraint      Objective       [if passed]
          .satisfy()      .calculate()    delta.update()
          (projection)    (projection)         │
               │               │         ┌─────┼─────┐──── ... ─────┐
               │               │         ▼     ▼     ▼              ▼
               │               │     Variable Variable Variable  Variable
               │               │     .update() .update() .update() .update()
               │               │     (mutate)  (mutate)  (mutate)  (mutate)
               ▼               ▼
          true/false     Value (marginal)


                        RecreateDelta(vm, placement)
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
          Constraint      Objective       [if winner]
          .satisfy()      .calculate()    delta.update()
          (projection)    (projection)         │
               │               │         ┌─────┼─────┐──── ... ─────┐
               │               │         ▼     ▼     ▼              ▼
               │               │     Variable Variable Variable  Variable
               │               │     .update() .update() .update() .update()
               ▼               ▼
          true/false     Value (marginal)


  Constraint and Objective READ from Variable state.
  They never write. The update fan-out happens only through delta.update().
```

---

## Adding a New Rule — The Extension Pattern

To add a new business rule (e.g., "no host may have more than 50 VMs"):

```java
// 1. Does it need new state? → Implement MigrationVariable
//    (In this case, HostVmsMigrationVariable already tracks VM counts — reuse it.)

// 2. Is it a feasibility rule? → Implement MigrationConstraint
public class MaxVmsPerHostConstraint implements MigrationConstraint {
    private final MigrationFetcher<HostVmsMigrationVariable> fetcher;
    private final int maxVms;

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        HostVmsMigrationVariable var = fetcher.fetch(solution);
        for (Host host : problem.getHosts()) {
            if (var.getNumVms(host.getIndex()) > maxVms) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem p, MigrationSolution sol, RuinDelta delta) {
        return true;  // removing VMs can't violate a max
    }

    @Override
    public boolean satisfy(Problem p, MigrationSolution sol, RecreateDelta delta) {
        HostVmsMigrationVariable var = fetcher.fetch(sol);
        return var.getNumVms(delta.getPlacement().getHost().getIndex()) <= maxVms;
    }
}

// 3. Wire it in — one line added to the constraint builder
problem.setMigrationConstraint(
    HierarchicalMigrationConstraint.builder()
        .constraint(new CpuMemMigrationConstraint(cpuMemFetcher))
        .constraint(new IntraHostMigrationConstraint())
        .constraint(new AntiAffinityMigrationConstraint(aaFetcher))
        .constraint(new MaxVmsPerHostConstraint(hostVmsFetcher, 50))  // ← NEW
        .build()
);
```

**Zero changes** to MigrationSolution, AlnsMigrationSolver, any existing Variable, any existing Constraint, or any existing Objective. The Composite pattern absorbs it. The Fetcher reads from the same shared Variable.

If the new rule needs **new state** not captured by any existing Variable, then also implement a new `MigrationVariable`, register it via `problem.addMigrationVariable(...)`, and pass the fetcher to the new Constraint or Objective.

---

## Hierarchical Composition (Composite Pattern)

Both constraints and objectives compose into a single root that the algorithm interacts with. The algorithm never knows how many individual constraints or objectives exist.

```java
// Constraint composition — short-circuits on first failure
HierarchicalMigrationConstraint.builder()
    .constraint(constraintA)  // checked 1st
    .constraint(constraintB)  // checked 2nd (skipped if A fails)
    .constraint(constraintC)  // checked 3rd (skipped if A or B fails)
    .build();
// satisfy() returns false on first failure — AND semantics

// Objective composition — lexicographic comparison
HierarchicalMigrationObjective.builder()
    .objective(objectiveA)                        // primary — compared first
    .objective(objectiveB)                        // secondary — compared on tie
    .minorObjective(objectiveC, /*lazy=*/true)    // minor — computed only on tie
    .build();
// calculate() returns ListValue [A, B, C] — compared left-to-right
```

The `lazy=true` flag is a practical optimization: minor objectives are expensive to compute and only matter when primary objectives tie (which is rare). They are skipped entirely unless needed.
