package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;

/**
 * Test strategy that mimics Sequential removal.
 * Selects a random starting node and follows the route sequentially.
 *
 * This is a manual test case to validate the adapter pattern works correctly.
 */
public class SequentialTestStrategy implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        List<Node> toRemove = new ArrayList<>();

        while (toRemove.size() < numToRemove) {
            // Calculate how many more nodes to remove in this string
            int remainingToRemove = numToRemove - toRemove.size();
            int stringSize = Math.min(Math.max(1, nodes.length / 10), remainingToRemove);

            // Select random starting node that belongs to a route
            Node startNode = null;
            for (int attempt = 0; attempt < 100 && startNode == null; attempt++) {
                Node candidate = nodes[rand.nextInt(nodes.length)];
                if (candidate.nodeBelong) {
                    startNode = candidate;
                }
            }

            // If no valid start node found, break
            if (startNode == null) {
                break;
            }

            // Follow the route sequentially
            Node current = startNode;
            int count = 0;

            do {
                count++;
                current = current.next;

                // Skip depot
                if (current.name == 0) {
                    current = current.next;
                }

                // Add if not already added and belongs to route
                if (current.nodeBelong && !toRemove.contains(current)) {
                    toRemove.add(current);
                }

            } while (current.name != startNode.name && count < stringSize && toRemove.size() < numToRemove);
        }

        return toRemove.toArray(new Node[0]);
    }
}
