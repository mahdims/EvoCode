# 04 — Objectives (Optimization Goals)

Objectives are pure readers — they read from Variables and return a `Value`. They contain no state.

---

## Value Polarity — CRITICAL

**Lower values are always better.** This is confirmed throughout the source:

- `compareTo(bestValue) < 0` → new global best
- `compareToZero() <= 0` → non-worsening placement (triggers early accept in `getBestRecreate`)
- LAHC `accept`: `newValue.compareTo(oldValue) <= 0` → better than current

`EmptyHostMigrationObjective` returns the **negated** empty count so that more empty hosts → lower value → better.

---

## MigrationObjective Interface

```java
public interface MigrationObjective<T extends Value> {
    // Full evaluation
    T calculate(Problem problem, MigrationSolution solution);

    // Projection: evaluate effect of ruin without mutating solution
    T calculate(Problem problem, MigrationSolution solution, RuinDelta delta);

    // Projection: evaluate effect of recreate without mutating solution
    T calculate(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
```

The delta overloads return a **marginal cost** (change from current state), not an absolute value.

---

## Lexicographic Hierarchy

Instead of a weighted sum, objectives are composed into a lexicographic hierarchy:

> *Maximize empty hosts first. Among ties, minimize load imbalance. Among ties there, minimize migration cost.*

```java
HierarchicalMigrationObjective objective = HierarchicalMigrationObjective.builder()
    .objective(new EmptyHostMigrationObjective(emptyHostFetcher))     // primary 1
    .objective(new MinLoadBalancingObjective(loadFetcher))            // primary 2
    .minorObjective(new MigrationCostMigrationObjective(costFetcher), /*lazy=*/true)
    .build();
```

The resulting `ListValue` is compared element by element, left to right. First difference wins.

```
Solution A: [-5, 0.12, 300]   (5 empty hosts, imbalance=0.12, cost=300)
Solution B: [-5, 0.09, 450]   (5 empty hosts, imbalance=0.09, cost=450)
→ B wins: at position 1, 0.09 < 0.12
```

**Lazy evaluation**: Minor objectives are only computed when primary objectives tie — saves computation in the inner loop.

---

## Catalogue of Migration Objectives

| Objective | Returns | What It Measures |
|-----------|---------|-----------------|
| `EmptyHostMigrationObjective` | `IntValue` | Negated count of hosts with zero VMs (lower = more empty = better) |
| `MinLoadBalancingObjective` | `ListValue` | Load variance across hosts |
| `PreferFlavorMigrationObjective` | `IntValue` | Negated remaining capacity for large-flavor VMs |
| `MigrationCostMigrationObjective` | `IntValue` | Total cost of all VM migrations |
| `TenantMigrationObjective` | `ListValue` | Tenant distribution spread metrics |
| `NumaResourceCuttingLineMigrationObjective` | `FloatValue` | NUMA usage above cutting line threshold |

### EmptyHostMigrationObjective — Primary Driver

```java
public class EmptyHostMigrationObjective implements MigrationObjective<IntValue> {
    private final MigrationFetcher<EmptyHostMigrationVariable> fetcher;

    @Override
    public IntValue calculate(Problem problem, MigrationSolution solution) {
        EmptyHostMigrationVariable variable = fetcher.fetch(solution);
        return IntValue.of(variable.getNumEmptyHost());  // pure read — O(1)
    }
}
```

---

## Where Objectives Are Evaluated in ALNS

1. **Initialization**: `value = problem.getMigrationObjective().calculate(problem, solution)` — full evaluation of starting state.

2. **Ruin phase** (`getRuinVms`): `calculate(problem, solution, ruinDelta).compareToZero()` — marginal cost of each VM removal. If `< 0`, the removal improves the objective → stop early.

3. **HostSorterType.RUIN_EXPECTED**: `calculate(problem, solution, ruinDelta)` — speculative objective evaluation of emptying each candidate host.

4. **Recreate phase** (`getBestRecreate`): `calculate(problem, solution, recreateDelta).compareToZero()` — marginal cost of each candidate placement. If `<= 0`, accept immediately.

5. **Main loop**: `problem.getMigrationObjective().calculate(problem, newSolution)` — full evaluation of the candidate solution after all placements are committed.

6. **Global best check**: `newValue.compareTo(bestValue) < 0` — strictly better than the best seen so far.
