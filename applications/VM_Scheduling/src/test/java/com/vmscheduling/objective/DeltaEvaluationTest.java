package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.input.ProblemBuilder;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.value.Value;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Regression test for delta evaluation correctness.
 * Verifies that objective.calculate(..., delta) equals full recompute after applying delta.
 *
 * This prevents bugs where delta methods return marginal changes instead of projected values.
 */
class DeltaEvaluationTest {

    @Test
    void deltaEvaluation_ruinDelta_matchesFullRecompute() throws IOException {
        // Load a test instance
        String json = Files.readString(Paths.get("data/small_h10_v12_s1.json"));
        Problem problem = new ProblemBuilder().build(json);

        MigrationSolution solution = new MigrationSolution(problem);
        MigrationObjective objective = problem.getMigrationObjective();

        // Select some VMs to ruin
        List<Vm> ruinVms = new ArrayList<>();
        for (Vm vm : problem.getVms()) {
            if (vm.isMigratable() && ruinVms.size() < 5) {
                ruinVms.add(vm);
            }
        }

        RuinDelta ruinDelta = new RuinDelta(ruinVms.toArray(new Vm[0]));

        // Calculate using delta method
        Value deltaValue = objective.calculate(problem, solution, ruinDelta);

        // Calculate using full recompute after applying delta
        MigrationSolution projected = new MigrationSolution(solution);
        ruinDelta.update(problem, projected);
        Value fullValue = objective.calculate(problem, projected);

        // They should be equal (use compareTo since Value doesn't override equals)
        assertThat(deltaValue.compareTo(fullValue))
                .as("RuinDelta evaluation should match full recompute: delta=%s, full=%s",
                        deltaValue, fullValue)
                .isEqualTo(0);
    }

    @Test
    void deltaEvaluation_recreateDelta_matchesFullRecompute() throws IOException {
        // Load a test instance
        String json = Files.readString(Paths.get("data/small_h10_v12_s1.json"));
        Problem problem = new ProblemBuilder().build(json);

        MigrationSolution solution = new MigrationSolution(problem);
        MigrationObjective objective = problem.getMigrationObjective();

        // Ruin one VM to create a recreate scenario
        Vm vm = problem.getVms().stream()
                .filter(Vm::isMigratable)
                .findFirst()
                .orElseThrow();

        RuinDelta ruinDelta = new RuinDelta(new Vm[]{vm});
        ruinDelta.update(problem, solution);

        // Try to recreate on a different host
        Placement newPlacement = problem.getHosts().get(1).getNumaGroups().get(0)
                .getPlacements(vm.getNumNumas()).get(0);

        RecreateDelta recreateDelta = new RecreateDelta(vm, newPlacement);

        // Calculate using delta method
        Value deltaValue = objective.calculate(problem, solution, recreateDelta);

        // Calculate using full recompute after applying delta
        MigrationSolution projected = new MigrationSolution(solution);
        recreateDelta.update(problem, projected);
        Value fullValue = objective.calculate(problem, projected);

        // They should be equal (use compareTo since Value doesn't override equals)
        assertThat(deltaValue.compareTo(fullValue))
                .as("RecreateDelta evaluation should match full recompute: delta=%s, full=%s",
                        deltaValue, fullValue)
                .isEqualTo(0);
    }

    @Test
    void deltaEvaluation_perComponentObjective_matchesFullRecompute() throws IOException {
        // Load a test instance
        String json = Files.readString(Paths.get("data/small_h10_v12_s1.json"));
        Problem problem = new ProblemBuilder().build(json);

        MigrationSolution solution = new MigrationSolution(problem);

        // Get individual objective components using known variable indices
        // Variable registration order: CpuMem(0), HostVms(1), EmptyHost(2), AntiAffinity(3), Cost(4), Load(5)
        EmptyHostMigrationObjective emptyHostObj =
                new EmptyHostMigrationObjective(new com.vmscheduling.variable.MigrationFetcher<>(2));
        MinLoadBalancingObjective loadBalancingObj =
                new MinLoadBalancingObjective(new com.vmscheduling.variable.MigrationFetcher<>(5));
        MigrationCostMigrationObjective migrationCostObj =
                new MigrationCostMigrationObjective(new com.vmscheduling.variable.MigrationFetcher<>(4));

        // Create a recreate delta
        Vm vm = problem.getVms().stream()
                .filter(Vm::isMigratable)
                .findFirst()
                .orElseThrow();

        RuinDelta ruinDelta = new RuinDelta(new Vm[]{vm});
        ruinDelta.update(problem, solution);

        Placement newPlacement = problem.getHosts().get(1).getNumaGroups().get(0)
                .getPlacements(vm.getNumNumas()).get(0);
        RecreateDelta recreateDelta = new RecreateDelta(vm, newPlacement);

        // Test each component objective
        testComponentDelta(problem, solution, recreateDelta, emptyHostObj, "EmptyHost");
        testComponentDelta(problem, solution, recreateDelta, loadBalancingObj, "LoadBalancing");
        testComponentDelta(problem, solution, recreateDelta, migrationCostObj, "MigrationCost");
    }

    private void testComponentDelta(Problem problem, MigrationSolution solution,
                                     RecreateDelta delta, MigrationObjective objective,
                                     String name) {
        Value deltaValue = objective.calculate(problem, solution, delta);

        MigrationSolution projected = new MigrationSolution(solution);
        delta.update(problem, projected);
        Value fullValue = objective.calculate(problem, projected);

        assertThat(deltaValue.compareTo(fullValue))
                .as(name + " delta evaluation should match full recompute: delta=%s, full=%s",
                        deltaValue, fullValue)
                .isEqualTo(0);
    }
}
