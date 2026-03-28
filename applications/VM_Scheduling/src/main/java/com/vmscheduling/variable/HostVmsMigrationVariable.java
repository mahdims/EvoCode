package com.vmscheduling.variable;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.util.AssignmentList;

/**
 * Tracks which VMs are currently on each host, with a separate list
 * for migratable VMs. Used by the ruin phase to find candidate VMs.
 *
 * See MainWiki §4.5 / 02-incremental-evaluation.md.
 */
public class HostVmsMigrationVariable implements MigrationVariable {

    private AssignmentList<Vm> hostVms;
    private AssignmentList<Vm> migratableHostVms;

    public AssignmentList<Vm> getHostVms() { return hostVms; }
    public AssignmentList<Vm> getMigratableHostVms() { return migratableHostVms; }

    @Override
    public void update(Problem problem, MigrationSolution solution) {
        int numHosts = problem.getHosts().size();
        hostVms = new AssignmentList<>(numHosts);
        migratableHostVms = new AssignmentList<>(numHosts);

        for (Vm vm : problem.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int hostIdx = p.getHost().getIndex();
            hostVms.get(hostIdx).add(vm);
            if (vm.isMigratable()) {
                migratableHostVms.get(hostIdx).add(vm);
            }
        }
    }

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p == null) continue;
            int hostIdx = p.getHost().getIndex();
            hostVms.get(hostIdx).remove(vm);
            if (vm.isMigratable()) {
                migratableHostVms.get(hostIdx).remove(vm);
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
            hostVms.get(oldHostIdx).remove(vm);
            if (vm.isMigratable()) {
                migratableHostVms.get(oldHostIdx).remove(vm);
            }
        }

        // Add to new host
        int newHostIdx = newP.getHost().getIndex();
        hostVms.get(newHostIdx).add(vm);
        if (vm.isMigratable()) {
            migratableHostVms.get(newHostIdx).add(vm);
        }
    }

    @Override
    public MigrationVariable copy() {
        HostVmsMigrationVariable c = new HostVmsMigrationVariable();
        if (hostVms != null) {
            c.hostVms = new AssignmentList<>(hostVms);
            c.migratableHostVms = new AssignmentList<>(migratableHostVms);
        }
        return c;
    }
}
