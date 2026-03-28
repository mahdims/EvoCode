package com.vmscheduling.value;

/**
 * Base interface for all objective values in the optimization framework.
 * Lower values are always better throughout the entire system.
 * {@code compareTo < 0} means the left operand is strictly better.
 */
public interface Value extends Comparable<Value> {

    /**
     * Compares this value against the zero/neutral point.
     * Used in getBestRecreate to determine if a placement is non-worsening:
     * {@code compareToZero() <= 0} means "this delta doesn't worsen the objective".
     *
     * @return negative if better than zero, 0 if equal, positive if worse
     */
    int compareToZero();
}
