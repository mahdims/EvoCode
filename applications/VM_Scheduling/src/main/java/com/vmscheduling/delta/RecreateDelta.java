package com.vmscheduling.delta;

import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.MigrationVariable;

/**
 * Delta representing a VM being placed at a target placement.
 * Self-applying: delta.update(problem, solution) commits the placement.
 *
 * The old placement is implicit from the current solution state.
 *
 * See MainWiki §4.3 / 02-incremental-evaluation.md.
 */
public class RecreateDelta {

    private final Vm vm;
    private final Placement placement;  // target (new) placement

    public RecreateDelta(Vm vm, Placement placement) {
        this.vm = vm;
        this.placement = placement;
    }

    public Vm getVm() {
        return vm;
    }

    public Placement getPlacement() {
        return placement;
    }

    public Host getHost() {
        return placement.getHost();
    }

    /**
     * Returns true if this delta places the VM back at its initial placement
     * (i.e., no migration needed).
     */
    public boolean isInitial() {
        return placement == vm.getInitialPlacement();
    }

    /**
     * Commits the placement: updates all variables incrementally, then sets the placement.
     * Variables read old placement from solution.getPlacement(vm) and new from this delta.
     */
    public void update(Problem problem, MigrationSolution solution) {
        // Step 1: Update all variables (they read old placement and use new placement)
        for (MigrationVariable variable : solution.getMigrationVariables()) {
            variable.update(problem, solution, this);
        }
        // Step 2: Set the new placement
        solution.setPlacement(vm, placement);
    }
}
