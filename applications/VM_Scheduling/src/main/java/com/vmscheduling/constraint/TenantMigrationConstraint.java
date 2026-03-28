package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.TenantMigrationVariable;

import java.util.Map;

/**
 * Limits how many VMs of a single tenant can be on the same host,
 * based on per-tenant max_vm_num_per_group from the problem configuration.
 *
 * See MainWiki §5.5 / 03-constraints.md, data_schema.proto TenantDistributionParameter.
 */
public class TenantMigrationConstraint implements MigrationConstraint {

    private final MigrationFetcher<TenantMigrationVariable> fetcher;
    private final Map<String, Integer> maxVmsPerGroup; // tenantId → max VMs per host

    public TenantMigrationConstraint(MigrationFetcher<TenantMigrationVariable> fetcher,
                                      Map<String, Integer> maxVmsPerGroup) {
        this.fetcher = fetcher;
        this.maxVmsPerGroup = maxVmsPerGroup;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        TenantMigrationVariable variable = fetcher.fetch(solution);
        for (Map.Entry<String, Integer> entry : maxVmsPerGroup.entrySet()) {
            String tenantId = entry.getKey();
            int maxPerHost = entry.getValue();
            int[] counts = variable.getTenantHostCounts().get(tenantId);
            if (counts == null) continue;
            for (int count : counts) {
                if (count > maxPerHost) return false;
            }
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs can't violate max limit
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        String tenantId = vm.getTenantId();
        if (tenantId == null) return true;

        Integer maxPerHost = maxVmsPerGroup.get(tenantId);
        if (maxPerHost == null) return true;

        TenantMigrationVariable variable = fetcher.fetch(solution);
        int targetHostIdx = delta.getPlacement().getHost().getIndex();
        int projected = variable.getCount(tenantId, targetHostIdx) + 1;

        // Subtract if VM is already on target host
        Placement oldP = solution.getPlacement(vm);
        if (oldP != null && oldP.getHost().getIndex() == targetHostIdx) {
            projected--;
        }

        return projected <= maxPerHost;
    }
}
