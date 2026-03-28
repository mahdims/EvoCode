package com.vmscheduling;

import com.vmscheduling.input.ProblemBuilder;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.plugin.TenantPlugin;
import com.vmscheduling.solver.AlnsMigrationSolver;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.SplittableRandom;

/**
 * CLI entry point: load JSON → build Problem → solve → print results.
 *
 * Usage: java -jar vm-scheduling.jar <instance.json> [seed] [PluginClassName]
 *
 * When PluginClassName is given, the class is loaded from the classpath
 * (candidate.jar should precede vmscheduling.jar on the classpath).
 * Structured penalty lines are printed on stdout for EvoCode fitness parsing.
 */
public class Main {

    public static void main(String[] args) throws IOException {
        if (args.length < 1) {
            System.err.println("Usage: java -jar vm-scheduling.jar <instance.json> [seed] [PluginClassName]");
            System.exit(1);
        }

        String json = Files.readString(Path.of(args[0]));
        long seed  = args.length >= 2 ? Long.parseLong(args[1]) : 42L;
        String pluginClassName = args.length >= 3 ? args[2] : null;

        // ── Load optional TenantPlugin ────────────────────────────────────────
        TenantPlugin plugin = null;
        if (pluginClassName != null) {
            try {
                plugin = (TenantPlugin) Class.forName(pluginClassName)
                        .getDeclaredConstructor()
                        .newInstance();
            } catch (Exception e) {
                System.err.println("ERROR: Could not load plugin class: " + pluginClassName);
                System.err.println("  " + e.getClass().getSimpleName() + ": " + e.getMessage());
                System.exit(2);
            }
        }

        // ── Build Problem ────────────────────────────────────────────────────
        ProblemBuilder builder = new ProblemBuilder();
        if (plugin != null) {
            builder.withTenantPlugin(plugin);
        }
        Problem problem = builder.build(json);

        System.out.println("Problem loaded:");
        System.out.println("  Hosts:  " + problem.getHosts().size());
        System.out.println("  VMs:    " + problem.getVms().size());
        System.out.println("  NUMAs:  " + problem.getNumas().size());
        System.out.println("  Plugin: " + (pluginClassName != null ? pluginClassName : "none (stub mode)"));

        // ── Initial solution & penalties ─────────────────────────────────────
        // MigrationSolution(problem) places VMs at initialPlacement and runs full variable update.
        MigrationSolution initialSolution = new MigrationSolution(problem);
        int initialEmpty = countEmptyHosts(problem, initialSolution);
        int[] initialPenalties = computePenalties(problem, initialSolution, builder, plugin != null);

        System.out.printf("  Initial empty hosts:   %d%n", initialEmpty);
        System.out.printf("  Initial penalty A:     %d%n", initialPenalties[0]);
        System.out.printf("  Initial penalty B:     %d%n", initialPenalties[1]);
        System.out.printf("  Initial penalty C:     %d%n", initialPenalties[2]);

        // ── Solve ────────────────────────────────────────────────────────────
        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher = ProblemBuilder.getHostVmsFetcher(problem);
        SplittableRandom random = new SplittableRandom(seed);
        AlnsMigrationSolver solver = new AlnsMigrationSolver(hostVmsFetcher, random);

        System.out.println("\nSolving (seed=" + seed + ")...");
        long start = System.currentTimeMillis();
        // Pass our pre-built initial solution; solver deep-copies it internally.
        MigrationSolution finalSolution = solver.solve(problem, initialSolution);
        long elapsed = System.currentTimeMillis() - start;
        System.out.println("Done in " + elapsed + " ms.\n");

        // ── Final metrics ────────────────────────────────────────────────────
        int finalEmpty = countEmptyHosts(problem, finalSolution);
        int[] finalPenalties = computePenalties(problem, finalSolution, builder, plugin != null);
        int migrations = countMigrations(problem, finalSolution);

        System.out.println("Results:");
        System.out.printf("  Empty hosts: %d → %d (+%d)%n", initialEmpty, finalEmpty, finalEmpty - initialEmpty);
        System.out.println("  Migrations:  " + migrations);

        // Print migration details for small instances
        if (migrations > 0 && migrations <= 100) {
            System.out.println("\nMigration details:");
            for (Vm vm : problem.getVms()) {
                Placement current = finalSolution.getPlacement(vm);
                if (current != vm.getInitialPlacement()) {
                    Host fromHost = vm.getInitialPlacement().getHost();
                    Host toHost = current.getHost();
                    System.out.println("  VM " + vm.getIndex()
                            + ": host " + fromHost.getIndex()
                            + " → host " + toHost.getIndex());
                }
            }
        }

        // ── Structured output for EvoCode fitness parsing ─────────────────────
        System.out.println();
        System.out.println("INITIAL_PENALTY_A=" + initialPenalties[0]);
        System.out.println("INITIAL_PENALTY_B=" + initialPenalties[1]);
        System.out.println("INITIAL_PENALTY_C=" + initialPenalties[2]);
        System.out.println("FINAL_PENALTY_A="   + finalPenalties[0]);
        System.out.println("FINAL_PENALTY_B="   + finalPenalties[1]);
        System.out.println("FINAL_PENALTY_C="   + finalPenalties[2]);
        System.out.println("EMPTY_HOSTS_INITIAL=" + initialEmpty);
        System.out.println("EMPTY_HOSTS_FINAL="   + finalEmpty);
        System.out.println("MIGRATIONS=" + migrations);
        System.out.println("RUNTIME_MS=" + elapsed);
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    /**
     * Compute tenant-level penalties [A, B, C] via the registered TenantPlugin.
     * Returns [0, 0, 0] when running in stub mode (no plugin).
     */
    private static int[] computePenalties(Problem problem, MigrationSolution solution,
                                          ProblemBuilder builder, boolean hasPlugin) {
        if (!hasPlugin || builder.getTenantPluginFetcher() == null) {
            return new int[]{0, 0, 0};
        }
        TenantPlugin pv = builder.getTenantPluginFetcher().fetch(solution);
        return new int[]{
            toInt(pv.tenantCountFull(problem, solution)),
            toInt(pv.tenantVmCountFull(problem, solution)),
            toInt(pv.maxVmsFull(problem, solution))
        };
    }

    /**
     * Extract an integer from a Value (handles IntValue; falls back to toString parsing).
     */
    private static int toInt(Value v) {
        if (v instanceof IntValue iv) {
            return iv.getValue();
        }
        // Fallback: strip non-digit/minus characters from "IntValue(123)"
        try {
            return Integer.parseInt(v.toString().replaceAll("[^0-9\\-]", ""));
        } catch (NumberFormatException e) {
            System.err.println("WARN: Could not parse Value as int: " + v);
            return 0;
        }
    }

    /**
     * Count hosts with no VMs assigned in the given solution.
     */
    private static int countEmptyHosts(Problem problem, MigrationSolution solution) {
        int count = 0;
        for (Host host : problem.getHosts()) {
            boolean hasVms = false;
            for (Vm vm : problem.getVms()) {
                Placement p = solution.getPlacement(vm);
                if (p != null && p.getHost() == host) {
                    hasVms = true;
                    break;
                }
            }
            if (!hasVms) count++;
        }
        return count;
    }

    /**
     * Count VMs whose final placement differs from their initial placement.
     */
    private static int countMigrations(Problem problem, MigrationSolution solution) {
        int count = 0;
        for (Vm vm : problem.getVms()) {
            if (solution.getPlacement(vm) != vm.getInitialPlacement()) {
                count++;
            }
        }
        return count;
    }
}
