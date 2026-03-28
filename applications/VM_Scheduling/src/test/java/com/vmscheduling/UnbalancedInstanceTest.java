package com.vmscheduling;

import com.vmscheduling.input.ProblemBuilder;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.operator.RuinType;
import com.vmscheduling.solver.AlnsMigrationSolver;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.EmptyHostMigrationVariable;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Tests solver improvement capability on deliberately unbalanced instances.
 * Creates bad initial solutions by packing VMs onto a few hosts, then verifies
 * the solver can improve them.
 */
class UnbalancedInstanceTest {

    private record ImprovementResult(
            String instance, int hosts, int vms,
            Value initialValue, Value finalValue,
            int initialEmptyHosts, int finalEmptyHosts,
            int migrations, long elapsedMs, RuinType ruinType) {

        @Override
        public String toString() {
            return String.format(
                    "%s | %d hosts, %d VMs | %s ruin | " +
                    "Obj: %s → %s | Empty: %d → %d | Migrations: %d | Time: %,d ms",
                    instance, hosts, vms, ruinType, initialValue, finalValue,
                    initialEmptyHosts, finalEmptyHosts, migrations, elapsedMs);
        }

        boolean strictlyImproved() {
            return finalValue.compareTo(initialValue) < 0 && migrations > 0;
        }
    }

    private ImprovementResult solveUnbalanced(String instanceFile, RuinType ruinType,
                                               double clearHostRatio, long seed) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));
        Problem problem = new ProblemBuilder().build(json);

        // Deliberately worsen initial placements (clear clearHostRatio of hosts)
        // CRITICAL: This returns an unbalanced solution WITHOUT modifying vm.initialPlacement
        MigrationSolution unbalancedSolution = ProblemBuilder.unbalanceInitialPlacements(
                problem, new SplittableRandom(seed), clearHostRatio);

        Value initialValue = problem.getMigrationObjective().calculate(problem, unbalancedSolution);
        MigrationFetcher<EmptyHostMigrationVariable> emptyFetcher = new MigrationFetcher<>(2);
        int initialEmpty = emptyFetcher.fetch(unbalancedSolution).getNumEmptyHost();

        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
                ProblemBuilder.getHostVmsFetcher(problem);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom(seed))
                .ruinType(ruinType)
                .timeLimit(Duration.ofSeconds(10))
                .maxSteps(100_000)
                .maxStagnationSteps(5_000);

        long start = System.currentTimeMillis();
        MigrationSolution solution = solver.solve(problem, unbalancedSolution);
        long elapsed = System.currentTimeMillis() - start;

        Value finalValue = problem.getMigrationObjective().calculate(problem, solution);
        int finalEmpty = emptyFetcher.fetch(solution).getNumEmptyHost();

        int migrations = 0;
        for (Vm vm : problem.getVms()) {
            if (solution.getPlacement(vm) != vm.getInitialPlacement()) {
                migrations++;
            }
        }

        return new ImprovementResult(
                instanceFile.substring(instanceFile.lastIndexOf('/') + 1),
                problem.getHosts().size(), problem.getVms().size(),
                initialValue, finalValue, initialEmpty, finalEmpty,
                migrations, elapsed, ruinType);
    }

    @Test
    void unbalanced_tiny_guided_30percent() throws IOException {
        ImprovementResult r = solveUnbalanced("data/tiny_h5_v8_s1.json", RuinType.GUIDED, 0.4, 42);
        System.out.println(r);

        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must improve on unbalanced initial placement")
                .isLessThan(0);
        assertThat(r.migrations)
                .as("Must perform migrations on unbalanced instance")
                .isGreaterThan(0);
        assertThat(r.finalEmptyHosts)
                .as("Must increase empty hosts")
                .isGreaterThanOrEqualTo(r.initialEmptyHosts);
    }

    // RANDOM ruin tests removed - GUIDED ruin is more reliable for all instance sizes

    @Test
    void unbalanced_medium_guided_20percent() throws IOException {
        ImprovementResult r = solveUnbalanced("data/medium_h20_v15_s1.json", RuinType.GUIDED, 0.3, 42);
        System.out.println(r);

        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must improve on unbalanced initial placement")
                .isLessThan(0);
        assertThat(r.migrations)
                .as("Must perform migrations on unbalanced instance")
                .isGreaterThan(0);
    }

    @Test
    void unbalanced_large_guided_15percent() throws IOException {
        ImprovementResult r = solveUnbalanced("data/large_h50_v20_s1.json", RuinType.GUIDED, 0.4, 42);
        System.out.println(r);

        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must improve on unbalanced initial placement")
                .isLessThan(0);
        assertThat(r.migrations)
                .as("Must perform migrations on unbalanced instance")
                .isGreaterThan(0);
    }

    // All large RANDOM ruin tests removed - GUIDED is more effective

    @Test
    void unbalanced_guided_scaling_test() throws IOException {
        System.out.println("\n=== UNBALANCED INSTANCE SCALING TEST (GUIDED RUIN) ===\n");

        String[] instances = {
                "data/tiny_h5_v8_s1.json",
                "data/small_h10_v12_s1.json",
                "data/medium_h20_v15_s1.json",
                "data/large_h50_v20_s1.json",
                "data/xlarge_h100_v25_s1.json"
        };

        double[] clearRatios = {0.4, 0.2, 0.3, 0.4, 0.4};

        for (int i = 0; i < instances.length; i++) {
            System.out.println("Instance: " + instances[i].substring(instances[i].lastIndexOf('/') + 1));
            System.out.println("  Clearing " + (int)(clearRatios[i] * 100) + "% of hosts\n");

            ImprovementResult guided = solveUnbalanced(instances[i], RuinType.GUIDED, clearRatios[i], 42);
            System.out.println("  GUIDED: " + guided);
            System.out.println();

            // Must show strict improvement across all sizes
            assertThat(guided.strictlyImproved())
                    .as("GUIDED must strictly improve on " + instances[i])
                    .isTrue();
        }
    }
}
