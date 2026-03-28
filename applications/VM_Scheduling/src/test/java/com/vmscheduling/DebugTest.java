package com.vmscheduling;

import com.vmscheduling.input.ProblemBuilder;
import com.vmscheduling.model.Host;
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
import java.util.SplittableRandom;

class DebugTest {

    @Test
    void debugTinyS1() throws IOException {
        String json = Files.readString(Paths.get("data/tiny_h5_v8_s3.json"));
        Problem problem = new ProblemBuilder().build(json);

        System.out.println("Hosts: " + problem.getHosts().size());
        System.out.println("VMs: " + problem.getVms().size());
        System.out.println("NUMAs: " + problem.getNumas().size());

        for (Host host : problem.getHosts()) {
            int numaCount = host.getNumaGroups().get(0).getNumas().size();
            System.out.println("Host " + host.getIndex() + ": " + numaCount + " NUMAs");
        }

        for (Vm vm : problem.getVms()) {
            System.out.println("VM " + vm.getIndex()
                    + ": cpu=" + vm.getNumaCpu() + " mem=" + vm.getNumaMem()
                    + " migratable=" + vm.isMigratable()
                    + " host=" + vm.getInitialPlacement().getHost().getIndex());
        }

        MigrationSolution initialSolution = new MigrationSolution(problem);
        Value initialValue = problem.getMigrationObjective().calculate(problem, initialSolution);
        System.out.println("Initial objective: " + initialValue);

        MigrationFetcher<EmptyHostMigrationVariable> emptyFetcher = new MigrationFetcher<>(2);
        System.out.println("Initial empty hosts: " + emptyFetcher.fetch(initialSolution).getNumEmptyHost());

        MigrationFetcher<HostVmsMigrationVariable> hvf = ProblemBuilder.getHostVmsFetcher(problem);
        HostVmsMigrationVariable hostVms = hvf.fetch(initialSolution);
        for (Host host : problem.getHosts()) {
            System.out.println("Host " + host.getIndex()
                    + " total VMs: " + hostVms.getHostVms().get(host.getIndex()).size()
                    + " migratable: " + hostVms.getMigratableHostVms().get(host.getIndex()).size());
        }

        System.out.println("\n=== Testing GUIDED ruin (default: 5s, 50k steps, 500 stagnation) ===");
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hvf, new SplittableRandom(42))
                .ruinType(RuinType.GUIDED);
        long start = System.currentTimeMillis();
        MigrationSolution solution = solver.solve(problem);
        long elapsed = System.currentTimeMillis() - start;
        Value finalValue = problem.getMigrationObjective().calculate(problem, solution);
        System.out.println("Final objective: " + finalValue);
        System.out.println("Final empty hosts: " + emptyFetcher.fetch(solution).getNumEmptyHost());

        int migrations = 0;
        for (Vm vm : problem.getVms()) {
            if (solution.getPlacement(vm) != vm.getInitialPlacement()) {
                migrations++;
            }
        }
        System.out.println("Migrations: " + migrations);
        System.out.println("Time: " + elapsed + " ms");

        System.out.println("\n=== Comparison ===");
        System.out.println("Initial: " + initialValue);
        System.out.println("Final:   " + finalValue + " (" + migrations + " migrations)");
    }
}
