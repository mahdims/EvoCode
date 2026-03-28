package com.vmscheduling.solver;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.NumaGroup;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.util.Pair;
import com.vmscheduling.value.Value;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.util.LinkedList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Top-level solver interface.
 * Static helper methods for placement precomputation and recreate strategies.
 *
 * See MainWiki §7 / 05-placement-precomputation.md / 09-recreate-phase.md.
 */
public interface MigrationSolver {

    MigrationSolution solve(Problem problem);

    /**
     * Pre-build all structural placements indexed by numNumas.
     * allPlacements.get(k) = all placements using exactly k NUMAs, across all NumaGroups.
     */
    static List<List<Placement>> calculateAllPlacements(Problem problem) {
        // Find max numNumas across all VMs
        int maxNumNumas = 0;
        for (Vm vm : problem.getVms()) {
            maxNumNumas = Math.max(maxNumNumas, vm.getNumNumas());
        }

        List<List<Placement>> allPlacements = new ObjectArrayList<>();
        // Index 0 is unused (numNumas is 1-based), so add empty list at 0
        for (int k = 0; k <= maxNumNumas; k++) {
            allPlacements.add(new ObjectArrayList<>());
        }

        for (NumaGroup group : problem.getNumaGroups()) {
            for (int k = 1; k <= maxNumNumas; k++) {
                allPlacements.get(k).addAll(group.getPlacements(k));
            }
        }

        return allPlacements;
    }

    /**
     * Three-phase best placement selection:
     * Phase 1: Try initial placement (early exit if ≤ 0)
     * Phase 2: Scan all placements (early exit if ≤ 0)
     * Phase 3: Pick least-bad from worsening candidates
     *
     * Implementation provided in Phase 6/7.
     */
    static RecreateDelta getBestRecreate(Problem problem, MigrationSolution solution,
                                          Vm vm, List<Placement> placements) {
        List<Pair<RecreateDelta, Value>> deltaValuePairs = new LinkedList<>();

        // PHASE 1: Try initial placement first ("stay home" heuristic)
        RecreateDelta recreateDelta = new RecreateDelta(vm, vm.getInitialPlacement());
        if (problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
            Value newValue = problem.getMigrationObjective()
                    .calculate(problem, solution, recreateDelta);
            // CRITICAL FIX: Don't check compareToZero() - delta methods may return full values
            // Always collect candidates and pick minimum at end
            deltaValuePairs.add(Pair.of(recreateDelta, newValue));
        }

        // PHASE 2: Scan all candidate placements
        for (Placement placement : placements) {
            if (placement == vm.getInitialPlacement()) {
                continue; // already tried above
            }
            recreateDelta = new RecreateDelta(vm, placement);
            if (!problem.getMigrationConstraint().satisfy(problem, solution, recreateDelta)) {
                continue;
            }
            Value newValue = problem.getMigrationObjective()
                    .calculate(problem, solution, recreateDelta);
            // CRITICAL FIX: Don't check compareToZero() - collect all and pick minimum
            deltaValuePairs.add(Pair.of(recreateDelta, newValue));
        }

        // PHASE 3: Among all worsening-but-feasible, pick the least-bad
        RecreateDelta bestDelta = null;
        Value bestValue = null;
        for (Pair<RecreateDelta, Value> deltaValuePair : deltaValuePairs) {
            if (bestValue == null || deltaValuePair.right().compareTo(bestValue) < 0) {
                bestDelta = deltaValuePair.left();
                bestValue = deltaValuePair.right();
            }
        }
        return bestDelta; // null if nothing feasible at all
    }

    /**
     * Random feasible placement: shuffle → first feasible.
     * CRITICAL FIX: Try initial placement first to prevent false infeasibility.
     */
    static RecreateDelta getRandomRecreate(Problem problem, MigrationSolution solution,
                                            Vm vm, List<Placement> placements,
                                            SplittableRandom random) {
        // Try initial placement first (always feasible, prevents false infeasibility)
        RecreateDelta initialDelta = new RecreateDelta(vm, vm.getInitialPlacement());
        if (problem.getMigrationConstraint().satisfy(problem, solution, initialDelta)) {
            return initialDelta;
        }

        List<Placement> shuffled = new ObjectArrayList<>(placements);
        com.vmscheduling.util.AlgorithmUtil.shuffleList(shuffled, random);
        for (Placement placement : shuffled) {
            if (placement == vm.getInitialPlacement()) {
                continue; // already tried above
            }
            RecreateDelta delta = new RecreateDelta(vm, placement);
            if (problem.getMigrationConstraint().satisfy(problem, solution, delta)) {
                return delta;
            }
        }
        return null;
    }

    /**
     * First-fit: first feasible in natural order.
     * CRITICAL FIX: Try initial placement first to prevent false infeasibility.
     */
    static RecreateDelta getFirstFitRecreate(Problem problem, MigrationSolution solution,
                                              Vm vm, List<Placement> placements) {
        // Try initial placement first (always feasible, prevents false infeasibility)
        RecreateDelta initialDelta = new RecreateDelta(vm, vm.getInitialPlacement());
        if (problem.getMigrationConstraint().satisfy(problem, solution, initialDelta)) {
            return initialDelta;
        }

        for (Placement placement : placements) {
            if (placement == vm.getInitialPlacement()) {
                continue; // already tried above
            }
            RecreateDelta delta = new RecreateDelta(vm, placement);
            if (problem.getMigrationConstraint().satisfy(problem, solution, delta)) {
                return delta;
            }
        }
        return null;
    }
}
