package com.vmscheduling.plugin;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.objective.MigrationObjective;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.MigrationVariable;

/**
 * Abstract base class for LLM-generated tenant-level soft constraint implementations.
 *
 * <h2>What the LLM implements</h2>
 * <ol>
 *   <li>3 {@link MigrationVariable} update methods (incremental state tracking)</li>
 *   <li>{@link #copy()} — deep copy of internal state arrays/maps</li>
 *   <li>{@link #createFresh()} — new uninitialised instance of the same concrete class</li>
 *   <li>9 penalty calculation methods (3 per constraint A/B/C)</li>
 * </ol>
 *
 * <h2>Constraint specifications</h2>
 * <ul>
 *   <li><b>A</b> ({@code n1}): distinct high-level tenants (level&ge;5) per host &le; n1.
 *       Penalty = sum over hosts of max(0, distinct_count - n1)</li>
 *   <li><b>B</b> ({@code n2}): VMs from a single high-level tenant per host &le; n2.
 *       Penalty = sum over (tenant,host) pairs of max(0, vm_count - n2)</li>
 *   <li><b>C</b> ({@code n3}): total VMs per host &le; n3.
 *       Penalty = sum over hosts of max(0, total_vm_count - n3)</li>
 * </ul>
 *
 * <h2>Critical rules</h2>
 * <ul>
 *   <li>Delta methods return PROJECTED FULL values, not marginal changes.</li>
 *   <li>Delta evaluation must be incremental (O(1) or O(affected hosts)) — never copy
 *       the solution and recompute everything.</li>
 *   <li>High-level tenant check: {@code vm.getTenantLevel() >= 5}, NOT == 5.</li>
 *   <li>Use {@code Math.max(0, count - threshold)} for all penalties.</li>
 *   <li>Check null placement before accessing host: {@code solution.getPlacement(vm)} can be null.</li>
 * </ul>
 *
 * <h2>Factory methods (do NOT override)</h2>
 * The three {@code final} factory methods return {@link MigrationObjective} adapters that
 * use a {@link MigrationFetcher} to retrieve the correct variable copy from any solution,
 * ensuring correctness under ALNS copy-on-write semantics.
 */
public abstract class TenantPlugin implements MigrationVariable {

    /** Threshold n_1: max distinct high-level tenants per host. */
    protected int n1;
    /** Threshold n_2: max VMs from one high-level tenant per host. */
    protected int n2;
    /** Threshold n_3: max total VMs per host. */
    protected int n3;

    /**
     * Called by ProblemBuilder before the plugin is registered.
     * LLM-generated subclasses do NOT need to override this.
     */
    public final void setThresholds(int n1, int n2, int n3) {
        this.n1 = n1;
        this.n2 = n2;
        this.n3 = n3;
    }

    // ── MigrationVariable: state tracking (LLM implements) ────────────────────

    /**
     * Full O(V) rebuild from scratch. Called at solution initialisation.
     * Iterate all VMs; for each VM with tenantLevel >= 5 and non-null placement,
     * record (a) per-host distinct tenant count and (b) per-(tenant,host) VM count.
     */
    @Override
    public abstract void update(Problem problem, MigrationSolution solution);

    /**
     * Incremental O(k) update for a ruin step (VMs removed from their hosts).
     * For each VM in delta.getVms() with tenantLevel >= 5:
     * decrement vm count for that tenant on that host;
     * if count drops to 0, decrement the distinct tenant count for that host.
     */
    @Override
    public abstract void update(Problem problem, MigrationSolution solution, RuinDelta delta);

    /**
     * Incremental O(1) update for a recreate step (one VM placed/moved).
     * Handle removal from old host (if non-null) and addition to new host.
     * Update distinct tenant counts only when adding the first or removing the last VM.
     */
    @Override
    public abstract void update(Problem problem, MigrationSolution solution, RecreateDelta delta);

    /**
     * Deep copy of all internal state (int arrays, maps) so the ALNS loop can work
     * on an independent copy of the solution without affecting the original.
     * Must copy EVERY field that update() writes to.
     */
    @Override
    public abstract MigrationVariable copy();

    /**
     * Return a new, uninitialised instance of the same concrete class with the same
     * thresholds. Called by the ProblemBuilder supplier to create fresh variable slots.
     * Typical implementation: {@code return new MyConcreteClass(n1, n2, n3);}
     */
    public abstract TenantPlugin createFresh();

    // ── Constraint A: distinct high-level tenants per host (LLM implements) ────

    /** Full O(H) calculation. Returns sum of max(0, distinct_count - n1) over all hosts. */
    public abstract Value tenantCountFull(Problem p, MigrationSolution s);

    /**
     * Projected penalty after ruin delta (O(1)).
     * Recalculate ONLY for the affected host(s), return current_total + delta.
     */
    public abstract Value tenantCountRuin(Problem p, MigrationSolution s, RuinDelta d);

    /**
     * Projected penalty after recreate delta (O(1)).
     * Recalculate ONLY for old host (if any) and new host, return current_total + delta.
     */
    public abstract Value tenantCountRecreate(Problem p, MigrationSolution s, RecreateDelta d);

    // ── Constraint B: VMs per high-level tenant per host (LLM implements) ───────

    /** Full O(T*H) calculation. Returns sum of max(0, vm_count - n2) over all (tenant,host). */
    public abstract Value tenantVmCountFull(Problem p, MigrationSolution s);

    /** Projected penalty after ruin delta (O(1)). */
    public abstract Value tenantVmCountRuin(Problem p, MigrationSolution s, RuinDelta d);

    /** Projected penalty after recreate delta (O(1)). */
    public abstract Value tenantVmCountRecreate(Problem p, MigrationSolution s, RecreateDelta d);

    // ── Constraint C: total VMs per host (LLM implements) ────────────────────────

    /** Full O(H) calculation. Returns sum of max(0, total_vm_count - n3) over all hosts. */
    public abstract Value maxVmsFull(Problem p, MigrationSolution s);

    /** Projected penalty after ruin delta (O(1)). */
    public abstract Value maxVmsRuin(Problem p, MigrationSolution s, RuinDelta d);

    /** Projected penalty after recreate delta (O(1)). */
    public abstract Value maxVmsRecreate(Problem p, MigrationSolution s, RecreateDelta d);

    // ── Factory: MigrationObjective adapters (final — LLM does NOT override) ─────

    /**
     * Returns a {@link MigrationObjective} for Constraint A backed by this plugin.
     * Uses the fetcher so the objective always operates on the correct variable copy.
     */
    public final MigrationObjective tenantCountObjective(MigrationFetcher<TenantPlugin> fetcher) {
        return new MigrationObjective() {
            @Override
            public Value calculate(Problem p, MigrationSolution s) {
                return fetcher.fetch(s).tenantCountFull(p, s);
            }
            @Override
            public Value calculate(Problem p, MigrationSolution s, RuinDelta d) {
                return fetcher.fetch(s).tenantCountRuin(p, s, d);
            }
            @Override
            public Value calculate(Problem p, MigrationSolution s, RecreateDelta d) {
                return fetcher.fetch(s).tenantCountRecreate(p, s, d);
            }
        };
    }

    /**
     * Returns a {@link MigrationObjective} for Constraint B backed by this plugin.
     */
    public final MigrationObjective tenantVmCountObjective(MigrationFetcher<TenantPlugin> fetcher) {
        return new MigrationObjective() {
            @Override
            public Value calculate(Problem p, MigrationSolution s) {
                return fetcher.fetch(s).tenantVmCountFull(p, s);
            }
            @Override
            public Value calculate(Problem p, MigrationSolution s, RuinDelta d) {
                return fetcher.fetch(s).tenantVmCountRuin(p, s, d);
            }
            @Override
            public Value calculate(Problem p, MigrationSolution s, RecreateDelta d) {
                return fetcher.fetch(s).tenantVmCountRecreate(p, s, d);
            }
        };
    }

    /**
     * Returns a {@link MigrationObjective} for Constraint C backed by this plugin.
     */
    public final MigrationObjective maxVmsObjective(MigrationFetcher<TenantPlugin> fetcher) {
        return new MigrationObjective() {
            @Override
            public Value calculate(Problem p, MigrationSolution s) {
                return fetcher.fetch(s).maxVmsFull(p, s);
            }
            @Override
            public Value calculate(Problem p, MigrationSolution s, RuinDelta d) {
                return fetcher.fetch(s).maxVmsRuin(p, s, d);
            }
            @Override
            public Value calculate(Problem p, MigrationSolution s, RecreateDelta d) {
                return fetcher.fetch(s).maxVmsRecreate(p, s, d);
            }
        };
    }
}
