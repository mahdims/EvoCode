# 08 — Ruin Phase

The ruin phase selects hosts and removes VMs from them. This is **not** blind destruction — it is a guided, per-VM, constraint-checked process that aborts the entire iteration if no improving removal is found.

---

## Step 1: getRuinHosts — Host Selection (Confirmed Source)

Builds the candidate host list, shuffles it, then delegates to the `HostSorterType` (see File 07) for sorting/truncation.

```java
private List<Host> getRuinHosts(Problem problem, MigrationSolution solution,
        int numRuinHost, HostSorterType hostSorterType) {
    List<Host> ruinHosts = new ObjectArrayList<>(problem.getHosts().size());
    AssignmentList<Vm> migratableHostVms =
        hostVmsFetcher.fetch(solution).getMigratableHostVms();
    for (Host host : problem.getHosts()) {
        if (!migratableHostVms.get(host.getIndex()).isEmpty()) {
            ruinHosts.add(host);
        }
    }
    AlgorithmUtil.shuffleList(ruinHosts, random);
    hostSorterType.sort(problem, solution, ruinHosts, numRuinHost, random, hostVmsFetcher);
    return ruinHosts;
}
```

**What happens:**
1. Collect all hosts that have at least one migratable VM.
2. Shuffle for randomness (ensures the initial ordering is unbiased).
3. Apply `hostSorterType.sort()` which truncates/reorders to `numRuinHost` entries based on the strategy:
   - `RANDOM`: truncate the shuffled list to `numRuinHost`.
   - `RUIN_EXPECTED`: speculatively ruin each host (projection), keep the `numRuinHost` with best objective.
   - `RUIN_EXPECTED_RANDOM`: score all hosts, then select with rank-based weighted random (1/(rank+1)).

---

## Step 2: getRuinVms — Guided, Improvement-Gated Ruin (Confirmed Source)

This is the most significant departure from standard ALNS literature. VMs are removed one at a time with per-VM checks.

```java
private List<Vm> getRuinVms(Problem problem, MigrationSolution solution,
        List<Host> ruinHosts, VmSorterType vmSorterType) {
    HostVmsMigrationVariable variable = hostVmsFetcher.fetch(solution);
    List<Vm> ruinVms = new ObjectArrayList<>();
    boolean improved = false;
    for (Host host : ruinHosts) {
        List<Vm> vms = new ObjectArrayList<>(
            variable.getMigratableHostVms().get(host.getIndex()));
        sortVmsByType(solution, vms, vmSorterType, true);  // isRuin=true
        for (Vm vm : vms) {
            RuinDelta ruinDelta = new RuinDelta(new Vm[] {vm});
            if (!problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                continue;  // skip VMs whose removal would violate constraints
            }
            ruinVms.add(vm);
            int compareToZero =
                problem.getMigrationObjective()
                    .calculate(problem, solution, ruinDelta).compareToZero();
            ruinDelta.update(problem, solution);  // apply AFTER projection
            if (compareToZero < 0) {
                improved = true;
                break;  // found an improving removal — stop this host's VMs
            }
        }
    }
    return improved ? ruinVms : null;  // null = skip entire ALNS iteration
}
```

### Key Behaviors

1. **One-at-a-time ruin**: Each VM is a separate `RuinDelta(new Vm[] {vm})`. Not batch removal.

2. **Constraint-checked**: `satisfy(problem, solution, ruinDelta)` is a projection — if removal would violate a constraint, the VM is skipped.

3. **Objective-evaluated**: `calculate(problem, solution, ruinDelta).compareToZero()` computes the marginal cost of removing the VM. `< 0` means the removal improves the objective.

4. **Applied after projection**: `ruinDelta.update(problem, solution)` is called **after** both the constraint check and objective evaluation pass. The order is: project → evaluate → apply.

5. **Early exit on improvement**: Once a removal improves the objective, `break` stops processing VMs on that host. The loop moves to the next host.

6. **Improvement gate**: If **no** removal across **any** host produces an improvement, the method returns `null` and the **entire ALNS iteration is skipped** (`continue` in the main loop).

7. **Already-moved VMs first**: `sortVmsByType(..., true)` pre-sorts so VMs that have already been displaced (current ≠ initial placement) are processed first (see below).

---

## sortVmsByType — Context-Aware VM Sorting (Confirmed Source)

```java
private void sortVmsByType(MigrationSolution solution, List<Vm> vms,
        VmSorterType vmSorterType, boolean isRuin) {
    if (isRuin && vmSorterType != VmSorterType.RANDOM) {
        // During ruin: already-moved VMs first (false < true in Java boolean comparison)
        vms.sort(Comparator.comparing(
            vm -> vm.getInitialPlacement() == solution.getPlacement(vm)));
    }
    vmSorterType.sort(vms, random);
    if (!isRuin) {
        Collections.reverse(vms);  // During recreate: reverse ascending → largest first
    }
}
```

### Ruin (isRuin=true)

1. **Pre-sort**: VMs where `initialPlacement != currentPlacement` (already moved) sort first (`false < true`). This prioritizes re-ruining VMs that were previously moved, giving the algorithm another chance to find better placements.
2. **Apply VmSorterType**: Sort ascending by the selected criterion.
3. **No reversal**: VMs are iterated in ascending order during ruin.

### Recreate (isRuin=false)

1. **No pre-sort**: The moved-VM pre-sort is skipped.
2. **Apply VmSorterType**: Sort ascending.
3. **Reverse**: `Collections.reverse(vms)` makes it **largest first** — the standard bin-packing heuristic: place the hardest-to-fit items while the most options remain.

---

## Flow Summary

```
getRuinHosts(problem, solution, numRuinHost, hostSorterType)
  → collect hosts with migratable VMs
  → shuffle
  → hostSorterType.sort() → truncate/reorder to numRuinHost

newSolution = new MigrationSolution(solution)  // deep copy [in main loop]

getRuinVms(problem, newSolution, ruinHosts, vmSorterType)
  for each host in ruinHosts:
    get migratable VMs → sort (moved-first, then vmSorterType ascending)
    for each VM:
      constraint-check RuinDelta (projection)
      if fails → skip
      evaluate objective (projection)
      apply RuinDelta → update variables
      if improved → break (stop this host)

  if no improvement found across all hosts → return null → SKIP ITERATION
  else → return list of ruined VMs
```
