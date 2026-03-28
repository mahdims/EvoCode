package com.vmscheduling.constraint;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/**
 * Composite constraint — AND semantics with short-circuit.
 * Checks constraints in registration order; first failure stops evaluation.
 *
 * See MainWiki §5.2 / 03-constraints.md.
 */
public class HierarchicalMigrationConstraint implements MigrationConstraint {

    private static final Logger log = LoggerFactory.getLogger(HierarchicalMigrationConstraint.class);

    private final List<MigrationConstraint> constraints;

    private HierarchicalMigrationConstraint(List<MigrationConstraint> constraints) {
        this.constraints = constraints;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution) {
        for (MigrationConstraint c : constraints) {
            if (!c.satisfy(problem, solution)) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (MigrationConstraint c : constraints) {
            if (!c.satisfy(problem, solution, delta)) return false;
        }
        return true;
    }

    @Override
    public boolean satisfy(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        for (MigrationConstraint c : constraints) {
            if (!c.satisfy(problem, solution, delta)) {
                log.debug("Constraint FAILED: {} for VM {} -> Host {} ({})",
                        c.getClass().getSimpleName(),
                        delta.getVm().getIndex(),
                        delta.getHost().getIndex(),
                        delta.isInitial() ? "initial" : "migration");
                return false;
            }
        }
        return true;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final List<MigrationConstraint> constraints = new ObjectArrayList<>();

        public Builder constraint(MigrationConstraint c) {
            constraints.add(c);
            return this;
        }

        public HierarchicalMigrationConstraint build() {
            return new HierarchicalMigrationConstraint(new ObjectArrayList<>(constraints));
        }
    }
}
