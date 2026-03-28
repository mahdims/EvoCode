package com.vmscheduling.operator;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Adaptive operator selection via roulette wheel.
 * Four weight maps (numRuinHost, VmSorter, HostSorter, Recreate).
 * All initialized to 1.0. Weights only increase (+1.0 on global best). No decay.
 *
 * See MainWiki §7.3a / 06-adaptive-maintainer.md.
 */
public class AdaptiveMaintainer {

    private final Map<Integer, Double> numRuinHostWeights;
    private final Map<VmSorterType, Double> vmSorterWeights;
    private final Map<HostSorterType, Double> hostSorterWeights;
    private final Map<RecreateType, Double> recreateWeights;

    public AdaptiveMaintainer(int numMaxRuinHost) {
        numRuinHostWeights = new LinkedHashMap<>();
        for (int i = 1; i <= numMaxRuinHost; i++) {
            numRuinHostWeights.put(i, 1.0);
        }

        vmSorterWeights = new LinkedHashMap<>();
        for (VmSorterType type : VmSorterType.values()) {
            vmSorterWeights.put(type, 1.0);
        }

        hostSorterWeights = new LinkedHashMap<>();
        for (HostSorterType type : HostSorterType.values()) {
            hostSorterWeights.put(type, 1.0);
        }

        recreateWeights = new LinkedHashMap<>();
        for (RecreateType type : RecreateType.values()) {
            recreateWeights.put(type, 1.0);
        }
    }

    public int rollNumRuinHost(SplittableRandom random) {
        return rollByWeights(numRuinHostWeights, random);
    }

    public VmSorterType rollVmSorterType(SplittableRandom random) {
        return rollByWeights(vmSorterWeights, random);
    }

    public HostSorterType rollHostSorterType(SplittableRandom random) {
        return rollByWeights(hostSorterWeights, random);
    }

    public RecreateType rollRecreateType(SplittableRandom random) {
        return rollByWeights(recreateWeights, random);
    }

    /**
     * Reward all four operators when a global best is found.
     * Note: numRuinHost is the ACTUAL host count (ruinHosts.size()), not the rolled value.
     */
    public void updateWeights(int numRuinHost, VmSorterType vmSorterType,
                               HostSorterType hostSorterType, RecreateType recreateType,
                               double weight) {
        numRuinHostWeights.computeIfPresent(numRuinHost, (k, v) -> v + weight);
        vmSorterWeights.computeIfPresent(vmSorterType, (k, v) -> v + weight);
        hostSorterWeights.computeIfPresent(hostSorterType, (k, v) -> v + weight);
        recreateWeights.computeIfPresent(recreateType, (k, v) -> v + weight);
    }

    /**
     * Roulette wheel selection — O(n) in number of operator types.
     */
    static <T> T rollByWeights(Map<T, Double> weights, SplittableRandom random) {
        double sum = 0;
        for (double w : weights.values()) sum += w;
        double r = random.nextDouble(sum);
        double cumulative = 0.0;
        for (Map.Entry<T, Double> entry : weights.entrySet()) {
            cumulative += entry.getValue();
            if (r < cumulative) return entry.getKey();
        }
        throw new IllegalStateException("Roulette selection failed");
    }
}
