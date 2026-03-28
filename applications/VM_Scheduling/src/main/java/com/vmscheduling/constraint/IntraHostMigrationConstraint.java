package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;

/**
 * Forbids intra-host placement: a migratable VM must move to a DIFFERENT host
 * from its initial placement. Prevents "migrations" that stay on the same host.
 *
 * Stateless — no fetcher needed.
 *
 * See MainWiki §5.4 / 03-constraints.md.
 */
public class IntraHostMigrationConstraint implements MigrationConstraint {

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // Accept if: initial placement (no migration), OR placed on a DIFFERENT host
        return delta.isInitial()
                || delta.getHost() != delta.getVm().getInitialPlacement().getHost();
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs can't cause intra-host violation
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        for (Vm vm : problem.getVms()) {
            Placement placement = solution.getPlacement(vm);
            if (placement == null) continue;
            if (vm.getInitialPlacement() != placement
                    && vm.getInitialPlacement().getHost() == placement.getHost()) {
                return false;
            }
        }
        return true;
    }
}
