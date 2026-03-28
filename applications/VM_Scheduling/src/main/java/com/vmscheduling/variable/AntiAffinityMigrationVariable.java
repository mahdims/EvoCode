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
 * Tracks per-host counts for each anti-affinity group.
 * Used to enforce that no two members of the same group land on the same host.
 *
 * Internal state: Map<groupId, int[hostIndex]> — count of group members per host.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class AntiAffinityMigrationVariable implements MigrationVariable {

    private Map<String, int[]> groupHostCounts;
    private int numHosts;

    public Map<String, int[]> getGroupHostCounts() { return groupHostCounts; }

    public int getCount(String groupId, int hostIndex) {
        int[] counts = groupHostCounts.get(groupId);
        return counts == null ? 0 : counts[hostIndex];
    }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        numHosts = problem.getHosts().size();
        groupHostCounts = new HashMap<>();

        for (Vm vm : problem.getVms()) {
            String groupId = vm.getAntiAffinityGroupId();
            if (groupId == null) continue;
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            groupHostCounts.computeIfAbsent(groupId, k -> new int[numHosts]);
            groupHostCounts.get(groupId)[p.getHost().getIndex()]++;
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (Vm vm : delta.getVms()) {
            String groupId = vm.getAntiAffinityGroupId();
            if (groupId == null) continue;
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int[] counts = groupHostCounts.get(groupId);
            if (counts != null) {
                counts[p.getHost().getIndex()]--;
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        String groupId = vm.getAntiAffinityGroupId();
        if (groupId == null) return;

        Placement oldP = solution.getPlacement(vm);
        Placement newP = delta.getPlacement();

        int[] counts = groupHostCounts.computeIfAbsent(groupId, k -> new int[numHosts]);

        if (oldP != null) {
            counts[oldP.getHost().getIndex()]--;
        }
        counts[newP.getHost().getIndex()]++;
    }

    @Override
    public MigrationVariable copy() {
        AntiAffinityMigrationVariable c = new AntiAffinityMigrationVariable();
        c.numHosts = this.numHosts;
        if (groupHostCounts != null) {
            c.groupHostCounts = new HashMap<>();
            for (Map.Entry<String, int[]> entry : groupHostCounts.entrySet()) {
                c.groupHostCounts.put(entry.getKey(), Arrays.copyOf(entry.getValue(), entry.getValue().length));
            }
        }
        return c;
    }
}
