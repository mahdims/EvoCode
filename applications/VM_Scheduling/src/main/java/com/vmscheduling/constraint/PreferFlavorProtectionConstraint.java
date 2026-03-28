package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.PreferFlavorMigrationVariable;

/**
 * Reserves capacity on each host for large-flavor VMs.
 * Prevents over-packing that would block future large-VM placement.
 *
 * See MainWiki §5.5 / 03-constraints.md.
 */
public class PreferFlavorProtectionConstraint implements MigrationConstraint {

    private final MigrationFetcher<PreferFlavorMigrationVariable> fetcher;

    public PreferFlavorProtectionConstraint(MigrationFetcher<PreferFlavorMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        PreferFlavorMigrationVariable variable = fetcher.fetch(solution);
        return variable.getTotalRemainingCapacity() >= 0;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs increases remaining capacity
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        PreferFlavorMigrationVariable variable = fetcher.fetch(solution);
        int targetHostIdx = delta.getPlacement().getHost().getIndex();
        // Ensure placing this VM doesn't reduce remaining capacity below 0
        return variable.getHostRemainingCapacity(targetHostIdx) >= 0;
    }
}
