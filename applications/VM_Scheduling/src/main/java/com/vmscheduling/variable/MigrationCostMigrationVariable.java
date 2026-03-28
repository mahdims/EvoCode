package com.vmscheduling.variable;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;

/**
 * Tracks total migration cost — the sum of migrationCost for all VMs
 * that have moved from their initial placement.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class MigrationCostMigrationVariable implements MigrationVariable {

    private int totalCost;

    public int getTotalCost() { return totalCost; }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        totalCost = 0;
        for (Vm vm : problem.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            if (p != vm.getInitialPlacement()) {
                totalCost += vm.getMigrationCost();
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // When a VM is ruined, if it was at a non-initial placement, subtract its cost
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            if (p != vm.getInitialPlacement()) {
                totalCost -= vm.getMigrationCost();
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        Placement oldP = solution.getPlacement(vm);
        Placement newP = delta.getPlacement();

        // Subtract old contribution
        if (oldP != null && oldP != vm.getInitialPlacement()) {
            totalCost -= vm.getMigrationCost();
        }

        // Add new contribution
        if (newP != vm.getInitialPlacement()) {
            totalCost += vm.getMigrationCost();
        }
    }

    @Override
    public MigrationVariable copy() {
        MigrationCostMigrationVariable c = new MigrationCostMigrationVariable();
        c.totalCost = this.totalCost;
        return c;
    }
}
