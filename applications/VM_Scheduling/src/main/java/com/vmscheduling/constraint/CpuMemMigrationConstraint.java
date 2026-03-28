package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Numa;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.CpuMemMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

/**
 * Hard constraint: NUMA-level CPU and memory capacity.
 * Ensures usedCPU <= capacity AND usedMem <= capacity for every NUMA node.
 *
 * RecreateDelta: simulates the placement and checks only the target host.
 * RuinDelta: always true (removing VMs can't violate capacity).
 *
 * See MainWiki §5.4 / 03-constraints.md.
 */
public class CpuMemMigrationConstraint implements MigrationConstraint {

    private final MigrationFetcher<CpuMemMigrationVariable> fetcher;

    public CpuMemMigrationConstraint(MigrationFetcher<CpuMemMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        CpuMemMigrationVariable variable = fetcher.fetch(solution);
        for (Numa numa : problem.getNumas()) {
            Host host = numa.getNumaGroup().getHost();
            if (variable.getNumaCpu(host.getIndex(), numa.getLocalIndex()) > numa.getCpu()) return false;
            if (variable.getNumaMem(host.getIndex(), numa.getLocalIndex()) > numa.getMem()) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return true; // Removing VMs can't violate capacity
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        CpuMemMigrationVariable variable = fetcher.fetch(solution);
        Vm vm = delta.getVm();
        Placement newP = delta.getPlacement();
        Host targetHost = newP.getHost();

        // Simulate: add VM's resources to target, check capacity
        for (Numa numa : newP.getNumas()) {
            float projectedCpu = variable.getNumaCpu(targetHost.getIndex(), numa.getLocalIndex())
                    + vm.getNumaCpu();
            float projectedMem = variable.getNumaMem(targetHost.getIndex(), numa.getLocalIndex())
                    + vm.getNumaMem();

            // Subtract from old placement if same host (intra-host move)
            Placement oldP = solution.getPlacement(vm);
            if (oldP != null && oldP.getHost() == targetHost) {
                for (Numa oldNuma : oldP.getNumas()) {
                    if (oldNuma.getLocalIndex() == numa.getLocalIndex()) {
                        projectedCpu -= vm.getNumaCpu();
                        projectedMem -= vm.getNumaMem();
                    }
                }
            }

            if (projectedCpu > numa.getCpu()) return false;
            if (projectedMem > numa.getMem()) return false;
        }
        return true;
    }
}
