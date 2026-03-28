package com.vmscheduling;

import com.vmscheduling.operator.AdaptiveMaintainer;
import com.vmscheduling.operator.HostSorterType;
import com.vmscheduling.operator.RecreateType;
import com.vmscheduling.operator.VmSorterType;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.*;

class AdaptiveMaintainerTest {

    @Test
    void initialWeights_uniformDistribution() {
        AdaptiveMaintainer am = new AdaptiveMaintainer(5);
        SplittableRandom random = new SplittableRandom(42);

        Map<Integer, Integer> counts = new HashMap<>();
        int trials = 50000;
        for (int i = 0; i < trials; i++) {
            int val = am.rollNumRuinHost(random);
            counts.merge(val, 1, Integer::sum);
        }

        // With uniform weights, each of 1..5 should get ~20% ± 2%
        for (int k = 1; k <= 5; k++) {
            double ratio = counts.getOrDefault(k, 0) / (double) trials;
            assertThat(ratio).isBetween(0.17, 0.23);
        }
    }

    @Test
    void updateWeights_skewsDistribution() {
        AdaptiveMaintainer am = new AdaptiveMaintainer(3);
        SplittableRandom random = new SplittableRandom(42);

        // Heavily reward numRuinHost=2
        for (int i = 0; i < 100; i++) {
            am.updateWeights(2, VmSorterType.CPU_MEM, HostSorterType.RANDOM,
                    RecreateType.BEST, 1.0);
        }

        Map<Integer, Integer> counts = new HashMap<>();
        int trials = 50000;
        for (int i = 0; i < trials; i++) {
            counts.merge(am.rollNumRuinHost(random), 1, Integer::sum);
        }

        // numRuinHost=2 has weight 101.0 vs 1.0 each for 1 and 3
        // Should get ~101/103 ≈ 98%
        double ratio2 = counts.getOrDefault(2, 0) / (double) trials;
        assertThat(ratio2).isGreaterThan(0.95);
    }

    @Test
    void allOperatorDimensions_returnsValidValues() {
        AdaptiveMaintainer am = new AdaptiveMaintainer(5);
        SplittableRandom random = new SplittableRandom(123);

        for (int i = 0; i < 1000; i++) {
            int n = am.rollNumRuinHost(random);
            assertThat(n).isBetween(1, 5);

            VmSorterType vst = am.rollVmSorterType(random);
            assertThat(vst).isNotNull();

            HostSorterType hst = am.rollHostSorterType(random);
            assertThat(hst).isNotNull();

            RecreateType rt = am.rollRecreateType(random);
            assertThat(rt).isNotNull();
        }
    }
}
