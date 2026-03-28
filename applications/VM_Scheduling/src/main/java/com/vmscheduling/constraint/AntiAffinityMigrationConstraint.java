package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.AntiAffinityMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

import java.util.Map;

/**
 * Ensures no two VMs in the same anti-affinity group share the same host.
 *
 * See MainWiki §5.4 / 03-constraints.md.
 */
public class AntiAffinityMigrationConstraint implements MigrationConstraint {

    private final MigrationFetcher<AntiAffinityMigrationVariable> fetcher;

    public AntiAffinityMigrationConstraint(MigrationFetcher<AntiAffinityMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        AntiAffinityMigrationVariable variable = fetcher.fetch(solution);
        for (Map.Entry<String, int[]> entry : variable.getGroupHostCounts().entrySet()) {
            for (int count : entry.getValue()) {
                if (count > 1) return false;
            }
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs can't create anti-affinity violations
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        String groupId = vm.getAntiAffinityGroupId();
        if (groupId == null) return true;

        AntiAffinityMigrationVariable variable = fetcher.fetch(solution);
        Host targetHost = delta.getPlacement().getHost();
        int currentCount = variable.getCount(groupId, targetHost.getIndex());

        // Check if placing this VM would exceed 1 per host
        // Account for the VM's current placement if it's on the same host
        int projected = currentCount + 1;
        var oldP = solution.getPlacement(vm);
        if (oldP != null && oldP.getHost() == targetHost) {
            projected--; // VM is already counted on this host
        }

        return projected <= 1;
    }
}
