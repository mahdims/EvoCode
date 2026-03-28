package com.vmscheduling.variable;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Numa;
import com.vmscheduling.model.NumaGroup;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;

import java.util.Arrays;

/**
 * Tracks load metric per host for load balancing objectives.
 * Load is defined as max(cpu_ratio, mem_ratio) across all NUMAs on the host.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class LoadVariable implements MigrationVariable {

    private float[] hostLoads;
    private MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher;

    public LoadVariable() {}

    public LoadVariable(MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher) {
        this.cpuMemFetcher = cpuMemFetcher;
    }

    public float[] getHostLoads() { return hostLoads; }
    public float getHostLoad(int hostIndex) { return hostLoads[hostIndex]; }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        int numHosts = problem.getHosts().size();
        hostLoads = new float[numHosts];

        for (Host host : problem.getHosts()) {
            hostLoads[host.getIndex()] = computeHostLoad(host, problem, solution);
        }
    }

    private float computeHostLoad(Host host, Problem problem, MigrationSolution solution) {
        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);
        float maxLoad = 0;
        for (NumaGroup group : host.getNumaGroups()) {
            for (Numa numa : group.getNumas()) {
                float cpuRatio = numa.getCpu() > 0 ?
                        cpuMem.getNumaCpu(host.getIndex(), numa.getLocalIndex()) / numa.getCpu() : 0;
                float memRatio = numa.getMem() > 0 ?
                        cpuMem.getNumaMem(host.getIndex(), numa.getLocalIndex()) / numa.getMem() : 0;
                maxLoad = Math.max(maxLoad, Math.max(cpuRatio, memRatio));
            }
        }
        return maxLoad;
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // Recompute load for affected hosts
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            Host host = p.getHost();
            hostLoads[host.getIndex()] = computeHostLoad(host, problem, solution);
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Placement oldP = solution.getPlacement(delta.getVm());
        Placement newP = delta.getPlacement();

        if (oldP != null) {
            Host oldHost = oldP.getHost();
            hostLoads[oldHost.getIndex()] = computeHostLoad(oldHost, problem, solution);
        }

        Host newHost = newP.getHost();
        hostLoads[newHost.getIndex()] = computeHostLoad(newHost, problem, solution);
    }

    @Override
    public MigrationVariable copy() {
        LoadVariable c = new LoadVariable();
        c.cpuMemFetcher = this.cpuMemFetcher;
        if (hostLoads != null) {
            c.hostLoads = Arrays.copyOf(hostLoads, hostLoads.length);
        }
        return c;
    }
}
