package com.vmscheduling.variable;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;

import java.util.Arrays;

/**
 * Tracks the count of fully empty hosts and per-host VM counts.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class EmptyHostMigrationVariable implements MigrationVariable {

    private int numEmptyHost;
    private int[] hostVmCount;

    public int getNumEmptyHost() { return numEmptyHost; }
    public int getHostVmCount(int hostIndex) { return hostVmCount[hostIndex]; }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        int numHosts = problem.getHosts().size();
        hostVmCount = new int[numHosts];
        numEmptyHost = 0;

        for (Vm vm : problem.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            hostVmCount[p.getHost().getIndex()]++;
        }

        for (Host host : problem.getHosts()) {
            if (hostVmCount[host.getIndex()] == 0) {
                numEmptyHost++;
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int hostIdx = p.getHost().getIndex();
            hostVmCount[hostIdx]--;
            if (hostVmCount[hostIdx] == 0) {
                numEmptyHost++;
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        Placement oldP = solution.getPlacement(vm);
        Placement newP = delta.getPlacement();

        // Remove from old host
        if (oldP != null) {
            int oldHostIdx = oldP.getHost().getIndex();
            hostVmCount[oldHostIdx]--;
            if (hostVmCount[oldHostIdx] == 0) {
                numEmptyHost++;
            }
        }

        // Add to new host
        int newHostIdx = newP.getHost().getIndex();
        if (hostVmCount[newHostIdx] == 0) {
            numEmptyHost--;
        }
        hostVmCount[newHostIdx]++;
    }

    @Override
    public MigrationVariable copy() {
        EmptyHostMigrationVariable c = new EmptyHostMigrationVariable();
        c.numEmptyHost = this.numEmptyHost;
        if (hostVmCount != null) {
            c.hostVmCount = Arrays.copyOf(hostVmCount, hostVmCount.length);
        }
        return c;
    }
}
