# Server Consolidation V2 — Comprehensive Technical Guide

> **Audience:** Research Scientists and Engineers working on cloud resource optimization, combinatorial optimization, and large-scale scheduling systems.

---

## Table of Contents

1. [The Problem — What We Are Solving](#1-the-problem--what-we-are-solving)
   - 1.1 [Context: Cloud Defragmentation](#11-context-cloud-defragmentation)
   - 1.2 [The ROADEF 2012 Reference Problem](#12-the-roadef-2012-reference-problem)
   - 1.3 [Decision Variable and Search Space](#13-decision-variable-and-search-space)
   - 1.4 [Hard Constraints (ROADEF)](#14-hard-constraints-roadef)
   - 1.5 [Objective Functions (ROADEF)](#15-objective-functions-roadef)
   - 1.6 [How Huawei's Problem Extends ROADEF](#16-how-huaweis-problem-extends-roadef)
2. [Architecture Overview](#2-architecture-overview)
   - 2.1 [Layered Design Philosophy](#21-layered-design-philosophy)
   - 2.2 [Module Structure](#22-module-structure)
   - 2.3 [End-to-End Data Flow](#23-end-to-end-data-flow)
3. [Model Layer — Data Structures](#3-model-layer--data-structures)
   - 3.1 [Physical Resource Hierarchy](#31-physical-resource-hierarchy)
   - 3.2 [Rack](#32-rack)
   - 3.3 [Host](#33-host)
   - 3.4 [NumaGroup and Numa](#34-numagroup-and-numa)
   - 3.5 [VM (Virtual Machine)](#35-vm-virtual-machine)
   - 3.6 [Placement](#36-placement)
   - 3.7 [Problem](#37-problem)
   - 3.8 [MigrationSolution and Solution](#38-migrationsolution-and-solution)
   - 3.9 [Value Types](#39-value-types)
4. [Variable Layer — State Aggregators](#4-variable-layer--state-aggregators)
   - 4.1 [What Variables Are (and Are Not)](#41-what-variables-are-and-are-not)
   - 4.2 [The MigrationVariable Interface](#42-the-migrationvariable-interface)
   - 4.3 [Incremental Updates — The Core Performance Design](#43-incremental-updates--the-core-performance-design)
   - 4.4 [The Fetcher Pattern](#44-the-fetcher-pattern)
   - 4.5 [Catalogue of Migration Variables](#45-catalogue-of-migration-variables)
   - 4.6 [Catalogue of Batching Variables](#46-catalogue-of-batching-variables)
   - 4.7 [Implementing a Custom Variable](#47-implementing-a-custom-variable)
5. [Constraint Layer — Feasibility Logic](#5-constraint-layer--feasibility-logic)
   - 5.1 [The MigrationConstraint Interface](#51-the-migrationconstraint-interface)
   - 5.2 [Hierarchical Constraint Composition](#52-hierarchical-constraint-composition)
   - 5.3 [Decoupling Constraints from Variables](#53-decoupling-constraints-from-variables)
   - 5.4 [Hard Constraints](#54-hard-constraints)
   - 5.5 [Soft / Business Constraints](#55-soft--business-constraints)
   - 5.6 [Batching Constraints](#56-batching-constraints)
   - 5.7 [Implementing a Custom Constraint](#57-implementing-a-custom-constraint)
6. [Objective Layer — Optimization Goals](#6-objective-layer--optimization-goals)
   - 6.1 [The MigrationObjective Interface](#61-the-migrationobjective-interface)
   - 6.2 [Lexicographic Hierarchy vs. Weighted Sum](#62-lexicographic-hierarchy-vs-weighted-sum)
   - 6.3 [HierarchicalMigrationObjective](#63-hierarchicalmigrationobjective)
   - 6.4 [Catalogue of Migration Objectives](#64-catalogue-of-migration-objectives)
   - 6.5 [Catalogue of Batching Objectives](#65-catalogue-of-batching-objectives)
   - 6.6 [Lazy Evaluation of Secondary Objectives](#66-lazy-evaluation-of-secondary-objectives)
   - 6.7 [Implementing a Custom Objective](#67-implementing-a-custom-objective)
7. [Algorithm Layer — Optimization Engines](#7-algorithm-layer--optimization-engines)
   - 7.1 [Two-Stage Decomposition](#71-two-stage-decomposition)
   - 7.2 [The Solver Interface Hierarchy](#72-the-solver-interface-hierarchy)
   - 7.3 [ALNS Migration Solver](#73-alns-migration-solver)
     - 7.3a [The Adaptive Mechanism — AdaptiveMaintainer](#73a-the-adaptive-mechanism--adaptivemaintainer)
     - 7.3b [Acceptance Criterion — Late Acceptance Hill Climbing (LAHC)](#73b-acceptance-criterion--late-acceptance-hill-climbing-lahc)
     - 7.3c [Full ALNS Iteration Structure](#73c-full-alns-iteration-structure)
   - 7.4 [Greedy Migration Solver](#74-greedy-migration-solver)
   - 7.5 [Robust Knapsack Solvers (mitigation/algorithm/robust/)](#75-robust-knapsack-solvers-mitigationalgorithmrobust)
   - 7.6 [Sequence Batching Solver](#76-sequence-batching-solver)
   - 7.7 [SCC Batching Solver](#77-scc-batching-solver)
   - 7.8 [Genetic Batching Solver](#78-genetic-batching-solver)
   - 7.9 [Greedy Batching Solver](#79-greedy-batching-solver)
   - 7.10 [One Full ALNS Iteration — Step-by-Step](#710-one-full-alns-iteration--step-by-step)
8. [Hotspot Mitigation Module](#8-hotspot-mitigation-module)
   - 8.1 [Architecture: A Framework Within a Framework](#81-architecture-a-framework-within-a-framework)
   - 8.2 [Two Hotspot Types and Their Solver Paths](#82-two-hotspot-types-and-their-solver-paths)
   - 8.3 [Model Layer — HotspotProblem, MitigationLevel, SolverConfig](#83-model-layer--hotspotproblem-mitigationlevel-solverconfig)
   - 8.4 [Variable Layer — Target-Focused State Tracking](#84-variable-layer--target-focused-state-tracking)
   - 8.5 [Constraint Layer — Migration Safety on Targets](#85-constraint-layer--migration-safety-on-targets)
   - 8.6 [Objective Layer — Five Mitigation-Specific Objectives](#86-objective-layer--five-mitigation-specific-objectives)
   - 8.7 [Algorithm Layer — Two-Stage Hotspot Mitigation](#87-algorithm-layer--two-stage-hotspot-mitigation)
   - 8.8 [API Layer and Factory](#88-api-layer-and-factory)
   - 8.9 [Full Mitigation Flow](#89-full-mitigation-flow)
9. [Design Patterns and Engineering Principles](#9-design-patterns-and-engineering-principles)
   - 9.1 [Composite / Hierarchical Pattern](#91-composite--hierarchical-pattern)
   - 9.2 [Strategy Pattern](#92-strategy-pattern)
   - 9.3 [Observer / Delta Pattern](#93-observer--delta-pattern)
   - 9.4 [Factory / Registry Pattern](#94-factory--registry-pattern)
   - 9.5 [Template Method Pattern](#95-template-method-pattern)
10. [ROADEF 2012 vs. Server Consolidation V2 — Full Mapping](#10-roadef-2012-vs-server-consolidation-v2--full-mapping)
11. [Supporting Modules](#11-supporting-modules)
12. [Frequently Asked Questions (FAQ)](#12-frequently-asked-questions-faq)

---

## 1. The Problem — What We Are Solving

### 1.1 Context: Cloud Defragmentation

In a large-scale cloud data center, thousands of Virtual Machines (VMs) run concurrently on physical servers (hosts). Over time, VMs are created and deleted in unpredictable patterns, leaving the infrastructure in a **fragmented** state: many hosts are partially utilized, no host is fully empty, power is consumed without corresponding service output, and new large VMs cannot be placed because no single host has enough contiguous free capacity.

**Server Consolidation** (also called defragmentation) is the process of **migrating VMs from lightly-loaded hosts onto more densely-packed hosts**, aiming to:

- Empty as many physical hosts as possible (so they can be powered down or reserved)
- Maximize overall CPU and memory utilization
- Achieve balanced load distribution across active hosts
- Mitigate hotspots where individual hosts are overloaded
- Satisfy complex operational constraints (affinity, tenancy, topology, migration costs)

This is an **NP-hard combinatorial optimization problem**. The search space — all possible assignments of VMs to hosts — grows exponentially with the number of entities. Real Huawei Cloud scenarios involve up to thousands of hosts and tens of thousands of VMs, making exhaustive search computationally infeasible.

### 1.2 The ROADEF 2012 Reference Problem

The academic reference for this class of problems is the **Google ROADEF/EURO 2012 Challenge: Machine Reassignment**. It formally defines the problem as:

> Given a set of machines $\mathcal{M}$ and processes $P$, find an assignment $M: P \rightarrow \mathcal{M}$ that satisfies all hard constraints and minimizes a weighted cost function.

The key entities in ROADEF map directly to Huawei's system:

| ROADEF | Huawei Cloud |
|--------|-------------|
| **Process** $p$ | **VM** |
| **Machine** $m$ | **Host** (physical server) |
| **Assignment** $M(p) = m$ | **Placement** in `MigrationSolution` |
| **Resource** $r$ (CPU, RAM) | **CPU, Memory** per NUMA |
| **Service** (conflict group) | **Anti-affinity group** |
| **Location** (spread zones) | **Fault domain / Rack** |

### 1.3 Decision Variable and Search Space

There is exactly **one mathematical decision variable** in this problem:

$$M : \text{VM} \rightarrow \text{Placement}(\text{Host}, \text{NumaGroup}, \text{Numa}[])$$

A **solution** is a complete assignment mapping every VM to a placement. In code, this is the `MigrationSolution` object:

```java
// MigrationSolution: the one true decision variable
MigrationSolution solution = new MigrationSolution(problem);

// Setting the decision: VM v goes to this placement
// Placements are pre-built by NumaGroup — not manually constructed.
// Each Placement wraps a Numa[] array; host and numaGroup are derived from the Numa parents.
Placement placement = allPlacements.get(vm.getNumNumas()).get(candidateIndex);
solution.setPlacement(vm, placement);

// Reading the decision
Placement current = solution.getPlacement(vm);
```

The search space size is $|\text{Placements}|^{|\text{VMs}|}$, which at real cloud scale (10,000+ VMs, 500+ hosts) is astronomically large — a direct justification for metaheuristic approaches rather than exact solvers.

### 1.4 Hard Constraints (ROADEF)

**Capacity Constraint** — The total resource demand of all processes on a machine cannot exceed machine capacity:

$$\forall m \in \mathcal{M},\; r \in R:\quad U(m,r) = \sum_{p:\; M(p)=m} R(p,r) \;\leq\; C(m,r)$$

**Conflict Constraint** (Anti-Affinity) — All processes within the same service must run on distinct machines:

$$\forall s \in S,\; (p_i, p_j) \in s,\; p_i \neq p_j \;\Rightarrow\; M(p_i) \neq M(p_j)$$

**Spread Constraint** (Location Diversity) — Each service must span a minimum number of distinct physical locations:

$$\forall s \in S:\quad \sum_{l \in L} \min\!\left(1, \left|\{p \in s \mid M(p) \in l\}\right|\right) \;\geq\; \text{spreadMin}(s)$$

**Dependency Constraint** (Neighborhood) — If service $s_a$ depends on $s_b$, each process of $s_a$ must be co-located in the same neighborhood as at least one process of $s_b$:

$$\forall p_a \in s_a,\;\exists p_b \in s_b,\; n \in N:\quad M(p_a) \in n \;\wedge\; M(p_b) \in n$$

**Transient Usage Constraint** — For resources like disk that are consumed during live migration on both source and destination simultaneously:

$$\forall m \in \mathcal{M},\; r \in TR:\quad \sum_{p:\; M_0(p)=m \;\vee\; M(p)=m} R(p,r) \;\leq\; C(m,r)$$

### 1.5 Objective Functions (ROADEF)

ROADEF uses a single **weighted sum** of five cost components to minimize:

$$\text{totalCost} = \sum_r w_r \cdot \text{loadCost}(r) + \sum_b w_b \cdot \text{balanceCost}(b) + w_{PM} \cdot \text{processMoveCost} + w_{SM} \cdot \text{serviceMoveCost} + w_{MM} \cdot \text{machineMoveCost}$$

Where:
- **Load cost** penalizes usage above the safety threshold: $\sum_m \max(0,\; U(m,r) - SC(m,r))$
- **Balance cost** penalizes resource ratio imbalance: $\sum_m \max(0,\; t \cdot A(m,r_1) - A(m,r_2))$
- **Process move cost**: $\sum_{p: M(p) \neq M_0(p)} PMC(p)$
- **Service move cost**: $\max_{s} |\{p \in s \mid M(p) \neq M_0(p)\}|$
- **Machine move cost**: $\sum_p MMC(M_0(p), M(p))$

### 1.6 How Huawei's Problem Extends ROADEF

Server Consolidation V2 is meaningfully more complex than ROADEF along several dimensions:

**NUMA Hierarchy.** ROADEF treats a machine as a flat resource container. Huawei models a full `Rack → Host → NumaGroup → Numa` hierarchy. VMs are assigned not just to a host but to specific NUMA nodes, creating a two-level bin-packing problem with NUMA locality requirements.

**Lexicographic Objectives instead of Weighted Sum.** Rather than a scalar weighted cost, Huawei uses a strict priority ordering (maximize empty hosts first, then balance load, then minimize migration cost). This avoids the weight-tuning problem and is more robust.

**Two-Stage Decomposition.** ROADEF produces a static assignment with no notion of execution order. Huawei adds a full **batching phase** that sequences migrations into dependency-respecting rounds, handling circular migration dependencies and concurrency limits.

**Richer Business Constraints.** Huawei adds: prefer-flavor capacity protection, per-tenant migration limits, host health states (EVACUATION), hotspot detection and mitigation, centralized scheduling traits, and NUMA resource cutting lines.

---

## 2. Architecture Overview

### 2.1 Layered Design Philosophy

The framework is organized into five core layers, each with a single responsibility:

```
┌─────────────────────────────────────────────────────────────┐
│                        Input Layer                          │
│              Protobuf deserialization → Problem             │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                        Model Layer                          │
│         Problem, Solution, Host, VM, Numa, Placement        │
│              (data structures — no logic)                   │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
┌──────▼──────┐  ┌────────▼──────┐  ┌────────▼───────────────┐
│  Constraint │  │   Objective   │  │      Variable Layer     │
│    Layer    │  │    Layer      │  │  (precomputed state      │
│ (feasibility│  │ (solution     │  │   aggregates; updated    │
│  checking)  │  │  quality)     │  │   incrementally)         │
└──────┬──────┘  └────────┬──────┘  └────────┬───────────────┘
       └──────────────────┼──────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     Algorithm Layer                         │
│        ALNS │ Greedy │ Robust Knapsack │ Genetic │ SCC │ Sequence  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                       Output Layer                          │
│                 Solution → Protobuf response                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Module Structure

```
server-consolidation-v2/
├── server-consolidation-core/              # Core algorithm implementation
│   └── src/main/java/.../consolidation/
│       ├── model/                          # Problem, Solution, Host, Vm, Numa...
│       ├── constraint/                     # Constraint interfaces & implementations
│       ├── objective/                      # Objective interfaces & implementations
│       ├── variable/                       # Variable interfaces & implementations
│       ├── algorithm/                      # ALNS, Greedy, Genetic, SCC...
│       ├── visualization/                  # Solver progress tracking
│       └── util/                           # Utility classes
│
│   └── mitigation/                         # ── Hotspot Mitigation Subsystem ──
│       ├── algorithm/                      # Mitigation-specific solvers
│       │   ├── greedy/
│       │   │   └── GreedySolver.java       # Greedy migration for hotspot relief
│       │   ├── robust/                     # Robust knapsack optimization (Bertsimas & Sim)
│       │   │   ├── RobustKnapsackSolver.java     # Enum: QUEX_GREEDY / QUEX_DROPOUT / QUEX_FULL
│       │   │   ├── RobustKnapsackProblem.java    # Problem def + calcVmsRobustLoad()
│       │   │   └── QuexSolver.java               # Core solver: greedy+dropout+exhaustive core
│       │   ├── DataProcess.java            # Input preprocessing & feature extraction
│       │   ├── HotspotMigrationStrategy.java  # Strategy selector (host vs rack hotspot)
│       │   ├── SimpleRackHotspotMitigationSolver.java  # Rack power hotspot solver
│       │   ├── SimpleSequenceBatchingSolver.java        # Lightweight batching for hotspot
│       │   ├── Solver.java                 # Base solver interface for mitigation context
│       │   └── TwoStageHotspotMitigationSolver.java    # Two-stage: migrate → batch
│       ├── api/
│       │   ├── HostHotspotSolver.java      # Public API: entry point for host hotspots
│       │   └── RackHotspotSolver.java      # Public API: entry point for rack hotspots
│       ├── common/
│       │   └── Constants.java              # Thresholds and default values
│       ├── config/
│       │   └── MitigationConfig.java       # Runtime configuration for mitigation
│       ├── constraint/
│       │   ├── MigrateToEmptyHostConstraint.java             # Only migrate to empty targets
│       │   ├── RackPowerLimitMigrationConstraint.java        # Cap rack power after migration
│       │   ├── TargetHostCpuAllocationThresholdConstraint.java  # Target host CPU ceiling
│       │   └── TargetNumaCpuLoadThresholdConstraint.java     # Target NUMA CPU load ceiling
│       ├── imp/
│       │   ├── HostHotspotSolverFactory.java   # Factory: creates host hotspot solver
│       │   └── HotspotMitigationSolver.java    # Core coordinator of the mitigation run
│       ├── model/
│       │   ├── HotspotProblem.java         # Extends Problem with hotspot-specific metadata
│       │   ├── MitigationLevel.java        # Enum: LIGHT / MEDIUM / HEAVY aggressiveness
│       │   └── SolverConfig.java           # Per-run solver configuration (time limits etc.)
│       ├── objective/
│       │   ├── MaxTargetHostUnusedResourceObjective.java     # Maximize free resources on targets
│       │   ├── MinHotspotRackOverusedPowerMigrationObjective.java  # Minimize overused rack power
│       │   ├── MinTargetProviderMaxLoadObjective.java        # Minimize max load on any target
│       │   ├── MinVmNumOnHotspotProvidersObjective.java      # Minimize VMs left on hotspot hosts
│       │   └── RackPowerUsageVarianceMigrationObjective.java # Minimize rack power variance
│       ├── utils/
│       │   ├── HostHotspotMitigationProtoHelper.java  # Protobuf I/O helper
│       │   └── HotspotTypeUtil.java                   # Hotspot type classification utilities
│       └── variable/
│           ├── HostHotspotVmNumVariable.java      # VM count remaining on hotspot hosts
│           ├── RackPowerUsageMigrationVariable.java  # Power usage per rack
│           ├── TargetHostLoadVariable.java        # Load on candidate target hosts
│           ├── TargetNumaGroupLoadVariable.java   # Load on target NUMA groups
│           ├── TargetNumaLoadVariable.java        # Load on target NUMA nodes
│           └── TargetProviderLoadVariable.java    # Load on target providers (hosts)
│
├── benchmark/                              # Performance evaluation tools
├── batch-tester/                           # Batch testing framework
└── jacoco/                                 # Code coverage reporting
```

**Technology Stack:**

| Technology | Version | Purpose |
|------------|---------|---------|
| Java | 8+ | Core language |
| Maven | 3.6+ | Build management |
| Protobuf | 3.21.11 | I/O serialization |
| Lombok | 1.18.20 | Boilerplate reduction |
| FastUtil | 8.5.13 | High-performance collections |
| JUnit | 5.10.2 | Testing |

### 2.3 End-to-End Data Flow

The overall solving flow follows a clear pipeline:

```
1. INPUT
   Protobuf bytes → Parser → Problem object
   (hosts, VMs, racks, numa topology, initial placements)

2. PROBLEM SETUP
   Register Variables (CpuMemVariable, HostVmsVariable, ...)
   Register Constraints (CpuMemConstraint, AntiAffinityConstraint, ...)
   Register Objectives (EmptyHostObjective, LoadBalancingObjective, ...)

3. STAGE 1 — MIGRATION PHASE
   AlnsMigrationSolver.solve(problem)
   → iterate { ruin → recreate → check constraints → evaluate objective → accept/reject }
   → returns MigrationSolution (VM → Placement map)

4. STAGE 2 — BATCHING PHASE
   GeneticBatchingSolver.solve(problem, placements)
   → sequence migrations, resolve circular dependencies (SCC)
   → returns Solution with ordered Steps

5. OUTPUT
   Solution → Protobuf serialization → response
```

---

## 3. Model Layer — Data Structures

The Model Layer defines pure data structures with no algorithmic logic. It represents the physical and logical entities of the data center.

### 3.1 Physical Resource Hierarchy

The data center is modeled as a five-level hierarchy:

```
Rack
 └── Host (physical server)
      └── NumaGroup (logical NUMA grouping)
           └── Numa (NUMA node: has CPU + Memory capacity)
                └── VM (virtual machine placed here)
```

Each level adds a distinct constraint scope: racks constrain power, hosts constrain total capacity, NUMA groups constrain NUMA-aware placement, NUMA nodes constrain per-socket resources.

### 3.2 Rack

A `Rack` is a physical rack housing multiple hosts. It is the unit for rack-level power hotspot constraints.

```java
public class Rack {
    private List<Host> hosts;

    public Host addHost() { ... }
    public List<Host> getHosts() { return hosts; }
}

// Usage
Rack rack = problem.addRack();
Host host1 = rack.addHost();
Host host2 = rack.addHost();
```

### 3.3 Host

A `Host` represents a physical server. It has a health state and fault domain membership.

```java
public class Host {
    private List<NumaGroup> numaGroups;
    private HostHealthyState healthyState;   // HEALTHY | UNHEALTHY | EVACUATION
    private String faultDomainId;
    private List<String> allowedTenantIds;
    private boolean migrationInRestricted;   // Cannot receive VMs
}
```

**Health States:**

| State | Meaning |
|-------|---------|
| `HEALTHY` | Normal operation, can send and receive VMs |
| `UNHEALTHY` | Degraded but still running; VMs may be migrated away |
| `EVACUATION` | Must be fully drained; all VMs must leave |

```java
Host host = problem.addHost(
    rack,                               // parent rack
    HostHealthyState.HEALTHY,           // health state
    Arrays.asList("tenant-A"),          // allowed tenants
    "fault-domain-west-1"               // fault domain
);
NumaGroup group = host.addNumaGroup();
```

### 3.4 NumaGroup and Numa

A `NumaGroup` is a logical grouping of NUMA nodes. A `Numa` represents a single Non-Uniform Memory Access socket with its own CPU and memory capacity.

```java
public class NumaGroup {
    private List<Numa> numas;
    public Numa addNuma() { ... }
}

public class Numa {
    private float cpu;    // total CPU capacity (cores)
    private float mem;    // total memory capacity (GB)
}

// Setup example: 2-socket host with 32 cores and 128 GB per socket
NumaGroup group = host.addNumaGroup();
Numa socket0 = group.addNuma();
socket0.setCpu(32.0f);
socket0.setMem(128.0f);

Numa socket1 = group.addNuma();
socket1.setCpu(32.0f);
socket1.setMem(128.0f);
```

**Why NUMA Matters:** On modern multi-socket servers, cross-NUMA memory access is significantly slower. Placing a VM's vCPUs and memory on the same NUMA socket is a hard requirement for performance-sensitive workloads. This is why the model goes below host-level to NUMA-level granularity.

### 3.5 VM (Virtual Machine)

A `Vm` is the entity being placed. It has resource demands per NUMA node and carries metadata used by constraints.

```java
public class Vm {
    private boolean migratable;          // can this VM be moved?
    private float numaCpu;               // CPU demand per NUMA node
    private float numaMem;               // Memory demand per NUMA node
    private List<Numa> initialNumas;     // M₀(p) — current placement
    private List<String> traits;         // e.g., ["windows", "gpu"]
    private String tenantId;             // owning tenant
}

// Single-NUMA VM: placed on one socket
Vm smallVm = problem.addVm();
smallVm.setMigratable(true);
smallVm.setNumaCpu(2.0f);
smallVm.setNumaMem(8.0f);
smallVm.setInitialNumas(Collections.singletonList(socket0));

// Multi-NUMA VM: spans both sockets (e.g., large memory VM)
Vm largeVm = problem.addVm();
largeVm.setNumaCpu(16.0f);
largeVm.setNumaMem(64.0f);
largeVm.setInitialNumas(Arrays.asList(socket0, socket1));
```

### 3.6 Placement

A `Placement` fully specifies where a VM lives: which host, which NUMA group, and which specific NUMA nodes. The host and NUMA group are derived from the NUMA nodes' parent chain — the constructor takes only the NUMA array.

```java
public class Placement {
    private final Numa[] numas;       // 1 for single-NUMA, 2+ for multi-NUMA

    public Placement(Numa[] numas) { this.numas = numas; }

    // Host and NumaGroup are derived from the Numa parent chain
    public Host getHost()         { return numas[0].getNumaGroup().getHost(); }
    public NumaGroup getNumaGroup() { return numas[0].getNumaGroup(); }
    public Numa[] getNumas()      { return numas; }
}
```

**Placements are not manually constructed by the solver.** They are pre-built combinatorially by `NumaGroup.addNuma()` during problem construction and retrieved at O(1) via `NumaGroup.getPlacements(numNumas)`:

```java
// NumaGroup.java — confirmed source: combinatorial placement generation
public Numa addNuma() {
    List<Numa> allNumas = host.getProblem().getNumas();
    Numa numa = new Numa(this, numas.size(), allNumas.size());
    numas.add(numa);
    allNumas.add(numa);
    placements.add(new ObjectArrayList<>());
    // Combinatorial expansion: extend every existing k-placement into a (k+1)-placement
    for (int i = placements.size() - 2; i >= 0; --i) {
        for (Placement placement : placements.get(i)) {
            Numa[] newNumas = Arrays.copyOf(placement.getNumas(), i + 2);
            newNumas[i + 1] = numa;
            placements.get(i + 1).add(new Placement(newNumas));
        }
    }
    placements.get(0).add(new Placement(new Numa[] {numa}));
    return numa;
}

/**
 * Returns all possible Placements for numNumas numas — O(1) lookup.
 * For a NumaGroup with N numas, getPlacements(k) returns all C(N,k) combinations.
 */
public List<Placement> getPlacements(int numNumas) {
    if (numNumas > placements.size()) return Collections.emptyList();
    return placements.get(numNumas - 1);
}
```

For a NumaGroup with 4 NUMA nodes: `getPlacements(1)` returns 4 single-NUMA placements, `getPlacements(2)` returns $C(4,2)=6$ two-NUMA placements, and so on.

### 3.7 Problem

`Problem` is the root container that wires together all entities, registered variables, constraints, and objectives. It is the single object passed through the entire framework.

```java
public class Problem {
    private List<Rack> racks;
    private List<Vm> vms;
    private MigrationConstraint migrationConstraint;
    private MigrationObjective migrationObjective;
    private BatchingConstraint batchingConstraint;
    private BatchingObjective batchingObjective;
    // Internal: variable registry (fetcher list)
    private List<MigrationFetcher<? extends MigrationVariable>> migrationFetchers;
    private List<BatchingFetcher<? extends BatchingVariable>> batchingFetchers;
}
```

**Critical methods:**

```java
// Register a variable (returns a fetcher for later use)
MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher =
    problem.addMigrationVariable(CpuMemMigrationVariable::new);

// Wire constraints and objectives
problem.setMigrationConstraint(
    HierarchicalMigrationConstraint.builder()
        .constraint(new CpuMemMigrationConstraint(cpuMemFetcher))
        .build()
);
problem.setMigrationObjective(
    HierarchicalMigrationObjective.builder()
        .objective(new EmptyHostMigrationObjective(emptyHostFetcher))
        .build()
);

// Evaluate a solution
Value score = problem.calculateObjective(solution);
```

### 3.8 MigrationSolution and Solution

`MigrationSolution` holds the current VM-to-Placement assignment and all registered variable instances.

```java
public class MigrationSolution {
    // The decision variable: VM → Placement (array indexed by vm.getIndex())
    private Placement[] placements;
    // Variable instances stored indexed by their fetcher slot
    private MigrationVariable[] migrationVariables;

    // Constructor 1: Initialize from Problem — places all VMs at their initial placements
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

    // Constructor 2: Deep copy for working candidates in ALNS inner loop
    public MigrationSolution(MigrationSolution other) {
        this.placements = Arrays.copyOf(other.placements, other.placements.length);
        this.migrationVariables = new MigrationVariable[other.migrationVariables.length];
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = other.migrationVariables[i].copy();
        }
    }

    // Constructor 3: Shallow copy for best-solution storage (variables recomputed later)
    // When copyVariables=false, variable array is NOT deep-copied.
    // Caller must call updateMigrationVariables(problem) before using this copy.
    public MigrationSolution(MigrationSolution other, boolean copyVariables) { ... }

    public Placement getPlacement(Vm vm) { return placements[vm.getIndex()]; }
    public void setPlacement(Vm vm, Placement p) { placements[vm.getIndex()] = p; }
    public void updateMigrationVariables(Problem problem) { /* full recompute all variables */ }
}
```

**Copy semantics in the ALNS loop (confirmed from source):**
- `new MigrationSolution(solution)` — **working copy** for ruin/recreate mutations. Deep-copies all variables so the original `solution` is never mutated. If the iteration is rejected, the working copy is simply discarded (no rollback needed).
- `new MigrationSolution(newSolution, false)` — **best-solution storage**. Copies placements but skips variable deep-copy as an optimization, since `bestSolution.updateMigrationVariables(problem)` is called once at the end before returning.

`Solution` extends `MigrationSolution` with batching information:

```java
public class Solution extends MigrationSolution {
    private List<Step> batchingSteps;    // ordered migration batches

    public void addStep(Step step) { ... }
    public void updateBatchingVariables(Problem problem) { ... }
}
```

Each `Step` is one round of simultaneous migrations:

```java
public class Step {
    private List<MigratingVm> migratingVms;

    public void addMigratingVm(Vm vm, Placement from, Placement to) { ... }
}
```

### 3.9 Value Types

Objectives return typed values that support lexicographic comparison. **Lower values are better throughout the entire system** — `compareTo < 0` means the left operand is strictly better. This convention holds for all `Value` types: `IntValue`, `FloatValue`, and `ListValue`.

```java
// Integer value — for count-based objectives
IntValue.of(42)

// Float value — for ratio-based objectives
FloatValue.of(0.87f)

// List value — for hierarchical lexicographic comparison
ListValue.of(IntValue.of(5), FloatValue.of(0.12f))
```

Two `ListValue` objects are compared element by element from left to right — the first position where they differ determines the winner. Since **lower is better**, the `EmptyHostMigrationObjective` returns the **negated** empty host count so that more empty hosts (a good outcome) produces a lower (better) value.

**Critical Value method — `compareToZero()`:** Returns the result of comparing a value against the zero/neutral point. Used in `getBestRecreate` to determine if a placement is non-worsening: `newValue.compareToZero() <= 0` means "this delta doesn't worsen the objective" and triggers early acceptance.

---

## 4. Variable Layer — State Aggregators

### 4.1 What Variables Are (and Are Not)

> **Critical clarification:** The term "Variable" in this codebase does **not** mean the optimization decision variable. The decision variable is the `VM → Placement` map in `MigrationSolution`.

`MigrationVariable` objects are **precomputed, incrementally-maintained aggregate statistics** derived from the current solution state. They answer questions like:

- *"How much CPU is used on NUMA node 3 right now?"* → `CpuMemMigrationVariable`
- *"How many VMs are on host 7?"* → `HostVmsMigrationVariable`
- *"How many hosts are completely empty?"* → `EmptyHostMigrationVariable`

Without these, every constraint check would need to scan all VMs and sum up resources — O(n) per check, where n can be tens of thousands. The Variable layer makes this O(1) by maintaining running totals and updating them only for the VMs that actually moved.

### 4.2 The MigrationVariable Interface

```java
public interface MigrationVariable {
    // Full recomputation from scratch — O(n), used at initialization
    void update(Problem problem, MigrationSolution solution);

    // Incremental: undo contribution of VMs removed in the ruin step — O(k)
    void update(Problem problem, MigrationSolution solution, RuinDelta delta);

    // Incremental: add contribution of VMs re-placed in the recreate step — O(k)
    void update(Problem problem, MigrationSolution solution, RecreateDelta delta);

    // Deep copy — used when saving best solution
    MigrationVariable copy();
}
```

The parallel interface for the batching phase is `BatchingVariable`, with `update(MigratingVm)` and `update(StepDelta)` overloads.

### 4.3 Incremental Updates — The Core Performance Design

This is the most important performance decision in the entire framework. Consider what happens when the ALNS algorithm moves VM `v` from `hostA` to `hostB`:

**Without incremental updates (naïve — O(n) per move):**
```java
// To check if hostB has capacity after placing v:
float usedCpu = 0;
for (Vm vm : allVms) {
    if (solution.getPlacement(vm).getHost() == hostB) {
        usedCpu += vm.getNumaCpu();  // scan ALL VMs
    }
}
if (usedCpu + v.getNumaCpu() > hostB.getCpu()) reject();
```

**With incremental updates (O(1) per move):**
```java
// CpuMemMigrationVariable already has the answer pre-cached:
// Update: subtract v's resources from hostA's numa, add to hostB's numa
variable.update(problem, solution, new RecreateDelta(v, newPlacement));

// Constraint just reads:
float usedCpu = variable.getNumaCpu(hostB_numaIndex);
if (usedCpu > capacity) reject();  // constant time
```

The performance difference is enormous at scale: 10,000 iterations × 50 VMs moved per iteration × 10,000 VMs per scan = 5 billion operations versus 10,000 × 50 × O(1) operations.

**Delta Objects** carry just enough information for the incremental update:

```java
// RuinDelta: "these VMs were removed from their placements"
// Confirmed: constructor takes Vm[] array (single-element in ALNS inner loop)
class RuinDelta {
    private final Vm[] vms;
    public RuinDelta(Vm[] vms) { this.vms = vms; }
    public Vm[] getVms() { return vms; }
    // Self-applying: delta.update(problem, solution) commits the ruin
    public void update(Problem problem, MigrationSolution solution) { ... }
}

// RecreateDelta: "this VM was placed at this target"
// Confirmed: constructor takes (Vm, Placement) — only VM and target placement.
// The old placement is implicit from the current solution state.
class RecreateDelta {
    private final Vm vm;
    private final Placement placement;  // target placement
    public RecreateDelta(Vm vm, Placement placement) { this.vm = vm; this.placement = placement; }
    public Vm getVm() { return vm; }
    public Placement getPlacement() { return placement; }
    // Self-applying: delta.update(problem, solution) commits the placement
    public void update(Problem problem, MigrationSolution solution) { ... }
}
```

**Important:** Both delta types are **self-applying** — `delta.update(problem, solution)` commits the change and triggers incremental variable updates. The constraint/objective projection methods (`satisfy(problem, solution, delta)` and `calculate(problem, solution, delta)`) evaluate the delta's effect **without** mutating the solution. Only after the winner is chosen is `update()` called to commit.

### 4.4 The Fetcher Pattern

Variables are registered at problem-build time and retrieved at runtime through a **fetcher** mechanism. This decouples the variable lifecycle from the constraint/objective that uses it. The actual implementation, confirmed from source, uses a direct **array index** pattern — the fetcher is nothing more than a typed wrapper around an integer slot index.

```java
// MigrationFetcher.java — actual implementation
@RequiredArgsConstructor(access = AccessLevel.PACKAGE)
public class MigrationFetcher<T extends MigrationVariable> {
    private final int index;  // slot index into MigrationSolution's variable array

    public T fetch(MigrationSolution solution) {
        return (T) solution.getMigrationVariables()[index];  // O(1) direct array access
    }
}

// Problem.java — index is assigned at registration time
public <T extends MigrationVariable> MigrationFetcher<T> addMigrationVariable(Supplier<T> supplier) {
    migrationVariableSuppliers.add(supplier);
    return new MigrationFetcher<>(migrationVariableSuppliers.size() - 1);  // list position = index
}

// MigrationSolution.java — the backing array
public class MigrationSolution {
    private final MigrationVariable[] migrationVariables;

    public MigrationSolution(Problem problem) {
        // Array pre-sized to the number of registered suppliers
        migrationVariables = new MigrationVariable[problem.getMigrationVariableSuppliers().size()];
        // Each slot initialised using the supplier at the corresponding index
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = problem.getMigrationVariableSuppliers().get(i).get();
        }
    }

    public MigrationVariable[] getMigrationVariables() { return migrationVariables; }
}
```

**Why array index and not a `Map`?** A `Map<Class<?>, MigrationVariable>` lookup is O(1) amortised but involves hashing and boxing overhead. The array approach is truly O(1) with no overhead — critical when fetched millions of times per second inside the inner ALNS loop.

**Why not `solution.getCpuMemVariable()`?** Because then `MigrationSolution` would need a field for every variable type — tight coupling that prevents adding new variables without modifying the core class. With the registry, `MigrationSolution` is a generic array that knows nothing about specific variable types.

Multiple consumers (e.g., `CpuMemMigrationConstraint` and `MinLoadBalancingObjective`) share the **same variable instance** stored at the same array slot. Computation happens once per delta; all readers see the updated state immediately.

### 4.5 Catalogue of Migration Variables

| Variable | Internal State | What It Tracks |
|----------|---------------|----------------|
| `CpuMemMigrationVariable` | `float[][] numaCpu`, `float[][] numaMem` | CPU and memory used per NUMA node per host |
| `HostVmsMigrationVariable` | `List<List<Vm>> hostVms` | VMs currently on each host |
| `EmptyHostMigrationVariable` | `int numEmptyHost` | Count (and identity) of fully empty hosts |
| `LoadVariable` | `float[] hostLoads` | Load metric per host (for balancing) |
| `AntiAffinityMigrationVariable` | `Map<String, Set<Host>> groups` | Which hosts each anti-affinity group currently spans |
| `MigrationCostMigrationVariable` | `int totalCost` | Cumulative migration cost |
| `TenantMigrationVariable` | `Map<String, List<Vm>> tenantVms` | VMs per tenant per host |
| `PreferFlavorMigrationVariable` | Capacity arrays | Remaining capacity for large-flavor VMs |
| `NumaResourceCuttingLineMigrationVariable` | Utilization per NUMA | Whether NUMA usage exceeds the cutting line threshold |

**Example — CpuMemMigrationVariable internals:**

```java
public class CpuMemMigrationVariable implements MigrationVariable {
    private float[][] numaCpu;  // [hostIndex][numaIndex] = used CPU
    private float[][] numaMem;  // [hostIndex][numaIndex] = used Memory

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        // Full recompute: iterate all VMs
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
        // Incremental: only update affected NUMA nodes
        Vm vm = delta.getVm();
        Placement newP = delta.getPlacement();                 // target placement
        Placement oldP = solution.getPlacement(delta.getVm()); // current (pre-move) placement

        // Remove from old placement
        for (Numa numa : oldP.getNumas()) {
            numaCpu[oldP.getHost().getIndex()][numa.getIndex()] -= vm.getNumaCpu();
            numaMem[oldP.getHost().getIndex()][numa.getIndex()] -= vm.getNumaMem();
        }
        // Add to new placement
        for (Numa numa : newP.getNumas()) {
            numaCpu[newP.getHost().getIndex()][numa.getIndex()] += vm.getNumaCpu();
            numaMem[newP.getHost().getIndex()][numa.getIndex()] += vm.getNumaMem();
        }
    }

    public float getNumaCpu(int numaIndex) { return numaCpu[numaIndex]; }
    public float getNumaMem(int numaIndex) { return numaMem[numaIndex]; }
}
```

### 4.6 Catalogue of Batching Variables

| Variable | What It Tracks |
|----------|----------------|
| `DegreeBatchingVariable` | Number of concurrent migrations per host in current batch |
| `MigrationCostBatchingVariable` | Total migration cost accumulated so far in batching |
| `AntiAffinityBatchingVariable` | Anti-affinity group state during batch execution |

### 4.7 Implementing a Custom Variable

```java
public class CustomMigrationVariable implements MigrationVariable {
    private int customMetric;

    public CustomMigrationVariable(Problem problem) {
        this.customMetric = 0;
    }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        // Full recompute from scratch
        this.customMetric = computeFromScratch(problem, solution);
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // Undo contributions of ruined VMs (current placement read from solution)
        for (Vm vm : delta.getVms()) {
            this.customMetric -= contributionOf(vm, solution.getPlacement(vm));
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // Add contribution of newly placed VM
        this.customMetric += contributionOf(delta.getVm(), delta.getPlacement());
    }

    @Override
    public MigrationVariable copy() {
        CustomMigrationVariable copy = new CustomMigrationVariable(problem);
        copy.customMetric = this.customMetric;
        return copy;
    }

    public int getCustomMetric() { return customMetric; }
}

// Registration at build time
MigrationFetcher<CustomMigrationVariable> fetcher =
    problem.addMigrationVariable(CustomMigrationVariable::new);
```

---

## 5. Constraint Layer — Feasibility Logic

### 5.1 The MigrationConstraint Interface

```java
public interface MigrationConstraint {
    // Full check: is the entire solution feasible?
    boolean satisfy(Problem problem, MigrationSolution solution);

    // Incremental check after a ruin operation (VMs removed)
    boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta);

    // Incremental check after a recreate operation (one VM placed)
    boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
```

The incremental overloads are the key to efficiency. After placing one VM, only the constraints affected by that VM's new and old host need to be re-evaluated.

### 5.2 Hierarchical Constraint Composition

All active constraints are composed into a single root `HierarchicalMigrationConstraint` using the **Composite design pattern**. Constraints are checked in registration order; the first failure short-circuits the remaining checks.

```java
MigrationConstraint rootConstraint = HierarchicalMigrationConstraint.builder()
    .constraint(new CpuMemMigrationConstraint(cpuMemFetcher))          // checked 1st
    .constraint(new IntraHostMigrationConstraint())                    // checked 2nd
    .constraint(new AntiAffinityMigrationConstraint(aaFetcher))       // checked 3rd
    .constraint(new BudgetLimitMigrationConstraint(costFetcher, 500)) // checked 4th
    .build();

problem.setMigrationConstraint(rootConstraint);
```

Ordering by decreasing "probability of violation" is a practical optimization: if CPU capacity is violated far more often than the budget, putting it first saves evaluating the budget check on infeasible solutions.

### 5.3 Decoupling Constraints from Variables

This is a fundamental architectural decision. **Constraints contain no state and perform no computation.** They are pure predicates that read from Variables.

**Tightly coupled (bad — O(n) per check):**
```java
// BAD: constraint scans all VMs to compute CPU usage itself
public boolean satisfy(Problem p, MigrationSolution sol) {
    for (Host host : p.getHosts()) {
        float used = 0;
        for (Vm vm : p.getVms()) {           // O(n) scan!
            if (sol.getPlacement(vm).getHost() == host)
                used += vm.getNumaCpu();
        }
        if (used > host.getTotalCpu()) return false;
    }
    return true;
}
```

**Decoupled (good — O(1) per check):**
```java
// GOOD: constraint reads precomputed value from Variable
public class CpuMemMigrationConstraint implements MigrationConstraint {
    private final MigrationFetcher<CpuMemMigrationVariable> fetcher;

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        CpuMemMigrationVariable variable = fetcher.fetch(solution);  // O(1) lookup
        for (Numa numa : problem.getAllNumas()) {
            if (variable.getNumaCpu(numa.getIndex()) > numa.getCpu()) return false;
            if (variable.getNumaMem(numa.getIndex()) > numa.getMem()) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem p, MigrationSolution sol, RecreateDelta delta) {
        // Only check the affected host (target of the placement)
        CpuMemMigrationVariable variable = fetcher.fetch(sol);
        return checkHost(variable, delta.getPlacement().getHost());
    }
}
```

The decoupling achieves three things simultaneously:
1. O(1) per-move constraint evaluation (variable is already updated)
2. No duplicated computation: if both `CpuMemConstraint` and a load objective need CPU usage, they share one `CpuMemMigrationVariable` instance
3. Full extensibility: new constraints can be added without touching existing variables

### 5.4 Hard Constraints

These must be satisfied for any solution to be valid.

**CpuMemMigrationConstraint** — NUMA-level capacity:
```java
// Ensures ∀ numa: usedCPU ≤ capacity AND usedMem ≤ capacity
MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher =
    problem.addMigrationVariable(CpuMemMigrationVariable::new);
new CpuMemMigrationConstraint(cpuMemFetcher);
```

**AntiAffinityMigrationConstraint** — VMs in the same anti-affinity group must be on different hosts:
```java
// Ensures ∀ group g: no two VMs in g share the same host
MigrationFetcher<AntiAffinityMigrationVariable> aaFetcher =
    problem.addMigrationVariable(AntiAffinityMigrationVariable::new);
new AntiAffinityMigrationConstraint(aaFetcher);
```

**IntraHostMigrationConstraint** — Despite the name, this constraint **forbids** intra-host placement: a migratable VM must move to a **different** host from its initial placement. It prevents the solver from "migrating" a VM within the same physical host (e.g., to a different NUMA group on the same host), which would consume migration budget without freeing capacity on the source host.

```java
// IntraHostMigrationConstraint.java — actual implementation
public class IntraHostMigrationConstraint implements MigrationConstraint {

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // Accept if: initial placement (no migration yet), OR placed on a DIFFERENT host
        return delta.isInitial()
            || delta.getHost() != delta.getVm().getInitialPlacement().getHost();
    }

    @Override
    public boolean satisfy(Problem problem, Solution solution, MigrateDelta delta) {
        // Reject if the migration stays on the same host (source == destination)
        return delta.getHost() != delta.getFromPlacement().getHost();
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        // Full check: every VM that was moved must be on a different host than before
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

**Semantic note:** The name "Intra-Host" describes what it *rejects* — movement that stays intra-host. Every accepted placement is either the original (no move) or a genuine cross-host migration.

### 5.5 Soft / Business Constraints

**BudgetLimitMigrationConstraint** — Total migration overhead must not exceed a budget:
```java
// Ensures Σ PMC(vm) ≤ budgetLimit for migrated VMs
MigrationFetcher<MigrationCostMigrationVariable> costFetcher =
    problem.addMigrationVariable(MigrationCostMigrationVariable::new);
new BudgetLimitMigrationConstraint(costFetcher, 1000 /*budget*/);
```

**PreferFlavorProtectionConstraint** — Reserves capacity on each host for large-flavor VMs that may be placed in the future. This prevents the optimizer from packing hosts so tightly that large VMs can never be admitted:
```java
MigrationFetcher<PreferFlavorMigrationVariable> pfFetcher =
    problem.addMigrationVariable(PreferFlavorMigrationVariable::new);
new PreferFlavorProtectionConstraint(pfFetcher);
```

**TenantMigrationConstraint** — Limits how many VMs a single tenant can have migrated simultaneously, preventing service disruption for any one customer:
```java
MigrationFetcher<TenantMigrationVariable> tenantFetcher =
    problem.addMigrationVariable(TenantMigrationVariable::new);
new TenantMigrationConstraint(tenantFetcher);
```

**NumaResourceCuttingLineMigrationConstraint** — Prevents NUMA nodes from being packed above a configurable threshold (e.g., 90%), reserving headroom for burst workloads:
```java
MigrationFetcher<NumaResourceCuttingLineMigrationVariable> cutFetcher =
    problem.addMigrationVariable(NumaResourceCuttingLineMigrationVariable::new);
new NumaResourceCuttingLineMigrationConstraint(cutFetcher);
```

### 5.6 Batching Constraints

Applied during the batching phase to constrain the execution of migrations:

**DegreeBatchingConstraint** — Limits the number of simultaneous migrations per host. Too many concurrent migrations stress the network and storage subsystems:
```java
BatchingFetcher<DegreeBatchingVariable> degreeFetcher =
    problem.addBatchingVariable(DegreeBatchingVariable::new);
new DegreeBatchingConstraint(degreeFetcher, 3 /*max concurrent migrations per host*/);
```

**AntiAffinityBatchingConstraint** — Ensures anti-affinity is never transiently violated during batch execution (e.g., while a VM is mid-flight, it momentarily occupies both source and target):
```java
BatchingFetcher<AntiAffinityBatchingVariable> aaBatchFetcher =
    problem.addBatchingVariable(AntiAffinityBatchingVariable::new);
new AntiAffinityBatchingConstraint(aaBatchFetcher);
```

### 5.7 Implementing a Custom Constraint

```java
public class MaxVmsPerHostConstraint implements MigrationConstraint {
    private final MigrationFetcher<HostVmsMigrationVariable> fetcher;
    private final int maxVmsPerHost;

    public MaxVmsPerHostConstraint(MigrationFetcher<HostVmsMigrationVariable> fetcher,
                                    int maxVmsPerHost) {
        this.fetcher = fetcher;
        this.maxVmsPerHost = maxVmsPerHost;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        HostVmsMigrationVariable var = fetcher.fetch(solution);
        for (Host host : problem.getHosts()) {
            if (var.getNumVms(host.getIndex()) > maxVmsPerHost) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem p, MigrationSolution sol, RuinDelta delta) {
        return true; // Ruin only removes VMs — can't violate max
    }

    @Override
    public boolean satisfy(Problem p, MigrationSolution sol, RecreateDelta delta) {
        // Only check the target host
        HostVmsMigrationVariable var = fetcher.fetch(sol);
        Host target = delta.getPlacement().getHost();
        return var.getNumVms(target.getIndex()) <= maxVmsPerHost;
    }
}
```

---

## 6. Objective Layer — Optimization Goals

### 6.1 The MigrationObjective Interface

```java
public interface MigrationObjective<T extends Value> {
    T calculate(Problem problem, MigrationSolution solution);
    T calculate(Problem problem, MigrationSolution solution, RuinDelta delta);
    T calculate(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
```

Like constraints, objectives are **pure readers** — they read from Variables and return a `Value`. They contain no state and perform no computation of their own.

### 6.2 Lexicographic Hierarchy vs. Weighted Sum

**ROADEF approach (weighted sum):**
$$\text{cost} = 100 \cdot \text{loadCost} + 10 \cdot \text{balanceCost} + 1 \cdot \text{moveCost}$$

This requires careful weight tuning. A poorly chosen weight can dominate the entire objective. Two solutions that differ on the primary goal but agree on secondary goals may be impossible to distinguish if weight ratios are wrong.

**Huawei approach (lexicographic hierarchy):**
> *Maximize empty hosts. Among equal empty-host counts, minimize load imbalance. Among ties there, minimize migration cost.*

This is implemented as a `ListValue` comparison:

```
Solution A: [5 empty hosts, load imbalance=0.12, migration cost=300]
Solution B: [5 empty hosts, load imbalance=0.09, migration cost=450]
→ B wins because at position 2 (load imbalance), 0.09 < 0.12
```

No weight tuning is needed. The priority ordering reflects explicit business intent.

### 6.3 HierarchicalMigrationObjective

```java
public class HierarchicalMigrationObjective implements MigrationObjective<ListValue> {
    private final List<MigrationObjective<? extends Value>> objectives;       // primary
    private final List<MigrationObjective<? extends Value>> minorObjectives;  // secondary
}

// Assembly
HierarchicalMigrationObjective objective = HierarchicalMigrationObjective.builder()
    .objective(new EmptyHostMigrationObjective(emptyHostFetcher))    // primary 1
    .objective(new MinLoadBalancingObjective(loadFetcher))           // primary 2
    .minorObjective(new MigrationCostMigrationObjective(costFetcher), /*lazy=*/true)
    .build();
```

The resulting `ListValue` contains all objective values in priority order. The `compareTo` method on `ListValue` implements lexicographic comparison.

### 6.4 Catalogue of Migration Objectives

| Objective | Direction | Returns | What It Measures |
|-----------|-----------|---------|-----------------|
| `EmptyHostMigrationObjective` | Maximize | `IntValue` | Number of hosts with zero VMs |
| `MinLoadBalancingObjective` | Minimize | `ListValue` | Load variance across hosts |
| `PreferFlavorMigrationObjective` | Maximize | `IntValue` | Remaining capacity for large-flavor VMs |
| `MigrationCostMigrationObjective` | Minimize | `IntValue` | Total cost of all VM migrations |
| `TenantMigrationObjective` | Varies | `ListValue` | Tenant distribution spread metrics |
| `NumaResourceCuttingLineMigrationObjective` | Minimize | `FloatValue` | NUMA usage above cutting line threshold |

**EmptyHostMigrationObjective — The Primary Driver:**
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

### 6.5 Catalogue of Batching Objectives

| Objective | Direction | What It Minimizes |
|-----------|-----------|-------------------|
| `NumStepBatchingObjective` | Minimize | Number of sequential migration batches |
| `LastBatchSizeBatchingObjective` | Minimize | Size of the final batch (shorter last batch = faster completion) |
| `MigrationCostBatchingObjective` | Minimize | Total migration cost during batching |

Batching objectives are assembled similarly:
```java
HierarchicalBatchingObjective batchObjective = HierarchicalBatchingObjective.builder()
    .objective(new NumStepBatchingObjective())          // minimize rounds
    .objective(new LastBatchSizeBatchingObjective())    // minimize tail size
    .build();
```

### 6.6 Lazy Evaluation of Secondary Objectives

Secondary objectives are often expensive to compute and are needed only when primary objectives tie — which is rare. Lazy evaluation skips secondary computation unless needed:

```java
HierarchicalMigrationObjective.builder()
    .objective(new EmptyHostMigrationObjective(emptyHostFetcher))
    // lazy=true: MigrationCostObjective is only computed when empty host count ties
    .minorObjective(new MigrationCostMigrationObjective(costFetcher), /*lazy=*/true)
    .build();
```

This is a practical optimization that can significantly reduce total computation in the inner search loop.

### 6.7 Implementing a Custom Objective

```java
public class HostVarianceObjective implements MigrationObjective<FloatValue> {
    private final MigrationFetcher<LoadVariable> fetcher;

    public HostVarianceObjective(MigrationFetcher<LoadVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public FloatValue calculate(Problem problem, MigrationSolution solution) {
        LoadVariable var = fetcher.fetch(solution);
        float[] loads = var.getHostLoads();
        float mean = Arrays.stream(loads).average().orElse(0);
        float variance = (float) Arrays.stream(loads)
            .map(l -> (l - mean) * (l - mean))
            .average().orElse(0);
        return FloatValue.of(variance);  // lower is better
    }

    @Override
    public FloatValue calculate(Problem p, MigrationSolution sol, RuinDelta delta) {
        return calculate(p, sol);  // simplified — use full recalc
    }

    @Override
    public FloatValue calculate(Problem p, MigrationSolution sol, RecreateDelta delta) {
        return calculate(p, sol);  // simplified — can be made incremental
    }
}
```

---

## 7. Algorithm Layer — Optimization Engines

### 7.1 Two-Stage Decomposition

The framework decomposes the full problem into two sequential sub-problems:

```
Stage 1 — Migration Phase
  Input:  Problem (hosts, VMs, constraints, objectives)
  Output: MigrationSolution (VM → target Placement for each VM)
  Goal:   Find the optimal final placement of all VMs
  Algorithms: ALNS (with AdaptiveMaintainer), Greedy, Robust Knapsack

Stage 2 — Batching Phase
  Input:  Problem + target Placements from Stage 1
  Output: Solution (ordered Steps, each a set of simultaneous migrations)
  Goal:   Schedule the migrations in feasible, minimal-round batches
  Algorithms: Genetic, SCC, Greedy, Sequence
```

The `TwoStageSolver` orchestrates both:

```java
public class TwoStageSolver implements Solver {
    private final MigrationOptimizer migrationOptimizer;
    private final BatchingSolver batchingSolver;

    @Override
    public Solution solve(Problem problem) {
        // Stage 1
        MigrationSolution migrationSolution = migrationOptimizer.solve(problem);

        // Stage 2 — feed Stage 1's placements into the batching solver
        Placement[] placements = extractPlacements(migrationSolution, problem);
        Solution solution = batchingSolver.solve(problem, placements);

        return solution;
    }
}

// Wiring it together
TwoStageSolver solver = new TwoStageSolver(
    new AlnsMigrationOptimizer(hostVmsFetcher, random),     // Stage 1
    new GeneticBatchingSolver(new SequenceBatchingSolver(), random)  // Stage 2
);
Solution solution = solver.solve(problem);
```

### 7.2 The Solver Interface Hierarchy

```
Solver
 └── TwoStageSolver (combines both stages)

MigrationSolver
 ├── AlnsMigrationSolver         (metaheuristic — primary for large problems)
 ├── GreedyMigrationSolver       (deterministic — fast baseline)
 └── [Robust Knapsack solvers]   (mathematical — used inside hotspot mitigation)
     ├── QUEX_GREEDY             (classical greedy heuristic)
     ├── QUEX_DROPOUT            (greedy + dropout search)
     └── QUEX_FULL               (greedy + dropout + exhaustive core search)

BatchingSolver
 ├── SequenceBatchingSolver      (deterministic primitive — greedy packing)
 ├── GreedyBatchingSolver        (priority-sorted + Sequence)
 ├── SccBatchingSolver           (dependency graph — handles circular dependencies)
 └── GeneticBatchingSolver       (evolutionary — uses SequenceSolver as fitness evaluator)
```

All interfaces are simple and substitutable:

```java
public interface MigrationSolver {
    MigrationSolution solve(Problem problem);
}

public interface BatchingSolver {
    Solution solve(Problem problem, Placement[] placements);
}
```

### 7.3 ALNS Migration Solver

**Adaptive Large Neighborhood Search** is the primary algorithm for large-scale problems. The implementation is **genuinely adaptive**: multiple operator types compete and their selection probabilities are updated in real time based on historical performance via `AdaptiveMaintainer`. The acceptance criterion is **Late Acceptance Hill Climbing** (not simulated annealing — see Section 7.3b).

**Confirmed configurable defaults (via Lombok `@Setter` with fluent accessors):**

| Field | Default | Purpose |
|---|---|---|
| `acceptanceCriteria` | `LateAcceptanceHillClimbingAcceptanceCriteria(10)` | LAHC with buffer length **10** |
| `numMaxRuinHost` | `5` | Upper bound of adaptive `numRuinHost` dimension |
| `maxSteps` | `50000` | Maximum total ALNS iterations |
| `maxStagnationSteps` | `500` | Iterations without global improvement before termination |
| `timeLimit` | `Duration.ofSeconds(5)` | Wall-clock time budget |
| `useChainOptimizer` | `true` | Post-recreate chain optimization pass |

```java
// AlnsMigrationSolver.java — confirmed source (Lombok @Accessors(fluent = true))
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

##### `AlnsMigrationSolver.solve()` — Complete Source (Confirmed)

```java
@Override
public MigrationSolution solve(Problem problem) {
    Instant endTime = Instant.now().plus(timeLimit);
    MigrationSolution solution = new MigrationSolution(problem);
    if (problem.getHosts().isEmpty() || problem.getVms().isEmpty()) {
        return solution;
    }
    allPlacements = MigrationSolver.calculateAllPlacements(problem);
    AdaptiveMaintainer adaptiveMaintainer = new AdaptiveMaintainer(numMaxRuinHost);
    int steps = 0;
    int stagnationSteps = 0;
    Value value = problem.getMigrationObjective().calculate(problem, solution);
    MigrationSolution bestSolution = new MigrationSolution(solution, false);
    Value bestValue = value;
    acceptanceCriteria.init(value);
    OptimizationTrackData optimizationTrackData = new OptimizationTrackData();
    optimizationTrackData.addOptimizationTrackDataItem(Collections.emptyList(), value);

    while (steps < maxSteps && stagnationSteps < maxStagnationSteps
            && Instant.now().isBefore(endTime)) {
        ++steps;
        ++stagnationSteps;

        // 1. SELECT OPERATORS (adaptive roulette wheel)
        int numRuinHost = adaptiveMaintainer.rollNumRuinHost(random);
        HostSorterType hostSorterType = adaptiveMaintainer.rollHostSorterType(random);
        VmSorterType vmSorterType = adaptiveMaintainer.rollVmSorterType(random);
        RecreateType recreateType = adaptiveMaintainer.rollRecreateType(random);

        // 2. RUIN — select hosts, copy-on-write the solution, guided ruin
        List<Host> ruinHosts = getRuinHosts(problem, solution, numRuinHost, hostSorterType);
        MigrationSolution newSolution = new MigrationSolution(solution);  // deep copy
        List<Vm> ruinVms = getRuinVms(problem, newSolution, ruinHosts, vmSorterType);

        // 3. RECREATE — if ruin found no improvement or recreate fails, skip iteration
        List<RecreateDelta> recreateDeltas = new ArrayList<>();
        if (Objects.isNull(ruinVms)
            || !recreate(problem, newSolution, ruinVms, recreateDeltas,
                         vmSorterType, recreateType)) {
            continue;
        }

        // 4. EVALUATE — full objective on the candidate solution
        Value newValue = problem.getMigrationObjective().calculate(problem, newSolution);
        if (useChainOptimizer) {
            newValue = MigrationOptimizer.optimizeChain(problem, newSolution, newValue,
                hostVmsFetcher, ruinVms, recreateDeltas);
        }

        // 5. GLOBAL BEST CHECK — independent of acceptance
        if (newValue.compareTo(bestValue) < 0) {       // lower is better
            bestValue = newValue;
            bestSolution = new MigrationSolution(newSolution, false);  // shallow copy
            stagnationSteps = 0;                        // reset stagnation
            adaptiveMaintainer.updateWeights(ruinHosts.size(), vmSorterType,
                hostSorterType, recreateType, 1.0);     // reward operators
        }

        // 6. ACCEPT / REJECT (LAHC) — determines working solution for next iteration
        if (acceptanceCriteria.accept(value, newValue, random, stagnationSteps)) {
            value = newValue;
            solution = newSolution;  // adopt the candidate
            optimizationTrackData.addOptimizationTrackDataItem(recreateDeltas, value);
        } else {
            // newSolution is simply discarded — no rollback needed
            optimizationTrackData.addOptimizationTrackDataItem(Collections.emptyList(), value);
        }
    }
    bestSolution.setOptimizationTrackData(optimizationTrackData);
    bestSolution.updateMigrationVariables(problem);  // full recompute before returning
    return bestSolution;
}
```

**Critical architectural observations from the source:**

1. **Copy-on-write forward pattern (not snapshot-restore).** `new MigrationSolution(solution)` creates a deep copy *before* any mutations. All ruin/recreate mutations happen on `newSolution`. If rejected, `newSolution` is simply discarded — `solution` was never touched. There is no undo, no reverse delta, no snapshot restore.

2. **Three stopping criteria (AND).** The loop terminates when *any* of these conditions is met: `steps ≥ maxSteps` (50,000), `stagnationSteps ≥ maxStagnationSteps` (500), or `time ≥ endTime` (5 seconds). The stagnation counter increments *every* iteration and only resets on **global best improvement** — not on mere acceptance.

3. **Best-tracking is independent of acceptance.** The global best check (`newValue.compareTo(bestValue) < 0`) happens *before* the LAHC acceptance check. A solution can become the new global best without being accepted as the working solution (though in practice, the LAHC will accept any improvement).

4. **Lower values are better throughout.** `compareTo < 0` means the left operand is *better*. This is confirmed throughout: `getBestRecreate` uses `compareTo < 0` to find the minimum, `compareToZero() <= 0` means "acceptable/non-worsening", and the LAHC `accept` method uses `compareTo <= 0` for current comparison.

5. **Weight update passes `ruinHosts.size()`, not `numRuinHost`.** The actual number of hosts in the ruin list (after sorting/truncation by `HostSorterType`) may differ from the rolled value. The adaptive mechanism rewards the actual outcome, not the intent.

6. **`MigrationOptimizer.optimizeChain()`** — An undocumented post-processing step that attempts further improvement after recreate. It takes the ruined VMs and recreate deltas and performs targeted local optimization (chain swaps).

##### `getRuinHosts` — Host Selection (Confirmed Source)

```java
private List<Host> getRuinHosts(Problem problem, MigrationSolution solution, int numRuinHost,
    HostSorterType hostSorterType) {
    List<Host> ruinHosts = new ObjectArrayList<>(problem.getHosts().size());
    AssignmentList<Vm> migratableHostVms = hostVmsFetcher.fetch(solution).getMigratableHostVms();
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

All hosts with at least one migratable VM are candidates. They are shuffled (for randomness), then the `HostSorterType` sorts/truncates to `numRuinHost`.

##### `getRuinVms` — Guided, Improvement-Gated Ruin (Confirmed Source)

This is the most surprising discovery from the source code. **Ruin is not blind destruction** — it is a guided, per-VM, constraint-checked process that aborts the entire iteration if it cannot find an improving removal:

```java
private List<Vm> getRuinVms(Problem problem, MigrationSolution solution, List<Host> ruinHosts,
    VmSorterType vmSorterType) {
    HostVmsMigrationVariable variable = hostVmsFetcher.fetch(solution);
    List<Vm> ruinVms = new ObjectArrayList<>();
    boolean improved = false;
    for (Host host : ruinHosts) {
        List<Vm> vms = new ObjectArrayList<>(variable.getMigratableHostVms().get(host.getIndex()));
        sortVmsByType(solution, vms, vmSorterType, true);
        for (Vm vm : vms) {
            RuinDelta ruinDelta = new RuinDelta(new Vm[] {vm});
            if (!problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                continue;  // skip VMs whose removal would violate constraints
            }
            ruinVms.add(vm);
            int compareToZero =
                problem.getMigrationObjective().calculate(problem, solution, ruinDelta).compareToZero();
            ruinDelta.update(problem, solution);  // apply AFTER projection
            if (compareToZero < 0) {
                improved = true;
                break;  // found an improving ruin — stop processing this host's VMs
            }
        }
    }
    return improved ? ruinVms : null;  // null = skip entire ALNS iteration
}
```

**Key behaviors:**
- VMs are ruined **one at a time**, each with its own `RuinDelta(new Vm[] {vm})`
- Each removal is **constraint-checked** before applying (`satisfy` is a projection — no state change)
- Each removal's **objective impact is evaluated** before applying (`calculate` returns marginal cost)
- If removal improves the objective (`compareToZero < 0`), the ruin phase stops early for that host
- If **no** ruin across any host produces an improvement, `null` is returned and the **entire ALNS iteration is skipped**
- The delta is applied (`ruinDelta.update(...)`) only after passing the constraint check

This is a significant departure from standard ALNS literature, where ruin typically removes all VMs from selected hosts unconditionally.

##### `sortVmsByType` — VM Sorting with Pre-Sort for Ruin (Confirmed Source)

```java
private void sortVmsByType(MigrationSolution solution, List<Vm> vms,
    VmSorterType vmSorterType, boolean isRuin) {
    if (isRuin && vmSorterType != VmSorterType.RANDOM) {
        // During ruin: already-moved VMs first (false < true in Java boolean comparison)
        vms.sort(Comparator.comparing(vm -> vm.getInitialPlacement() == solution.getPlacement(vm)));
    }
    vmSorterType.sort(vms, random);
    if (!isRuin) {
        Collections.reverse(vms);  // During recreate: reverse the ascending sort → largest first
    }
}
```

**During ruin:** VMs that have already been displaced (current ≠ initial placement) are sorted first. This prioritizes re-ruining VMs that were previously moved, giving the algorithm another chance to find better placements for them.

**During recreate:** The `VmSorterType` sort (ascending) is reversed, so **largest VMs are placed first** — the standard bin-packing heuristic: place the hardest-to-fit items while the most options remain.

#### 7.3a The Adaptive Mechanism — `AdaptiveMaintainer`

Each ALNS iteration selects four independent operator dimensions, all drawn via **roulette-wheel selection** weighted by cumulative historical performance:

| Dimension | Type | Concrete values |
|---|---|---|
| `numRuinHost` | `int` | `1 … numMaxRuinHost` |
| `VmSorterType` | enum | `CPU_MEM, MEM_CPU, CPU_MEM_PROD, NUM_NUMA, RANDOM` |
| `HostSorterType` | enum | `RUIN_EXPECTED, RANDOM, RUIN_EXPECTED_RANDOM` |
| `RecreateType` | enum | `BEST, RANDOM, FirstFit` |

```java
// AdaptiveMaintainer.java — actual implementation
class AdaptiveMaintainer {
    private final Map<Integer, Double>        numRuinHostWeights;   // 1..numMaxRuinHost → 1.0 initial each
    private final Map<VmSorterType, Double>   vmSorterWeights;      // each enum constant → 1.0
    private final Map<HostSorterType, Double> hostSorterWeights;    // each enum constant → 1.0
    private final Map<RecreateType, Double>   recreateWeights;      // each enum constant → 1.0

    // All weights initialised to 1.0 in constructor — no decay, no reset, no sliding window.
    // Weights only ever increase. Operators that find improvements early will permanently
    // dominate selection in later iterations.

    int            rollNumRuinHost   (SplittableRandom r) { return rollByWeights(numRuinHostWeights, r); }
    VmSorterType   rollVmSorterType  (SplittableRandom r) { return rollByWeights(vmSorterWeights, r); }
    HostSorterType rollHostSorterType(SplittableRandom r) { return rollByWeights(hostSorterWeights, r); }
    RecreateType   rollRecreateType  (SplittableRandom r) { return rollByWeights(recreateWeights, r); }

    // Reward all four operators when the iteration produced an improvement
    void updateWeights(int numRuinHost, VmSorterType vmSorterType,
                       HostSorterType hostSorterType, RecreateType recreateType, double weight) {
        numRuinHostWeights .computeIfPresent(numRuinHost,    (k, v) -> v + weight);
        vmSorterWeights    .computeIfPresent(vmSorterType,   (k, v) -> v + weight);
        hostSorterWeights  .computeIfPresent(hostSorterType, (k, v) -> v + weight);
        recreateWeights    .computeIfPresent(recreateType,   (k, v) -> v + weight);
    }

    // Roulette wheel selection — O(n) in number of operator types
    static <T> T rollByWeights(Map<T, Double> weights, SplittableRandom random) {
        double sum = weights.values().stream().mapToDouble(Double::doubleValue).sum();
        double r = random.nextDouble(sum);
        double cumulative = 0.0;
        for (Map.Entry<T, Double> entry : weights.entrySet()) {
            cumulative += entry.getValue();
            if (r < cumulative) return entry.getKey();
        }
        throw new IllegalStateException("Roulette selection failed");
    }
}
```

##### `VmSorterType` — How Ruined VMs Are Ordered for Recreate (confirmed source)

Sorting is ascending (smallest first). However, during recreate, `sortVmsByType` **reverses** the list, so the **largest VMs are placed first** — the standard bin-packing heuristic: place the hardest-to-fit items while the most options remain. During ruin, the ascending order is kept, and an additional pre-sort places already-moved VMs first (see `sortVmsByType` source in Section 7.3).

```java
public enum VmSorterType {
    /** Sort by total CPU (ascending), break ties by total memory */
    CPU_MEM {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing((Vm vm) -> vm.getNumaCpu() * vm.getNumNumas())
                .thenComparing(vm -> vm.getNumaMem() * vm.getNumNumas()));
        }
    },
    /** Sort by total memory (ascending), break ties by total CPU */
    MEM_CPU {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing((Vm vm) -> vm.getNumaMem() * vm.getNumNumas())
                .thenComparing(vm -> vm.getNumaCpu() * vm.getNumNumas()));
        }
    },
    /** Sort by CPU × Memory × NUMA_count² (product of all resource dimensions) */
    CPU_MEM_PROD {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing(
                vm -> vm.getNumaCpu() * vm.getNumaMem() * vm.getNumNumas() * vm.getNumNumas()));
        }
    },
    /** Sort by number of NUMA nodes the VM spans (ascending — single-NUMA VMs first) */
    NUM_NUMA {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing(Vm::getNumNumas));
        }
    },
    /** Shuffle randomly */
    RANDOM {
        public void sort(List<Vm> vms, SplittableRandom random) {
            AlgorithmUtil.shuffleList(vms, random);
        }
    };
    public abstract void sort(List<Vm> vms, SplittableRandom random);
}
```

**Design note:** `CPU_MEM_PROD` creates a single scalar combining CPU, memory, and NUMA span — VMs that are small on all dimensions simultaneously get placed first. `NUM_NUMA` specifically prioritises single-socket VMs, which have far more candidate placements than multi-NUMA VMs (a multi-NUMA VM needs a host with at least 2 free NUMA nodes satisfying capacity on each).

##### `HostSorterType` — How Candidate Hosts Are Ordered for Ruin (confirmed source)

```java
public enum HostSorterType {

    /**
     * Select the numRuinHost hosts whose ruin would produce the best objective value.
     * Evaluates each candidate by computing RuinDelta + objective — exact but O(candidates × objectives).
     */
    RUIN_EXPECTED {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            PriorityQueue<Pair<Host, Value>> queue = new PriorityQueue<>(numRuinHost,
                Comparator.comparing((Function<Pair<Host, Value>, Value>) Pair::right).reversed());
            AssignmentList<Vm> migratableHostVms = hostVmsFetcher.fetch(solution).getMigratableHostVms();
            for (Host host : ruinHosts) {
                RuinDelta ruinDelta = new RuinDelta(migratableHostVms.get(host.getIndex()));
                if (problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                    Value value = problem.getMigrationObjective().calculate(problem, solution, ruinDelta);
                    if (queue.isEmpty() || queue.size() < numRuinHost) {
                        queue.add(Pair.of(host, value));
                    } else if (value.compareTo(queue.peek().right()) < 0) {
                        queue.poll();
                        queue.add(Pair.of(host, value));
                    }
                }
            }
            ruinHosts.clear();
            for (Pair<Host, Value> pair : queue) {
                ruinHosts.add(pair.left());
            }
        }
    },

    /**
     * Simply truncate the (already shuffled) candidate list to numRuinHost.
     * Cheapest possible selection — O(1).
     */
    RANDOM {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            if (numRuinHost < ruinHosts.size()) {
                ruinHosts.subList(numRuinHost, ruinHosts.size()).clear();
            }
        }
    },

    /**
     * Score all candidates by expected ruin value, then use weighted random selection
     * (rank-based 1/(i+1) weights) to pick numRuinHost hosts. Balances quality and diversity.
     */
    RUIN_EXPECTED_RANDOM {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            AssignmentList<Vm> migratableHostVms = hostVmsFetcher.fetch(solution).getMigratableHostVms();
            List<Pair<Host, Value>> hostsWithValue = new ObjectArrayList<>();
            for (Host host : ruinHosts) {
                RuinDelta ruinDelta = new RuinDelta(migratableHostVms.get(host.getIndex()));
                if (problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                    hostsWithValue.add(Pair.of(host,
                        problem.getMigrationObjective().calculate(problem, solution, ruinDelta)));
                }
            }
            hostsWithValue.sort(Comparator.comparing(Pair::right));  // best (lowest) objective first
            ruinHosts.clear();
            for (int num = 0; num < numRuinHost && !hostsWithValue.isEmpty(); ++num) {
                // Rank-based weights: weight[i] = 1/(i+1) — best-ranked host 2× more likely than 2nd
                double sum = 0.0;
                int chosenIndex = 0;
                for (int i = 0; i < hostsWithValue.size(); i++) {
                    double weight = 1.0 / (i + 1);
                    sum += weight;
                    if (random.nextDouble(sum) < weight) chosenIndex = i;
                }
                ruinHosts.add(hostsWithValue.get(chosenIndex).left());
                hostsWithValue.remove(chosenIndex);
            }
        }
    };

    public abstract void sort(Problem problem, MigrationSolution solution, List<Host> ruinHosts,
        int numRuinHost, SplittableRandom random,
        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher);
}
```

**Design note:** `RUIN_EXPECTED` is the most informed selector — it speculatively applies a `RuinDelta` to compute the exact objective improvement of emptying each host. `RUIN_EXPECTED_RANDOM` adds exploration: even a lower-ranked host (not the single best) gets a chance proportional to `1/(rank+1)`, preventing the algorithm from always attacking the same host.

##### `RecreateType` — How Displaced VMs Are Re-placed (confirmed source)

```java
public enum RecreateType {

    /**
     * For each ruined VM, evaluate ALL candidate placements and pick the one that
     * maximises the objective (best-improvement). Most expensive but highest quality.
     */
    BEST {
        public boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                SplittableRandom random) {
            for (Vm vm : vms) {
                RecreateDelta bestDelta = MigrationSolver.getBestRecreate(
                    problem, solution, vm, allPlacements.get(vm.getNumNumas()));
                recreateDeltas.add(bestDelta);
                if (bestDelta == null) return false;  // no feasible placement found
                bestDelta.update(problem, solution);
            }
            return true;
        }
    },

    /**
     * For each ruined VM, pick a uniformly random feasible placement.
     * Cheapest but introduces stochasticity — important for diversification.
     */
    RANDOM {
        public boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                SplittableRandom random) {
            for (Vm vm : vms) {
                RecreateDelta randomDelta = MigrationSolver.getRandomRecreate(
                    problem, solution, vm, allPlacements.get(vm.getNumNumas()), random);
                recreateDeltas.add(randomDelta);
                if (randomDelta == null) return false;
                randomDelta.update(problem, solution);
            }
            return true;
        }
    },

    /**
     * For each ruined VM, pick the FIRST feasible placement found (in candidate list order).
     * Faster than BEST, more deterministic than RANDOM.
     */
    FirstFit {
        public boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                SplittableRandom random) {
            for (Vm vm : vms) {
                RecreateDelta firstFitDelta = MigrationSolver.getFirstFitRecreate(
                    problem, solution, vm, allPlacements.get(vm.getNumNumas()));
                recreateDeltas.add(firstFitDelta);
                if (firstFitDelta == null) return false;
                firstFitDelta.update(problem, solution);
            }
            return true;
        }
    };

    public abstract boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
        List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements, SplittableRandom random);
}
```

**Design note:** `allPlacements.get(vm.getNumNumas())` is key — the candidate list is pre-partitioned by NUMA count so that single-NUMA VMs only consider single-NUMA placements and multi-NUMA VMs only consider multi-NUMA placements. This avoids checking structurally incompatible placements at all.

##### `MigrationSolver` Static Helper Methods — Confirmed Source

The `MigrationSolver` interface contains static methods that implement the core placement logic used by all `RecreateType` variants. These are the most performance-critical methods in the entire framework — they are called for every VM on every ALNS iteration.

**`calculateAllPlacements` — Global Placement Pre-computation:**

```java
// MigrationSolver.java — static method on the interface
static List<List<Placement>> calculateAllPlacements(Problem problem) {
    int maxNumas = 0;
    for (Vm vm : problem.getVms()) {
        maxNumas = Math.max(maxNumas, vm.getNumNumas());
    }
    List<List<Placement>> allPlacements = new ObjectArrayList<>(maxNumas + 1);
    for (int i = 0; i <= maxNumas; ++i) {
        allPlacements.add(new ObjectArrayList<>());
    }
    for (NumaGroup numaGroup : problem.getNumaGroups()) {
        for (int numNumas = 1; numNumas <= maxNumas; ++numNumas) {
            allPlacements.get(numNumas).addAll(numaGroup.getPlacements(numNumas));
        }
    }
    return allPlacements;
}
```

Called once at the start of `solve()`. Iterates over `problem.getNumaGroups()` (a flat global list), collecting all placements partitioned by NUMA count. No host-level filtering — all structural placements are enumerated, with filtering deferred to the constraint layer at recreate time. `allPlacements.get(k)` returns all placements requiring exactly `k` NUMA nodes.

**`getAllPlacementsDelta` — Restricted Placement List for Target Hosts:**

```java
static List<List<Placement>> getAllPlacementsDelta(Problem problem, List<Host> targetHosts) {
    int maxNumasNum = 0;
    for (Vm vm : problem.getVms()) {
        maxNumasNum = Math.max(maxNumasNum, vm.getNumNumas());
    }
    List<List<Placement>> allPlacementsDelta = new ObjectArrayList<>(maxNumasNum + 1);
    for (int i = 0; i <= maxNumasNum; ++i) {
        allPlacementsDelta.add(new ObjectArrayList<>());
    }
    for (Host host : targetHosts) {
        for (NumaGroup numaGroup : host.getNumaGroups()) {
            for (int numNumas = 1; numNumas <= maxNumasNum; ++numNumas) {
                allPlacementsDelta.get(numNumas).addAll(numaGroup.getPlacements(numNumas));
            }
        }
    }
    return allPlacementsDelta;
}
```

Builds a restricted placement list for specific hosts — likely used in hotspot mitigation scenarios where only certain target hosts are candidates.

**`getBestRecreate` — Three-Phase Best Placement (Most Critical Method):**

```java
static RecreateDelta getBestRecreate(Problem problem, MigrationSolution solution, Vm vm,
    List<Placement> placements) {
    List<Pair<RecreateDelta, Value>> deltaValuePairs = new LinkedList<>();

    // PHASE 1: Try initial placement first ("stay home" heuristic)
    RecreateDelta recreateDelta = new RecreateDelta(vm, vm.getInitialPlacement());
    if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
        Value newValue = problem.getMigrationObjective().calculate(problem, solution, recreateDelta);
        if (newValue.compareToZero() <= 0) {
            return recreateDelta;  // non-worsening → accept immediately, no migration needed
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
        Value newValue = problem.getMigrationObjective().calculate(problem, solution, recreateDelta);
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

**Key insights from `getBestRecreate`:**

1. **Initial placement priority:** The method first tries `vm.getInitialPlacement()` — a "stay home if possible" heuristic that minimizes unnecessary migrations. If the VM can go back where it started without worsening the objective, it does.

2. **`compareToZero() <= 0` early exit:** Any feasible placement with a non-positive marginal cost triggers immediate return. This means `calculate(problem, solution, delta)` returns a **marginal cost** (change from current state), not an absolute value. Value ≤ 0 = "doesn't worsen the objective" = acceptable. This makes `BEST` mode viable even with large candidate lists by short-circuiting on the first good-enough option.

3. **Lower Value = better:** Phase 3 uses `compareTo(bestValue) < 0` to find the minimum. Combined with the ≤ 0 acceptance threshold, this confirms the convention: **lower values are better** throughout the entire objective system.

4. **Projection pattern:** `satisfy()` and `calculate()` evaluate the delta's effect *without* mutating the solution. Only the final winning delta calls `update(problem, solution)` to commit. This is why evaluating hundreds of candidates per VM is cheap.

**`getRandomRecreate` and `getFirstFitRecreate`:**

```java
static RecreateDelta getRandomRecreate(Problem problem, MigrationSolution solution, Vm vm,
    List<Placement> placements, SplittableRandom random) {
    AlgorithmUtil.shuffleList(placements, random);
    for (Placement placement : placements) {
        RecreateDelta recreateDelta = new RecreateDelta(vm, placement);
        if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
            return recreateDelta;  // first feasible after shuffle
        }
    }
    return null;
}

static RecreateDelta getFirstFitRecreate(Problem problem, MigrationSolution solution, Vm vm,
    List<Placement> placements) {
    for (Placement placement : placements) {
        RecreateDelta recreateDelta = new RecreateDelta(vm, placement);
        if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
            return recreateDelta;  // first feasible in candidate order
        }
    }
    return null;
}
```

Both are feasibility-only: return the first placement that passes `satisfy()`, with no objective evaluation. `RANDOM` shuffles first for diversity; `FirstFit` uses the candidate list's natural order.

**Weight behaviour summary (Q3 confirmed):** All four operator maps initialise every entry to `1.0`. There is **no decay, no reset, and no sliding window**. Weights monotonically increase. An operator family that finds improvements in the first 100 iterations will permanently have higher selection probability for the remaining thousands of iterations. This is a known trade-off: simplicity and low overhead at the cost of reduced late-stage exploration.

#### 7.3b Acceptance Criterion — Late Acceptance Hill Climbing (LAHC)

> ⚠️ **Correction from earlier draft:** The acceptance criterion is **NOT Simulated Annealing**. There is no temperature, no cooling schedule, and no `exp(Δ/T)` probability. The actual implementation is `LateAcceptanceHillClimbingAcceptanceCriteria`.

LAHC maintains a **circular buffer of historical objective values**. A new solution is accepted if it is better than the *current* solution OR better than the value recorded at the same buffer position `L` steps ago. This allows escaping plateaus without any temperature parameter to tune.

```java
// LateAcceptanceHillClimbingAcceptanceCriteria.java — actual implementation
public class LateAcceptanceHillClimbingAcceptanceCriteria implements AcceptanceCriteria {
    private final Value[] values;  // circular buffer of historical values
    private int position;          // current buffer position

    public LateAcceptanceHillClimbingAcceptanceCriteria(int length) {
        values = new Value[length];  // buffer length controls "memory" depth
    }

    @Override
    public void init(Value value) {
        Arrays.fill(values, value);  // initialise all slots with the starting objective
    }

    @Override
    public boolean accept(Value oldValue, Value newValue,
                          SplittableRandom random, int stagnationSteps) {
        // Accept if improved over current OR improved over history[position]
        Value candidate;
        if (newValue.compareTo(oldValue) <= 0        // better than current
                || newValue.compareTo(values[position]) < 0) {  // better than L steps ago
            candidate = newValue;
        } else {
            candidate = oldValue;  // reject — keep current
        }

        // Update history slot if candidate is better than what was there
        if (candidate.compareTo(values[position]) < 0) {
            values[position] = candidate;
        }
        position = (position + 1) % values.length;  // advance circular buffer

        return candidate == newValue;  // true = accepted
    }
}
```

**Why LAHC instead of SA?** SA requires tuning initial temperature and cooling rate, which are problem-size-dependent and fragile. LAHC's single parameter (buffer length `L`) is easier to reason about: larger `L` means more historical memory and broader exploration.

**Confirmed default: L = 10.** This is 100–500× smaller than values typical in LAHC literature (which suggest L = 1000–5000). A buffer of 10 means the solver compares against the objective from just 10 iterations ago — effectively an extremely short-memory hill climber. Combined with `maxStagnationSteps=500` and `timeLimit=5s`, this configuration is optimized for fast convergence in production rather than deep exploration. The chain optimizer (`MigrationOptimizer.optimizeChain()`) likely compensates by performing targeted local improvements after each recreate phase.

#### 7.3c Full ALNS Iteration Structure

```
Initialize:
  solution ← new MigrationSolution(problem)       // all VMs at initial placements
  allPlacements ← MigrationSolver.calculateAllPlacements(problem)
  adaptiveMaintainer ← AdaptiveMaintainer(numMaxRuinHost=5)
  acceptanceCriteria ← LateAcceptanceHillClimbingAcceptanceCriteria(L=10)
  value ← problem.getMigrationObjective().calculate(problem, solution)
  bestSolution ← MigrationSolution(solution, false)  // shallow copy
  bestValue ← value
  acceptanceCriteria.init(value)
  steps ← 0; stagnationSteps ← 0

Loop while steps < 50000 AND stagnationSteps < 500 AND time < endTime:
  ++steps; ++stagnationSteps;

  1. SELECT OPERATORS (adaptive — roulette wheel):
     numRuinHost    ← adaptiveMaintainer.rollNumRuinHost(random)
     hostSorterType ← adaptiveMaintainer.rollHostSorterType(random)
     vmSorterType   ← adaptiveMaintainer.rollVmSorterType(random)
     recreateType   ← adaptiveMaintainer.rollRecreateType(random)

  2. RUIN (guided, per-VM, constraint-checked):
     ruinHosts ← getRuinHosts(problem, solution, numRuinHost, hostSorterType)
     newSolution ← new MigrationSolution(solution)  // COPY-ON-WRITE
     ruinVms ← getRuinVms(problem, newSolution, ruinHosts, vmSorterType)
     If ruinVms == null → SKIP iteration (continue)

  3. RECREATE (strategy = recreateType):
     Sort ruinVms by vmSorterType (reversed → largest first)
     For each vm in ruinVms:
       Find placement using recreateType strategy (BEST/RANDOM/FirstFit)
       If no feasible placement → SKIP iteration (continue)
       recreateDelta.update(problem, newSolution)  // commit placement

  4. EVALUATE:
     newValue ← problem.getMigrationObjective().calculate(problem, newSolution)
     If useChainOptimizer:
       newValue ← MigrationOptimizer.optimizeChain(...)

  5. GLOBAL BEST CHECK (independent of acceptance):
     If newValue < bestValue:                       // LOWER is better
       bestValue ← newValue
       bestSolution ← MigrationSolution(newSolution, false)
       stagnationSteps ← 0
       adaptiveMaintainer.updateWeights(ruinHosts.size(), vmSorterType,
                                        hostSorterType, recreateType, 1.0)

  6. ACCEPT / REJECT (LAHC):
     If acceptanceCriteria.accept(value, newValue, random, stagnationSteps):
       value ← newValue
       solution ← newSolution
     Else:
       // newSolution is simply discarded — NO rollback needed

Return bestSolution (after updateMigrationVariables)
```

### 7.4 Greedy Migration Solver

A simple, fast deterministic algorithm. Good for small problems or as a warm-start for ALNS.

```java
@Override
public MigrationSolution solve(Problem problem) {
    MigrationSolution solution = initializeSolution(problem);
    solution.updateMigrationVariables(problem);

    boolean improved = true;
    while (improved) {
        improved = false;
        for (Vm vm : problem.getVms()) {
            if (!vm.isMigratable()) continue;
            Value currentValue = problem.calculateObjective(solution);
            Host bestHost = findBestHost(problem, solution, vm);
            if (bestHost != null && objectiveImproved(currentValue, ...)) {
                applyMove(solution, vm, bestHost);
                improved = true;
            }
        }
    }
    return solution;
}
```

**Limitation:** Greedy is susceptible to local optima. Once it gets stuck, it cannot escape because it never accepts worse moves.

### 7.5 Robust Knapsack Solvers (`mitigation/algorithm/robust/`)

**Problem context:** In hotspot mitigation, the core subproblem is: *"which VMs should be migrated off the hotspot host to bring its load below threshold, while minimising total migration memory cost?"* This is a **knapsack problem** where items (VMs) have a load contribution and a migration cost (memory footprint). The "robust" aspect handles **load uncertainty** — a VM's actual load varies over time, so the solver must guarantee the host stays below threshold even under adverse load fluctuations.

#### Robust Load Calculation (Bertsimas & Sim)

The key mathematical primitive is `calcVmsRobustLoad`, which computes a pessimistic load estimate that holds with high probability. Given a budget parameter $\Gamma$ (gamma), it takes the nominal load plus the $\Gamma$ largest uncertainty radii:

```java
// RobustKnapsackProblem.java
public double calcVmsRobustLoad(List<Vm> vmList, ValueRangeProvider<Vm> loadProvider) {
    // Sort VMs by uncertainty radius descending (highest variance first)
    List<Vm> sortedVms = new ArrayList<>(vmList);
    Collections.sort(sortedVms, (a, b) ->
        Double.compare(loadProvider.getValueRange(b).radius(),
                       loadProvider.getValueRange(a).radius()));

    double totalRobustLoad = 0.0;
    for (int i = 0; i < sortedVms.size(); i++) {
        // Nominal load (centre of load range) is always counted
        totalRobustLoad += loadProvider.getValueRange(sortedVms.get(i)).center();
        // Uncertainty radius is counted only for the top-Γ most uncertain VMs
        if (i < maxSetSize /* = Γ */) {
            totalRobustLoad += loadProvider.getValueRange(sortedVms.get(i)).radius();
        }
    }
    return totalRobustLoad;
    // Mathematical guarantee: load(remaining VMs) ≤ totalRobustLoad
    // with probability ≥ 1 − ε(Γ, n)
}
```

Where `ValueRange` is a `(center, radius)` pair: the load fluctuates in `[center − radius, center + radius]`. The robust load is $\sum_i \mu_i + \sum_{i=1}^{\Gamma} \hat{\delta}_i$ (sorted by radius descending).

#### Three Solver Variants — `RobustKnapsackSolver` Enum

```java
// RobustKnapsackSolver.java
public enum RobustKnapsackSolver {

    /** Classical greedy: sort VMs by load-reduction-per-memory-cost, take greedily */
    QUEX_GREEDY {
        @Override
        public List<Vm> solve(RobustKnapsackProblem problem) {
            return new QuexSolver(problem, /*dropout=*/false, /*coreSize=*/0).solve();
        }
    },

    /** Greedy + dropout search: after greedy solution, try removing items to improve */
    QUEX_DROPOUT {
        @Override
        public List<Vm> solve(RobustKnapsackProblem problem) {
            return new QuexSolver(problem, /*dropout=*/true, /*coreSize=*/0).solve();
        }
    },

    /** Greedy + dropout + exhaustive search on a core of 10 items:
     *  Most accurate; examines all 2^10 = 1024 combinations for the
     *  hardest-to-decide items near the capacity boundary */
    QUEX_FULL {
        @Override
        public List<Vm> solve(RobustKnapsackProblem problem) {
            return new QuexSolver(problem, /*dropout=*/true, /*coreSize=*/10).solve();
        }
    };

    public abstract List<Vm> solve(RobustKnapsackProblem problem);
}
```

**The `QuexSolver` — Full Source**

Before reading the code, the critical framing: the **knapsack holds VMs that *stay* on the host**, not VMs to migrate. `invert(knapsack)` returns VMs *not* in the knapsack — those are the migration candidates returned to the caller. The objective maximises `knapsack.getMemory()` — total memory of VMs kept in place — which is equivalent to minimising migration memory cost.

**Efficiency** is defined as `maxLoad / memory`: VMs are sorted ascending by this ratio, so the **least load-per-memory VMs are tried first** for keeping. High-efficiency VMs (large load relative to their memory footprint) naturally fall out of the knapsack when capacity is exceeded, because they were added last — this is precisely what the algorithm wants: migrating high-load-density VMs relieves the most load per unit of migration cost.

```java
package com.huawei.clouds.lyra.mitigation.algorithm.robust;

public class QuexSolver {
    private final RobustKnapsackProblem problem;
    private final boolean useDropout;
    private final int coreSize;

    // VMs sorted by efficiency ascending: efficiency = maxLoad / memory
    // Least load-intensive per memory unit first → kept in knapsack preferentially
    private Lazy<List<Vm>> availableVms = new Lazy<>(this::newAvailableVms);

    // Knapsack pre-seeded with all non-migratable VMs (baseline load that cannot change)
    private Lazy<RobustKnapsack> trivialKnapsack = new Lazy<>(this::newTrivialKnapsack);

    // Greedy solution (computed lazily, reused by dropout and core phases)
    private Lazy<RobustKnapsack> greedyKnapsack = new Lazy<>(() -> computeGreedySolution(null, null));

    public QuexSolver(RobustKnapsackProblem problem, boolean useDropout, int coreSize) {
        this.problem = problem;
        this.useDropout = useDropout;
        this.coreSize = coreSize;
    }

    /** Entry point: solve and return VMs to MIGRATE OUT */
    public List<Vm> solve() {
        RobustKnapsack knapsack = greedyKnapsack.get();
        if (useDropout) {
            knapsack = computeDropoutSolution(knapsack);
        }
        if (coreSize > 0) {
            knapsack = computeCoreSolution(knapsack);
        }
        return invert(knapsack);  // VMs NOT in knapsack = VMs to migrate out
    }

    /** Return VMs not in the knapsack (i.e., the VMs to evict from the host) */
    private List<Vm> invert(RobustKnapsack knapsack) {
        List<Vm> result = new ArrayList<>();
        for (Vm vm : problem.getVms()) {
            if (!knapsack.contains(vm)) {
                result.add(vm);
            }
        }
        return result;
    }

    /**
     * Greedy phase: starting from the trivial knapsack (non-migratable VMs),
     * try adding each migratable VM in ascending efficiency order.
     * If adding makes the knapsack infeasible (robust load > safety capacity), remove and skip.
     *
     * @param include  VM that must be forcefully added (used by dropout: "what if we force X in?")
     * @param exclude  VM that must be skipped (used by dropout: "what if we force X out?")
     */
    private RobustKnapsack computeGreedySolution(Vm include, Vm exclude) {
        RobustKnapsack knapsack = trivialKnapsack.get().copy();
        if (include != null) {
            knapsack.add(include);
        }
        for (Vm vm : availableVms.get()) {  // ascending efficiency order
            if (vm == include || vm == exclude) continue;
            knapsack.add(vm);
            if (!knapsack.isFeasible()) {
                knapsack.remove(vm);  // exceeds robust safety capacity → skip
            }
        }
        return knapsack;
    }

    /**
     * Dropout phase: for each VM, try flipping its membership relative to the greedy solution.
     * - If VM is IN the greedy knapsack: compute greedy WITHOUT it (evict it, migrate it out)
     * - If VM is NOT in the greedy knapsack: compute greedy WITH it forced in (keep it, migrate something else)
     * Accept the flip if the resulting knapsack is feasible AND has higher total memory.
     * This is a 1-opt local search over the greedy solution.
     */
    private RobustKnapsack computeDropoutSolution(RobustKnapsack input) {
        RobustKnapsack best = input;
        for (Vm vm : availableVms.get()) {
            RobustKnapsack knapsack;
            if (input.contains(vm)) {
                knapsack = computeGreedySolution(null, vm);  // exclude this VM
            } else {
                knapsack = computeGreedySolution(vm, null);  // force-include this VM
            }
            if (knapsack.isFeasible() && knapsack.getMemory() > best.getMemory()) {
                best = knapsack;
            }
        }
        return best;
    }

    /** Baseline knapsack: add all non-migratable VMs (their load is fixed, cannot be reduced) */
    private RobustKnapsack newTrivialKnapsack() {
        RobustKnapsack rk = new RobustKnapsack(
            problem.getGammaCalculator(),
            problem.getVmLoadProvider(),
            problem.getSafetyLoadCapacity());
        for (Vm vm : problem.getVms()) {
            if (!vm.isMigratable()) rk.add(vm);
        }
        return rk;
    }

    /**
     * Sort migratable VMs by efficiency ascending: efficiency = maxLoad / memory.
     * Low efficiency VMs (little load per unit of memory) are preferred in the knapsack —
     * keeping them costs little load budget but saves migration memory cost.
     * High efficiency VMs (heavy load relative to size) are natural eviction candidates.
     */
    private List<Vm> newAvailableVms() {
        Int2DoubleOpenHashMap vm2eff = new Int2DoubleOpenHashMap();
        for (Vm vm : problem.getVms()) {
            double memory  = vm.getNumaMem() * vm.getNumNumas();
            double maxUtil = problem.getVmLoadProvider().getValueRange(vm).getMaxValue();
            vm2eff.put(vm.getIndex(), maxUtil / memory);
        }
        List<Vm> vms = new ArrayList<>();
        for (Vm vm : problem.getVms()) {
            if (vm.isMigratable()) vms.add(vm);
        }
        vms.sort(Comparator.comparing(vm -> vm2eff.get(vm.getIndex())));  // ascending efficiency
        return vms;
    }

    /**
     * Core concept (from Kellerer, Pferschy, Pisinger "Knapsack Problems"):
     * The "break point" is the first VM in efficiency-sorted order that the greedy solution
     * could NOT include (the item that just exceeded capacity).
     * The "core" is a window of coreSize items centered around the break point —
     * these are the items whose inclusion is most ambiguous: close to the capacity boundary,
     * approximately equal efficiency. The greedy decision on these items is least reliable.
     */
    private List<Vm> getCore() {
        RobustKnapsack greedy = greedyKnapsack.get();
        int breakPoint = 0;
        for (Vm vm : availableVms.get()) {
            if (greedy.contains(vm)) {
                breakPoint++;
            } else {
                break;  // first item the greedy could not include
            }
        }
        int end   = Math.min(breakPoint + coreSize / 2, availableVms.get().size());
        int begin = Math.max(end - coreSize, 0);
        return availableVms.get().subList(begin, end);
    }

    /**
     * Core phase: exhaustive search over all 2^coreSize subsets of core items.
     * Uses Gray code iteration — each step flips exactly ONE bit (add or remove one VM),
     * making each iteration O(1) knapsack update rather than O(coreSize) rebuild.
     * The Gray code position is extracted via Integer.numberOfTrailingZeros(i),
     * which gives the index of the bit that changed from i-1 to i in Gray code order.
     *
     * For coreSize=10: 2^10 = 1024 iterations, each O(1) → effectively constant time.
     */
    private RobustKnapsack computeCoreSolution(RobustKnapsack input) {
        RobustKnapsack best    = input;
        List<Vm>       core    = getCore();
        RobustKnapsack knapsack = input.copy();

        for (int i = 1; i < (1 << core.size()); i++) {
            // Gray code: numberOfTrailingZeros(i) gives the position that flipped
            int pos = Math.min(core.size(), Integer.numberOfTrailingZeros(i));
            Vm vm = core.get(pos);
            if (knapsack.contains(vm)) {
                knapsack.remove(vm);
            } else {
                knapsack.add(vm);
            }
            if (knapsack.isFeasible() && knapsack.getMemory() > best.getMemory()) {
                best = knapsack.copy();
            }
        }
        return best;
    }
}
```

**Algorithmic summary:**

| Phase | Method | Complexity | What it does |
|---|---|---|---|
| Greedy | `computeGreedySolution` | O(n log n + n) | Sort by efficiency; greedily keep VMs until robust capacity exceeded |
| Dropout | `computeDropoutSolution` | O(n²) | 1-opt local search: try flipping each VM's membership |
| Core | `computeCoreSolution` | O(2^k) with k=10 | Exhaustive Gray code search over the k items nearest the break point |

The three `RobustKnapsackSolver` variants compose these phases:

| Variant | Phases run | Use case |
|---|---|---|
| `QUEX_GREEDY` | Greedy only | Fast, good enough for simple hotspots |
| `QUEX_DROPOUT` | Greedy + Dropout | Better quality, moderate cost |
| `QUEX_FULL` | Greedy + Dropout + Core | Best quality, core search is effectively O(1024) ≈ free for k=10 |

**Output:** A `List<Vm>` of VMs to **migrate out**. The `RobustKnapsack` feasibility check uses `calcVmsRobustLoad` (Bertsimas & Sim) to guarantee the remaining load stays within `safetyLoadCapacity` even under worst-case load fluctuations over the Γ most uncertain VMs.

### 7.6 Sequence Batching Solver

The fundamental primitive for the batching phase. Given a migration sequence, it packs migrations into batches greedily.

```
Initialize: currentStep = new Step()
For each migratingVm in sequence:
    Add vm to currentStep
    Update batching variables with MigrateDelta
    If batchingConstraint.satisfy(problem, solution, migrateDelta) == FALSE:
        Remove vm from currentStep
        Finalize currentStep → add to solution.steps
        currentStep = new Step()
        Add vm to new currentStep
Return solution with all steps
```

### 7.7 SCC Batching Solver

Handles **circular migration dependencies**. A circular dependency occurs when VM A must move to host X, but VM B (currently on host X) must first move away. If A→X and B→Y and C→X's original location, there may be a cycle.

```
1. Build dependency graph:
   For each VM v migrating from host_src to host_dst:
     If another VM u currently on host_dst has not yet migrated:
       Add edge v → u (v depends on u vacating first)

2. Find Strongly Connected Components (Tarjan's / Kosaraju's algorithm)
   Each SCC is a set of migrations with circular dependencies

3. For migrations within an SCC:
   One VM must use a temporary "trampoline" location to break the cycle
   (or they must be batched into a single step where order doesn't matter)

4. Topological sort of SCCs → determines inter-SCC execution order

5. Within each SCC → apply Sequence solver
```

This is the most algorithmically sophisticated component of the batching phase.

### 7.8 Genetic Batching Solver

An evolutionary algorithm that treats the migration **ordering** (permutation) as the chromosome. The fitness function is the `SequenceBatchingSolver` result: a better ordering produces fewer batches.

#### Actual Crossover — Batch-Preservation Crossover

> ⚠️ **Correction from earlier draft:** The crossover is **NOT Order Crossover (OX)**. It is a custom **batch-preservation crossover** that inherits a structural batch from one parent and fills remaining slots from the other.

```java
// GeneticBatchingSolver.java — actual crossover implementation
private MigratingVm[] crossover(Individual parentA, Individual parentB) {
    int length = parentA.migratingVms.length;

    // 1. Select a random batch from parentA's current solution structure
    List<List<MigratingVm>> batches = parentA.solution.getBatches();
    List<MigratingVm> selectedBatch = batches.get(random.nextInt(batches.size()));

    // 2. Record which VM indices belong to the selected batch
    IntSet batchVmIndices = new IntOpenHashSet(selectedBatch.size());
    for (MigratingVm mv : selectedBatch) {
        batchVmIndices.add(mv.getVm().getIndex());
    }

    // 3. Build child: positions from parentA if VM is in selected batch, null otherwise
    MigratingVm[] child = new MigratingVm[length];
    for (int i = 0; i < length; i++) {
        MigratingVm mv = parentA.migratingVms[i];
        if (batchVmIndices.contains(mv.getVm().getIndex())) {
            child[i] = mv;  // preserve parentA's position for batch members
        }
        // else: slot left null, to be filled from parentB
    }

    // 4. Fill null slots in child order with parentB's ordering (skip batch members)
    int writePos = 0;
    for (int i = 0; i < length; i++) {
        // Advance write cursor to next null slot
        while (writePos < length && child[writePos] != null) writePos++;
        MigratingVm mv = parentB.migratingVms[i];
        if (!batchVmIndices.contains(mv.getVm().getIndex())) {
            child[writePos] = mv;
        }
    }
    return child;
}
```

**Semantic insight:** This crossover tries to preserve the **co-scheduling structure** of one parent's batch. If parentA found that VMs `{v1, v3, v7}` can safely execute in the same parallel step, the child inherits that group intact and fills the surrounding ordering from parentB. This is semantically richer than OX, which treats all positions symmetrically — here, the "gene" being preserved is a *feasible batch*, not a positional ordering.

#### Full Genetic Algorithm Structure

```
Initialize population:
  Generate N random permutations of the migrating VMs → N individuals

For each generation:
  Evaluate fitness:
    For each individual (permutation):
      Run SequenceBatchingSolver → Solution with steps
      fitness = hierarchical objective [numSteps, lastBatchSize, migrationCost]
      (fewer steps = better; among ties, smaller last batch = better)

  Select parents:
    Tournament or roulette selection weighted by fitness

  Crossover:
    Batch-preservation crossover (see above)

  Mutate:
    Random swap of two positions in the permutation

  Replace:
    New population from offspring + elitism (keep best individual unchanged)

Return best permutation found → run SequenceBatchingSolver → final Solution
```

### 7.9 Greedy Batching Solver

Sorts migrations by a priority heuristic (e.g., by VM size or source host load) and runs the Sequence solver. Simple and fast; does not explore the ordering space.

### 7.10 One Full ALNS Iteration — Step-by-Step

Here is the complete walkthrough of one iteration of ALNS, showing how all five layers interact. This reflects the actual source code verified in the gap analysis.

```
Suppose: hostA is selected for ruin; VM v is among its migratable VMs

STEP 0 — COPY-ON-WRITE
  newSolution ← new MigrationSolution(solution)  // deep copy; original NEVER mutated
  // From here, all ruin/recreate operations mutate ONLY newSolution

STEP 1 — GUIDED RUIN (per-VM, constraint-checked)
  For each host in ruinHosts:
    Sort migratable VMs by vmSorterType (already-moved VMs first)
    For each VM v on that host:
      ruinDelta = new RuinDelta(new Vm[] {v})     // single-VM array
      IF NOT constraint.satisfy(problem, newSolution, ruinDelta): skip v
      marginalCost = objective.calculate(problem, newSolution, ruinDelta).compareToZero()
      ruinDelta.update(problem, newSolution)       // apply AFTER checking
      ruinVms.add(v)
      IF marginalCost < 0:                         // found improving removal!
        improved = true
        break                                       // stop this host's VMs

  IF NOT improved: return null → skip entire ALNS iteration (continue)

  Variable state after ruin (in newSolution only):
  CpuMemVariable:
    numaCpu[hostA][numa0] -= v.numaCpu
    numaMem[hostA][numa0] -= v.numaMem
  EmptyHostVariable: check if hostA is now empty
  HostVmsVariable: v removed from hostA's VM list

STEP 2 — RECREATE (for VM v → hostB)
  Sort ruinVms by vmSorterType (reversed → largest first)
  For each vm in ruinVms:
    // getBestRecreate: three-phase placement search
    // Phase 1: Try initial placement ("stay home" if non-worsening)
    // Phase 2: Scan candidates with early exit on non-worsening
    // Phase 3: If all worsening, pick least-bad
    RecreateDelta = { vm: v, placement: Placement(hostB_numas) }

    Variable updates (in newSolution):
    CpuMemVariable.update(problem, newSolution, recreateDelta):
      numaCpu[hostB][numa1] += v.numaCpu
      numaMem[hostB][numa1] += v.numaMem
    HostVmsVariable: add v to hostB's VM list
    EmptyHostVariable: if hostB was empty, decrement emptyCount

    Constraint check (O(1) — reads pre-updated Variables):
    CpuMemConstraint: numaCpu[hostB][numa1] ≤ hostB_numa1.cpu ? ✓
    AntiAffinityConstraint: v's group still spans distinct hosts? ✓

    recreateDelta.update(problem, newSolution)  // commit placement

STEP 3 — OBJECTIVE EVALUATION (O(1))
  newValue ← objective.calculate(problem, newSolution)
  If useChainOptimizer: newValue ← optimizeChain(...)
  → e.g., ListValue [-3, 0.08]  (lower is better; -3 = 3 empty hosts)

STEP 4 — GLOBAL BEST CHECK (independent of acceptance)
  bestValue was [-2, 0.15]
  newValue [-3, 0.08] < bestValue [-2, 0.15] → NEW GLOBAL BEST
  bestSolution ← MigrationSolution(newSolution, false)  // shallow copy
  stagnationSteps ← 0                                    // reset
  adaptiveMaintainer.updateWeights(ruinHosts.size(), vmSorterType,
                                   hostSorterType, recreateType, 1.0)

STEP 5 — ACCEPT / REJECT (Late Acceptance Hill Climbing)
  oldValue (current working): [-2, 0.15]
  history[position]:          [-2, 0.18]
  newValue:                   [-3, 0.08]
  newValue ≤ oldValue (LAHC condition 1) → ACCEPT
  solution ← newSolution    // adopt the candidate as working solution
  value ← newValue

  LAHC rejection case (if newValue had been [-1, 0.20]):
    newValue > oldValue AND newValue > history[position] → REJECT
    newSolution is simply discarded (garbage collected)
    solution remains untouched (copy-on-write protection)
```

---

## 8. Hotspot Mitigation Module

The Hotspot Mitigation module is a **fully self-contained optimization subsystem** that mirrors the main framework's architecture — it has its own model, variable, constraint, objective, algorithm, and API layers. It is triggered reactively (by monitoring alerts) and operates independently from the main consolidation run. Critically, it handles **two distinct hotspot types** through separate solver paths: host-level CPU/load hotspots and rack-level power hotspots.

### 8.1 Architecture: A Framework Within a Framework

The module reuses the same Variable→Constraint→Objective→Algorithm layered design as the core, but with a **narrower scope**: it only considers hotspot hosts as migration *sources* and a set of viable candidate hosts as migration *targets*. This scoping is what makes the module fast enough to run reactively.

```
mitigation/
 ├── api/          HostHotspotSolver, RackHotspotSolver        ← entry points
 ├── imp/          HostHotspotSolverFactory, HotspotMitigationSolver  ← coordination
 ├── model/        HotspotProblem, MitigationLevel, SolverConfig       ← data
 ├── algorithm/    TwoStageHotspotMitigationSolver, GreedySolver,      ← search
 │                 SimpleRackHotspotMitigationSolver,
 │                 robust/ (RobustKnapsackSolver: QUEX_GREEDY/DROPOUT/FULL)
 ├── constraint/   4 mitigation-specific constraints                   ← feasibility
 ├── objective/    5 mitigation-specific objectives                    ← quality
 ├── variable/     6 mitigation-specific variables                     ← state
 └── utils/        HostHotspotMitigationProtoHelper, HotspotTypeUtil   ← helpers
```

### 8.2 Hotspot Types and Strategy Selection

The system handles multiple hotspot types defined by the protobuf API:

| Hotspot Type | Entry Point | Primary Solver | Primary Concern |
|---|---|---|---|
| **Storage** | `HostHotspotSolver` | `TwoStageHotspotMitigationSolver` or `HOTSPOT_SEPARATION` | Isolate high-load storage VMs or relieve storage QoS |
| **CPU / Load** | `HostHotspotSolver` | `TwoStageHotspotMitigationSolver` | Migrate VMs off overloaded hosts |
| **Rack Power** | `RackHotspotSolver` | `SimpleRackHotspotMitigationSolver` | Reduce total rack power draw |

**`HotspotMigrationStrategy`** — The strategy enum (not a class with `if/else`) selects between two execution modes. For storage hotspots, it first checks whether any VM's load exceeds a QoS separation threshold — if so, it selects `HOTSPOT_SEPARATION` (isolate that VM) rather than generic migration:

```java
// HotspotMigrationStrategy.java — actual implementation
public static HotspotMigrationStrategy getStrategy(Request request,
                                                    HotspotProblem hotspotProblem) {
    // Storage hotspots get special handling for extremely high-load VMs
    if (hotspotProblem.getHotspotType() == HostHotSpotMitigationProto.HotspotType.Storage) {
        double hostStorageLimit = request
            .getHosts(hotspotProblem.getHotspotHost().getIndex())
            .getQosConf()
            .getStorageLimit();

        // STORAGE_QOS_SEPARATION_THRESHOLD = 0.7d (confirmed, Constants.java — hardcoded, not configurable)
        double highLoadThreshold = hostStorageLimit * STORAGE_QOS_SEPARATION_THRESHOLD;
        // → triggers HOTSPOT_SEPARATION when VM's maxLoad > 70% of the host's storage QoS limit

### 8.3 Model Layer — `HotspotProblem`, `MitigationLevel`, `SolverConfig`

**`HotspotProblem`** extends the base `Problem` with hotspot-specific metadata: the identified hotspot host (source), candidate target hosts, rack power topology, and VM load ranges (centre + uncertainty radius for robust optimisation). This scoped problem is what gets passed into the mitigation solvers — they never see the entire cluster.

**`MitigationLevel`** controls the **granularity of resource accounting** during mitigation — not intensity or aggressiveness. The three levels correspond to the three tiers of the physical resource hierarchy:

```java
// MitigationLevel.java — actual implementation
public enum MitigationLevel {
    MITIGATE_BY_HOST,       // Account for resources at host level
    MITIGATE_BY_NUMA_GROUP, // Account for resources at NUMA group level
    MITIGATE_BY_NUMA        // Account for resources at individual NUMA node level
}
```

A higher granularity level (`MITIGATE_BY_NUMA`) means the solver considers per-socket load when selecting migration targets — more accurate but requiring more variable state. `MITIGATE_BY_HOST` is faster and sufficient when the hotspot is a general CPU overload that spans all sockets equally.

**`SolverConfig`** wraps per-run parameters that drive solver behaviour:
```java
public class SolverConfig {
    private long timeLimitMs;           // search time budget
    private int maxMigrations;          // upper bound on total VM moves
    private MitigationLevel level;      // resource accounting granularity
    // ... additional fields
}
```

### 8.4 Variable Layer — Target-Focused State Tracking

A key design insight: hotspot mitigation variables track **target** host state, not all hosts. This is because the algorithm needs to reason about where VMs can land safely, not about the full cluster state.

| Variable (actual file) | What it tracks |
|---|---|
| `HostHotspotVmNumVariable.java` | Number of VMs still remaining on hotspot (source) hosts — the primary progress metric |
| `RackPowerUsageMigrationVariable.java` | Current power consumption per rack — drives rack hotspot objectives |
| `TargetHostLoadVariable.java` | CPU/load on each candidate *target* host after hypothetical placements |
| `TargetNumaGroupLoadVariable.java` | Load on NUMA groups within target hosts |
| `TargetNumaLoadVariable.java` | Per-socket load on target hosts (NUMA-level granularity) |
| `TargetProviderLoadVariable.java` | Aggregate load across the full target provider (host) |

The distinction between `TargetHostLoadVariable`, `TargetNumaGroupLoadVariable`, and `TargetNumaLoadVariable` reflects the three-tier resource hierarchy within a host. The algorithm needs all three to make NUMA-aware placement decisions on targets.

### 8.5 Constraint Layer — Migration Safety on Targets

Four constraints govern where VMs can land during hotspot mitigation:

**`MigrateToEmptyHostConstraint`** — The most aggressive form of consolidation: a VM may only be placed on a host that is currently **empty**. This ensures hotspot mitigation does not create new hotspots on already-loaded targets.

**`RackPowerLimitMigrationConstraint`** — After placing a VM on a target, the target rack's total power consumption must not exceed its configured power cap. This prevents the rack hotspot from simply moving to the target rack.
```java
// After placing vm on targetHost:
float newRackPower = rackPowerVariable.getRackPower(targetHost.getRack());
return newRackPower <= rackPowerLimit;
```

**`TargetHostCpuAllocationThresholdConstraint`** — The target host's CPU allocation (committed vCPU) must remain below a configured ceiling after the placement. This is a capacity buffer constraint, not a utilization constraint — it ensures the target has headroom for burst workloads.

**`TargetNumaCpuLoadThresholdConstraint`** — The actual CPU *load* (current utilization, not just allocated capacity) on the specific target NUMA node must stay below a threshold. This prevents placing a VM onto a NUMA socket that is already heavily loaded even if its allocation headroom appears sufficient.

The combination of an *allocation* threshold and a *load* threshold on the target is a deliberate defense-in-depth: allocated capacity may differ significantly from actual utilization in cloud environments (VMs often consume less than their reserved CPU).

### 8.6 Objective Layer — Five Mitigation-Specific Objectives

Unlike the main framework's consolidation objectives (maximize empty hosts, minimize migration cost), hotspot mitigation objectives are tuned to **relieve overload** while **not degrading target quality**:

**`MinVmNumOnHotspotProvidersObjective`** — Primary driver: minimize the number of VMs remaining on the hotspot hosts. The fewer VMs left, the more the hotspot is relieved.
```java
// HostHotspotVmNumVariable tracks this directly
return IntValue.of(hostHotspotVmNumVariable.getTotalVmsOnHotspots());
```

**`MaxTargetHostUnusedResourceObjective`** — Maximize the remaining free resources on target hosts after migration. This is an anti-packing objective: it pushes the algorithm toward spreading VMs across multiple targets rather than cramming them onto one.

**`MinTargetProviderMaxLoadObjective`** — Minimize the maximum load across all target hosts (minimax objective). Prevents the mitigation from creating a new hotspot by overloading the best target.

**`MinHotspotRackOverusedPowerMigrationObjective`** — Minimize the total power exceeding the rack limit across all hotspot racks. Used specifically in rack hotspot mitigation scenarios.

**`RackPowerUsageVarianceMigrationObjective`** — Minimize the variance in power usage across racks. Drives toward an even power distribution across the physical infrastructure rather than just fixing the worst-offending rack.

### 8.7 Algorithm Layer — Two-Stage Hotspot Mitigation

**`TwoStageHotspotMitigationSolver`** — The primary solver for host hotspots. It follows the same two-stage pattern as the main framework:

```
Stage 1 — Migration Phase (which VMs move where):
  Input:  HotspotProblem (scoped to hotspot host + target hosts)
  Goal:   Minimize VMs remaining on hotspot host
          while satisfying target host load/allocation constraints
  Algorithms:
    - GreedySolver: fast deterministic baseline
    - robust/ (RobustKnapsackSolver): mathematically optimal subset selection
      using Bertsimas & Sim robust optimisation with three solver variants:
        QUEX_GREEDY  → greedy knapsack
        QUEX_DROPOUT → greedy + dropout search
        QUEX_FULL    → greedy + dropout + exhaustive core (size 10)
      The robust solver guarantees load reduction holds under load uncertainty.

Stage 2 — Batching Phase:
  Algorithm: SimpleSequenceBatchingSolver (see below)
```

**`SimpleSequenceBatchingSolver` — Full Source**

Unlike the main framework's `GeneticBatchingSolver` (which evolves permutations) or `SccBatchingSolver` (which decomposes dependency graphs), `SimpleSequenceBatchingSolver` runs a **time-bounded iterative migration loop**. It does not search for an optimal ordering — instead, it repeatedly attempts all pending migrations in one pass and commits any that are currently feasible, then advances a step boundary for those that blocked each other. This is appropriate for hotspot mitigation because the migration count is small (typically 1–5 VMs) and dependency cycles are rare.

```java
// SimpleSequenceBatchingSolver.java — actual implementation
public class SimpleSequenceBatchingSolver implements SequenceBatchingSolver {

    private Duration timeLimit = Duration.ofSeconds(2);  // hard wall-clock limit

    @Override
    public Solution solve(Problem problem, Solution initialSolution,
                          MigratingVm[] migratingVms, Instant endTime) {
        Instant solveEndTime = Instant.now().plus(timeLimit);
        Solution solution = new Solution(initialSolution);

        // All pending migrations — VMs not yet at their target placement
        List<MigratingVm> lastMigrations = new ObjectArrayList<>(migratingVms);

        while (!lastMigrations.isEmpty() && Instant.now().isBefore(solveEndTime)) {

            // PASS: attempt every pending migration; commit those that are feasible now
            tryAndMigrate(problem, solution, lastMigrations);

            // If all pending VMs have reached their target: done
            if (solution.getMigratingVms().isEmpty()) break;

            // STEP BOUNDARY: the migrations that couldn't run go into the next step
            StepDelta stepDelta = new StepDelta(solution.getMigratingVms());
            stepDelta.update(problem, solution);

            // Remove VMs that successfully reached their target placement
            lastMigrations.removeIf(
                migratingVm -> solution.getPlacement(migratingVm.getVm())
                               == migratingVm.getPlacement());
        }
        return solution;
    }

    /**
     * One pass over all pending migrations.
     * For each VM: create a MigrateDelta, check both migration AND batching constraints.
     * If both satisfied: commit the delta (VM moves to its target placement in this step).
     * If not: leave the VM in lastMigrations for the next step.
     */
    private void tryAndMigrate(Problem problem, Solution solution,
                                List<MigratingVm> migratingVms) {
        for (MigratingVm migratingVm : migratingVms) {
            MigrateDelta delta = new MigrateDelta(solution, migratingVm, true);
            if (problem.getMigrationConstraint().satisfy(problem, solution, delta)
                    && problem.getBatchingConstraint().satisfy(problem, solution, delta)) {
                delta.update(problem, solution);  // commit: VM migrates in this step
            }
            // else: VM stays blocked, will be retried in next iteration
        }
    }
}
```

**Behavioural analysis:** Each outer `while` loop iteration corresponds to one **migration step** (a set of concurrent migrations). Within `tryAndMigrate`, VMs are attempted in input order, and a VM is committed the moment its constraints are satisfied — which may immediately free up resources for the next VM in the same pass. This means the within-step ordering is greedy and order-dependent.

The 2-second `timeLimit` is a safety valve: if migrations remain blocked after many iterations (e.g., an unresolvable dependency cycle that would require SCC logic), the solver exits rather than looping indefinitely. This is a key difference from the main framework's `SccBatchingSolver`, which guarantees resolution of cycles via trampoline hosts.

**`HotspotMigrationStrategy`** — Selects between `HOTSPOT_MITIGATION` (standard multi-VM migration via the two-stage solver) and `HOTSPOT_SEPARATION` (single-VM isolation for extreme storage QoS outliers). See Section 8.2 for the actual branching logic with code.

**`SimpleRackHotspotMitigationSolver`** — Dedicated to rack power hotspots. Its objective is not to empty hosts but to bring total rack power consumption below the rack power cap. It may move VMs between racks without emptying any individual host, guided by `RackPowerUsageMigrationVariable` and `MinHotspotRackOverusedPowerMigrationObjective`.

**`DataProcess.java`** — Preprocesses raw protobuf monitoring data before handing it to the solver: filters non-migratable VMs, identifies valid target hosts, computes VM load ranges (centre + radius for robust optimisation), and constructs the `HotspotProblem`. Scope control here is critical — a poorly scoped problem (too many candidates) would negate the performance advantage of the lightweight hotspot-specific solvers.

### 8.8 API Layer and Factory

**`HostHotspotSolver`** and **`RackHotspotSolver`** are the public entry points. External monitoring systems (or the main scheduler) call these interfaces with raw protobuf input describing the overload situation. They delegate construction of the `HotspotProblem` to `DataProcess`, solver selection to `HotspotMigrationStrategy`, and solver creation to `HostHotspotSolverFactory`.

**`HostHotspotSolverFactory`** creates the correct `HotspotMitigationSolver` instance based on `MitigationConfig` and `MitigationLevel`. This is the **Factory pattern** applied to solver construction — the caller doesn't need to know which solver implementation will be used.

**`HostHotspotMitigationProtoHelper`** handles Protobuf serialization/deserialization, converting between the external wire format and the internal `HotspotProblem` / `Solution` objects.

### 8.9 Full Mitigation Flow

```
EXTERNAL TRIGGER (monitoring alert: host H has CPU > threshold)
        │
        ▼
HostHotspotSolver.solve(protoRequest)
        │
        ├─► HostHotspotMitigationProtoHelper.deserialize()
        │       → raw monitoring data → structured input
        │
        ├─► DataProcess.process()
        │       → identify hotspot hosts (sources)
        │       → identify candidate target hosts
        │       → filter non-migratable VMs
        │       → build HotspotProblem (scoped sub-problem)
        │
        ├─► HotspotTypeUtil.classify(hotspotProblem)
        │       → HOST_CPU_HOTSPOT or RACK_POWER_HOTSPOT
        │
        ├─► HotspotMigrationStrategy.selectSolver()
        │       → TwoStageHotspotMitigationSolver (CPU)
        │       → SimpleRackHotspotMitigationSolver (power)
        │
        ├─► Register Variables:
        │     HostHotspotVmNumVariable, TargetHostLoadVariable,
        │     TargetNumaLoadVariable, RackPowerUsageMigrationVariable, ...
        │
        ├─► Register Constraints:
        │     TargetHostCpuAllocationThresholdConstraint,
        │     TargetNumaCpuLoadThresholdConstraint,
        │     RackPowerLimitMigrationConstraint, ...
        │
        ├─► Register Objectives:
        │     MinVmNumOnHotspotProvidersObjective (primary),
        │     MaxTargetHostUnusedResourceObjective (secondary),
        │     MinTargetProviderMaxLoadObjective (secondary), ...
        │
        ├─► TwoStageHotspotMitigationSolver.solve(hotspotProblem)
        │     Stage 1: GreedySolver → migration plan
        │     Stage 2: SimpleSequenceBatchingSolver → ordered steps
        │
        └─► HostHotspotMitigationProtoHelper.serialize(solution)
                → protobuf response: migration steps to execute
```

---

## 9. Design Patterns and Engineering Principles

### 9.1 Composite / Hierarchical Pattern

Used in both the constraint and objective layers. Multiple instances are composed into a single root that behaves identically to a single instance.

```
HierarchicalMigrationConstraint
    ├── CpuMemMigrationConstraint
    ├── AntiAffinityMigrationConstraint
    └── BudgetLimitMigrationConstraint

HierarchicalMigrationObjective
    ├── EmptyHostMigrationObjective    (primary)
    ├── MinLoadBalancingObjective      (primary)
    └── MigrationCostMigrationObjective (minor/lazy)
```

The algorithm interacts only with the root composite — it doesn't know how many individual constraints or objectives exist.

### 9.2 Strategy Pattern

The Strategy pattern appears at two levels in the codebase.

**Level 1 — Main framework:** Solvers are interchangeable behind a common interface. The `TwoStageSolver` is parameterized at construction time with any `MigrationSolver` and `BatchingSolver` implementation:

```java
// Swap ALNS for Greedy without changing any other code
MigrationSolver solver = new GreedyMigrationSolver();
// or
MigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, random);

TwoStageSolver twoStage = new TwoStageSolver(solver, batchingSolver);
```

**Level 2 — Hotspot mitigation:** `HotspotMigrationStrategy` is an enum with a static factory method that selects the execution mode based on hotspot type and VM load characteristics. The coordinator (`HotspotMitigationSolver`) calls `getStrategy()` and gets back an enum constant that drives the solver dispatch:

```java
// HotspotMigrationStrategy.java — enum-based strategy selection
public static HotspotMigrationStrategy getStrategy(Request request,
                                                    HotspotProblem hotspotProblem) {
    if (hotspotProblem.getHotspotType() == HostHotSpotMitigationProto.HotspotType.Storage) {
        double hostStorageLimit = request
            .getHosts(hotspotProblem.getHotspotHost().getIndex())
            .getQosConf().getStorageLimit();
        double highLoadThreshold = hostStorageLimit * STORAGE_QOS_SEPARATION_THRESHOLD;
        // STORAGE_QOS_SEPARATION_THRESHOLD = 0.7d (Constants.java — hardcoded)
            }
        }
    }
    return HOTSPOT_MITIGATION;  // Standard multi-VM migration
}
```

The enum has two constants: `HOTSPOT_SEPARATION` (isolate one extreme VM) and `HOTSPOT_MITIGATION` (migrate multiple VMs to relieve load). Adding a new hotspot mode requires adding one enum constant, one `getStrategy()` branch, and a corresponding solver — zero changes to existing code.

### 9.3 Observer / Delta Pattern

When the solution changes (a VM moves), a `Delta` object is created and self-applied. The `update()` method on the delta propagates changes to all registered Variables:

```java
// Delta is self-applying — update() commits the change and updates all variables
RecreateDelta delta = new RecreateDelta(vm, targetPlacement);
// First, use projection to check feasibility and evaluate objective:
boolean feasible = constraint.satisfy(problem, solution, delta);   // no state change
Value cost = objective.calculate(problem, solution, delta);         // no state change
// Then, commit the delta — this updates all registered variables incrementally:
delta.update(problem, solution);
// Constraints and objectives now read the fresh state
```

The key distinction is between **projection** (constraint/objective methods that take a delta parameter evaluate it without mutating the solution) and **application** (`delta.update()` which commits the change). This allows evaluating hundreds of candidate placements cheaply before committing the winner.

### 9.4 Factory / Registry Pattern

Variables are created via factory functions and stored in a registry (the solution's variable array). The `Fetcher` is a lightweight proxy that knows the index of its variable in the array:

```java
// Registration time: factory is stored, index is assigned
MigrationFetcher<CpuMemMigrationVariable> fetcher =
    problem.addMigrationVariable(CpuMemMigrationVariable::new);
// Internally: fetcher = index -> solution.variables[index]

// Retrieval time: O(1) array lookup
CpuMemMigrationVariable variable = fetcher.fetch(solution);
```

This pattern allows new variable types to be added without modifying `Solution` or any existing class — the registry grows dynamically.

### 9.5 Template Method Pattern

The abstract `CompositeMigrationObjective` defines the structural algorithm for combining multiple sub-objectives, with concrete subclasses providing the combination logic (lexicographic, weighted, etc.):

```java
public abstract class CompositeMigrationObjective<T extends Value, S extends Value>
    implements MigrationObjective<T> {

    protected abstract T calculate(
        MigrationSolution solution,
        Function<MigrationObjective<? extends S>, S> evaluator  // injected evaluation strategy
    );
}
```

---

## 10. ROADEF 2012 vs. Server Consolidation V2 — Full Mapping

| Dimension | ROADEF 2012 | Server Consolidation V2 |
|-----------|------------|------------------------|
| **Decision variable** | $M: P \rightarrow \mathcal{M}$ (process → machine) | `VM → Placement(Host, NumaGroup, Numa[])` |
| **Resource model** | Flat: one capacity per resource per machine | Hierarchical: NUMA-level CPU + Memory within hosts |
| **Capacity constraint** | $U(m,r) \leq C(m,r)$ | `CpuMemMigrationConstraint` at NUMA level |
| **Conflict / anti-affinity** | Service: processes on distinct machines | `AntiAffinityMigrationConstraint` |
| **Spread / location** | Min locations per service | Fault domain + rack constraints |
| **Dependency / neighborhood** | Service dependency graph | Centralized scheduling traits |
| **Transient usage** | Static capacity on both endpoints | Handled dynamically by batching phase |
| **Objective structure** | Single weighted sum (minimize) | Lexicographic hierarchy (maximize empty hosts first) |
| **Execution sequencing** | None (static assignment only) | Full batching phase (Steps, concurrency limits) |
| **Circular dependencies** | Not modeled | SCC Batching Solver |
| **Primary algorithm** | Varies by competitor (ALNS won) | ALNS (ruin-recreate + Late Acceptance Hill Climbing) |
| **Incremental evaluation** | Competitor-specific | First-class framework feature (Variable layer) |
| **Business constraints** | Minimal | Prefer-flavor protection, tenant limits, EVACUATION, hotspot mitigation |
| **Problem scale** | Up to 50,000 processes, 5,000 machines | Tens of thousands of VMs, hundreds of hosts |

---

## 11. Supporting Modules

### Evaluation Module

Compares solution quality across different algorithm configurations and instances. Used for benchmarking and regression testing.

```java
// Compare two solutions on the same problem
EvaluationResult result = evaluator.compare(solutionA, solutionB, problem);
result.getObjectiveDiff();    // difference in objective value
result.getConstraintStatus(); // both feasible?
result.getPerformanceMetrics(); // solve time, iterations, etc.
```

### Batch Tester

Runs the solver against a collection of problem instances (a test suite) and aggregates results. Detects regressions when algorithm changes affect solution quality across the instance distribution.

```java
BatchTester tester = new BatchTester(solver, testInstances);
BatchResult results = tester.run();
results.getPassRate();        // fraction of instances solved feasibly
results.getAverageObjective(); // mean objective value across instances
results.getWorstCase();        // most difficult instance
```

### Visualization Module

Tracks objective value over algorithm iterations to diagnose convergence behavior, detect premature convergence, and tune parameters.

```
Iteration 0:    objective = [0 empty hosts, variance=0.45]
Iteration 100:  objective = [2 empty hosts, variance=0.31]
Iteration 500:  objective = [4 empty hosts, variance=0.18]
Iteration 1000: objective = [5 empty hosts, variance=0.12]  ← plateaus
```

---

## 12. Frequently Asked Questions (FAQ)

---

### General Understanding

**Q: What is the one true decision variable in this system?**

A: There is exactly one: the mapping from every VM to a `Placement` (host + NUMA group + NUMA nodes). This is stored in `MigrationSolution` as a `Placement[]` array indexed by `vm.getIndex()`. Everything else — variables, constraints, objectives — exists to evaluate whether a given assignment is feasible and how good it is. The algorithm's entire job is to find the best values for this array.

---

**Q: If the "Variables" in the Variable layer are not the decision variable, what are they?**

A: They are **precomputed, incrementally-maintained aggregate statistics** derived from the current solution (the decision variable). For example, `CpuMemMigrationVariable` maintains a 2D array `numaCpu[hostIndex][numaIndex]` that always reflects the current total CPU consumption at each NUMA node. When the algorithm moves a VM, these arrays are updated in O(1) instead of recomputing from scratch in O(n). They exist purely for performance — without them, constraint checking and objective evaluation would be too slow for real-time metaheuristic search.

---

**Q: Why does the framework use a lexicographic objective hierarchy instead of a weighted sum?**

A: The weighted sum approach (as in ROADEF) requires careful manual tuning of weights. A poor choice can make one objective so dominant that the others are irrelevant. More importantly, it conflates objectives with different units and scales into a single number, making the optimization opaque. The lexicographic approach makes the priority order explicit and transparent: maximize empty hosts first, then resolve ties with load balancing, then migration cost. No tuning is needed, and the business priority is directly encoded in the objective structure.

---

**Q: How does the ROADEF "transient usage constraint" map to this system?**

A: ROADEF models transient usage as a static constraint: during the migration of process p, both the source and destination machine simultaneously hold p's disk capacity. Server Consolidation V2 handles this differently through the **batching phase**: the `SccBatchingSolver` explicitly computes migration dependencies (including circular ones) and sequences batches so that a destination host is freed before a new VM arrives. The `DegreeBatchingConstraint` further limits how many simultaneous migrations per host can proceed, bounding the transient resource spike.

---

### Algorithm Questions

**Q: Why is ALNS the primary algorithm? Why not an exact solver (e.g., ILP)?**

A: The problem is NP-hard with a search space of size $|\text{Placements}|^{|\text{VMs}|}$. At production cloud scale (10,000+ VMs, 500+ hosts), exact solvers (Integer Linear Programming, Branch-and-Bound) cannot find solutions within operationally acceptable time limits — even state-of-the-art ILP solvers like Gurobi struggle beyond a few hundred variables for this problem class. ALNS is designed precisely for this: it explores the space efficiently using ruin-and-recreate operators, uses Late Acceptance Hill Climbing (LAHC) to accept occasional non-improving solutions to escape local optima, and produces high-quality solutions within a fixed time budget. The ROADEF 2012 challenge — the benchmark problem for this class — was won by ALNS-based approaches.

---

**Q: What is the difference between the Migration Phase and the Batching Phase?**

A: The Migration Phase answers "**where** should each VM end up?" It produces a target placement for every VM — the final steady-state configuration. The Batching Phase answers "**how** do we get there?" It organizes the required VM migrations into sequential rounds (batches), ensuring that at each round the system remains feasible (no host is overloaded mid-migration, no anti-affinity is temporarily violated, concurrency limits are respected). Without the batching phase, you would know the destination but not the safe route.

---

**Q: What happens when migrations form circular dependencies?**

A: VM A wants to move to host X, but VM B currently occupies a slot on host X and needs to move to host Y first. And VM C needs to move to host Y's previous slot... forming a cycle. The `SccBatchingSolver` uses Tarjan's algorithm for Strongly Connected Components to detect these cycles. Within an SCC, one migration must be resolved using a temporary intermediate placement (a "trampoline host") to break the cycle. The remaining migrations in the SCC can then proceed in topological order.

---

**Q: When should I use Greedy vs. ALNS?**

A: `GreedyMigrationSolver` is a deterministic solver that evaluates each VM and moves it to the best available host, iterating until no further improvement is found. It is fast and deterministic but susceptible to local optima — it can never accept a worse move to escape a dead end. ALNS is more general: it simultaneously optimizes all objectives in the lexicographic hierarchy, uses a guided ruin-and-recreate approach that can escape local optima via LAHC acceptance of non-improving moves, and adapts its operator selection based on what has worked historically. However, ALNS is stochastic and takes longer (bounded by its `maxSteps`, `maxStagnationSteps`, and `timeLimit` parameters — defaulting to 50,000 iterations, 500 stagnation steps, and 5 seconds respectively). For production use, ALNS is the primary solver for large-scale problems.

---

### Design and Engineering Questions

**Q: Why are constraints and objectives not allowed to compute their own state?**

A: This is the core of the "decoupling" architecture. If `CpuMemMigrationConstraint` computed CPU usage itself, it would need to scan all VMs every time it's called — O(n) per check, called millions of times during ALNS. By delegating all state computation to the Variable layer and reading precomputed values, each check becomes O(1). Additionally, if two constraints both needed CPU usage, they would each recompute it independently. With shared Variables, computation happens once and is read by as many consumers as needed.

---

**Q: Why use a Fetcher pattern rather than direct field access on Solution?**

A: Direct field access (e.g., `solution.getCpuMemVariable()`) would require `Solution` to have a field for every possible variable type. This creates a dependency from the core data structure to every specific variable implementation, making the codebase monolithic. With the Fetcher/Registry pattern, `Solution` only stores a generic array `MigrationVariable[]`. New variable types can be added, removed, or modified without changing `Solution` at all — they just register at problem-build time and get assigned an array slot. The fetcher is a statically-typed wrapper around the array index.

---

**Q: How does the framework handle NUMA-aware placement? Why is it more complex than flat capacity?**

A: In ROADEF, a machine has one capacity value per resource. In this framework, a host has multiple NUMA nodes (sockets), each with its own CPU and memory. A VM must be placed not just on a host, but on specific NUMA nodes within that host. A multi-NUMA VM (e.g., a large-memory VM spanning two sockets) must have its resources split evenly across its assigned NUMA nodes. This adds a second tier of bin-packing: you must find a host with a valid NUMA node (or pair of NUMA nodes) that can accommodate the VM's per-socket demand — not just the host's aggregate. The `CpuMemMigrationVariable` tracks this as a 2D array `[hostIndex][numaIndex]` precisely to support this granularity.

---

**Q: How does the framework support extension with new algorithms or constraints?**

A: The framework is entirely interface-driven:
- New **constraint**: implement `MigrationConstraint`, add to `HierarchicalMigrationConstraint.builder()`
- New **objective**: implement `MigrationObjective<T>`, add to `HierarchicalMigrationObjective.builder()`
- New **variable**: implement `MigrationVariable`, register via `problem.addMigrationVariable(...)`
- New **algorithm**: implement `MigrationSolver` or `BatchingSolver`, pass to `TwoStageSolver`

No existing class needs to be modified. The Composite pattern (hierarchical constraints/objectives) absorbs new components transparently. The Fetcher/Registry pattern absorbs new variables transparently.

---

### Performance Questions

**Q: What is the computational complexity of one ALNS iteration?**

A: With the incremental Variable layer and the guided ruin mechanism:
- **Copy-on-write:** O(V × S) where V is the number of registered variables and S is the per-variable state size (variable.copy())
- **Ruin (guided, per-VM):** For each VM v on each ruin host: O(1) constraint projection + O(1) objective projection + O(V) variable update. Total: O(k × V) where k is the number of VMs processed across ruin hosts. Early exit on first improving removal.
- **Recreate (per VM):** O(P) where P is the number of candidate placements — each evaluated with O(1) constraint and objective projection. For `BEST` mode, early exit on first non-worsening placement. For `RANDOM`/`FirstFit`, first feasible only.
- **Variable update after recreate:** O(V) per variable per VM placed
- **Total per iteration:** O(V × S + k × (P + V)) — dominated by the candidate placement scan

Without the Variable layer (naïve), constraint checking alone would be O(N) per check where N is the total VM count — orders of magnitude slower. The guided ruin additionally saves entire iterations: if no improving removal is found, the iteration is skipped entirely (`continue`).

---

**Q: The framework has both `copy()` on variables and full recompute. When is each used?**

A: The ALNS solver uses a **copy-on-write forward** pattern rather than snapshot-and-rollback. Before each iteration, a deep copy is made: `new MigrationSolution(solution)` creates a full working copy including deep-copied variables (`variable.copy()` on each registered variable). All ruin/recreate mutations happen exclusively on the working copy. If the iteration is rejected, the working copy is simply discarded — the original `solution` was never touched, so no rollback is needed.

For the global best solution, a shallow copy is used: `new MigrationSolution(newSolution, false)` copies only the placement array, skipping the expensive variable deep-copy. When the solver returns its final answer, `bestSolution.updateMigrationVariables(problem)` does a full O(n) recompute of all variables from scratch. This optimization is safe because the best solution only needs correct placements until final return — the variables are not consulted until after recomputation.

---

**Q: What is typical solve time for production-scale problems?**

A: The ALNS solver has a confirmed default `timeLimit` of **5 seconds**, `maxSteps` of 50,000 iterations, and `maxStagnationSteps` of 500. The solver terminates when *any* of these three conditions is met. This configuration is designed for production speed — the solver typically converges well within the time budget for most problem sizes. For hotspot mitigation scenarios, the `SimpleSequenceBatchingSolver` has an even shorter 2-second time limit. All limits are configurable via Lombok `@Setter` annotations, so they can be adjusted for different deployment contexts.

---

**Q: Can the solver be used incrementally — i.e., re-optimized as the cluster changes?**

A: Yes. The `solve(problem, referenceProblem)` overload supports this. The reference problem represents the cluster's last known good state. The solver uses it to initialize the solution (rather than starting cold) and can bias toward solutions that minimize deviation from the reference — useful for real-time operation where the cluster is constantly changing and migration plans should be stable across re-solves.

---

*End of Document*
