package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;

/**
 * Simple interface for LLM-generated destroy logic.
 * Implementations specify which nodes to remove from a CVRP solution.
 *
 * The destroy strategy is responsible for selecting nodes to remove.
 * Repair is handled by AILS's standard addCandidates() logic.
 */
public interface DestroyStrategy {

    /**
     * Select which nodes to remove from the current solution.
     *
     * @param numToRemove - target number of nodes to remove (omega)
     * @param routes      - array of all routes in current solution
     * @param numRoutes   - number of active routes
     * @param nodes       - array of all customer nodes (excluding depot)
     * @param instance    - problem instance (distances, KNN, etc.)
     * @param rand        - random number generator (use this, don't create new
     *                    Random)
     *
     * @return array of nodes to remove (size <= numToRemove)
     *
     *         CONSTRAINTS:
     *         - Returned array size must be <= numToRemove
     *         - Only return nodes where node.nodeBelong == true
     *         - Never return depot nodes (node.name == 0)
     *         - No duplicates in returned array
     *         - Use provided Random instance for reproducibility
     */
    Node[] selectNodesToRemove(
            int numToRemove,
            Route[] routes,
            int numRoutes,
            Node[] nodes,
            Instance instance,
            Random rand);
}
