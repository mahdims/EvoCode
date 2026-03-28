package com.vmscheduling.operator;

import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.util.Comparator;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Ruin strategy: GUIDED (improvement-gated, skip if no improvement).
 * VMs removed one-at-a-time with per-VM constraint/objective checks.
 */
public enum RuinType {

    /**
     * Guided, improvement-gated ruin (default from documentation).
     * VMs removed one-at-a-time with per-VM constraint/objective checks.
     * Returns null if no improving removal found → skips entire ALNS iteration.
     */
    GUIDED {
        @Override
        public List<Vm> getRuinVms(Problem problem, MigrationSolution solution,
                                    List<Host> ruinHosts, VmSorterType vmSorterType,
                                    SplittableRandom random,
                                    MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher) {
            HostVmsMigrationVariable variable = hostVmsFetcher.fetch(solution);
            List<Vm> ruinVms = new ObjectArrayList<>();
            boolean improved = false;

            // CRITICAL FIX: Store current objective to compare against (delta methods may return full values)
            Value currentObjective = problem.getMigrationObjective().calculate(problem, solution);

            for (Host host : ruinHosts) {
                List<Vm> vms = new ObjectArrayList<>(
                        variable.getMigratableHostVms().get(host.getIndex()));
                sortVmsByType(solution, vms, vmSorterType, random, true);
                for (Vm vm : vms) {
                    RuinDelta ruinDelta = new RuinDelta(new Vm[]{vm});
                    if (!problem.getMigrationConstraint().satisfy(problem, solution, ruinDelta)) {
                        continue;
                    }
                    ruinVms.add(vm);
                    Value projectedObjective = problem.getMigrationObjective()
                                    .calculate(problem, solution, ruinDelta);
                    ruinDelta.update(problem, solution);

                    // CRITICAL FIX: Compare projected vs current, not vs zero
                    if (projectedObjective.compareTo(currentObjective) < 0) {
                        improved = true;
                        currentObjective = projectedObjective; // Update baseline before break
                        break;
                    }
                    currentObjective = projectedObjective; // Update for next iteration
                }
            }
            return improved ? ruinVms : null;
        }
    };

    public abstract List<Vm> getRuinVms(Problem problem, MigrationSolution solution,
                                         List<Host> ruinHosts, VmSorterType vmSorterType,
                                         SplittableRandom random,
                                         MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher);

    /**
     * Context-aware VM sorting (shared between GUIDED and RANDOM).
     * Ruin: moved-VMs first (pre-sort), then ascending by VmSorterType.
     * Recreate: ascending by VmSorterType, then reversed (largest first).
     */
    protected void sortVmsByType(MigrationSolution solution, List<Vm> vms,
                                   VmSorterType vmSorterType, SplittableRandom random,
                                   boolean isRuin) {
        if (isRuin && vmSorterType != VmSorterType.RANDOM) {
            // CRITICAL FIX: Sort by VmSorterType FIRST, then by moved-status
            // This makes moved-status the primary key (applied last with stable sort)
            vmSorterType.sort(vms, random);
            // Moved VMs (false) should sort before not-moved VMs (true)
            vms.sort(Comparator.comparing(
                    vm -> vm.getInitialPlacement() == solution.getPlacement(vm)));
        } else {
            vmSorterType.sort(vms, random);
        }
        if (!isRuin) {
            java.util.Collections.reverse(vms);
        }
    }
}
