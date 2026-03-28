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
 * Tracks per-NUMA CPU and memory usage across all hosts.
 * Internal state: float[][] numaCpu[hostIndex][numaLocalIndex],
 *                 float[][] numaMem[hostIndex][numaLocalIndex].
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class CpuMemMigrationVariable implements MigrationVariable {

    private float[][] numaCpu;  // [hostIndex][numaLocalIndex] = used CPU
    private float[][] numaMem;  // [hostIndex][numaLocalIndex] = used Memory

    public float[][] getNumaCpu() { return numaCpu; }
    public float[][] getNumaMem() { return numaMem; }

    public float getNumaCpu(int hostIndex, int numaLocalIndex) {
        return numaCpu[hostIndex][numaLocalIndex];
    }

    public float getNumaMem(int hostIndex, int numaLocalIndex) {
        return numaMem[hostIndex][numaLocalIndex];
    }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        // Initialize arrays
        int numHosts = problem.getHosts().size();
        numaCpu = new float[numHosts][];
        numaMem = new float[numHosts][];
        for (Host host : problem.getHosts()) {
            int maxNumas = 0;
            for (NumaGroup group : host.getNumaGroups()) {
                maxNumas = Math.max(maxNumas, group.getNumas().size());
            }
            numaCpu[host.getIndex()] = new float[maxNumas];
            numaMem[host.getIndex()] = new float[maxNumas];
        }

        // Full recompute: iterate all VMs
        for (Vm vm : problem.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int hostIdx = p.getHost().getIndex();
            for (Numa numa : p.getNumas()) {
                numaCpu[hostIdx][numa.getLocalIndex()] += vm.getNumaCpu();
                numaMem[hostIdx][numa.getLocalIndex()] += vm.getNumaMem();
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // Subtract contributions of ruined VMs (placements still readable)
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int hostIdx = p.getHost().getIndex();
            for (Numa numa : p.getNumas()) {
                numaCpu[hostIdx][numa.getLocalIndex()] -= vm.getNumaCpu();
                numaMem[hostIdx][numa.getLocalIndex()] -= vm.getNumaMem();
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        Placement newP = delta.getPlacement();
        Placement oldP = solution.getPlacement(vm);

        // Subtract from old placement (if VM was placed somewhere)
        if (oldP != null) {
            int oldHostIdx = oldP.getHost().getIndex();
            for (Numa numa : oldP.getNumas()) {
                numaCpu[oldHostIdx][numa.getLocalIndex()] -= vm.getNumaCpu();
                numaMem[oldHostIdx][numa.getLocalIndex()] -= vm.getNumaMem();
            }
        }

        // Add to new placement
        int newHostIdx = newP.getHost().getIndex();
        for (Numa numa : newP.getNumas()) {
            numaCpu[newHostIdx][numa.getLocalIndex()] += vm.getNumaCpu();
            numaMem[newHostIdx][numa.getLocalIndex()] += vm.getNumaMem();
        }
    }

    @Override
    public MigrationVariable copy() {
        CpuMemMigrationVariable c = new CpuMemMigrationVariable();
        if (numaCpu != null) {
            c.numaCpu = new float[numaCpu.length][];
            c.numaMem = new float[numaMem.length][];
            for (int i = 0; i < numaCpu.length; i++) {
                c.numaCpu[i] = Arrays.copyOf(numaCpu[i], numaCpu[i].length);
                c.numaMem[i] = Arrays.copyOf(numaMem[i], numaMem[i].length);
            }
        }
        return c;
    }
}
