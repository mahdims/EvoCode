package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.TenantLevelMigrationVariable;

/**
 * Constraint A: High-Level Tenant Count Penalty (n_1)
 * Penalize hosts exceeding the threshold for distinct high-level tenants (level >= 5).
 *
 * CURRENT STATUS: DUMMY IMPLEMENTATION
 * - Always returns IntValue(0) regardless of actual tenant counts
 *
 * TODO: Implement full penalty calculation
 * TODO: Implement delta evaluation (RuinDelta and RecreateDelta)
 */
public class HighLevelTenantCountPenaltyObjective implements MigrationObjective {

    private final MigrationFetcher<TenantLevelMigrationVariable> fetcher;
    private final int threshold;  // n_1 (default 10)

    public HighLevelTenantCountPenaltyObjective(
            MigrationFetcher<TenantLevelMigrationVariable> fetcher,
            int threshold) {
        this.fetcher = fetcher;
        this.threshold = threshold;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        // TODO: Implement full penalty calculation
        // Should iterate all hosts and sum Math.max(0, count - threshold)
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
