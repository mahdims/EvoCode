package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationCostMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

/**
 * Minimize total migration cost.
 * Lower cost = better.
 *
 * See MainWiki §6.4 / 04-objectives.md.
 */
public class MigrationCostMigrationObjective implements MigrationObjective {

    private final MigrationFetcher<MigrationCostMigrationVariable> fetcher;

    public MigrationCostMigrationObjective(MigrationFetcher<MigrationCostMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        return IntValue.of(fetcher.fetch(solution).getTotalCost());
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // SEMANTIC FIX: Return projected full value, not marginal delta
        MigrationCostMigrationVariable variable = fetcher.fetch(solution);
        int projectedCost = variable.getTotalCost();

        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p != null && p != vm.getInitialPlacement()) {
                projectedCost -= vm.getMigrationCost(); // Removing migrated VM reduces cost
            }
        }
        return IntValue.of(projectedCost);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // SEMANTIC FIX: Return projected full value, not marginal delta
        MigrationCostMigrationVariable variable = fetcher.fetch(solution);
        int projectedCost = variable.getTotalCost();
        Vm vm = delta.getVm();

        // Subtract old contribution
        Placement oldP = solution.getPlacement(vm);
        if (oldP != null && oldP != vm.getInitialPlacement()) {
            projectedCost -= vm.getMigrationCost();
        }

        // Add new contribution
        if (delta.getPlacement() != vm.getInitialPlacement()) {
            projectedCost += vm.getMigrationCost();
        }

        return IntValue.of(projectedCost);
    }
}
