package com.vmscheduling;

import com.vmscheduling.input.ProblemBuilder;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.SplittableRandom;

class UnbalanceDebugTest {

    @Test
    void debug_unbalancing() throws IOException {
        String json = Files.readString(Paths.get("data/small_h10_v12_s1.json"));
        Problem problem = new ProblemBuilder().build(json);

        System.out.println("\n=== BEFORE UNBALANCING ===");
        printDistribution(problem, new MigrationSolution(problem));

        // Unbalance by clearing 30% of hosts (3 hosts out of 10)
        ProblemBuilder.unbalanceInitialPlacements(problem, new SplittableRandom(42), 0.3);

        System.out.println("\n=== AFTER UNBALANCING (clearing 30% = 3 hosts cleared, pack onto 7 hosts) ===");
        printDistribution(problem, new MigrationSolution(problem));
    }

    private void printDistribution(Problem problem, MigrationSolution solution) {
        MigrationFetcher<HostVmsMigrationVariable> hvf = ProblemBuilder.getHostVmsFetcher(problem);
        HostVmsMigrationVariable hostVms = hvf.fetch(solution);

        System.out.println("Total hosts: " + problem.getHosts().size());
        System.out.println("Total VMs: " + problem.getVms().size());

        int migratableCount = 0;
        for (Vm vm : problem.getVms()) {
            if (vm.isMigratable()) migratableCount++;
        }
        System.out.println("Migratable VMs: " + migratableCount);

        System.out.println("\nVMs per host:");
        for (Host host : problem.getHosts()) {
            int count = hostVms.getHostVms().get(host.getIndex()).size();
            int migratableOnHost = hostVms.getMigratableHostVms().get(host.getIndex()).size();
            System.out.println("  Host " + host.getIndex() + ": " + count + " VMs (" + migratableOnHost + " migratable)");
        }
    }
}
