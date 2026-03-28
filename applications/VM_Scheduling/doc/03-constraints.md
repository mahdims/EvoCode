# 03 — Constraints (Feasibility Logic)

Constraints are pure predicates that read from Variables. They contain no state and perform no computation of their own.

---

## MigrationConstraint Interface

```java
public interface MigrationConstraint {
    // Full check: is the entire solution feasible?
    boolean satisfy(Problem problem, MigrationSolution solution);

    // Incremental check after a ruin operation
    boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta);

    // Incremental check after a recreate operation (one VM placed)
    boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
```

The incremental overloads are projections — they evaluate the delta's effect **without** mutating the solution. This is how `getBestRecreate` evaluates hundreds of candidate placements cheaply.

---

## Hierarchical Constraint Composition

All active constraints compose into a single root via the Composite pattern. Checked in registration order; first failure short-circuits.

```java
MigrationConstraint rootConstraint = HierarchicalMigrationConstraint.builder()
    .constraint(new CpuMemMigrationConstraint(cpuMemFetcher))          // checked 1st
    .constraint(new IntraHostMigrationConstraint())                    // checked 2nd
    .constraint(new AntiAffinityMigrationConstraint(aaFetcher))        // checked 3rd
    .constraint(new BudgetLimitMigrationConstraint(costFetcher, 500))  // checked 4th
    .build();

problem.setMigrationConstraint(rootConstraint);
```

Order matters: put the most-frequently-violated constraints first (e.g., CPU capacity before budget) to maximize short-circuit savings.

---

## Hard Constraints

### CpuMemMigrationConstraint — NUMA-level capacity

```java
public class CpuMemMigrationConstraint implements MigrationConstraint {
    private final MigrationFetcher<CpuMemMigrationVariable> fetcher;

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        CpuMemMigrationVariable variable = fetcher.fetch(solution);  // O(1)
        for (Numa numa : problem.getAllNumas()) {
            if (variable.getNumaCpu(numa.getIndex()) > numa.getCpu()) return false;
            if (variable.getNumaMem(numa.getIndex()) > numa.getMem()) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem p, MigrationSolution sol, RecreateDelta delta) {
        CpuMemMigrationVariable variable = fetcher.fetch(sol);
        return checkHost(variable, delta.getPlacement().getHost());  // only target host
    }
}
```

### AntiAffinityMigrationConstraint

```java
// Ensures ∀ group g: no two VMs in g share the same host
MigrationFetcher<AntiAffinityMigrationVariable> aaFetcher =
    problem.addMigrationVariable(AntiAffinityMigrationVariable::new);
new AntiAffinityMigrationConstraint(aaFetcher);
```

### IntraHostMigrationConstraint — full source

Despite the name, this **forbids** intra-host placement: a migratable VM must move to a **different** host from its initial placement.

```java
public class IntraHostMigrationConstraint implements MigrationConstraint {

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // Accept if: initial placement (no migration), OR placed on a DIFFERENT host
        return delta.isInitial()
            || delta.getHost() != delta.getVm().getInitialPlacement().getHost();
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        for (Vm vm : problem.getVms()) {
            Placement placement = solution.getPlacement(vm);
            if (vm.getInitialPlacement() != placement
                    && vm.getInitialPlacement().getHost() == placement.getHost()) {
                return false;  // VM "moved" but stayed on same host
            }
        }
        return true;
    }
}
```

---

## Soft / Business Constraints

### BudgetLimitMigrationConstraint

```java
// Ensures Σ PMC(vm) ≤ budgetLimit for migrated VMs
new BudgetLimitMigrationConstraint(costFetcher, 1000);
```

### PreferFlavorProtectionConstraint

Reserves capacity on each host for large-flavor VMs. Prevents over-packing.

```java
new PreferFlavorProtectionConstraint(pfFetcher);
```

### TenantMigrationConstraint

Limits how many VMs a single tenant can have migrated simultaneously.

```java
new TenantMigrationConstraint(tenantFetcher);
```

### NumaResourceCuttingLineMigrationConstraint

Prevents NUMA nodes from being packed above a configurable threshold (e.g., 90%).

```java
new NumaResourceCuttingLineMigrationConstraint(cutFetcher);
```

---

## Where Constraints Are Checked in ALNS

1. **Ruin phase** (`getRuinVms`): `satisfy(problem, solution, ruinDelta)` — each VM removal is constraint-checked before applying.

2. **Recreate phase** (`getBestRecreate` / `getRandomRecreate` / `getFirstFitRecreate`): `satisfy(problem, solution, recreateDelta)` — each candidate placement is checked. Infeasible placements are skipped.

3. **HostSorterType.RUIN_EXPECTED**: `satisfy(problem, solution, ruinDelta)` — speculative ruin of each host is constraint-checked before scoring.

All three use the projection form (delta parameter) — no state is mutated during checking.
