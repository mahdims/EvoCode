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
 * Benchmark tests for large instances (200+ hosts, 6000+ VMs).
 * These tests verify scalability and performance on production-scale problems.
 */
class LargeInstanceBenchmark {

    private record BenchmarkResult(
            String instance, int hosts, int vms, int numas,
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
    }

    private BenchmarkResult benchmark(String instanceFile, RuinType ruinType,
                                       Duration timeLimit, int maxSteps) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));
        Problem problem = new ProblemBuilder().build(json);

        MigrationSolution initialSolution = new MigrationSolution(problem);
        Value initialValue = problem.getMigrationObjective().calculate(problem, initialSolution);
        MigrationFetcher<EmptyHostMigrationVariable> emptyFetcher = new MigrationFetcher<>(2);
        int initialEmpty = emptyFetcher.fetch(initialSolution).getNumEmptyHost();

        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
                ProblemBuilder.getHostVmsFetcher(problem);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom(42))
                .ruinType(ruinType)
                .timeLimit(timeLimit)
                .maxSteps(maxSteps)
                .maxStagnationSteps(10_000);

        long start = System.currentTimeMillis();
        MigrationSolution solution = solver.solve(problem);
        long elapsed = System.currentTimeMillis() - start;

        Value finalValue = problem.getMigrationObjective().calculate(problem, solution);
        int finalEmpty = emptyFetcher.fetch(solution).getNumEmptyHost();

        int migrations = 0;
        for (Vm vm : problem.getVms()) {
            if (solution.getPlacement(vm) != vm.getInitialPlacement()) {
                migrations++;
            }
        }

        return new BenchmarkResult(
                instanceFile.substring(instanceFile.lastIndexOf('/') + 1),
                problem.getHosts().size(), problem.getVms().size(), problem.getNumas().size(),
                initialValue, finalValue, initialEmpty, finalEmpty,
                migrations, elapsed, ruinType);
    }

    @Test
    void benchmark_xxlarge_h200_v30_guided() throws IOException {
        BenchmarkResult r = benchmark("data/xxlarge_h200_v30_s1.json", RuinType.GUIDED,
                Duration.ofSeconds(60), 500_000);
        System.out.println(r);

        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen")
                .isLessThanOrEqualTo(0);
        assertThat(r.elapsedMs).isLessThan(120_000); // 2 min
    }

    @Test
    void benchmark_xxxlarge_h500_v40_guided() throws IOException {
        BenchmarkResult r = benchmark("data/xxxlarge_h500_v40_s1.json", RuinType.GUIDED,
                Duration.ofMinutes(2), 1_000_000);
        System.out.println(r);

        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen")
                .isLessThanOrEqualTo(0);
        assertThat(r.elapsedMs).isLessThan(300_000); // 5 min
    }

    @Test
    void benchmark_mega_h1000_v50_guided() throws IOException {
        BenchmarkResult r = benchmark("data/mega_h1000_v50_s1.json", RuinType.GUIDED,
                Duration.ofMinutes(5), 2_000_000);
        System.out.println(r);

        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen")
                .isLessThanOrEqualTo(0);
        assertThat(r.elapsedMs).isLessThan(600_000); // 10 min
    }

    @Test
    void scalability_comparison() throws IOException {
        System.out.println("\n=== SCALABILITY BENCHMARK (GUIDED RUIN) ===\n");

        String[] instances = {
                "data/xxlarge_h200_v30_s1.json",
                "data/xxxlarge_h500_v40_s1.json",
                "data/mega_h1000_v50_s1.json"
        };

        Duration[] timeLimits = {
                Duration.ofSeconds(30),
                Duration.ofMinutes(1),
                Duration.ofMinutes(2)
        };

        int[] maxSteps = {300_000, 500_000, 1_000_000};

        for (int i = 0; i < instances.length; i++) {
            System.out.println("Instance: " + instances[i].substring(instances[i].lastIndexOf('/') + 1));

            BenchmarkResult guided = benchmark(instances[i], RuinType.GUIDED, timeLimits[i], maxSteps[i]);
            System.out.println("  " + guided);

            System.out.println();
        }
    }
}
