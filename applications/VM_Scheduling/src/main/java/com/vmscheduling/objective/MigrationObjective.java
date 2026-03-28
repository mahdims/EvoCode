package com.vmscheduling.objective;

import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.Value;

/**
 * Interface for optimization objective functions.
 * All methods are pure readers — they read from Variables and return a Value.
 * Lower values are always better.
 *
 * CRITICAL CONTRACT: Delta methods return PROJECTED FULL VALUES, not marginal deltas.
 * This contract is enforced by DeltaEvaluationTest regression tests.
 *
 * See MainWiki §6 / 04-objectives.md.
 */
public interface MigrationObjective {

    /**
     * Full evaluation of the entire solution.
     * @return The complete objective value for the current solution state
     */
    Value calculate(Problem problem, MigrationSolution solution);

    /**
     * Projected evaluation after applying a ruin delta (pure projection - no state change).
     *
     * CRITICAL: Must return the FULL objective value that would result AFTER applying the delta,
     * NOT the marginal change. For example, if current value is 100 and delta would result in 95,
     * return 95 (not -5).
     *
     * @param delta The ruin delta to project
     * @return PROJECTED full objective value after applying delta (verified by DeltaEvaluationTest)
     */
    Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta);

    /**
     * Projected evaluation after applying a recreate delta (pure projection - no state change).
     *
     * CRITICAL: Must return the FULL objective value that would result AFTER applying the delta,
     * NOT the marginal change. For example, if current value is 100 and delta would result in 95,
     * return 95 (not -5).
     *
     * @param delta The recreate delta to project
     * @return PROJECTED full objective value after applying delta (verified by DeltaEvaluationTest)
     */
    Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
