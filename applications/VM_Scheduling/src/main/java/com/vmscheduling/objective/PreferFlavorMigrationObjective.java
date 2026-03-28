package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.PreferFlavorMigrationVariable;

/**
 * Maximize remaining capacity for large-flavor VMs.
 * Returns NEGATED remaining capacity so lower = more capacity = better.
 *
 * See MainWiki §6.4 / 04-objectives.md.
 */
public class PreferFlavorMigrationObjective implements MigrationObjective {

    private final MigrationFetcher<PreferFlavorMigrationVariable> fetcher;

    public PreferFlavorMigrationObjective(MigrationFetcher<PreferFlavorMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        return IntValue.of(-fetcher.fetch(solution).getTotalRemainingCapacity());
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return calculate(problem, solution);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        return calculate(problem, solution);
    }
}
