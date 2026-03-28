package com.vmscheduling.util;

import java.util.List;
import java.util.SplittableRandom;

/**
 * Utility methods for the ALNS algorithm.
 */
public final class AlgorithmUtil {

    private AlgorithmUtil() {}

    /**
     * Fisher-Yates shuffle using the provided random source.
     */
    public static <T> void shuffleList(List<T> list, SplittableRandom random) {
        for (int i = list.size() - 1; i > 0; i--) {
            int j = random.nextInt(i + 1);
            T temp = list.get(i);
            list.set(i, list.get(j));
            list.set(j, temp);
        }
    }
}
