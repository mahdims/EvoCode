package com.vmscheduling.variable;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * Tracks per-tenant per-host VM counts.
 * Used by TenantMigrationConstraint to limit how many VMs of a single tenant
 * can be migrated simultaneously, and by TenantMigrationObjective for
 * distribution spread metrics.
 *
 * Internal state: Map<tenantId, int[hostIndex]> — count of tenant VMs per host.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class TenantMigrationVariable implements MigrationVariable {

    private Map<String, int[]> tenantHostCounts;
    private int numHosts;

    public Map<String, int[]> getTenantHostCounts() { return tenantHostCounts; }

    public int getCount(String tenantId, int hostIndex) {
        int[] counts = tenantHostCounts.get(tenantId);
        return counts == null ? 0 : counts[hostIndex];
    }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        numHosts = problem.getHosts().size();
        tenantHostCounts = new HashMap<>();

        for (Vm vm : problem.getVms()) {
            String tenantId = vm.getTenantId();
            if (tenantId == null) continue;
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            tenantHostCounts.computeIfAbsent(tenantId, k -> new int[numHosts]);
            tenantHostCounts.get(tenantId)[p.getHost().getIndex()]++;
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (Vm vm : delta.getVms()) {
            String tenantId = vm.getTenantId();
            if (tenantId == null) continue;
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int[] counts = tenantHostCounts.get(tenantId);
            if (counts != null) {
                counts[p.getHost().getIndex()]--;
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        String tenantId = vm.getTenantId();
        if (tenantId == null) return;

        Placement oldP = solution.getPlacement(vm);
        Placement newP = delta.getPlacement();

        int[] counts = tenantHostCounts.computeIfAbsent(tenantId, k -> new int[numHosts]);

        if (oldP != null) {
            counts[oldP.getHost().getIndex()]--;
        }
        counts[newP.getHost().getIndex()]++;
    }

    @Override
    public MigrationVariable copy() {
        TenantMigrationVariable c = new TenantMigrationVariable();
        c.numHosts = this.numHosts;
        if (tenantHostCounts != null) {
            c.tenantHostCounts = new HashMap<>();
            for (Map.Entry<String, int[]> entry : tenantHostCounts.entrySet()) {
                c.tenantHostCounts.put(entry.getKey(),
                        Arrays.copyOf(entry.getValue(), entry.getValue().length));
            }
        }
        return c;
    }
}
