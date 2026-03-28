package com.vmscheduling.acceptance;

import com.vmscheduling.value.Value;

import java.util.SplittableRandom;

/**
 * Interface for acceptance criteria in the ALNS main loop.
 *
 * See MainWiki §7.3b / 10-acceptance-criterion.md.
 */
public interface AcceptanceCriteria {

    /** Initialize with the starting objective value */
    void init(Value value);

    /**
     * Decide whether to accept the candidate solution.
     * @param oldValue current working solution's objective
     * @param newValue candidate solution's objective
     * @param random RNG
     * @param stagnationSteps iterations since last global best
     * @return true if the candidate should be adopted
     */
    boolean accept(Value oldValue, Value newValue, SplittableRandom random, int stagnationSteps);
}
