package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.value.FloatValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.LoadVariable;
import com.vmscheduling.variable.MigrationFetcher;

/**
 * Minimize load variance across hosts.
 * Lower variance = more balanced = better.
 *
 * See MainWiki §6.4 / 04-objectives.md.
 */
public class MinLoadBalancingObjective implements MigrationObjective {

    private final MigrationFetcher<LoadVariable> fetcher;

    public MinLoadBalancingObjective(MigrationFetcher<LoadVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        LoadVariable variable = fetcher.fetch(solution);
        float[] loads = variable.getHostLoads();
        return FloatValue.of(computeVariance(loads));
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        // CORRECTNESS FIX: Return PROJECTED variance after applying delta
        // Load calculation is complex (max of CPU/MEM ratios per NUMA), so we simulate
        MigrationSolution projected = new MigrationSolution(solution);
        delta.update(problem, projected);
        LoadVariable projectedVariable = fetcher.fetch(projected);
        float[] projectedLoads = projectedVariable.getHostLoads();
        return FloatValue.of(computeVariance(projectedLoads));
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        // CORRECTNESS FIX: Return PROJECTED variance after applying delta
        // Load calculation is complex (max of CPU/MEM ratios per NUMA), so we simulate
        MigrationSolution projected = new MigrationSolution(solution);
        delta.update(problem, projected);
        LoadVariable projectedVariable = fetcher.fetch(projected);
        float[] projectedLoads = projectedVariable.getHostLoads();
        return FloatValue.of(computeVariance(projectedLoads));
    }

    private float computeVariance(float[] loads) {
        if (loads.length == 0) return 0;
        float sum = 0;
        for (float load : loads) {
            sum += load;
        }
        float mean = sum / loads.length;
        float variance = 0;
        for (float load : loads) {
            float diff = load - mean;
            variance += diff * diff;
        }
        return variance / loads.length;
    }
}
