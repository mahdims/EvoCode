package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

/**
 * Constraint C: Max VMs Per Host Penalty (n_3)
 * Penalize hosts exceeding the total VM count threshold.
 *
 * CURRENT STATUS: DUMMY IMPLEMENTATION
 * - Always returns IntValue(0) regardless of actual VM counts
 *
 * TODO: Implement full penalty calculation
 * TODO: Implement delta evaluation (RuinDelta and RecreateDelta)
 */
public class MaxVmsPerHostPenaltyObjective implements MigrationObjective {

    private final MigrationFetcher<HostVmsMigrationVariable> fetcher;
    private final int threshold;  // n_3 (default 120)

    public MaxVmsPerHostPenaltyObjective(
            MigrationFetcher<HostVmsMigrationVariable> fetcher,
            int threshold) {
        this.fetcher = fetcher;
        this.threshold = threshold;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        // TODO: Implement full penalty calculation
        // Should iterate all hosts and sum Math.max(0, vmCount - threshold)
        return IntValue.of(0);  // DUMMY: Always return 0 penalty
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // TODO: Implement delta evaluation
        // Should simulate delta and return projected full penalty
        return IntValue.of(0);  // DUMMY: Always return 0 penalty
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // TODO: Implement delta evaluation
        // Should simulate delta and return projected full penalty
        return IntValue.of(0);  // DUMMY: Always return 0 penalty
    }
}
