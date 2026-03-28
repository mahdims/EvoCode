package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.FloatValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.NumaResourceCuttingLineMigrationVariable;

/**
 * Minimize NUMA usage above cutting line threshold.
 * Lower excess = better.
 *
 * See MainWiki §6.4 / 04-objectives.md.
 */
public class NumaResourceCuttingLineMigrationObjective implements MigrationObjective {

    private final MigrationFetcher<NumaResourceCuttingLineMigrationVariable> fetcher;

    public NumaResourceCuttingLineMigrationObjective(
            MigrationFetcher<NumaResourceCuttingLineMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        return FloatValue.of(fetcher.fetch(solution).getTotalExcess());
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
