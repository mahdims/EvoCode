package com.vmscheduling.constraint;

import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;

/**
 * Interface for feasibility checking constraints.
 * All methods are projections — they evaluate the delta's effect WITHOUT mutating the solution.
 *
 * See MainWiki §5 / 03-constraints.md.
 */
public interface MigrationConstraint {

    /** Full check: is the entire solution feasible? */
    boolean satisfy(Problem problem, MigrationSolution solution);

    /** Incremental check after a ruin operation (VMs removed) — projection */
    boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta);

    /** Incremental check after a recreate operation (one VM placed) — projection */
    boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta);
}
