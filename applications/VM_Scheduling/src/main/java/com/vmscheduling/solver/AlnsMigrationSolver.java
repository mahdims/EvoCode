package com.vmscheduling.solver;

import com.vmscheduling.acceptance.AcceptanceCriteria;
import com.vmscheduling.acceptance.LateAcceptanceHillClimbingAcceptanceCriteria;
import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.OptimizationTrackData;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.operator.AdaptiveMaintainer;
import com.vmscheduling.operator.HostSorterType;
import com.vmscheduling.operator.RecreateType;
import com.vmscheduling.operator.RuinType;
import com.vmscheduling.operator.VmSorterType;
import com.vmscheduling.util.AlgorithmUtil;
import com.vmscheduling.util.AssignmentList;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.SplittableRandom;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * ALNS Migration Solver — the top-level class orchestrating all components.
 *
 * See MainWiki §7.3 / 11-main-solve-loop.md.
 */
public class AlnsMigrationSolver implements MigrationSolver {

    private static final Logger log = LoggerFactory.getLogger(AlnsMigrationSolver.class);

    private final MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher;
    private final SplittableRandom random;

    private AcceptanceCriteria acceptanceCriteria =
            new LateAcceptanceHillClimbingAcceptanceCriteria(10);
    private RuinType ruinType = RuinType.GUIDED;
    private int numMaxRuinHost = 5;
    private int maxSteps = 50000;
    private int maxStagnationSteps = 500;
    private Duration timeLimit = Duration.ofSeconds(5);
    private boolean useChainOptimizer = true;

    private List<List<Placement>> allPlacements;

    public AlnsMigrationSolver(MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher,
                                SplittableRandom random) {
        this.hostVmsFetcher = hostVmsFetcher;
        this.random = random;
    }

    // Fluent setters
    public AlnsMigrationSolver acceptanceCriteria(AcceptanceCriteria c) { this.acceptanceCriteria = c; return this; }
    public AlnsMigrationSolver ruinType(RuinType r) { this.ruinType = r; return this; }
    public AlnsMigrationSolver numMaxRuinHost(int n) { this.numMaxRuinHost = n; return this; }
    public AlnsMigrationSolver maxSteps(int n) { this.maxSteps = n; return this; }
    public AlnsMigrationSolver maxStagnationSteps(int n) { this.maxStagnationSteps = n; return this; }
    public AlnsMigrationSolver timeLimit(Duration d) { this.timeLimit = d; return this; }
    public AlnsMigrationSolver useChainOptimizer(boolean b) { this.useChainOptimizer = b; return this; }

    @Override
    public MigrationSolution solve(Problem problem) {
        return solve(problem, null);
    }

    /**
     * Solve with optional custom initial solution (for testing with unbalanced starts).
     * If initialSolution is null, creates solution from vm.getInitialPlacement().
     */
    public MigrationSolution solve(Problem problem, MigrationSolution initialSolution) {
        Instant startTime = Instant.now();
        Instant endTime = startTime.plus(timeLimit);

        log.info("========== ALNS Solver Started ==========");
        log.info("Problem: {} hosts, {} VMs ({} migratable)",
                problem.getHosts().size(), problem.getVms().size(),
                problem.getVms().stream().filter(vm -> vm.isMigratable()).count());
        log.info("Configuration: ruinType={}, maxSteps={}, maxStagnation={}, timeLimit={}s",
                ruinType, maxSteps, maxStagnationSteps, timeLimit.getSeconds());

        MigrationSolution solution = (initialSolution != null)
                ? new MigrationSolution(initialSolution)
                : new MigrationSolution(problem);
        if (problem.getHosts().isEmpty() || problem.getVms().isEmpty()) {
            log.warn("Empty problem - returning trivial solution");
            return solution;
        }

        allPlacements = MigrationSolver.calculateAllPlacements(problem);
        log.debug("Precomputed {} placement lists", allPlacements.size());

        AdaptiveMaintainer adaptiveMaintainer = new AdaptiveMaintainer(numMaxRuinHost);
        int steps = 0;
        int stagnationSteps = 0;
        Value value = problem.getMigrationObjective().calculate(problem, solution);
        Value initialValue = value; // Save for summary logging
        log.info("Initial solution objective: {}", value);

        MigrationSolution bestSolution = new MigrationSolution(solution, false);
        Value bestValue = value;
        acceptanceCriteria.init(value);
        OptimizationTrackData optimizationTrackData = new OptimizationTrackData();
        optimizationTrackData.addOptimizationTrackDataItem(Collections.emptyList(), value);

        while (steps < maxSteps && stagnationSteps < maxStagnationSteps
                && Instant.now().isBefore(endTime)) {
            ++steps;
            ++stagnationSteps;

            if (steps % 100 == 0 || steps <= 10) {
                log.debug("Step {}: stagnation={}/{}, current={}", steps, stagnationSteps, maxStagnationSteps, value);
            }

            // ── STEP 1: SELECT OPERATORS ──
            int numRuinHost = adaptiveMaintainer.rollNumRuinHost(random);
            HostSorterType hostSorterType = adaptiveMaintainer.rollHostSorterType(random);
            VmSorterType vmSorterType = adaptiveMaintainer.rollVmSorterType(random);
            RecreateType recreateType = adaptiveMaintainer.rollRecreateType(random);

            log.trace("Step {}: Operators selected - numRuinHost={}, hostSorter={}, vmSorter={}, recreate={}",
                    steps, numRuinHost, hostSorterType, vmSorterType, recreateType);

            // ── STEP 2: RUIN ──
            List<Host> ruinHosts = getRuinHosts(problem, solution, numRuinHost, hostSorterType);
            log.trace("Step {}: Selected {} ruin hosts: {}", steps, ruinHosts.size(),
                    ruinHosts.stream().map(Host::getIndex).toList());

            MigrationSolution newSolution = new MigrationSolution(solution); // deep copy
            List<Vm> ruinVms = getRuinVms(problem, newSolution, ruinHosts, vmSorterType);

            // ── STEP 3: RECREATE ──
            List<RecreateDelta> recreateDeltas = new ArrayList<>();
            if (Objects.isNull(ruinVms)) {
                log.debug("Step {}: SKIPPED - Ruin returned null (no improving removal with {} ruin)", steps, ruinType);
                if (steps <= 5 || steps % 1000 == 0) {
                    System.out.printf("[Step %,6d] SKIPPED - Ruin returned null (no improving removal found)%n", steps);
                }
                continue;
            }

            log.trace("Step {}: Ruined {} VMs from {} hosts: {}", steps, ruinVms.size(),
                    ruinHosts.size(), ruinVms.stream().map(Vm::getIndex).limit(10).toList());

            if (!recreate(problem, newSolution, ruinVms, recreateDeltas, vmSorterType, recreateType)) {
                log.debug("Step {}: SKIPPED - Recreate failed for {} VMs using {} recreate",
                        steps, ruinVms.size(), recreateType);
                if (steps <= 5 || steps % 1000 == 0) {
                    System.out.printf("[Step %,6d] SKIPPED - Recreate failed for %d VMs%n", steps, ruinVms.size());
                }
                continue;
            }

            log.trace("Step {}: Recreate succeeded for {} VMs with {} deltas",
                    steps, ruinVms.size(), recreateDeltas.size());

            // ── STEP 4: EVALUATE ──
            Value newValue = problem.getMigrationObjective().calculate(problem, newSolution);
            log.trace("Step {}: New solution objective: {}", steps, newValue);

            int comparison = newValue.compareTo(value);
            log.debug("Step {}: Objective comparison - old={}, new={}, diff={}",
                    steps, value, newValue, comparison < 0 ? "BETTER" : comparison > 0 ? "WORSE" : "EQUAL");

            // ── STEP 5: GLOBAL BEST CHECK ──
            if (newValue.compareTo(bestValue) < 0) {
                log.info("Step {}: *** NEW GLOBAL BEST *** {} -> {} (improvement: {})",
                        steps, bestValue, newValue, bestValue.compareTo(newValue));
                bestValue = newValue;
                bestSolution = new MigrationSolution(newSolution, false);
                stagnationSteps = 0;
                adaptiveMaintainer.updateWeights(ruinHosts.size(), vmSorterType,
                        hostSorterType, recreateType, 1.0);
            }

            // ── STEP 6: ACCEPT / REJECT (LAHC) ──
            boolean accepted = acceptanceCriteria.accept(value, newValue, random, stagnationSteps);
            log.debug("Step {}: Acceptance decision: {} (criteria={}, stagnation={})",
                    steps, accepted ? "ACCEPTED" : "REJECTED",
                    acceptanceCriteria.getClass().getSimpleName(), stagnationSteps);

            if (accepted) {
                value = newValue;
                solution = newSolution;
                optimizationTrackData.addOptimizationTrackDataItem(recreateDeltas, value);

                // Log acceptance (TRACE level to avoid hot-loop performance impact)
                boolean isNewBest = newValue.compareTo(bestValue) == 0;
                log.trace("Step {}: ACCEPTED solution - ruined={} VMs, current={}, best={}{}",
                        steps, ruinVms.size(), newValue, bestValue,
                        isNewBest ? " ← NEW BEST" : "");
                // System.out removed for performance - use log.trace instead
                // System.out.printf("[Step %,6d] ACCEPTED | Ruined: %2d VMs | Current: %s | Best: %s%s%n",
                //         steps, ruinVms.size(), newValue, bestValue,
                //         isNewBest ? " ← NEW BEST" : "");
            } else {
                log.debug("Step {}: REJECTED solution - old={}, new={}", steps, value, newValue);
                if (steps <= 5 || steps % 1000 == 0) {
                    System.out.printf("[Step %,6d] REJECTED | Old: %s | New: %s%n",
                            steps, value, newValue);
                }
                optimizationTrackData.addOptimizationTrackDataItem(Collections.emptyList(), value);
            }
        }

        // Summary log
        long elapsedMs = Duration.between(startTime, Instant.now()).toMillis();
        // Use actual initial value from solve start (not recalculated from vm.getInitialPlacement())

        String terminationReason;
        if (steps >= maxSteps) {
            terminationReason = "MAX_STEPS";
        } else if (stagnationSteps >= maxStagnationSteps) {
            terminationReason = "MAX_STAGNATION";
        } else {
            terminationReason = "TIME_LIMIT";
        }

        log.info("========== ALNS Solver Finished ==========");
        log.info("Termination: {} after {} steps ({} ms)", terminationReason, steps, elapsedMs);
        log.info("Stagnation: {}/{} steps", stagnationSteps, maxStagnationSteps);
        log.info("Solution quality: Initial={} -> Final={}", initialValue, bestValue);

        int improvementComparison = bestValue.compareTo(initialValue);
        if (improvementComparison < 0) {
            log.info("Result: IMPROVED (better by {} levels)", Math.abs(improvementComparison));
        } else if (improvementComparison > 0) {
            log.warn("Result: DEGRADED (worse by {} levels)", improvementComparison);
        } else {
            log.warn("Result: NO CHANGE (same as initial)");
        }

        System.out.printf("%n[ALNS Summary] Steps: %,d | Stagnation: %,d/%,d | Time: %,d ms | " +
                        "Initial: %s → Final: %s | Termination: %s%n%n",
                steps, stagnationSteps, maxStagnationSteps, elapsedMs, initialValue, bestValue, terminationReason);

        bestSolution.setOptimizationTrackData(optimizationTrackData);
        bestSolution.updateMigrationVariables(problem);
        return bestSolution;
    }

    /**
     * Collect hosts with migratable VMs, shuffle, then sort/truncate via HostSorterType.
     */
    private List<Host> getRuinHosts(Problem problem, MigrationSolution solution,
                                     int numRuinHost, HostSorterType hostSorterType) {
        List<Host> ruinHosts = new ObjectArrayList<>(problem.getHosts().size());
        AssignmentList<Vm> migratableHostVms =
                hostVmsFetcher.fetch(solution).getMigratableHostVms();
        for (Host host : problem.getHosts()) {
            if (!migratableHostVms.get(host.getIndex()).isEmpty()) {
                ruinHosts.add(host);
            }
        }
        AlgorithmUtil.shuffleList(ruinHosts, random);
        hostSorterType.sort(problem, solution, ruinHosts, numRuinHost, random, hostVmsFetcher);
        return ruinHosts;
    }

    /**
     * Delegate to the configured RuinType (GUIDED or RANDOM).
     */
    private List<Vm> getRuinVms(Problem problem, MigrationSolution solution,
                                 List<Host> ruinHosts, VmSorterType vmSorterType) {
        return ruinType.getRuinVms(problem, solution, ruinHosts, vmSorterType, random, hostVmsFetcher);
    }

    /**
     * Sort VMs, then delegate to RecreateType.
     */
    private boolean recreate(Problem problem, MigrationSolution solution,
                              List<Vm> ruinVms, List<RecreateDelta> recreateDeltas,
                              VmSorterType vmSorterType, RecreateType recreateType) {
        sortVmsByType(solution, ruinVms, vmSorterType, false);
        return recreateType.recreate(problem, solution, ruinVms, recreateDeltas,
                allPlacements, random);
    }

    /**
     * Context-aware VM sorting.
     * Ruin: moved-VMs first (pre-sort), then ascending by VmSorterType.
     * Recreate: ascending by VmSorterType, then reversed (largest first).
     */
    private void sortVmsByType(MigrationSolution solution, List<Vm> vms,
                                VmSorterType vmSorterType, boolean isRuin) {
        if (isRuin && vmSorterType != VmSorterType.RANDOM) {
            // Already-moved VMs first (false < true in Java boolean comparison)
            vms.sort(Comparator.comparing(
                    vm -> vm.getInitialPlacement() == solution.getPlacement(vm)));
        }
        vmSorterType.sort(vms, random);
        if (!isRuin) {
            Collections.reverse(vms); // Recreate: largest first
        }
    }
}
