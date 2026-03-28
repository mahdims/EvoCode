package com.vmscheduling.variable;

import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;

/**
 * Interface for precomputed, incrementally-maintained aggregate statistics
 * derived from the current solution state.
 *
 * These are NOT the decision variable — the decision variable is the
 * VM → Placement map in MigrationSolution.
 *
 * See MainWiki §4 / 02-incremental-evaluation.md.
 */
public interface MigrationVariable {

    /** Full recomputation from scratch — O(n), used at initialization */
    void update(Problem problem, MigrationSolution solution);

    /** Incremental: undo contribution of VMs removed in the ruin step — O(k) */
    void update(Problem problem, MigrationSolution solution, RuinDelta delta);

    /** Incremental: add contribution of VMs re-placed in the recreate step — O(k) */
    void update(Problem problem, MigrationSolution solution, RecreateDelta delta);

    /** Deep copy — used for copy-on-write in ALNS loop */
    MigrationVariable copy();
}
