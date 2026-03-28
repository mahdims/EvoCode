package com.vmscheduling;

import com.vmscheduling.input.ProblemBuilder;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.solver.AlnsMigrationSolver;
import com.vmscheduling.variable.CpuMemMigrationVariable;
import com.vmscheduling.variable.EmptyHostMigrationVariable;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.value.Value;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.SplittableRandom;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.*;

class SolverIntegrationTest {

    static Stream<String> instanceFiles() {
        return Stream.of(
                "data/tiny_h5_v8_s1.json",
                "data/tiny_h5_v8_s2.json",
                "data/tiny_h5_v8_s3.json",
                "data/tiny_h5_v8_s4.json",
                "data/small_h10_v12_s1.json",
                "data/small_h10_v12_s2.json",
                "data/small_h10_v12_s3.json",
                "data/small_h10_v12_s4.json",
                "data/medium_h20_v15_s1.json",
                "data/medium_h20_v15_s2.json",
                "data/medium_h20_v15_s3.json",
                "data/medium_h20_v15_s4.json",
                "data/large_h50_v20_s1.json",
                "data/large_h50_v20_s2.json",
                "data/large_h50_v20_s3.json",
                "data/large_h50_v20_s4.json",
                "data/xlarge_h100_v25_s1.json",
                "data/xlarge_h100_v25_s2.json",
                "data/xlarge_h100_v25_s3.json",
                "data/xlarge_h100_v25_s4.json"
        );
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("instanceFiles")
    void solver_improvesOrMaintainsObjective(String instanceFile) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));
        Problem problem = new ProblemBuilder().build(json);

        assertThat(problem.getHosts()).isNotEmpty();
        assertThat(problem.getVms()).isNotEmpty();

        // Compute initial objective
        MigrationSolution initialSolution = new MigrationSolution(problem);
        Value initialValue = problem.getMigrationObjective().calculate(problem, initialSolution);

        // Solve
        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
                ProblemBuilder.getHostVmsFetcher(problem);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom(42));
        MigrationSolution solution = solver.solve(problem);

        // Final objective should be <= initial (lower is better)
        Value finalValue = problem.getMigrationObjective().calculate(problem, solution);
        assertThat(finalValue.compareTo(initialValue))
                .as("Solution should not worsen: initial=%s, final=%s", initialValue, finalValue)
                .isLessThanOrEqualTo(0);
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("instanceFiles")
    void solver_doesNotWorsenCapacityViolations(String instanceFile) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));
        Problem problem = new ProblemBuilder().build(json);

        // Compute initial capacity usage
        MigrationSolution initialSolution = new MigrationSolution(problem);
        MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher = new MigrationFetcher<>(0);
        CpuMemMigrationVariable initialCpuMem = cpuMemFetcher.fetch(initialSolution);
        float initialTotalCpuExcess = 0;
        for (Host host : problem.getHosts()) {
            int numNumas = host.getNumaGroups().get(0).getNumas().size();
            for (int n = 0; n < numNumas; n++) {
                float cap = host.getNumaGroups().get(0).getNumas().get(n).getCpu();
                float excess = initialCpuMem.getNumaCpu()[host.getIndex()][n] - cap;
                if (excess > 0) initialTotalCpuExcess += excess;
            }
        }

        // Solve
        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
                ProblemBuilder.getHostVmsFetcher(problem);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom(42));
        MigrationSolution solution = solver.solve(problem);

        // Compute final capacity usage — should not introduce new violations
        CpuMemMigrationVariable finalCpuMem = cpuMemFetcher.fetch(solution);
        float finalTotalCpuExcess = 0;
        for (Host host : problem.getHosts()) {
            int numNumas = host.getNumaGroups().get(0).getNumas().size();
            for (int n = 0; n < numNumas; n++) {
                float cap = host.getNumaGroups().get(0).getNumas().get(n).getCpu();
                float excess = finalCpuMem.getNumaCpu()[host.getIndex()][n] - cap;
                if (excess > 0) finalTotalCpuExcess += excess;
            }
        }

        assertThat(finalTotalCpuExcess)
                .as("Solver should not increase total CPU capacity violations")
                .isLessThanOrEqualTo(initialTotalCpuExcess + 0.001f);
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("instanceFiles")
    void solver_allVmsPlaced(String instanceFile) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));
        Problem problem = new ProblemBuilder().build(json);

        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
                ProblemBuilder.getHostVmsFetcher(problem);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom(42));
        MigrationSolution solution = solver.solve(problem);

        for (Vm vm : problem.getVms()) {
            Placement p = solution.getPlacement(vm);
            assertThat(p)
                    .as("VM %d should have a placement", vm.getIndex())
                    .isNotNull();
        }
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("instanceFiles")
    void solver_deterministic_sameSeedSameResult(String instanceFile) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));

        // Run 1
        Problem problem1 = new ProblemBuilder().build(json);
        MigrationFetcher<HostVmsMigrationVariable> f1 = ProblemBuilder.getHostVmsFetcher(problem1);
        MigrationSolution sol1 = new AlnsMigrationSolver(f1, new SplittableRandom(42)).solve(problem1);
        Value val1 = problem1.getMigrationObjective().calculate(problem1, sol1);

        // Run 2
        Problem problem2 = new ProblemBuilder().build(json);
        MigrationFetcher<HostVmsMigrationVariable> f2 = ProblemBuilder.getHostVmsFetcher(problem2);
        MigrationSolution sol2 = new AlnsMigrationSolver(f2, new SplittableRandom(42)).solve(problem2);
        Value val2 = problem2.getMigrationObjective().calculate(problem2, sol2);

        assertThat(val1.compareTo(val2))
                .as("Same seed should produce identical results")
                .isEqualTo(0);
    }

    // ── Per-instance improvement capability tests ──

    private record ImprovementResult(
            int initialEmptyHosts, int finalEmptyHosts,
            int migrations, Value initialValue, Value finalValue, long elapsedMs) {}

    private ImprovementResult solveAndMeasure(String instanceFile) throws IOException {
        String json = Files.readString(Paths.get(instanceFile));
        Problem problem = new ProblemBuilder().build(json);

        MigrationSolution initialSolution = new MigrationSolution(problem);
        Value initialValue = problem.getMigrationObjective().calculate(problem, initialSolution);
        MigrationFetcher<EmptyHostMigrationVariable> emptyFetcher = new MigrationFetcher<>(2);
        int initialEmpty = emptyFetcher.fetch(initialSolution).getNumEmptyHost();

        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher = ProblemBuilder.getHostVmsFetcher(problem);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, new SplittableRandom(42))
                .timeLimit(Duration.ofSeconds(30))
                .maxSteps(200_000)
                .maxStagnationSteps(5_000);

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

        return new ImprovementResult(initialEmpty, finalEmpty, migrations, initialValue, finalValue, elapsed);
    }

    @Test void improvement_tiny_h5_v8_s1() throws IOException {
        ImprovementResult r = solveAndMeasure("data/tiny_h5_v8_s1.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_tiny_h5_v8_s2() throws IOException {
        ImprovementResult r = solveAndMeasure("data/tiny_h5_v8_s2.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_tiny_h5_v8_s3() throws IOException {
        ImprovementResult r = solveAndMeasure("data/tiny_h5_v8_s3.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_tiny_h5_v8_s4() throws IOException {
        ImprovementResult r = solveAndMeasure("data/tiny_h5_v8_s4.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_small_h10_v12_s1() throws IOException {
        ImprovementResult r = solveAndMeasure("data/small_h10_v12_s1.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_small_h10_v12_s2() throws IOException {
        ImprovementResult r = solveAndMeasure("data/small_h10_v12_s2.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_small_h10_v12_s3() throws IOException {
        ImprovementResult r = solveAndMeasure("data/small_h10_v12_s3.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_small_h10_v12_s4() throws IOException {
        ImprovementResult r = solveAndMeasure("data/small_h10_v12_s4.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_medium_h20_v15_s1() throws IOException {
        ImprovementResult r = solveAndMeasure("data/medium_h20_v15_s1.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_medium_h20_v15_s2() throws IOException {
        ImprovementResult r = solveAndMeasure("data/medium_h20_v15_s2.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_medium_h20_v15_s3() throws IOException {
        ImprovementResult r = solveAndMeasure("data/medium_h20_v15_s3.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_medium_h20_v15_s4() throws IOException {
        ImprovementResult r = solveAndMeasure("data/medium_h20_v15_s4.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_large_h50_v20_s1() throws IOException {
        ImprovementResult r = solveAndMeasure("data/large_h50_v20_s1.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_large_h50_v20_s2() throws IOException {
        ImprovementResult r = solveAndMeasure("data/large_h50_v20_s2.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_large_h50_v20_s3() throws IOException {
        ImprovementResult r = solveAndMeasure("data/large_h50_v20_s3.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_large_h50_v20_s4() throws IOException {
        ImprovementResult r = solveAndMeasure("data/large_h50_v20_s4.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_xlarge_h100_v25_s1() throws IOException {
        ImprovementResult r = solveAndMeasure("data/xlarge_h100_v25_s1.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_xlarge_h100_v25_s2() throws IOException {
        ImprovementResult r = solveAndMeasure("data/xlarge_h100_v25_s2.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_xlarge_h100_v25_s3() throws IOException {
        ImprovementResult r = solveAndMeasure("data/xlarge_h100_v25_s3.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }

    @Test void improvement_xlarge_h100_v25_s4() throws IOException {
        ImprovementResult r = solveAndMeasure("data/xlarge_h100_v25_s4.json");
        // Solver must not worsen the objective
        assertThat(r.finalValue.compareTo(r.initialValue))
                .as("Solution must not worsen: %s → %s (migrations: %d)",
                        r.initialValue, r.finalValue, r.migrations)
                .isLessThanOrEqualTo(0);

        // If improvement occurred, verify migrations happened
        if (r.finalValue.compareTo(r.initialValue) < 0) {
            assertThat(r.migrations)
                    .as("Improved solution should have migrations")
                    .isGreaterThan(0);
        }

        assertThat(r.elapsedMs).isLessThan(60_000);
    }
}
