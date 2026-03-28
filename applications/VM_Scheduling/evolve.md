# Tenant-Level Soft Constraints - Implementation Guide for AlphaEvolve

This document guides automated code generation for implementing tenant-level soft constraint tracking and penalty calculation in the ALNS VM migration solver.

---

## 1. Constraint Specifications

### Business Motivation
In production cloud environments, host failures impact all VMs on that host. By limiting the concentration of important tenants (level ≥ 5) and total VM count per host, the system reduces the blast radius when a high-density host fails.

### Constraint A: High-Level Tenant Count Constraint (n_1)
**Purpose:** Limit the number of distinct high-level tenants on a single host.

**Parameters:**
- **Threshold (n_1):** Default 10, valid range [1, 100]
- **High-level tenant:** Any tenant with level ≥ 5 (NOT just level = 5)

**Violation:** A host with more than n_1 distinct high-level tenants.

**Penalty:** Linear - sum of excess across all hosts: `sum over hosts of max(0, distinct_high_level_tenant_count - n_1)`

**Example:** If a host has 12 distinct high-level tenants and threshold is 10, penalty contribution = 2.

---

### Constraint B: High-Level Tenant VM Count Constraint (n_2)
**Purpose:** Limit the number of VMs from a single high-level tenant on a single host.

**Parameters:**
- **Threshold (n_2):** Default 5, valid range [1, 50]
- **Applies to:** ALL tenants with level ≥ 5 (each independently checked)

**Violation:** A high-level tenant having more than n_2 VMs on a single host.

**Penalty:** Linear - sum of excess across all (tenant, host) pairs: `sum over (tenant_id, host_idx) of max(0, vm_count - n_2)` where tenant has level ≥ 5.

**Example:** If a high-level tenant (level 7) has 8 VMs on host A and 3 VMs on host B, with threshold 5:
- Host A penalty contribution = max(0, 8 - 5) = 3
- Host B penalty contribution = max(0, 3 - 5) = 0
- Total penalty contribution = 3

---

### Constraint C: Total VM Count Constraint (n_3)
**Purpose:** Limit the total number of VMs on a single host (regardless of tenant level).

**Parameters:**
- **Threshold (n_3):** Default 120, valid range [10, 500]

**Violation:** A host with more than n_3 total VMs.

**Penalty:** Linear - sum of excess across all hosts: `sum over hosts of max(0, total_vm_count - n_3)`

**Example:** If a host has 125 VMs and threshold is 120, penalty contribution = 5.

---

## 2. Algorithm Overview: ALNS with Soft Constraints

### ALNS (Adaptive Large Neighborhood Search)
ALNS is a metaheuristic optimization algorithm that iteratively improves a solution through destroy-and-repair operations:

1. **Destroy (Ruin):** Remove a subset of VMs from their current hosts
2. **Repair (Recreate):** Reassign removed VMs to new hosts
3. **Acceptance:** Accept or reject the new solution based on objective value comparison

### Soft Constraint Management in ALNS

**Objective Evaluation:**
- The solver maintains a **hierarchical objective** that combines multiple objectives in lexicographic order
- Tenant-level constraint objectives are **primary objectives** (evaluated before empty host count and load balancing)
- Order: HighLevelTenantCount → HighLevelTenantVmCount → MaxVmsPerHost → EmptyHost → LoadBalancing → MigrationCost
- Lower objective value = better solution

**How Variables Impact Search:**
- **MigrationVariable** instances track solution state incrementally (e.g., VM counts, tenant distributions)
- Variables are **updated incrementally** when the solution changes (not full recompute each time)
- Variables provide **O(1) queries** for metrics needed by objectives (distinct tenant count, VM counts per host)
- This enables **fast move evaluation** during search - O(1) or O(affected hosts) instead of O(all VMs)

**Move Evaluation (Delta Evaluation) - CRITICAL:**
- When a move is proposed (RuinDelta or RecreateDelta), the solver must quickly compute the projected objective value
- **Delta evaluation is INCREMENTAL** - it calculates the penalty change based only on affected hosts/tenants
- **Time complexity must be lower than full calculation** - typically O(1) or O(affected hosts) vs O(all hosts)
- The variable state remains unchanged during delta evaluation (read-only)
- Pattern: Query variable for current state, calculate penalty for only affected hosts, compute delta from current penalty
- **NEVER create a copy and do full recompute** - this defeats the entire purpose of incremental evaluation

**Why Incremental Delta Evaluation is Critical:**
- ALNS evaluates thousands of moves per second during search
- Full recomputation per move would make the solver 100-1000x slower
- Variables maintain incremental state specifically to enable O(1) delta queries
- Example: Moving one VM affects at most 2 hosts, so delta evaluation should only check 2 hosts, not all hosts

**Acceptance Criteria:**
- After evaluating a move, the solver compares the new objective value to the current best
- If new solution is better (lower penalty) → always accept
- If worse → accept with probability based on simulated annealing temperature
- Soft constraints influence acceptance: solutions with lower penalties are more likely to be accepted

**Incremental Update Pattern:**
- When a move is accepted, variables update incrementally to maintain correct state
- `update(solution, RuinDelta)` removes VMs from tracking structures
- `update(solution, RecreateDelta)` adds VMs to tracking structures
- Incremental updates maintain correctness: should match full recompute if started from scratch

---

## 3. Function Specifications (High-Level Natural Language)

### TenantLevelMigrationVariable

#### Function: `update(Problem problem, MigrationSolution solution)` - Full Update
**Aim:** Rebuild all tracking structures from scratch by scanning all VMs and recording which high-level tenants appear on each host and how many VMs each tenant has on each host.

**Time Complexity:** O(V) where V = number of VMs

**Key tracking structures:**
- `highLevelTenantCountPerHost[hostIndex]` → count of distinct high-level tenants on host
- `highLevelTenantHostVmCounts[tenantId][hostIndex]` → count of VMs for this high-level tenant on host

---

#### Function: `update(Problem problem, MigrationSolution solution, RuinDelta delta)` - Incremental Removal
**Aim:** Decrementally update tracking when a VM is removed from its host. Decrement VM count for the tenant, and decrement distinct tenant count only if this was the last VM from that tenant on the host.

**Time Complexity:** O(1) typically

---

#### Function: `update(Problem problem, MigrationSolution solution, RecreateDelta delta)` - Incremental Addition/Move
**Aim:** Incrementally update tracking when a VM is placed or moved. Handle removal from old host (if applicable) and addition to new host. Update distinct tenant counts only when adding the first or removing the last VM from a tenant on a host.

**Time Complexity:** O(1) typically

---

### HighLevelTenantCountPenaltyObjective (Constraint A)

#### Function: `calculate(Problem problem, MigrationSolution solution)` - Full Calculation
**Aim:** Sum the linear penalty (excess beyond threshold) across all hosts for distinct high-level tenant count violations.

**Time Complexity:** O(H) where H = number of hosts

**Formula:** `sum over all hosts of max(0, distinct_high_level_tenant_count - threshold)`

---

#### Function: `calculate(Problem problem, MigrationSolution solution, RuinDelta delta)` - Incremental Delta Evaluation
**Aim:** Compute projected total penalty after removing the VM by recalculating penalty only for the affected host (check if distinct count changes), then return current total penalty plus the penalty delta.

**Time Complexity:** O(1) - only one host affected

---

#### Function: `calculate(Problem problem, MigrationSolution solution, RecreateDelta delta)` - Incremental Delta Evaluation
**Aim:** Compute projected total penalty after moving/placing the VM by recalculating penalty only for affected hosts (at most 2: old and new), checking if distinct tenant counts change, then return current total penalty plus the penalty delta.

**Time Complexity:** O(1) - at most two hosts affected

---

### HighLevelTenantVmCountPenaltyObjective (Constraint B)

#### Function: `calculate(Problem problem, MigrationSolution solution)` - Full Calculation
**Aim:** Sum the linear penalty across all (high-level tenant, host) pairs where VM count exceeds threshold.

**Time Complexity:** O(T * H) where T = high-level tenants, H = hosts

**Formula:** `sum over all high-level tenants and all hosts of max(0, vm_count_for_tenant_on_host - threshold)`

---

#### Function: `calculate(Problem problem, MigrationSolution solution, RuinDelta delta)` - Incremental Delta Evaluation
**Aim:** Compute projected total penalty after removing the VM by recalculating penalty only for the affected (tenant, host) pair, then return current total penalty plus the penalty delta.

**Time Complexity:** O(1) - only one (tenant, host) pair affected

---

#### Function: `calculate(Problem problem, MigrationSolution solution, RecreateDelta delta)` - Incremental Delta Evaluation
**Aim:** Compute projected total penalty after moving/placing the VM by recalculating penalty only for affected (tenant, host) pairs (at most 2), then return current total penalty plus the penalty delta.

**Time Complexity:** O(1) - at most two (tenant, host) pairs affected

---

### MaxVmsPerHostPenaltyObjective (Constraint C)

#### Function: `calculate(Problem problem, MigrationSolution solution)` - Full Calculation
**Aim:** Sum the linear penalty across all hosts where total VM count exceeds threshold.

**Time Complexity:** O(H) where H = number of hosts

**Formula:** `sum over all hosts of max(0, total_vm_count - threshold)`

---

#### Function: `calculate(Problem problem, MigrationSolution solution, RuinDelta delta)` - Incremental Delta Evaluation
**Aim:** Compute projected total penalty after removing the VM by recalculating penalty only for the affected host, then return current total penalty plus the penalty delta.

**Time Complexity:** O(1) - only one host affected

---

#### Function: `calculate(Problem problem, MigrationSolution solution, RecreateDelta delta)` - Incremental Delta Evaluation
**Aim:** Compute projected total penalty after moving/placing the VM by recalculating penalty only for affected hosts (at most 2), then return current total penalty plus the penalty delta.

**Time Complexity:** O(1) - at most two hosts affected

---

## 4. Coding Rules for Consistency

### General Principles
1. **Incremental correctness:** Incremental updates must match full recompute when tested
2. **Delta evaluation is incremental:** NEVER create solution copies for delta evaluation - calculate only affected hosts/tenants
3. **Time complexity matters:** Delta evaluation must be faster than full calculation (O(1) or O(affected) vs O(all))
4. **Null safety:** Always check if placement is null before accessing host
5. **Boundary conditions:** Handle edge cases (0 VMs, unplaced VMs, empty hosts)
6. **Immutability:** Do not modify Problem or MigrationSolution objects in calculate methods
7. **Variable state is read-only during delta evaluation:** Query variable state, don't modify it

### Specific Patterns to Follow

#### Pattern 1: High-Level Tenant Check
```java
// CORRECT: Check level >= 5
if (vm.getTenantLevel() >= 5) {
    // Process high-level tenant
}

// INCORRECT: Check level == 5
if (vm.getTenantLevel() == 5) {  // ❌ WRONG - misses levels 6-10
}
```

#### Pattern 2: Null Placement Handling
```java
// CORRECT: Check null before accessing
Placement oldP = solution.getPlacement(vm);
if (oldP != null) {
    int hostIdx = oldP.getHost().getIndex();
    // Process old placement
}

// INCORRECT: Assume placement exists
int hostIdx = solution.getPlacement(vm).getHost().getIndex();  // ❌ NPE risk
```

#### Pattern 3: Delta Evaluation Pattern - INCREMENTAL
```java
// CORRECT: Incremental delta evaluation
public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
    Vm vm = delta.getVm();
    if (vm.getTenantLevel() < 5) {
        return calculate(problem, solution);  // No change
    }

    // Calculate penalty delta for affected hosts only
    int penaltyDelta = 0;
    Placement oldP = solution.getPlacement(vm);
    Placement newP = delta.getPlacement();

    // Recalculate only affected hosts
    if (oldP != null) {
        penaltyDelta -= calculateHostContribution(oldP.getHost().getIndex(), solution);
        penaltyDelta += calculateHostContribution_AfterRemoval(oldP.getHost().getIndex(), vm, solution);
    }
    penaltyDelta -= calculateHostContribution(newP.getHost().getIndex(), solution);
    penaltyDelta += calculateHostContribution_AfterAddition(newP.getHost().getIndex(), vm, solution);

    int currentTotal = calculate(problem, solution).intValue();
    return IntValue.of(currentTotal + penaltyDelta);
}

// INCORRECT: Copy and recompute (defeats purpose of incremental evaluation)
public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
    MigrationSolution projected = new MigrationSolution(solution);  // ❌ WRONG
    delta.update(problem, projected);
    return calculate(problem, projected);  // ❌ Full recalculation, not incremental
}
```

#### Pattern 4: Penalty Calculation Pattern
```java
// CORRECT: Linear penalty with max
int excess = Math.max(0, actualCount - threshold);
totalPenalty += excess;

// INCORRECT: Negative penalties
int excess = actualCount - threshold;  // ❌ Can be negative
totalPenalty += excess;
```

#### Pattern 5: Variable Fetching
```java
// CORRECT: Use fetcher to get variable
TenantLevelMigrationVariable variable = fetcher.fetch(solution);

// INCORRECT: Create new variable instance
TenantLevelMigrationVariable variable = new TenantLevelMigrationVariable(...);  // ❌ Wrong state
```

#### Pattern 6: Distinct Count Updates (First/Last VM Check)
```java
// CORRECT: Check if first/last VM before updating distinct count
int[] counts = highLevelTenantHostVmCounts.get(vm.getTenantId());
int currentCount = (counts == null) ? 0 : counts[hostIdx];

if (currentCount == 0) {
    // This is first VM from tenant on host
    highLevelTenantCountPerHost[hostIdx]++;
}
counts[hostIdx]++;  // Increment VM count

// For removal:
counts[hostIdx]--;
if (counts[hostIdx] == 0) {
    // This was last VM from tenant on host
    highLevelTenantCountPerHost[hostIdx]--;
}

// INCORRECT: Always increment/decrement distinct count
highLevelTenantCountPerHost[hostIdx]++;  // ❌ Counts duplicates
```

#### Pattern 7: Map Initialization
```java
// CORRECT: Use computeIfAbsent for lazy initialization
int[] counts = highLevelTenantHostVmCounts.computeIfAbsent(
    tenantId,
    k -> new int[problem.getHosts().size()]
);

// INCORRECT: Manual null check (verbose and error-prone)
if (!highLevelTenantHostVmCounts.containsKey(tenantId)) {
    highLevelTenantHostVmCounts.put(tenantId, new int[...]);
}
int[] counts = highLevelTenantHostVmCounts.get(tenantId);
```

#### Pattern 8: Return Type Consistency
```java
// CORRECT: Use IntValue.of() for integer penalties
return IntValue.of(totalPenalty);

// INCORRECT: Use raw int or wrong type
return totalPenalty;  // ❌ Type mismatch
return FloatValue.of(totalPenalty);  // ❌ Wrong value type
```

#### Pattern 9: Checking if VM is First/Last on Host
```java
// CORRECT: Query variable state to check first/last
TenantLevelMigrationVariable variable = fetcher.fetch(solution);
int currentVmCount = variable.getHighLevelTenantVmCount(vm.getTenantId(), hostIdx);

if (currentVmCount == 0) {
    // First VM from this tenant on this host
}
if (currentVmCount == 1) {
    // Last VM from this tenant on this host (after removal, will be 0)
}

// INCORRECT: Iterate through all VMs to count (slow)
int count = 0;
for (Vm v : problem.getVms()) {  // ❌ O(V) - defeats purpose of variable
    if (v.getTenantId().equals(vm.getTenantId()) &&
        solution.getPlacement(v).getHost().getIndex() == hostIdx) {
        count++;
    }
}
```

### Data Structure Consistency

#### For TenantLevelMigrationVariable:
- `highLevelTenantCountPerHost`: Simple int array indexed by host
- `highLevelTenantHostVmCounts`: Map from tenantId to int array indexed by host
- Both structures sized to `problem.getHosts().size()`
- Arrays are mutable, updated incrementally

#### For Objectives:
- Always return `IntValue` (not FloatValue, not ListValue)
- Penalty must be non-negative (use `Math.max(0, ...)`)
- Lower value = better (sum of excesses, not counts themselves)
- Delta evaluation returns projected total penalty, not just the delta

### Testing Expectations

#### Unit Tests Will Verify:
1. **Delta evaluation correctness:** `calculate(solution, delta)` must equal what `calculate(projected solution)` would return
2. **Incremental update correctness:** Variable state after incremental updates must match full recompute
3. **Boundary cases:** Zero violations → zero penalty
4. **Linear penalty:** Penalty proportional to excess (not quadratic, not exponential)
5. **Multiple violations:** Penalties accumulate correctly across hosts/tenants
6. **Time complexity:** Delta evaluation must be significantly faster than full recompute (measure in benchmarks)

#### Common Test Scenarios:
- No high-level tenants → all penalties = 0
- Exactly at threshold → penalty = 0
- One VM over threshold → penalty = 1
- Multiple hosts violating → penalties sum correctly
- Removing VM from only tenant on host → distinct count decreases
- Adding first VM from tenant to host → distinct count increases
- Moving VM between hosts → both hosts updated correctly

### Error Prevention Checklist

Before submitting implementation:
- [ ] All null checks in place for placements
- [ ] High-level check uses `>= 5`, not `== 5`
- [ ] Penalty calculation uses `Math.max(0, ...)`
- [ ] Delta evaluation is INCREMENTAL (no solution copying)
- [ ] Delta evaluation only checks affected hosts/tenants (not all)
- [ ] Incremental updates handle both old and new placements
- [ ] Map access uses `computeIfAbsent` or proper null checks
- [ ] Return types match interface (`IntValue` for penalties)
- [ ] Array indices use `host.getIndex()`, not raw host objects
- [ ] No modifications to Problem or original MigrationSolution objects
- [ ] Variable fetcher used, not manual variable construction
- [ ] First/last VM checks query variable state, not iterate all VMs

---

## 5. Implementation Priority

Implement in this order to enable incremental testing:

1. **TenantLevelMigrationVariable.update(full)** - Enables basic testing
2. **HighLevelTenantCountPenaltyObjective.calculate(full)** - Test Constraint A
3. **HighLevelTenantVmCountPenaltyObjective.calculate(full)** - Test Constraint B
4. **MaxVmsPerHostPenaltyObjective.calculate(full)** - Test Constraint C
5. **TenantLevelMigrationVariable.update(RecreateDelta)** - Enables incremental updates
6. **TenantLevelMigrationVariable.update(RuinDelta)** - Completes incremental updates
7. **All delta evaluation methods** - Implement incrementally, test against full recompute

After each step, run unit tests to verify correctness before proceeding.

---

## 6. Success Criteria

Implementation is complete when:
- All functions replace dummy implementations with actual logic
- Unit tests pass (delta evaluation matches full recompute)
- **Performance tests pass** (delta evaluation significantly faster than full recompute)
- Integration tests pass (solver reduces penalties from violated initial solutions)
- No regression in existing test suite (125+ tests)
- Benchmark shows acceptable performance (< 5% slowdown on existing benchmarks)

---

## 7. Key Implementation Insights

### Why Variables Exist
Variables maintain incremental state specifically to avoid scanning all VMs during objective evaluation. Without variables, every penalty calculation would require O(V) time. With variables, queries are O(1) and delta evaluation is O(affected hosts/tenants).

### Why Delta Evaluation Must Be Incremental
The solver evaluates thousands of moves per second. If each delta evaluation required copying the entire solution and recalculating all penalties, the solver would be 100-1000x slower. Incremental delta evaluation is the core performance optimization.

### The First/Last VM Problem
For Constraint A (distinct tenant count), adding/removing a VM only affects the distinct count if it's the first/last VM from that tenant on that host. This requires checking the current VM count for that tenant on that host, which is why the variable tracks both distinct count AND VM count per tenant.

### Penalty Delta vs Total Penalty
Delta evaluation methods return the **projected total penalty**, not the delta (change). The pattern is:
1. Calculate current total penalty
2. Calculate penalty change for affected hosts/tenants
3. Return current_total + penalty_delta

This matches the interface contract where all calculate methods return the full penalty value.

---

## References
- Implementation plan: `C:\Users\mahdi\.claude\plans\dazzling-popping-fountain.md`
- Implementation status: `IMPLEMENTATION_STATUS.md`
- Example patterns: `TenantMigrationVariable.java`, `HostVmsMigrationVariable.java`
- Example objective patterns: `MinLoadBalancingObjective.java` (for proper delta evaluation)
