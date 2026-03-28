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
import java.util.HashMap;
import java.util.Map;

/**
 * Tracks NUMA resource usage relative to a configurable "cutting line" threshold.
 * Prevents packing NUMAs above the threshold (e.g., 90%) to reserve headroom.
 *
 * Each VM has a cuttingLineTag that maps to a specific threshold.
 * This variable tracks the total excess above threshold across all NUMAs.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class NumaResourceCuttingLineMigrationVariable implements MigrationVariable {

    private float totalExcess;
    private float[][] numaExcess; // [hostIndex][numaLocalIndex]

    private MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher;
    private Map<String, Float> cuttingLineThresholds; // tag → threshold ratio (e.g. 0.9)

    public NumaResourceCuttingLineMigrationVariable() {
        this.cuttingLineThresholds = new HashMap<>();
    }

    public NumaResourceCuttingLineMigrationVariable(
            MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher,
            Map<String, Float> cuttingLineThresholds) {
        this.cpuMemFetcher = cpuMemFetcher;
        this.cuttingLineThresholds = cuttingLineThresholds;
    }

    public float getTotalExcess() { return totalExcess; }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        int numHosts = problem.getHosts().size();
        numaExcess = new float[numHosts][];
        totalExcess = 0;

        for (Host host : problem.getHosts()) {
            int maxNumas = 0;
            for (NumaGroup group : host.getNumaGroups()) {
                maxNumas = Math.max(maxNumas, group.getNumas().size());
            }
            numaExcess[host.getIndex()] = new float[maxNumas];
        }

        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);

        for (Host host : problem.getHosts()) {
            for (NumaGroup group : host.getNumaGroups()) {
                for (Numa numa : group.getNumas()) {
                    float threshold = getEffectiveThreshold(host);
                    float cpuUsed = cpuMem.getNumaCpu(host.getIndex(), numa.getLocalIndex());
                    float memUsed = cpuMem.getNumaMem(host.getIndex(), numa.getLocalIndex());
                    float cpuExcess = Math.max(0, cpuUsed - numa.getCpu() * threshold);
                    float memExcess = Math.max(0, memUsed - numa.getMem() * threshold);
                    float excess = cpuExcess + memExcess;
                    numaExcess[host.getIndex()][numa.getLocalIndex()] = excess;
                    totalExcess += excess;
                }
            }
        }
    }

    private float getEffectiveThreshold(Host host) {
        // Default threshold if no specific cutting line tag applies
        return cuttingLineThresholds.getOrDefault("default", 0.9f);
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // Full recompute for affected hosts
        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            recomputeHost(p.getHost(), cpuMem);
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        CpuMemMigrationVariable cpuMem = cpuMemFetcher.fetch(solution);

        Placement oldP = solution.getPlacement(delta.getVm());
        if (oldP != null) {
            recomputeHost(oldP.getHost(), cpuMem);
        }
        recomputeHost(delta.getPlacement().getHost(), cpuMem);
    }

    private void recomputeHost(Host host, CpuMemMigrationVariable cpuMem) {
        float threshold = getEffectiveThreshold(host);
        int hostIdx = host.getIndex();
        for (NumaGroup group : host.getNumaGroups()) {
            for (Numa numa : group.getNumas()) {
                float oldExcess = numaExcess[hostIdx][numa.getLocalIndex()];
                float cpuUsed = cpuMem.getNumaCpu(hostIdx, numa.getLocalIndex());
                float memUsed = cpuMem.getNumaMem(hostIdx, numa.getLocalIndex());
                float cpuExcess = Math.max(0, cpuUsed - numa.getCpu() * threshold);
                float memExcess = Math.max(0, memUsed - numa.getMem() * threshold);
                float newExcess = cpuExcess + memExcess;
                numaExcess[hostIdx][numa.getLocalIndex()] = newExcess;
                totalExcess += (newExcess - oldExcess);
            }
        }
    }

    @Override
    public MigrationVariable copy() {
        NumaResourceCuttingLineMigrationVariable c = new NumaResourceCuttingLineMigrationVariable();
        c.cpuMemFetcher = this.cpuMemFetcher;
        c.cuttingLineThresholds = this.cuttingLineThresholds;
        c.totalExcess = this.totalExcess;
        if (numaExcess != null) {
            c.numaExcess = new float[numaExcess.length][];
            for (int i = 0; i < numaExcess.length; i++) {
                c.numaExcess[i] = Arrays.copyOf(numaExcess[i], numaExcess[i].length);
            }
        }
        return c;
    }
}
