# 06 — AdaptiveMaintainer (Operator Selection)

The ALNS solver is "adaptive" because four operator dimensions are selected via roulette-wheel selection weighted by cumulative historical performance.

---

## Four Operator Dimensions

| Dimension | Type | Values | Controls |
|---|---|---|---|
| `numRuinHost` | `int` | `1 … numMaxRuinHost` (default max=5) | How many hosts to ruin |
| `VmSorterType` | enum | `CPU_MEM, MEM_CPU, CPU_MEM_PROD, NUM_NUMA, RANDOM` | VM ordering during sort |
| `HostSorterType` | enum | `RUIN_EXPECTED, RANDOM, RUIN_EXPECTED_RANDOM` | Host selection strategy |
| `RecreateType` | enum | `BEST, RANDOM, FirstFit` | Placement strategy |

Each dimension is selected independently on every iteration via roulette wheel.

---

## AdaptiveMaintainer — Full Source (Confirmed)

```java
class AdaptiveMaintainer {
    private final Map<Integer, Double>        numRuinHostWeights;   // 1..numMaxRuinHost → 1.0 each
    private final Map<VmSorterType, Double>   vmSorterWeights;      // each constant → 1.0
    private final Map<HostSorterType, Double> hostSorterWeights;    // each constant → 1.0
    private final Map<RecreateType, Double>   recreateWeights;      // each constant → 1.0

    // All weights initialised to 1.0 in constructor.
    // NO decay, NO reset, NO sliding window.
    // Weights only ever increase.

    int            rollNumRuinHost   (SplittableRandom r) { return rollByWeights(numRuinHostWeights, r); }
    VmSorterType   rollVmSorterType  (SplittableRandom r) { return rollByWeights(vmSorterWeights, r); }
    HostSorterType rollHostSorterType(SplittableRandom r) { return rollByWeights(hostSorterWeights, r); }
    RecreateType   rollRecreateType  (SplittableRandom r) { return rollByWeights(recreateWeights, r); }

    // Reward all four operators when a global best improvement is found
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

---

## Weight Update Semantics

Weights are updated in the main loop only when a **new global best** is found:

```java
// In solve() — step 5
if (newValue.compareTo(bestValue) < 0) {
    bestValue = newValue;
    bestSolution = new MigrationSolution(newSolution, false);
    stagnationSteps = 0;
    adaptiveMaintainer.updateWeights(
        ruinHosts.size(),   // NOTE: actual host count, not rolled numRuinHost
        vmSorterType,
        hostSorterType,
        recreateType,
        1.0                 // fixed reward increment
    );
}
```

**Important:** The first argument is `ruinHosts.size()`, not the rolled `numRuinHost`. The actual number of hosts after sorting/truncation may differ from the rolled value.

---

## Behavioral Consequence

Since weights monotonically increase and there is no decay:

- Operators that find improvements **early** will permanently have higher selection probability.
- An operator that works well in the first 100 iterations may dominate for the remaining thousands.
- This trades late-stage exploration for simplicity and low overhead.
- The `RANDOM` variants in both `HostSorterType` and `RecreateType` provide some inherent exploration even with skewed weights.
