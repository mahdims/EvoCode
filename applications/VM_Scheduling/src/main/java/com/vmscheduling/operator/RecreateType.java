package com.vmscheduling.operator;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.solver.MigrationSolver;

import java.util.List;
import java.util.SplittableRandom;

/**
 * Placement strategies for displaced VMs during the recreate phase.
 * All iterate over VMs in order and commit each placement immediately.
 *
 * See MainWiki §7.3 / 07-operator-types.md / 09-recreate-phase.md.
 */
public enum RecreateType {

    /** Evaluate ALL candidate placements; pick best objective. Most expensive, highest quality. */
    BEST {
        public boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                                List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                                SplittableRandom random) {
            for (Vm vm : vms) {
                RecreateDelta bestDelta = MigrationSolver.getBestRecreate(
                        problem, solution, vm, allPlacements.get(vm.getNumNumas()));
                recreateDeltas.add(bestDelta);
                if (bestDelta == null) return false;
                bestDelta.update(problem, solution);
            }
            return true;
        }
    },

    /** Pick a uniformly random feasible placement. Cheap, adds stochasticity. */
    RANDOM {
        public boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                                List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                                SplittableRandom random) {
            for (Vm vm : vms) {
                RecreateDelta randomDelta = MigrationSolver.getRandomRecreate(
                        problem, solution, vm, allPlacements.get(vm.getNumNumas()), random);
                recreateDeltas.add(randomDelta);
                if (randomDelta == null) return false;
                randomDelta.update(problem, solution);
            }
            return true;
        }
    },

    /** Pick the FIRST feasible placement in candidate order. Faster than BEST, deterministic. */
    FirstFit {
        public boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                                List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                                SplittableRandom random) {
            for (Vm vm : vms) {
                RecreateDelta firstFitDelta = MigrationSolver.getFirstFitRecreate(
                        problem, solution, vm, allPlacements.get(vm.getNumNumas()));
                recreateDeltas.add(firstFitDelta);
                if (firstFitDelta == null) return false;
                firstFitDelta.update(problem, solution);
            }
            return true;
        }
    };

    public abstract boolean recreate(Problem problem, MigrationSolution solution, List<Vm> vms,
                                      List<RecreateDelta> recreateDeltas, List<List<Placement>> allPlacements,
                                      SplittableRandom random);
}
