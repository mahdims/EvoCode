# 09 — Recreate Phase

After ruin, displaced VMs must be placed back. The recreate phase iterates over ruined VMs (largest first) and finds a placement for each using the selected `RecreateType` strategy.

---

## Dispatch (in main loop)

```java
List<RecreateDelta> recreateDeltas = new ArrayList<>();
if (Objects.isNull(ruinVms)
    || !recreate(problem, newSolution, ruinVms, recreateDeltas,
                 vmSorterType, recreateType)) {
    continue;  // skip iteration if ruin returned null or recreate failed
}
```

The `recreate()` method sorts VMs via `sortVmsByType(solution, vms, vmSorterType, false)` — which reverses the ascending sort so **largest VMs are placed first** — then delegates to `recreateType.recreate(...)` (see File 07).

If any VM cannot be placed (all `RecreateType` variants return `false` when a null delta is produced), the entire iteration is skipped.

---

## getBestRecreate — Three-Phase Best Placement (Confirmed Source)

The most critical method in the framework. Called for `RecreateType.BEST`.

```java
static RecreateDelta getBestRecreate(Problem problem, MigrationSolution solution,
        Vm vm, List<Placement> placements) {
    List<Pair<RecreateDelta, Value>> deltaValuePairs = new LinkedList<>();

    // PHASE 1: Try initial placement first ("stay home" heuristic)
    RecreateDelta recreateDelta = new RecreateDelta(vm, vm.getInitialPlacement());
    if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
        Value newValue = problem.getMigrationObjective()
            .calculate(problem, solution, recreateDelta);
        if (newValue.compareToZero() <= 0) {
            return recreateDelta;  // non-worsening → accept immediately
        }
        deltaValuePairs.add(Pair.of(recreateDelta, newValue));
    }

    // PHASE 2: Scan all candidate placements with early exit
    for (Placement placement : placements) {
        if (placement == vm.getInitialPlacement()) {
            continue;  // already tried above
        }
        recreateDelta = new RecreateDelta(vm, placement);
        if (!problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
            continue;  // infeasible — skip
        }
        Value newValue = problem.getMigrationObjective()
            .calculate(problem, solution, recreateDelta);
        if (newValue.compareToZero() <= 0) {
            return recreateDelta;  // non-worsening → accept immediately
        }
        deltaValuePairs.add(Pair.of(recreateDelta, newValue));
    }

    // PHASE 3: Among all worsening-but-feasible placements, pick the least-bad
    RecreateDelta bestDelta = null;
    Value bestValue = null;
    for (Pair<RecreateDelta, Value> deltaValuePair : deltaValuePairs) {
        if (bestValue == null || deltaValuePair.right().compareTo(bestValue) < 0) {
            bestDelta = deltaValuePair.left();
            bestValue = deltaValuePair.right();
        }
    }
    return bestDelta;  // null if nothing feasible at all
}
```

### Key Insights

1. **Initial placement priority**: Tries `vm.getInitialPlacement()` first — "stay home if possible" minimizes unnecessary migrations. If the VM can go back without worsening, it does.

2. **`compareToZero() <= 0` early exit**: `calculate()` returns a **marginal cost** (change from current state). `≤ 0` means "doesn't worsen the objective." This short-circuits on the first good-enough placement, making `BEST` mode viable even with large candidate lists.

3. **Lower Value = better**: Phase 3 uses `compareTo(bestValue) < 0` to find the minimum marginal cost.

4. **Projection pattern**: Both `satisfy()` and `calculate()` are projections — they evaluate the delta's effect without mutating the solution. Only the winning delta calls `update()` later.

---

## getRandomRecreate (Confirmed Source)

```java
static RecreateDelta getRandomRecreate(Problem problem, MigrationSolution solution,
        Vm vm, List<Placement> placements, SplittableRandom random) {
    AlgorithmUtil.shuffleList(placements, random);
    for (Placement placement : placements) {
        RecreateDelta recreateDelta = new RecreateDelta(vm, placement);
        if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
            return recreateDelta;  // first feasible after shuffle
        }
    }
    return null;
}
```

Feasibility-only: no objective evaluation. Shuffle provides diversity.

---

## getFirstFitRecreate (Confirmed Source)

```java
static RecreateDelta getFirstFitRecreate(Problem problem, MigrationSolution solution,
        Vm vm, List<Placement> placements) {
    for (Placement placement : placements) {
        RecreateDelta recreateDelta = new RecreateDelta(vm, placement);
        if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
            return recreateDelta;  // first feasible in candidate order
        }
    }
    return null;
}
```

No shuffle, no objective evaluation. Uses the natural order of the pre-computed candidate list.

---

## Recreate Flow Summary

```
sortVmsByType(solution, ruinVms, vmSorterType, false)
  → vmSorterType.sort(ascending)
  → Collections.reverse() → LARGEST FIRST

for each vm in ruinVms (largest first):
  depending on recreateType:
    BEST:     getBestRecreate(problem, newSolution, vm, allPlacements.get(vm.getNumNumas()))
              → Phase 1: try initial placement (early exit if ≤ 0)
              → Phase 2: scan all candidates (early exit if ≤ 0)
              → Phase 3: pick least-bad among worsening placements
    RANDOM:   getRandomRecreate(...)  → shuffle + first feasible
    FirstFit: getFirstFitRecreate(...) → first feasible in order

  if delta == null → return false (recreate failed → skip iteration)
  delta.update(problem, newSolution)  → commit placement, update variables
  recreateDeltas.add(delta)

return true (all VMs placed successfully)
```

**Important sequencing**: Each VM's placement is committed (`delta.update()`) before the next VM is processed. Later VMs see the updated state from earlier placements — this is a **greedy sequential** recreate, not a simultaneous optimization.
