package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.FloatValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.TenantMigrationVariable;

import java.util.Map;

/**
 * Tenant distribution spread metrics.
 * Measures how evenly tenants are distributed across hosts.
 * Lower variance = more spread = better.
 *
 * See MainWiki §6.4 / 04-objectives.md.
 */
public class TenantMigrationObjective implements MigrationObjective {

    private final MigrationFetcher<TenantMigrationVariable> fetcher;

    public TenantMigrationObjective(MigrationFetcher<TenantMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        TenantMigrationVariable variable = fetcher.fetch(solution);
        float totalVariance = 0;
        for (Map.Entry<String, int[]> entry : variable.getTenantHostCounts().entrySet()) {
            int[] counts = entry.getValue();
            totalVariance += computeVariance(counts);
        }
        return FloatValue.of(totalVariance);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        return calculate(problem, solution);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        return calculate(problem, solution);
    }

    private float computeVariance(int[] counts) {
        if (counts.length == 0) return 0;
        float sum = 0;
        for (int c : counts) sum += c;
        float mean = sum / counts.length;
        float variance = 0;
        for (int c : counts) {
            float diff = c - mean;
            variance += diff * diff;
        }
        return variance / counts.length;
    }
}
