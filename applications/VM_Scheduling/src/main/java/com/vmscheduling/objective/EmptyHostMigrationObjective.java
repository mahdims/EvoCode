package com.vmscheduling.objective;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.EmptyHostMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;

/**
 * Primary objective: maximize empty hosts.
 * Returns NEGATED empty count so lower = more empty = better.
 *
 * All methods return full/projected values (not marginal deltas):
 * - calculate(full): IntValue.of(-numEmptyHost)
 * - calculate(RuinDelta): IntValue.of(-projectedEmptyAfterRuin)
 * - calculate(RecreateDelta): IntValue.of(-projectedEmptyAfterRecreate)
 *
 * See MainWiki §6.4 / 04-objectives.md.
 */
public class EmptyHostMigrationObjective implements MigrationObjective {

    private final MigrationFetcher<EmptyHostMigrationVariable> fetcher;

    public EmptyHostMigrationObjective(MigrationFetcher<EmptyHostMigrationVariable> fetcher) {
        this.fetcher = fetcher;
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution) {
        EmptyHostMigrationVariable variable = fetcher.fetch(solution);
        return IntValue.of(-variable.getNumEmptyHost());
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RuinDelta delta) {
        EmptyHostMigrationVariable variable = fetcher.fetch(solution);

        // SEMANTIC FIX: Return projected full value, not marginal delta
        // Count VMs removed per host to handle multi-VM ruin correctly
        int[] removedPerHost = new int[problem.getHosts().size()];
        for (Vm vm : delta.getVms()) {
            Placement p = solution.getPlacement(vm);
            if (p != null) {
                removedPerHost[p.getHost().getIndex()]++;
            }
        }

        // Calculate projected number of empty hosts AFTER ruin
        int projectedEmpty = variable.getNumEmptyHost();
        for (int hostIdx = 0; hostIdx < removedPerHost.length; hostIdx++) {
            if (removedPerHost[hostIdx] > 0) {
                int currentCount = variable.getHostVmCount(hostIdx);
                // If removing all VMs makes the host empty, that's +1 empty host
                if (currentCount == removedPerHost[hostIdx]) {
                    projectedEmpty++;
                }
            }
        }
        return IntValue.of(-projectedEmpty);
    }

    @Override
    public Value calculate(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        EmptyHostMigrationVariable variable = fetcher.fetch(solution);

        // SEMANTIC FIX: Return projected full value, not marginal delta
        int projectedEmpty = variable.getNumEmptyHost();
        Vm vm = delta.getVm();
        int targetHostIdx = delta.getPlacement().getHost().getIndex();

        // Placing on an empty host loses one empty host
        if (variable.getHostVmCount(targetHostIdx) == 0) {
            projectedEmpty--;
        }

        // If VM was on a host and it becomes empty, gain one empty host
        Placement oldP = solution.getPlacement(vm);
        if (oldP != null) {
            int oldHostIdx = oldP.getHost().getIndex();
            if (variable.getHostVmCount(oldHostIdx) == 1 && oldHostIdx != targetHostIdx) {
                projectedEmpty++;
            }
        }

        return IntValue.of(-projectedEmpty);
    }
}
