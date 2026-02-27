"""
AILS VRP — Seed Templates and LLM Constraints

Contains the mandatory AILS adapter contract (AILS_CONSTRAINTS) and three
seed DestroyStrategy implementations used to bootstrap the initial population.
"""

from typing import List, Tuple


# ---------------------------------------------------------------------------
# LLM context strings
# ---------------------------------------------------------------------------

AILS_CONSTRAINTS = """
=== MANDATORY AILS ADAPTER CONTRACT ===
These requirements are NON-NEGOTIABLE. Violating any will cause runtime failure.

**PACKAGE & CLASS STRUCTURE:**
1. Package MUST be: package EvoDestroy;
2. Class MUST implement: DestroyStrategy interface
3. Class MUST have default constructor (no-arg): public ClassName() {}

**METHOD SIGNATURE (EXACT):**
Node[] selectNodesToRemove(int numToRemove, Route[] routes, int numRoutes,
                           Node[] nodes, Instance instance, Random rand)

**CRITICAL CONSTRAINTS:**
1. RETURN SIZE: Array size MUST be <= numToRemove (AILS will fail if more)
2. NODE VALIDATION: Only return nodes where:
   - node.nodeBelong == true (node is currently in a route)
   - node.name != 0 (never return depot)
3. NO DUPLICATES: Each node in returned array must be unique
4. USE PROVIDED RANDOM: Always use 'rand' parameter, NEVER create new Random()
5. NO I/O: No file operations, no System.out, no network calls
6. NO NEW DEPENDENCIES: Only use imports listed below
7. SINGLE CLASS: One class per file, no inner classes
8. DETERMINISTIC: Same seed must produce same selection

**REQUIRED IMPORTS:**
import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

**AVAILABLE DATA (read-only):**
- nodes[i]: Customer node (size = instance.getSize()-1, excludes depot)
  - node.name: int ID (1 to N, 0 is depot - never select!)
  - node.nodeBelong: boolean (true if currently assigned to route)
  - node.demand: int customer demand
  - node.knn[k]: k-th nearest neighbor node ID
  - node.route: parent Route object
  - node.next, node.prev: linked list pointers within route
- routes[i]: Route object (i < numRoutes)
  - route.first: depot Node (don't remove!)
  - route.first.next: first customer in route
  - route.totalDemand, route.fRoute (cost)
- instance.dist(i, j): distance between node IDs i and j

**SELECTION GUIDANCE:**
- numToRemove is adaptive (omega) - typically 5-50 nodes
- Prefer spatial clustering (nearby nodes) for better repair
- Mix deterministic and random selection (~70%/30%) for diversity
- Consider route structure when selecting

**CRITICAL: NO DUPLICATES**
You MUST ensure each node appears only ONCE in the returned array:
```java
// BAD - may contain duplicates
List<Node> selected = new ArrayList<>();
for (int i = 0; i < numToRemove; i++) {
    selected.add(candidates.get(rand.nextInt(candidates.size())));  // WRONG!
}

// GOOD - guaranteed unique nodes
List<Node> selected = new ArrayList<>();
Set<Integer> usedIds = new HashSet<>();
while (selected.size() < numToRemove && selected.size() < candidates.size()) {
    Node node = candidates.get(rand.nextInt(candidates.size()));
    if (usedIds.add(node.name)) {  // Returns false if already present
        selected.add(node);
    }
}
```
"""

AILS_PROBLEM_DESCRIPTION = "Vehicle Routing Problem (VRP) with AILS destroy-and-repair"

AILS_DATA_STRUCTURES = """
**Node fields**: name (int ID), nodeBelong (bool), demand (int), knn[] (neighbor IDs),
                 route (Route), next/prev (linked list pointers)
**Route fields**: first (depot Node), first.next (first customer), totalDemand, fRoute (cost)
**Instance methods**: dist(i, j) – distance between node IDs i and j
"""

_SEED_IDEAS = [
    "Randomly selects nodes from valid candidates, providing baseline diversity without spatial structure.",
    "Removes nodes with highest cost contribution (distance to prev+next), targeting problematic nodes for reconstruction.",
    "Uses KNN-based spatial clustering to select geographically coherent node groups, improving repair efficiency through locality.",
]


# ---------------------------------------------------------------------------
# Seed templates
# ---------------------------------------------------------------------------

def _template_random_removal() -> str:
    return """package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

/**
 * Random Removal Strategy
 * Randomly selects nodes to remove from the solution
 * Uses HashSet for guaranteed deduplication
 */
public class RandomRemoval implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        // Collect all valid nodes
        List<Node> validNodes = new ArrayList<>();
        for (Node node : nodes) {
            if (node != null && node.nodeBelong && node.name != 0) {
                validNodes.add(node);
            }
        }

        if (validNodes.isEmpty()) {
            return new Node[0];
        }

        // Randomly select with deduplication using HashSet
        List<Node> selected = new ArrayList<>();
        Set<Integer> usedIds = new HashSet<>();

        while (selected.size() < numToRemove && selected.size() < validNodes.size()) {
            Node node = validNodes.get(rand.nextInt(validNodes.size()));
            if (usedIds.add(node.name)) {
                selected.add(node);
            }
        }

        return selected.toArray(new Node[0]);
    }
}
"""


def _template_worst_removal() -> str:
    return """package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

/**
 * Worst Removal Strategy
 * Removes nodes that contribute most to total distance
 * NO inner classes - computes cost inline
 */
public class WorstRemoval implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        // Collect valid nodes with inline cost calculation
        List<Node> validNodes = new ArrayList<>();
        List<Double> nodeCosts = new ArrayList<>();

        for (Node node : nodes) {
            if (node != null && node.nodeBelong && node.name != 0) {
                // Cost = distance to prev + distance to next
                double cost = instance.dist(node.prev.name, node.name) +
                             instance.dist(node.name, node.next.name);
                validNodes.add(node);
                nodeCosts.add(cost);
            }
        }

        if (validNodes.isEmpty()) {
            return new Node[0];
        }

        // Sort indices by cost (descending) using simple bubble sort
        List<Integer> indices = new ArrayList<>();
        for (int i = 0; i < validNodes.size(); i++) {
            indices.add(i);
        }

        for (int i = 0; i < indices.size() - 1; i++) {
            for (int j = 0; j < indices.size() - i - 1; j++) {
                if (nodeCosts.get(indices.get(j)) < nodeCosts.get(indices.get(j + 1))) {
                    int temp = indices.get(j);
                    indices.set(j, indices.get(j + 1));
                    indices.set(j + 1, temp);
                }
            }
        }

        // Select top numToRemove with deduplication
        List<Node> selected = new ArrayList<>();
        Set<Integer> usedIds = new HashSet<>();
        int count = Math.min(numToRemove, validNodes.size());

        for (int i = 0; i < indices.size() && selected.size() < count; i++) {
            Node node = validNodes.get(indices.get(i));
            if (usedIds.add(node.name)) {
                selected.add(node);
            }
        }

        return selected.toArray(new Node[0]);
    }
}
"""


def _template_clustered_removal() -> str:
    return """package EvoDestroy;

import Solution.Node;
import Solution.Route;
import Data.Instance;
import java.util.Random;
import java.util.ArrayList;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

/**
 * Clustered Removal Strategy
 * Removes geographically clustered nodes using KNN
 * Uses HashSet for guaranteed deduplication
 */
public class ClusteredRemoval implements DestroyStrategy {

    @Override
    public Node[] selectNodesToRemove(
        int numToRemove,
        Route[] routes,
        int numRoutes,
        Node[] nodes,
        Instance instance,
        Random rand
    ) {
        // Collect all valid nodes
        List<Node> validNodes = new ArrayList<>();
        for (Node node : nodes) {
            if (node != null && node.nodeBelong && node.name != 0) {
                validNodes.add(node);
            }
        }

        if (validNodes.isEmpty()) {
            return new Node[0];
        }

        // Select with deduplication using HashSet
        List<Node> selected = new ArrayList<>();
        Set<Integer> usedIds = new HashSet<>();

        // Pick random seed node
        Node seed = validNodes.get(rand.nextInt(validNodes.size()));
        selected.add(seed);
        usedIds.add(seed.name);

        // Expand cluster using KNN
        while (selected.size() < numToRemove && usedIds.size() < validNodes.size()) {
            // Pick from current cluster
            Node current = selected.get(rand.nextInt(selected.size()));

            // Find nearest neighbor not yet selected
            Node nearest = null;
            for (int i = 0; i < current.knn.length && nearest == null; i++) {
                int knnId = current.knn[i];
                if (!usedIds.contains(knnId)) {
                    // Find the node with this ID
                    for (Node candidate : validNodes) {
                        if (candidate.name == knnId) {
                            nearest = candidate;
                            break;
                        }
                    }
                }
            }

            if (nearest != null && usedIds.add(nearest.name)) {
                selected.add(nearest);
            } else {
                // No KNN neighbor found, pick random unselected node
                int attempts = 0;
                int maxAttempts = validNodes.size() * 2;
                while (attempts < maxAttempts && selected.size() < numToRemove) {
                    Node candidate = validNodes.get(rand.nextInt(validNodes.size()));
                    if (usedIds.add(candidate.name)) {
                        selected.add(candidate);
                        break;
                    }
                    attempts++;
                }
                if (attempts >= maxAttempts) {
                    break;
                }
            }
        }

        return selected.toArray(new Node[0]);
    }
}
"""


def get_ails_initial_seeds() -> List[Tuple[str, str]]:
    """Return (idea, code) pairs for initial AILS VRP seed strategies."""
    return [
        (_SEED_IDEAS[0], _template_random_removal()),
        (_SEED_IDEAS[1], _template_worst_removal()),
        (_SEED_IDEAS[2], _template_clustered_removal()),
    ]
