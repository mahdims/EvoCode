# 12 — One Full ALNS Iteration — Step-by-Step Walkthrough

A concrete trace through one iteration showing how all components interact.

---

## Setup

Assume:
- hostA has migratable VMs [v, w, x] (v is a 2-CPU, 8-GB single-NUMA VM)
- hostB has free capacity on numa1
- Current objective value: `ListValue [-2, 0.15]` (2 empty hosts, imbalance 0.15)
- LAHC buffer at current position: `[-2, 0.18]`
- Global best value: `[-2, 0.15]`

---

## Step 0 — Select Operators (File 06)

AdaptiveMaintainer rolls via roulette wheel:

```
numRuinHost    = 1                      (from [1..5], weighted by history)
hostSorterType = RUIN_EXPECTED_RANDOM   (scored + weighted random)
vmSorterType   = CPU_MEM               (sort by CPU ascending, break ties by mem)
recreateType   = BEST                   (evaluate all candidates, pick best)
```

---

## Step 1 — Host Selection (File 08: getRuinHosts)

```
1. Collect hosts with migratable VMs → [hostA, hostC, hostD, hostE]
2. Shuffle → [hostD, hostA, hostE, hostC]
3. RUIN_EXPECTED_RANDOM.sort():
   - For each host, speculatively compute RuinDelta + objective (projection)
   - Rank by objective value (lower = better)
   - Select 1 host using rank-based weighted random (weight = 1/(rank+1))
   → hostA selected
```

---

## Step 2 — Copy-on-Write

```
newSolution = new MigrationSolution(solution)
  → placements array copied
  → every MigrationVariable deep-copied (variable.copy())
  → original `solution` is NEVER touched from here on
```

---

## Step 3 — Guided Ruin (File 08: getRuinVms)

Operating on `newSolution` (not original):

```
VMs on hostA: [v, w, x]
sortVmsByType(newSolution, vms, CPU_MEM, isRuin=true):
  Pre-sort: v was previously moved (initial ≠ current) → v goes first
  Then CPU_MEM ascending: [v(2 CPU), x(4 CPU), w(8 CPU)]
  
Process v:
  ruinDelta = new RuinDelta(new Vm[] {v})
  constraint.satisfy(problem, newSolution, ruinDelta) → ✓ (projection, no state change)
  objective.calculate(problem, newSolution, ruinDelta).compareToZero() → -1 (improving!)
  ruinDelta.update(problem, newSolution)  → commit: remove v, update CpuMemVariable etc.
  improved = true → BREAK (stop processing hostA's VMs)

ruinVms = [v]  (only v was ruined because improvement was found immediately)
```

If removing v had NOT improved the objective (`compareToZero >= 0`), the algorithm would continue to x, then w. If none improved, `return null` → skip iteration.

---

## Step 4 — Recreate (File 09: BEST mode)

```
sortVmsByType(newSolution, [v], CPU_MEM, isRuin=false):
  CPU_MEM ascending then reverse → [v] (only one VM, order doesn't matter)

For VM v:
  getBestRecreate(problem, newSolution, v, allPlacements.get(1)):

  PHASE 1: Try v.getInitialPlacement() (hostA_numa0)
    constraint.satisfy() → ✓
    objective.calculate().compareToZero() → +2 (worsening: puts v back, un-empties hostA)
    Store in candidates: (delta_initial, value=+2)

  PHASE 2: Scan all single-NUMA placements
    hostB_numa0: constraint → ✗ (capacity exceeded) → skip
    hostB_numa1: constraint → ✓
      objective.calculate().compareToZero() → -1 (non-worsening!) → EARLY EXIT
      return RecreateDelta(v, Placement(hostB_numa1))

  delta.update(problem, newSolution)
    → CpuMemVariable: hostB_numa1 CPU += 2.0, mem += 8.0
    → HostVmsVariable: add v to hostB
    → EmptyHostVariable: hostB was empty → decrement empty count... no wait, it wasn't
```

---

## Step 5 — Evaluate (File 04)

```
newValue = problem.getMigrationObjective().calculate(problem, newSolution)
  → EmptyHostObjective: 3 empty hosts → IntValue(-3)
  → LoadBalancingObjective: variance = 0.08
  → ListValue [-3, 0.08]

if useChainOptimizer:
  newValue = MigrationOptimizer.optimizeChain(...)  → may improve further
  Assume no change: newValue = [-3, 0.08]
```

---

## Step 6 — Global Best Check (File 06)

```
newValue  = [-3, 0.08]
bestValue = [-2, 0.15]

newValue.compareTo(bestValue) → -3 < -2 → compareTo returns negative → NEW GLOBAL BEST

bestValue = [-3, 0.08]
bestSolution = new MigrationSolution(newSolution, false)  // shallow copy
stagnationSteps = 0  // RESET

adaptiveMaintainer.updateWeights(
    1,                       // ruinHosts.size() = 1
    CPU_MEM,                 // vmSorterType
    RUIN_EXPECTED_RANDOM,    // hostSorterType
    BEST,                    // recreateType
    1.0                      // reward
)
→ numRuinHostWeights[1]          : 1.0 → 2.0
→ vmSorterWeights[CPU_MEM]      : 1.0 → 2.0
→ hostSorterWeights[RUIN_EXP_R] : 1.0 → 2.0
→ recreateWeights[BEST]         : 1.0 → 2.0
```

These operators now have 2× the selection probability of unrewarded operators.

---

## Step 7 — Accept / Reject (File 10: LAHC)

```
oldValue = [-2, 0.15]  (current working)
newValue = [-3, 0.08]

Condition 1: newValue.compareTo(oldValue) = -3 vs -2 → ≤ 0 → ACCEPT

value = [-3, 0.08]
solution = newSolution  // adopt as new working solution

LAHC buffer update:
  history[position] was [-2, 0.18]
  candidate [-3, 0.08] < [-2, 0.18] → update slot
  history[position] = [-3, 0.08]
  position = (position + 1) % 10
```

---

## Rejection Example

If newValue had been `[-1, 0.20]` (worse — only 1 empty host):

```
Condition 1: [-1, 0.20].compareTo([-2, 0.15]) > 0 → FAIL
Condition 2: [-1, 0.20].compareTo([-2, 0.18]) > 0 → FAIL

→ REJECT
→ newSolution is simply discarded (garbage collected)
→ solution remains untouched (it was never mutated — copy-on-write)
→ value remains [-2, 0.15]
→ stagnationSteps continues incrementing
```

---

## Iteration Summary

```
[Step 1]  Roll operators: numRuinHost=1, RUIN_EXPECTED_RANDOM, CPU_MEM, BEST
[Step 2]  getRuinHosts → hostA selected
[Step 3]  Deep copy solution → newSolution
[Step 4]  getRuinVms → remove v from hostA (guided, constraint-checked, improving)
[Step 5]  Recreate v → place on hostB_numa1 (BEST mode, early exit on non-worsening)
[Step 6]  Evaluate → [-3, 0.08]
[Step 7]  Global best check → YES → update best, reset stagnation, reward operators
[Step 8]  LAHC accept → YES → adopt newSolution as working solution
[Loop]    steps=1, stagnationSteps=0, continue...
```
