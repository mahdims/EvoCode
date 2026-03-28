package com.vmscheduling.delta;

import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.MigrationVariable;

/**
 * Delta representing VMs being removed from their placements.
 * Self-applying: delta.update(problem, solution) commits the ruin.
 *
 * CRITICAL: update() must read old placements BEFORE nulling them,
 * since variables need the old placement to subtract contributions.
 *
 * See MainWiki §4.3 / 02-incremental-evaluation.md.
 */
public class RuinDelta {

    private final Vm[] vms;

    public RuinDelta(Vm[] vms) {
        this.vms = vms;
    }

    public Vm[] getVms() {
        return vms;
    }

    /**
     * Commits the ruin: updates all variables incrementally, then nulls placements.
     * Order: (1) call variable updates (which read old placements) → (2) null placements.
     */
    public void update(Problem problem, MigrationSolution solution) {
        // Step 1: Update all variables (they read the old placement from solution)
        for (MigrationVariable variable : solution.getMigrationVariables()) {
            variable.update(problem, solution, this);
        }
        // Step 2: Null out the placements (VMs are now "unplaced")
        for (Vm vm : vms) {
            solution.setPlacement(vm, null);
        }
    }
}
