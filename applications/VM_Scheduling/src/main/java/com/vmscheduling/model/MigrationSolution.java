package com.vmscheduling.model;

import com.vmscheduling.variable.MigrationVariable;
import lombok.Getter;
import lombok.Setter;

import java.util.Arrays;

/**
 * The decision variable: a Placement[] array indexed by vm.getIndex(),
 * plus the variable instances for incremental evaluation.
 *
 * Three constructors:
 *   1. From Problem — all VMs at initial placements, full variable compute
 *   2. Deep copy — for working candidates in ALNS inner loop
 *   3. Shallow copy — for best-solution storage (variables recomputed later)
 *
 * See MainWiki §3.8 / 01-data-structures.md.
 */
public class MigrationSolution {

    private Placement[] placements;
    @Getter private MigrationVariable[] migrationVariables;
    @Getter @Setter private OptimizationTrackData optimizationTrackData;

    /**
     * Constructor 1: Initialize from Problem.
     * Places all VMs at their initial placements, then does a full variable recompute.
     */
    public MigrationSolution(Problem problem) {
        migrationVariables = new MigrationVariable[problem.getMigrationVariableSuppliers().size()];
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = problem.getMigrationVariableSuppliers().get(i).get();
        }
        placements = new Placement[problem.getVms().size()];
        for (Vm vm : problem.getVms()) {
            placements[vm.getIndex()] = vm.getInitialPlacement();
        }
        updateMigrationVariables(problem);
    }

    /**
     * Constructor 1b: Initialize from Problem with custom placements.
     * Used for testing with unbalanced initial solutions.
     * Does a full variable recompute with the provided placements.
     */
    public MigrationSolution(Problem problem, Placement[] customPlacements) {
        migrationVariables = new MigrationVariable[problem.getMigrationVariableSuppliers().size()];
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = problem.getMigrationVariableSuppliers().get(i).get();
        }
        this.placements = customPlacements;
        updateMigrationVariables(problem);
    }

    /**
     * Constructor 2: Deep copy for working candidates in ALNS inner loop.
     * Copies placements array and deep-copies every variable via copy().
     */
    public MigrationSolution(MigrationSolution other) {
        this.placements = Arrays.copyOf(other.placements, other.placements.length);
        this.migrationVariables = new MigrationVariable[other.migrationVariables.length];
        for (int i = 0; i < migrationVariables.length; i++) {
            migrationVariables[i] = other.migrationVariables[i].copy();
        }
    }

    /**
     * Constructor 3: Shallow copy for best-solution storage.
     * When copyVariables=false, only copies placements (variables recomputed at end).
     * When copyVariables=true, behaves like the deep copy constructor.
     */
    public MigrationSolution(MigrationSolution other, boolean copyVariables) {
        this.placements = Arrays.copyOf(other.placements, other.placements.length);
        if (copyVariables) {
            this.migrationVariables = new MigrationVariable[other.migrationVariables.length];
            for (int i = 0; i < migrationVariables.length; i++) {
                migrationVariables[i] = other.migrationVariables[i].copy();
            }
        } else {
            this.migrationVariables = other.migrationVariables;
        }
    }

    public Placement getPlacement(Vm vm) {
        return placements[vm.getIndex()];
    }

    public void setPlacement(Vm vm, Placement placement) {
        placements[vm.getIndex()] = placement;
    }

    /**
     * Full O(n) recompute of all variables from scratch.
     * Called at initialization and before returning the final best solution.
     */
    public void updateMigrationVariables(Problem problem) {
        for (MigrationVariable variable : migrationVariables) {
            variable.update(problem, this);
        }
    }
}
