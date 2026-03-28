package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.ListValue;
import com.vmscheduling.value.Value;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.util.List;

/**
 * Composite objective with lexicographic comparison.
 * Primary objectives are always computed; minor objectives are lazy
 * (only computed when primary values tie).
 *
 * Returns a ListValue containing all objective values in priority order.
 *
 * See MainWiki §6.3-6.6 / 04-objectives.md.
 */
public class HierarchicalMigrationObjective implements MigrationObjective {

    private final List<MigrationObjective> objectives;
    private final List<MigrationObjective> minorObjectives;

    private HierarchicalMigrationObjective(List<MigrationObjective> objectives,
                                            List<MigrationObjective> minorObjectives) {
        this.objectives = objectives;
        this.minorObjectives = minorObjectives;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        Value[] values = new Value[objectives.size() + minorObjectives.size()];
        for (int i = 0; i < objectives.size(); i++) {
            values[i] = objectives.get(i).calculate(problem, solution);
        }
        for (int i = 0; i < minorObjectives.size(); i++) {
            values[objectives.size() + i] = minorObjectives.get(i).calculate(problem, solution);
        }
        return ListValue.of(values);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        Value[] values = new Value[objectives.size() + minorObjectives.size()];
        for (int i = 0; i < objectives.size(); i++) {
            values[i] = objectives.get(i).calculate(problem, solution, delta);
        }
        for (int i = 0; i < minorObjectives.size(); i++) {
            values[objectives.size() + i] = minorObjectives.get(i).calculate(problem, solution, delta);
        }
        return ListValue.of(values);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Value[] values = new Value[objectives.size() + minorObjectives.size()];
        for (int i = 0; i < objectives.size(); i++) {
            values[i] = objectives.get(i).calculate(problem, solution, delta);
        }
        for (int i = 0; i < minorObjectives.size(); i++) {
            values[objectives.size() + i] = minorObjectives.get(i).calculate(problem, solution, delta);
        }
        return ListValue.of(values);
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final List<MigrationObjective> objectives = new ObjectArrayList<>();
        private final List<MigrationObjective> minorObjectives = new ObjectArrayList<>();

        public Builder objective(MigrationObjective o) {
            objectives.add(o);
            return this;
        }

        public Builder minorObjective(MigrationObjective o, boolean lazy) {
            minorObjectives.add(o);
            return this;
        }

        public HierarchicalMigrationObjective build() {
            return new HierarchicalMigrationObjective(
                    new ObjectArrayList<>(objectives),
                    new ObjectArrayList<>(minorObjectives));
        }
    }
}
