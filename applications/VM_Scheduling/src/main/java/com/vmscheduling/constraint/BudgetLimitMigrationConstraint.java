package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.MigrationCostMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

/**
 * Ensures total migration cost does not exceed a budget limit.
 * Σ PMC(vm) ≤ budgetLimit for all migrated VMs.
 *
 * See MainWiki §5.5 / 03-constraints.md.
 */
public class BudgetLimitMigrationConstraint implements MigrationConstraint {

    private final MigrationFetcher<MigrationCostMigrationVariable> fetcher;
    private final int budgetLimit;

    public BudgetLimitMigrationConstraint(MigrationFetcher<MigrationCostMigrationVariable> fetcher,
                                          int budgetLimit) {
        this.fetcher = fetcher;
        this.budgetLimit = budgetLimit;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        return fetcher.fetch(solution).getTotalCost() <= budgetLimit;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs can only reduce cost
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        MigrationCostMigrationVariable variable = fetcher.fetch(solution);
        Vm vm = delta.getVm();
        int projectedCost = variable.getTotalCost();

        // Subtract old contribution if VM was at non-initial
        Placement oldP = solution.getPlacement(vm);
        if (oldP != null && oldP != vm.getInitialPlacement()) {
            projectedCost -= vm.getMigrationCost();
        }

        // Add new contribution if target is non-initial
        if (delta.getPlacement() != vm.getInitialPlacement()) {
            projectedCost += vm.getMigrationCost();
        }

        return projectedCost <= budgetLimit;
    }
}
