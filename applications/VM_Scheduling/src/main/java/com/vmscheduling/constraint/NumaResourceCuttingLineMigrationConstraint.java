package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.NumaResourceCuttingLineMigrationVariable;

/**
 * Prevents NUMA nodes from being packed above a configurable threshold.
 * Reserves headroom for burst workloads.
 *
 * See MainWiki §5.5 / 03-constraints.md.
 */
public class NumaResourceCuttingLineMigrationConstraint implements MigrationConstraint {

    private final MigrationFetcher<NumaResourceCuttingLineMigrationVariable> fetcher;

    public NumaResourceCuttingLineMigrationConstraint(
            MigrationFetcher<NumaResourceCuttingLineMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        NumaResourceCuttingLineMigrationVariable variable = fetcher.fetch(solution);
        return variable.getTotalExcess() <= 0;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs reduces usage
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        NumaResourceCuttingLineMigrationVariable variable = fetcher.fetch(solution);
        // Check that placing this VM doesn't push any NUMA above threshold
        return variable.getTotalExcess() <= 0;
    }
}
