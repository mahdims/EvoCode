# 02 — Incremental Evaluation (Variable Layer + Delta Objects)

The Variable layer is the core performance mechanism. Without it, every constraint check scans all VMs — O(n). With it, each check is O(1).

---

## MigrationVariable Interface

```java
public interface MigrationVariable {
    // Full recomputation from scratch — O(n), used at initialization
    void update(Problem problem, MigrationSolution solution);

    // Incremental: undo contribution of VMs removed in ruin — O(k)
    void update(Problem problem, MigrationSolution solution, RuinDelta delta);

    // Incremental: add contribution of VM placed in recreate — O(1)
    void update(Problem problem, MigrationSolution solution, RecreateDelta delta);

    // Deep copy — used when creating working copies
    MigrationVariable copy();
}
```

Variables are **precomputed, incrementally-maintained aggregate statistics** derived from the placement array. They are **not** decision variables.

---

## Delta Objects

Deltas carry just enough information for incremental updates. Both types are **self-applying**: `delta.update(problem, solution)` commits the change and triggers variable updates.

### RuinDelta

```java
class RuinDelta {
    private final Vm[] vms;   // single-element array in ALNS inner loop

    public RuinDelta(Vm[] vms) { this.vms = vms; }
    public Vm[] getVms() { return vms; }

    // Self-applying: commits ruin and updates all variables
    public void update(Problem problem, MigrationSolution solution) { ... }
}
```

In the ALNS guided ruin, VMs are ruined one at a time: `new RuinDelta(new Vm[] {vm})`.

### RecreateDelta

```java
class RecreateDelta {
    private final Vm vm;
    private final Placement placement;  // target placement

    public RecreateDelta(Vm vm, Placement placement) {
        this.vm = vm;
        this.placement = placement;
    }

    public Vm getVm() { return vm; }
    public Placement getPlacement() { return placement; }

    // Self-applying: commits placement and updates all variables
    public void update(Problem problem, MigrationSolution solution) { ... }
}
```

The old placement is implicit — read from `solution.getPlacement(vm)` at update time.

### Projection vs. Application

This distinction is critical:

- **Projection** (no state change): `constraint.satisfy(problem, solution, delta)` and `objective.calculate(problem, solution, delta)` evaluate the delta's effect without mutating the solution. Used to evaluate hundreds of candidates cheaply.
- **Application** (commits change): `delta.update(problem, solution)` modifies the solution and updates all variables. Called only on the winning candidate.

---

## Fetcher Pattern

Variables are registered at problem-build time and retrieved at O(1) via array index.

```java
// MigrationFetcher — typed wrapper around an array slot index
@RequiredArgsConstructor(access = AccessLevel.PACKAGE)
public class MigrationFetcher<T extends MigrationVariable> {
    private final int index;

    public T fetch(MigrationSolution solution) {
        return (T) solution.getMigrationVariables()[index];  // O(1)
    }
}

// Registration at problem-build time
public <T extends MigrationVariable> MigrationFetcher<T> addMigrationVariable(
        Supplier<T> supplier) {
    migrationVariableSuppliers.add(supplier);
    return new MigrationFetcher<>(migrationVariableSuppliers.size() - 1);
}
```

Multiple consumers (constraints and objectives) sharing the same variable use the same fetcher → same array slot → computation happens once per delta.

---

## CpuMemMigrationVariable — Full Example

The most frequently accessed variable. Tracks per-NUMA CPU and memory usage.

```java
public class CpuMemMigrationVariable implements MigrationVariable {
    private float[][] numaCpu;  // [hostIndex][numaIndex] = used CPU
    private float[][] numaMem;  // [hostIndex][numaIndex] = used Memory

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        // Full recompute: iterate all VMs — O(n)
        Arrays.fill(numaCpu, 0);
        Arrays.fill(numaMem, 0);
        for (Vm vm : problem.getVms()) {
            Placement p = solution.getPlacement(vm);
            for (int i = 0; i < p.getNumas().size(); i++) {
                Numa numa = p.getNumas().get(i);
                numaCpu[p.getHost().getIndex()][numa.getIndex()] += vm.getNumaCpu();
                numaMem[p.getHost().getIndex()][numa.getIndex()] += vm.getNumaMem();
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // Incremental — O(1): only update affected NUMA nodes
        Vm vm = delta.getVm();
        Placement newP = delta.getPlacement();                 // target
        Placement oldP = solution.getPlacement(delta.getVm()); // current (pre-move)

        for (Numa numa : oldP.getNumas()) {
            numaCpu[oldP.getHost().getIndex()][numa.getIndex()] -= vm.getNumaCpu();
            numaMem[oldP.getHost().getIndex()][numa.getIndex()] -= vm.getNumaMem();
        }
        for (Numa numa : newP.getNumas()) {
            numaCpu[newP.getHost().getIndex()][numa.getIndex()] += vm.getNumaCpu();
            numaMem[newP.getHost().getIndex()][numa.getIndex()] += vm.getNumaMem();
        }
    }

    public float getNumaCpu(int numaIndex) { return numaCpu[numaIndex]; }
    public float getNumaMem(int numaIndex) { return numaMem[numaIndex]; }
}
```

---

## Catalogue of Migration Variables

| Variable | Internal State | What It Tracks |
|----------|---------------|----------------|
| `CpuMemMigrationVariable` | `float[][] numaCpu, numaMem` | CPU and memory used per NUMA node per host |
| `HostVmsMigrationVariable` | `AssignmentList<Vm> hostVms` | VMs currently on each host (+ migratable subset) |
| `EmptyHostMigrationVariable` | `int numEmptyHost` | Count of fully empty hosts |
| `LoadVariable` | `float[] hostLoads` | Load metric per host |
| `AntiAffinityMigrationVariable` | `Map<String, Set<Host>>` | Which hosts each anti-affinity group spans |
| `MigrationCostMigrationVariable` | `int totalCost` | Cumulative migration cost |
| `TenantMigrationVariable` | `Map<String, List<Vm>>` | VMs per tenant per host |
| `PreferFlavorMigrationVariable` | Capacity arrays | Remaining capacity for large-flavor VMs |
| `NumaResourceCuttingLineMigrationVariable` | Utilization per NUMA | NUMA usage relative to cutting line |

`HostVmsMigrationVariable` is especially important: it provides `.getMigratableHostVms()` which the ruin phase uses to find candidate VMs on each host.

---

## Custom Variable Template

```java
public class CustomMigrationVariable implements MigrationVariable {
    private int customMetric;

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        this.customMetric = computeFromScratch(problem, solution);
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (Vm vm : delta.getVms()) {
            this.customMetric -= contributionOf(vm, solution.getPlacement(vm));
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        this.customMetric += contributionOf(delta.getVm(), delta.getPlacement());
    }

    @Override
    public MigrationVariable copy() {
        CustomMigrationVariable copy = new CustomMigrationVariable();
        copy.customMetric = this.customMetric;
        return copy;
    }
}

// Registration
MigrationFetcher<CustomMigrationVariable> fetcher =
    problem.addMigrationVariable(CustomMigrationVariable::new);
```
