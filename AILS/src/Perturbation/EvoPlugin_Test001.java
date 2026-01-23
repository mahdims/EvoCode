package Perturbation;

import java.util.HashMap;

import Data.Instance;
import DiversityControl.OmegaAdjustment;
import Improvement.IntraLocalSearch;
import SearchMethod.Config;
import Solution.Node;
import Solution.Solution;
import EvoDestroy.*;

/**
 * Adapter wrapper for SequentialTestStrategy.
 * Bridges the simple DestroyStrategy interface to AILS Perturbation pattern.
 *
 * AUTO-GENERATED PATTERN (manually created for Phase 1 testing)
 */
public class EvoPlugin_Test001 extends Perturbation {

    private DestroyStrategy strategy;

    public EvoPlugin_Test001(
        Instance instance,
        Config config,
        HashMap<String, OmegaAdjustment> omegaSetup,
        IntraLocalSearch intraLocalSearch
    ) {
        super(instance, config, omegaSetup, intraLocalSearch);
        this.perturbationType = PerturbationType.Sequential; // Reuse type for testing
        this.strategy = new SequentialTestStrategy();
    }

    @Override
    public void applyPerturbation(Solution s) {
        // Standard AILS pattern
        setSolution(s);

        // DESTROY: Use strategy to select nodes
        Node[] toRemove = strategy.selectNodesToRemove(
            (int) omega,        // Adaptive parameter from OmegaAdjustment
            routes,
            numRoutes,
            solution,
            instance,
            rand
        );

        // Remove selected nodes and add to candidates array
        for (Node node : toRemove) {
            if (node != null && node.nodeBelong && node.name != 0) {
                candidates[countCandidates++] = node;

                // Save old positions for potential restoration
                node.prevOld = node.prev;
                node.nextOld = node.next;

                // Remove from route and update cost
                f += node.route.remove(node);
            }
        }

        // REPAIR: Use standard AILS repair logic (unchanged)
        setOrder();           // Randomize insertion order
        addCandidates();      // Greedy KNN-based insertion

        // Finalize changes
        assignSolution(s);
    }
}
