package com.vmscheduling.operator;

import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.util.AssignmentList;
import com.vmscheduling.util.Pair;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.PriorityQueue;
import java.util.SplittableRandom;
import java.util.function.Function;

/**
 * Host selection strategies for the ruin phase.
 * Operates on an already-shuffled candidate list and truncates/replaces to numRuinHost entries.
 *
 * See MainWiki §7.3 / 07-operator-types.md.
 */
public enum HostSorterType {

    /**
     * Select the numRuinHost hosts whose ruin would produce the best objective value.
     * Uses a priority queue of top numRuinHost candidates.
     */
    RUIN_EXPECTED {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            // Max-heap maintains top-K (best = smallest values)
            PriorityQueue<Pair<Host, Value>> queue = new PriorityQueue<>(
                    Math.max(1, numRuinHost),
                    Comparator.comparing(
                            (Function<Pair<Host, Value>, Value>) Pair::right).reversed());
            AssignmentList<Vm> migratableHostVms =
                    hostVmsFetcher.fetch(solution).getMigratableHostVms();
            for (Host host : ruinHosts) {
                Vm[] vms = migratableHostVms.get(host.getIndex()).toArray(new Vm[0]);
                RuinDelta ruinDelta = new RuinDelta(vms);
                if (problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                    Value value = problem.getMigrationObjective().calculate(
                            problem, solution, ruinDelta);
                    if (queue.size() < numRuinHost) {
                        queue.add(Pair.of(host, value));
                    } else if (value.compareTo(queue.peek().right()) < 0) {
                        queue.poll();
                        queue.add(Pair.of(host, value));
                    }
                }
            }
            // CRITICAL FIX: Extract hosts best-first by reversing poll() order (max-heap gives worst-first)
            ruinHosts.clear();
            List<Host> tempList = new ArrayList<>(numRuinHost);
            while (!queue.isEmpty()) {
                tempList.add(queue.poll().left());
            }
            Collections.reverse(tempList);  // Reverse to get best-first order
            ruinHosts.addAll(tempList);
        }
    },

    /**
     * Simply truncate the (already shuffled) list to numRuinHost.
     */
    RANDOM {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            if (numRuinHost < ruinHosts.size()) {
                ruinHosts.subList(numRuinHost, ruinHosts.size()).clear();
            }
        }
    },

    /**
     * Score candidates by expected ruin value, sort, then use rank-based weighted
     * random selection (weight[i] = 1/(i+1)). Reservoir sampling.
     */
    RUIN_EXPECTED_RANDOM {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            AssignmentList<Vm> migratableHostVms =
                    hostVmsFetcher.fetch(solution).getMigratableHostVms();
            List<Pair<Host, Value>> hostsWithValue = new ObjectArrayList<>();
            for (Host host : ruinHosts) {
                Vm[] vms = migratableHostVms.get(host.getIndex()).toArray(new Vm[0]);
                RuinDelta ruinDelta = new RuinDelta(vms);
                if (problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                    hostsWithValue.add(Pair.of(host,
                            problem.getMigrationObjective().calculate(
                                    problem, solution, ruinDelta)));
                }
            }
            hostsWithValue.sort(Comparator.comparing(Pair::right));
            ruinHosts.clear();
            for (int num = 0; num < numRuinHost && !hostsWithValue.isEmpty(); ++num) {
                double sum = 0.0;
                int chosenIndex = 0;
                for (int i = 0; i < hostsWithValue.size(); i++) {
                    double weight = 1.0 / (i + 1);
                    sum += weight;
                    if (random.nextDouble(sum) < weight) chosenIndex = i;
                }
                ruinHosts.add(hostsWithValue.get(chosenIndex).left());
                hostsWithValue.remove(chosenIndex);
            }
        }
    };

    public abstract void sort(Problem problem, MigrationSolution solution,
                               List<Host> ruinHosts, int numRuinHost,
                               SplittableRandom random,
                               MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher);
}
