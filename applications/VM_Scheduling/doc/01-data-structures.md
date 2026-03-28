# 01 — Data Structures (Model Layer)

All classes the ALNS solver operates on. Pure data — no algorithmic logic.

---

## Physical Resource Hierarchy

```
Rack
 └── Host (physical server)
      └── NumaGroup (logical NUMA grouping)
           └── Numa (NUMA node: has CPU + Memory capacity)
                └── VM (virtual machine placed here)
```

---

## Rack

```java
public class Rack {
    private List<Host> hosts;

    public Host addHost() { ... }
    public List<Host> getHosts() { return hosts; }
}
```

---

## Host

```java
public class Host {
    private List<NumaGroup> numaGroups;
    private HostHealthyState healthyState;   // HEALTHY | UNHEALTHY | EVACUATION
    private String faultDomainId;
    private List<String> allowedTenantIds;
    private boolean migrationInRestricted;   // Cannot receive VMs
}
```

| State | Meaning |
|-------|---------|
| `HEALTHY` | Normal operation, can send and receive VMs |
| `UNHEALTHY` | Degraded but still running; VMs may be migrated away |
| `EVACUATION` | Must be fully drained; all VMs must leave |

---

## NumaGroup and Numa

```java
public class NumaGroup {
    private List<Numa> numas;
    private List<List<Placement>> placements;  // pre-built combinatorial placements

    public Numa addNuma() { ... }              // see File 05 for full source
    public List<Placement> getPlacements(int numNumas) {
        if (numNumas > placements.size()) return Collections.emptyList();
        return placements.get(numNumas - 1);   // O(1) lookup
    }
}

public class Numa {
    private float cpu;    // total CPU capacity (cores)
    private float mem;    // total memory capacity (GB)
    private NumaGroup numaGroup;  // parent — used by Placement.getHost()
}
```

NUMA matters because cross-socket memory access is significantly slower. VM placement must be NUMA-aware.

---

## Vm (Virtual Machine)

The entity being placed. Has per-NUMA resource demands.

```java
public class Vm {
    private int index;                        // array index for O(1) lookup
    private boolean migratable;               // can this VM be moved?
    private float numaCpu;                    // CPU demand per NUMA node
    private float numaMem;                    // Memory demand per NUMA node
    private Placement initialPlacement;       // M₀(p) — where it starts
    private int numNumas;                     // 1 for single-socket, 2+ for multi-socket
    private List<String> traits;              // e.g., ["windows", "gpu"]
    private String tenantId;                  // owning tenant
}
```

A single-NUMA VM needs 1 Numa node. A multi-NUMA VM (e.g., large memory) spans 2+ nodes and demands `numaCpu` and `numaMem` on **each** node it occupies.

---

## Placement

Fully specifies where a VM lives. Constructor takes only the NUMA array — host and numaGroup are derived from the Numa parent chain.

```java
public class Placement {
    private final Numa[] numas;       // 1 for single-NUMA, 2+ for multi-NUMA

    public Placement(Numa[] numas) { this.numas = numas; }

    public Host getHost()           { return numas[0].getNumaGroup().getHost(); }
    public NumaGroup getNumaGroup() { return numas[0].getNumaGroup(); }
    public Numa[] getNumas()        { return numas; }
}
```

**Placements are never manually constructed by the solver.** They are pre-built combinatorially by `NumaGroup.addNuma()` during problem construction (see File 05) and retrieved at O(1) via `allPlacements.get(vm.getNumNumas())`.

---

## Problem

Root container wiring all entities, variables, constraints, and objectives. The single object passed through the entire framework.

```java
public class Problem {
    private List<Rack> racks;
    private List<Host> hosts;                 // flat list of all hosts
    private List<Vm> vms;                     // flat list of all VMs
    private List<NumaGroup> numaGroups;       // flat list of all NumaGroups
    private MigrationConstraint migrationConstraint;
    private MigrationObjective migrationObjective;
    // Variable registry
    private List<Supplier<? extends MigrationVariable>> migrationVariableSuppliers;
}
```

Key methods:

```java
// Register a variable — returns a fetcher for O(1) retrieval
MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher =
    problem.addMigrationVariable(CpuMemMigrationVariable::new);

// Wire constraint/objective hierarchies
problem.setMigrationConstraint(rootConstraint);
problem.setMigrationObjective(rootObjective);
```

---

## MigrationSolution

The decision variable: a `Placement[]` array indexed by `vm.getIndex()`, plus the variable instances.

```java
public class MigrationSolution {
    private Placement[] placements;
    private MigrationVariable[] migrationVariables;

    // Constructor 1: Initialize from Problem — all VMs at initial placements
    public MigrationSolution(Problem problem) {
        migrationVariables = new MigrationVariable[problem.getMigrationVariableSuppliers().size()];
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = problem.getMigrationVariableSuppliers().get(i).get();
        }
        placements = new Placement[problem.getVms().size()];
        for (Vm vm : problem.getVms()) {
            placements[vm.getIndex()] = vm.getInitialPlacement();
        }
        updateMigrationVariables(problem);
    }

    // Constructor 2: Deep copy — for ALNS working candidates
    public MigrationSolution(MigrationSolution other) {
        this.placements = Arrays.copyOf(other.placements, other.placements.length);
        this.migrationVariables = new MigrationVariable[other.migrationVariables.length];
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = other.migrationVariables[i].copy();
        }
    }

    // Constructor 3: Shallow copy — for best-solution storage (skip variable deep-copy)
    public MigrationSolution(MigrationSolution other, boolean copyVariables) { ... }

    public Placement getPlacement(Vm vm) { return placements[vm.getIndex()]; }
    public void setPlacement(Vm vm, Placement p) { placements[vm.getIndex()] = p; }
    public void updateMigrationVariables(Problem problem) { /* full O(n) recompute */ }
}
```

### Copy Semantics in ALNS

| Constructor | When Used | What's Copied |
|---|---|---|
| `new MigrationSolution(solution)` | Start of each iteration (working copy) | Placements array + deep-copy every variable |
| `new MigrationSolution(newSolution, false)` | Saving global best | Placements array only (variables recomputed at end) |

The ALNS loop uses **copy-on-write**: the original solution is never mutated. If the iteration is rejected, the working copy is simply discarded.

---

## Value Types

Objectives return typed values. **Lower is always better** — `compareTo < 0` means the left is strictly better.

```java
IntValue.of(42)                                        // count-based
FloatValue.of(0.87f)                                   // ratio-based
ListValue.of(IntValue.of(-5), FloatValue.of(0.12f))   // lexicographic

// Lexicographic comparison: left-to-right, first difference wins
// ListValue [-5, 0.12] < ListValue [-3, 0.01]  →  -5 < -3, so left wins
```

`EmptyHostMigrationObjective` returns the **negated** empty count so more-empty = lower = better.

**`compareToZero()`**: Compares a value against the neutral point. Used in `getBestRecreate`: `newValue.compareToZero() <= 0` means "this placement doesn't worsen the objective" → accept immediately.
