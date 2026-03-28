# 07 — Operator Types (Full Source)

Three enum types define the operator strategies selected by AdaptiveMaintainer each iteration.

---

## VmSorterType — VM Ordering (Confirmed Source)

All sorts are **ascending** (smallest first). During ruin, this order is kept. During recreate, it is **reversed** (largest first). See `sortVmsByType` in File 08 for details.

```java
public enum VmSorterType {
    /** Sort by total CPU (ascending), break ties by total memory */
    CPU_MEM {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing((Vm vm) -> vm.getNumaCpu() * vm.getNumNumas())
                .thenComparing(vm -> vm.getNumaMem() * vm.getNumNumas()));
        }
    },
    /** Sort by total memory (ascending), break ties by total CPU */
    MEM_CPU {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing((Vm vm) -> vm.getNumaMem() * vm.getNumNumas())
                .thenComparing(vm -> vm.getNumaCpu() * vm.getNumNumas()));
        }
    },
    /** Sort by CPU × Memory × NUMA_count² (product of all resource dimensions) */
    CPU_MEM_PROD {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing(
                vm -> vm.getNumaCpu() * vm.getNumaMem() * vm.getNumNumas() * vm.getNumNumas()));
        }
    },
    /** Sort by number of NUMA nodes the VM spans (ascending — single-NUMA first) */
    NUM_NUMA {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing(Vm::getNumNumas));
        }
    },
    /** Shuffle randomly */
    RANDOM {
        public void sort(List<Vm> vms, SplittableRandom random) {
            AlgorithmUtil.shuffleList(vms, random);
        }
    };
    public abstract void sort(List<Vm> vms, SplittableRandom random);
}
```

`CPU_MEM_PROD` creates a single scalar combining all dimensions — VMs small in all dimensions get sorted first. `NUM_NUMA` specifically prioritises single-socket VMs, which have far more candidate placements.

---

## HostSorterType — Host Selection for Ruin (Confirmed Source)

Determines which hosts to ruin. Operates on an already-shuffled candidate list and truncates/replaces it to `numRuinHost` entries.

```java
public enum HostSorterType {

    /**
     * Select the numRuinHost hosts whose ruin would produce the best objective value.
     * Evaluates RuinDelta + objective for each candidate — most informed but most expensive.
     */
    RUIN_EXPECTED {
        public void sort(Problem problem, MigrationSolution solution,
                         List<Host> ruinHosts, int numRuinHost,
                         SplittableRandom random,
                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            PriorityQueue<Pair<Host, Value>> queue = new PriorityQueue<>(numRuinHost,
                Comparator.comparing(
                    (Function<Pair<Host, Value>, Value>) Pair::right).reversed());
            AssignmentList<Vm> migratableHostVms =
                hostVmsFetcher.fetch(solution).getMigratableHostVms();
            for (Host host : ruinHosts) {
                RuinDelta ruinDelta = new RuinDelta(
                    migratableHostVms.get(host.getIndex()));
                if (problem.getMigrationConstraint().satisfy(
                        problem, solution, ruinDelta)) {
                    Value value = problem.getMigrationObjective().calculate(
                        problem, solution, ruinDelta);
                    if (queue.isEmpty() || queue.size() < numRuinHost) {
                        queue.add(Pair.of(host, value));
                    } else if (value.compareTo(queue.peek().right()) < 0) {
                        queue.poll();
                        queue.add(Pair.of(host, value));
                    }
                }
            }
            ruinHosts.clear();
            for (Pair<Host, Value> pair : queue) {
                ruinHosts.add(pair.left());
            }
        }
    },

    /**
     * Simply truncate the (already shuffled) list to numRuinHost.
     * O(1) — cheapest possible selection.
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
     * Score candidates by expected ruin value, then use rank-based weighted random
     * selection (weight[i] = 1/(i+1)). Balances quality and diversity.
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
                RuinDelta ruinDelta = new RuinDelta(
                    migratableHostVms.get(host.getIndex()));
                if (problem.getMigrationConstraint().satisfy(
                        problem, solution, ruinDelta)) {
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
        List<Host> ruinHosts, int numRuinHost, SplittableRandom random,
        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher);
}
```

---

## RecreateType — Placement Strategy for Displaced VMs (Confirmed Source)

```java
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
```

All three iterate over VMs in order and commit each placement via `delta.update(problem, solution)` immediately — meaning later VMs in the same recreate see the updated state from earlier placements.

The critical detail: `allPlacements.get(vm.getNumNumas())` ensures single-NUMA VMs only consider single-NUMA placements and multi-NUMA VMs only consider multi-NUMA placements.
