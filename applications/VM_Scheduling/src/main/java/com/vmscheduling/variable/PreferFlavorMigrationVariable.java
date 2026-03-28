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
 * Tracks remaining capacity for large-flavor (preferred) VMs on each host.
 * Prevents over-packing by reserving capacity for large-flavor VMs.
 *
 * The "prefer flavor" is a specific VM flavor (defined in problem parameters)
 * whose CPU/memory demands define the reservation threshold. For each host,
 * this variable tracks how many such VMs could still be placed given current usage.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class PreferFlavorMigrationVariable implements MigrationVariable {

    private int totalRemainingCapacity;
    private int[] hostRemainingCapacity;

    // Prefer flavor parameters (set from problem configuration)
    private float preferFlavorCpu;
    private float preferFlavorMem;
    private int preferFlavorNumaNums;

    private MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher;

    public PreferFlavorMigrationVariable() {}

    public PreferFlavorMigrationVariable(MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher,
                                         float preferFlavorCpu, float preferFlavorMem,
                                         int preferFlavorNumaNums) {
        this.cpuMemFetcher = cpuMemFetcher;
        this.preferFlavorCpu = preferFlavorCpu;
        this.preferFlavorMem = preferFlavorMem;
        this.preferFlavorNumaNums = preferFlavorNumaNums;
    }

    public int getTotalRemainingCapacity() { return totalRemainingCapacity; }
    public int getHostRemainingCapacity(int hostIndex) { return hostRemainingCapacity[hostIndex]; }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        int numHosts = problem.getHosts().size();
        hostRemainingCapacity = new int[numHosts];
        totalRemainingCapacity = 0;

        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);

        for (Host host : problem.getHosts()) {
            int capacity = computeHostCapacity(host, cpuMem);
            hostRemainingCapacity[host.getIndex()] = capacity;
            totalRemainingCapacity += capacity;
        }
    }

    private int computeHostCapacity(Host host, CpuMemMigrationVariable cpuMem) {
        int minCapacity = Integer.MAX_VALUE;
        for (NumaGroup group : host.getNumaGroups()) {
            if (group.getNumas().size() < preferFlavorNumaNums) continue;
            // For each numa, compute how many prefer-flavor VMs can fit
            for (Numa numa : group.getNumas()) {
                float remainCpu = numa.getCpu() - cpuMem.getNumaCpu(host.getIndex(), numa.getLocalIndex());
                float remainMem = numa.getMem() - cpuMem.getNumaMem(host.getIndex(), numa.getLocalIndex());
                int cpuFit = preferFlavorCpu > 0 ? (int) (remainCpu / preferFlavorCpu) : Integer.MAX_VALUE;
                int memFit = preferFlavorMem > 0 ? (int) (remainMem / preferFlavorMem) : Integer.MAX_VALUE;
                minCapacity = Math.min(minCapacity, Math.min(cpuFit, memFit));
            }
        }
        return minCapacity == Integer.MAX_VALUE ? 0 : Math.max(0, minCapacity);
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // Recompute for affected hosts
        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            Host host = p.getHost();
            int oldCap = hostRemainingCapacity[host.getIndex()];
            int newCap = computeHostCapacity(host, cpuMem);
            hostRemainingCapacity[host.getIndex()] = newCap;
            totalRemainingCapacity += (newCap - oldCap);
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);

        Placement oldP = solution.getPlacement(delta.getVm());
        if (oldP != null) {
            Host oldHost = oldP.getHost();
            int oldCap = hostRemainingCapacity[oldHost.getIndex()];
            int newCap = computeHostCapacity(oldHost, cpuMem);
            hostRemainingCapacity[oldHost.getIndex()] = newCap;
            totalRemainingCapacity += (newCap - oldCap);
        }

        Host newHost = delta.getPlacement().getHost();
        int oldCap = hostRemainingCapacity[newHost.getIndex()];
        int newCap = computeHostCapacity(newHost, cpuMem);
        hostRemainingCapacity[newHost.getIndex()] = newCap;
        totalRemainingCapacity += (newCap - oldCap);
    }

    @Override
    public MigrationVariable copy() {
        PreferFlavorMigrationVariable c = new PreferFlavorMigrationVariable();
        c.cpuMemFetcher = this.cpuMemFetcher;
        c.preferFlavorCpu = this.preferFlavorCpu;
        c.preferFlavorMem = this.preferFlavorMem;
        c.preferFlavorNumaNums = this.preferFlavorNumaNums;
        c.totalRemainingCapacity = this.totalRemainingCapacity;
        if (hostRemainingCapacity != null) {
            c.hostRemainingCapacity = Arrays.copyOf(hostRemainingCapacity, hostRemainingCapacity.length);
        }
        return c;
    }
}
