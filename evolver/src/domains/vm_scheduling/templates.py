"""
VM Scheduling Domain — LLM Context Templates and Initial Seeds

Contains prompt constraints, data-structure documentation, and a
reference seed implementation of TenantPlugin.
"""

from typing import List, Tuple


# ---------------------------------------------------------------------------
# LLM context strings
# ---------------------------------------------------------------------------

VM_PROBLEM_DESCRIPTION = """
=== VM SCHEDULING — TENANT-LEVEL SOFT CONSTRAINT EVOLUTION ===

You are evolving Java implementations of soft constraints for a VM consolidation solver.

**Background:**
The solver (ALNS) migrates virtual machines (VMs) across physical hosts to consolidate
workloads and free up hosts. Each host has NUMA sockets with limited CPU/memory.

**Your task:**
Implement a `TenantPlugin` subclass that correctly tracks tenant distribution state and
computes penalties for three soft constraints:

  Constraint A (n1): For each host, the number of DISTINCT high-level tenants (tenantLevel >= 5)
                     must be <= n1 (default: 2).
                     Penalty = sum over hosts of max(0, distinct_high_tenants_on_host - n1)

  Constraint B (n2): For each (tenant, host) pair, the number of VMs from one high-level tenant
                     on that host must be <= n2 (default: 3).
                     Penalty = sum over (tenant,host) pairs of max(0, vm_count - n2)

  Constraint C (n3): For each host, the total number of VMs must be <= n3 (default: 12).
                     Penalty = sum over hosts of max(0, total_vm_count - n3)

**Fitness metric:** The solver is guided by these penalties. A good implementation
allows the solver to reduce violations, measured as:
  reduction = (initial_penalty_total - final_penalty_total) / max(1, initial_penalty_total)

Higher reduction = better fitness. The solver CAN only reduce violations if the
penalties are computed correctly (incorrectly always returning 0 gives no signal).
"""

VM_CONSTRAINTS = """
=== MANDATORY CONTRACT ===

**PACKAGE AND CLASS:**
  package plugin;
  public class MyTenantPlugin extends TenantPlugin { ... }

**REQUIRED IMPORTS:**
  import com.vmscheduling.delta.RecreateDelta;
  import com.vmscheduling.delta.RuinDelta;
  import com.vmscheduling.model.MigrationSolution;
  import com.vmscheduling.model.Problem;
  import com.vmscheduling.model.Vm;
  import com.vmscheduling.value.IntValue;
  import com.vmscheduling.value.Value;
  import com.vmscheduling.variable.MigrationVariable;
  import java.util.HashMap;
  import java.util.Map;

**MUST IMPLEMENT (14 abstract methods):**
  1. void update(Problem, MigrationSolution)                          — full O(V) state rebuild
  2. void update(Problem, MigrationSolution, RuinDelta)               — incremental state update on ruin
  3. void update(Problem, MigrationSolution, RecreateDelta)           — incremental state update on recreate
  4. MigrationVariable copy()                                         — deep copy of all state fields
  5. TenantPlugin createFresh()                                       — new empty instance (with thresholds)
  6-8.  Value tenantCount{Full,Ruin,Recreate}(...)                    — Constraint A penalties
  9-11. Value tenantVmCount{Full,Ruin,Recreate}(...)                  — Constraint B penalties
  12-14.Value maxVms{Full,Ruin,Recreate}(...)                         — Constraint C penalties

**CRITICAL RULES:**
1. HIGH-LEVEL TENANT CHECK: vm.getTenantLevel() >= 5  (NOT == 5; level can be 5, 6, 7, ...)
2. NULL CHECK: solution.getPlacement(vm) can return null; ALWAYS check before .getHost()
3. PENALTY FORMULA: Math.max(0, count - threshold) for all three constraints
4. DELTA PROJECTION: tenantCount/Ruin/Recreate return PROJECTED FULL penalty values (not deltas)
5. INCREMENTAL UPDATES: delta methods must be O(1) or O(affected_hosts), NOT O(all_hosts)
6. RETURN TYPE: All penalty methods return IntValue.of(value)
7. NO I/O: No System.out, no file operations, no logging
8. NO EXTERNAL DEPS: Only imports listed above are allowed
9. SINGLE CLASS: One class per file, no inner classes
10. THRESHOLDS: Use this.n1, this.n2, this.n3 (set by ProblemBuilder via setThresholds)

**RuinDelta API:**
  delta.getVms()  — Vm[] of VMs being removed; solution.getPlacement(vm) is still valid here

**RecreateDelta API:**
  delta.getVm()        — the VM being placed
  delta.getPlacement() — the NEW placement (target)
  solution.getPlacement(delta.getVm())  — old placement (null if VM was just ruined)
  delta.getHost()      — shortcut for delta.getPlacement().getHost()

**Vm API:**
  vm.getTenantLevel()  — int (0-9; >= 5 means high-level)
  vm.getTenantId()     — String tenant identifier
  vm.getIndex()        — int VM index

**Placement API:**
  placement.getHost()          — Host object
  placement.getHost().getIndex() — int host index (0-based)
"""

VM_DATA_STRUCTURES = """
=== DATA STRUCTURES ===

class TenantPlugin extends abstract (your class extends this):
  protected int n1, n2, n3;  // thresholds (set by setThresholds())

class Problem:
  List<Host>  getHosts()   — all hosts (index 0..H-1)
  List<Vm>    getVms()     — all VMs

class MigrationSolution:
  Placement getPlacement(Vm vm)  — current placement of VM (null if unplaced)

class Vm:
  int    getTenantLevel()  — 0-9 (>=5 means high-level tenant)
  String getTenantId()     — tenant identifier
  int    getIndex()        — VM index

class Placement:
  Host getHost()   — physical host where VM is placed

class Host:
  int getIndex()   — 0-based host index

IntValue.of(int x)  — creates a Value wrapping integer x (use for all return values)

=== RECOMMENDED STATE LAYOUT ===

Maintain running totals to avoid O(H) scans on delta calls:

  int[] distinctTenantCount      // per host: number of distinct high-level tenants
  int[] totalVmCount             // per host: total VMs placed
  Map<String, Integer>[] tenantVmCountPerHost  // per host: tenant_id -> VM count
  int penaltyA, penaltyB, penaltyC  // running totals (updated incrementally)

For delta projection, avoid modifying state — compute projected value from current totals.
"""


# ---------------------------------------------------------------------------
# Initial seed — reference TenantPlugin implementation
# ---------------------------------------------------------------------------

_SEED_IDEA = (
    "Track per-host distinct-tenant counts and per-(host,tenant) VM counts. "
    "Maintain running penalty totals updated incrementally. "
    "Delta methods project the new total without mutating state."
)

_SEED_CODE = '''\
package plugin;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.delta.RuinDelta;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Vm;
import com.vmscheduling.plugin.TenantPlugin;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import com.vmscheduling.variable.MigrationVariable;

import java.util.HashMap;
import java.util.Map;

/**
 * Reference TenantPlugin implementation.
 * Tracks per-host tenant state with running penalty totals for O(1) deltas.
 */
public class TenantPluginRef extends TenantPlugin {

    private int numHosts;
    private int[] distinctTenantCount;   // per host: distinct high-level tenants
    private int[] totalVmCount;          // per host: total VMs
    @SuppressWarnings("unchecked")
    private Map<String, Integer>[] tenantVmCountPerHost;  // per host: tenant->count

    // Running penalty totals (updated incrementally)
    private int penaltyA;
    private int penaltyB;
    private int penaltyC;

    public TenantPluginRef() {}

    private TenantPluginRef(int n1, int n2, int n3) {
        setThresholds(n1, n2, n3);
    }

    @Override
    public TenantPlugin createFresh() {
        return new TenantPluginRef(n1, n2, n3);
    }

    @Override
    @SuppressWarnings("unchecked")
    public MigrationVariable copy() {
        TenantPluginRef c = new TenantPluginRef(n1, n2, n3);
        c.numHosts = numHosts;
        c.distinctTenantCount = distinctTenantCount.clone();
        c.totalVmCount = totalVmCount.clone();
        c.tenantVmCountPerHost = new HashMap[numHosts];
        for (int i = 0; i < numHosts; i++) {
            c.tenantVmCountPerHost[i] = new HashMap<>(tenantVmCountPerHost[i]);
        }
        c.penaltyA = penaltyA;
        c.penaltyB = penaltyB;
        c.penaltyC = penaltyC;
        return c;
    }

    // ── Full O(V) rebuild ────────────────────────────────────────────────────

    @Override
    @SuppressWarnings("unchecked")
    public void update(Problem problem, MigrationSolution solution) {
        numHosts = problem.getHosts().size();
        distinctTenantCount = new int[numHosts];
        totalVmCount = new int[numHosts];
        tenantVmCountPerHost = new HashMap[numHosts];
        for (int i = 0; i < numHosts; i++) {
            tenantVmCountPerHost[i] = new HashMap<>();
        }
        penaltyA = penaltyB = penaltyC = 0;

        for (Vm vm : problem.getVms()) {
            var placement = solution.getPlacement(vm);
            if (placement == null) continue;
            int h = placement.getHost().getIndex();
            totalVmCount[h]++;
            if (vm.getTenantLevel() >= 5) {
                String t = vm.getTenantId();
                int prev = tenantVmCountPerHost[h].getOrDefault(t, 0);
                tenantVmCountPerHost[h].put(t, prev + 1);
                if (prev == 0) distinctTenantCount[h]++;
            }
        }
        for (int h = 0; h < numHosts; h++) {
            penaltyA += Math.max(0, distinctTenantCount[h] - n1);
            for (int cnt : tenantVmCountPerHost[h].values()) {
                penaltyB += Math.max(0, cnt - n2);
            }
            penaltyC += Math.max(0, totalVmCount[h] - n3);
        }
    }

    // ── Incremental ruin (VMs removed, placements still valid) ───────────────

    @Override
    public void update(Problem problem, MigrationSolution solution, RuinDelta delta) {
        for (Vm vm : delta.getVms()) {
            var placement = solution.getPlacement(vm);
            if (placement == null) continue;
            int h = placement.getHost().getIndex();

            // Constraint C
            penaltyC += Math.max(0, totalVmCount[h] - 1 - n3) - Math.max(0, totalVmCount[h] - n3);
            totalVmCount[h]--;

            if (vm.getTenantLevel() >= 5) {
                String t = vm.getTenantId();
                int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
                if (cnt == 0) continue;

                // Constraint B
                penaltyB += Math.max(0, cnt - 1 - n2) - Math.max(0, cnt - n2);
                cnt--;

                if (cnt == 0) {
                    tenantVmCountPerHost[h].remove(t);
                    // Constraint A: this tenant disappears from host
                    penaltyA += Math.max(0, distinctTenantCount[h] - 1 - n1)
                              - Math.max(0, distinctTenantCount[h] - n1);
                    distinctTenantCount[h]--;
                } else {
                    tenantVmCountPerHost[h].put(t, cnt);
                }
            }
        }
    }

    // ── Incremental recreate (VM placed, old placement may be null) ──────────

    @Override
    public void update(Problem problem, MigrationSolution solution, RecreateDelta delta) {
        Vm vm = delta.getVm();
        var oldPlacement = solution.getPlacement(vm);
        var newPlacement = delta.getPlacement();

        // Remove from old host (if it had one)
        if (oldPlacement != null) {
            int h = oldPlacement.getHost().getIndex();
            penaltyC += Math.max(0, totalVmCount[h] - 1 - n3) - Math.max(0, totalVmCount[h] - n3);
            totalVmCount[h]--;
            if (vm.getTenantLevel() >= 5) {
                String t = vm.getTenantId();
                int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
                if (cnt > 0) {
                    penaltyB += Math.max(0, cnt - 1 - n2) - Math.max(0, cnt - n2);
                    cnt--;
                    if (cnt == 0) {
                        tenantVmCountPerHost[h].remove(t);
                        penaltyA += Math.max(0, distinctTenantCount[h] - 1 - n1)
                                  - Math.max(0, distinctTenantCount[h] - n1);
                        distinctTenantCount[h]--;
                    } else {
                        tenantVmCountPerHost[h].put(t, cnt);
                    }
                }
            }
        }

        // Add to new host
        if (newPlacement != null) {
            int h = newPlacement.getHost().getIndex();
            penaltyC += Math.max(0, totalVmCount[h] + 1 - n3) - Math.max(0, totalVmCount[h] - n3);
            totalVmCount[h]++;
            if (vm.getTenantLevel() >= 5) {
                String t = vm.getTenantId();
                int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
                penaltyB += Math.max(0, cnt + 1 - n2) - Math.max(0, cnt - n2);
                if (cnt == 0) {
                    penaltyA += Math.max(0, distinctTenantCount[h] + 1 - n1)
                              - Math.max(0, distinctTenantCount[h] - n1);
                    distinctTenantCount[h]++;
                }
                tenantVmCountPerHost[h].put(t, cnt + 1);
            }
        }
    }

    // ── Constraint A: distinct high-level tenants per host ───────────────────

    @Override
    public Value tenantCountFull(Problem p, MigrationSolution s) {
        return IntValue.of(penaltyA);
    }

    @Override
    public Value tenantCountRuin(Problem p, MigrationSolution s, RuinDelta d) {
        // Project penaltyA after ruin without modifying state
        // Group removals by (host, tenant) to handle multiple VMs from same tenant
        Map<String, Integer> ruinMap = new HashMap<>();  // "h:t" -> count being removed
        for (Vm vm : d.getVms()) {
            if (vm.getTenantLevel() < 5) continue;
            var pl = s.getPlacement(vm);
            if (pl == null) continue;
            String key = pl.getHost().getIndex() + ":" + vm.getTenantId();
            ruinMap.merge(key, 1, Integer::sum);
        }
        int projected = penaltyA;
        Map<Integer, Integer> distinctDelta = new HashMap<>();  // host -> net change in distinct
        for (Map.Entry<String, Integer> e : ruinMap.entrySet()) {
            int colon = e.getKey().indexOf(':');
            int h = Integer.parseInt(e.getKey().substring(0, colon));
            String t = e.getKey().substring(colon + 1);
            int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
            if (cnt > 0 && e.getValue() >= cnt) {
                // Tenant disappears from host
                int curDistinct = distinctTenantCount[h] + distinctDelta.getOrDefault(h, 0);
                projected += Math.max(0, curDistinct - 1 - n1) - Math.max(0, curDistinct - n1);
                distinctDelta.merge(h, -1, Integer::sum);
            }
        }
        return IntValue.of(projected);
    }

    @Override
    public Value tenantCountRecreate(Problem p, MigrationSolution s, RecreateDelta d) {
        Vm vm = d.getVm();
        int projected = penaltyA;
        if (vm.getTenantLevel() >= 5) {
            String t = vm.getTenantId();
            var oldPl = s.getPlacement(vm);
            var newPl = d.getPlacement();
            if (oldPl != null) {
                int h = oldPl.getHost().getIndex();
                if (tenantVmCountPerHost[h].getOrDefault(t, 0) == 1) {
                    // Last VM of this tenant leaving host
                    projected += Math.max(0, distinctTenantCount[h] - 1 - n1)
                               - Math.max(0, distinctTenantCount[h] - n1);
                }
            }
            if (newPl != null) {
                int h = newPl.getHost().getIndex();
                if (tenantVmCountPerHost[h].getOrDefault(t, 0) == 0) {
                    // First VM of this tenant arriving at host
                    projected += Math.max(0, distinctTenantCount[h] + 1 - n1)
                               - Math.max(0, distinctTenantCount[h] - n1);
                }
            }
        }
        return IntValue.of(projected);
    }

    // ── Constraint B: VMs per high-level tenant per host ─────────────────────

    @Override
    public Value tenantVmCountFull(Problem p, MigrationSolution s) {
        return IntValue.of(penaltyB);
    }

    @Override
    public Value tenantVmCountRuin(Problem p, MigrationSolution s, RuinDelta d) {
        Map<String, Integer> ruinMap = new HashMap<>();
        for (Vm vm : d.getVms()) {
            if (vm.getTenantLevel() < 5) continue;
            var pl = s.getPlacement(vm);
            if (pl == null) continue;
            String key = pl.getHost().getIndex() + ":" + vm.getTenantId();
            ruinMap.merge(key, 1, Integer::sum);
        }
        int projected = penaltyB;
        for (Map.Entry<String, Integer> e : ruinMap.entrySet()) {
            int colon = e.getKey().indexOf(':');
            int h = Integer.parseInt(e.getKey().substring(0, colon));
            String t = e.getKey().substring(colon + 1);
            int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
            int removed = Math.min(e.getValue(), cnt);
            projected += Math.max(0, cnt - removed - n2) - Math.max(0, cnt - n2);
        }
        return IntValue.of(projected);
    }

    @Override
    public Value tenantVmCountRecreate(Problem p, MigrationSolution s, RecreateDelta d) {
        Vm vm = d.getVm();
        int projected = penaltyB;
        if (vm.getTenantLevel() >= 5) {
            String t = vm.getTenantId();
            var oldPl = s.getPlacement(vm);
            var newPl = d.getPlacement();
            if (oldPl != null) {
                int h = oldPl.getHost().getIndex();
                int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
                projected += Math.max(0, cnt - 1 - n2) - Math.max(0, cnt - n2);
            }
            if (newPl != null) {
                int h = newPl.getHost().getIndex();
                int cnt = tenantVmCountPerHost[h].getOrDefault(t, 0);
                projected += Math.max(0, cnt + 1 - n2) - Math.max(0, cnt - n2);
            }
        }
        return IntValue.of(projected);
    }

    // ── Constraint C: total VMs per host ─────────────────────────────────────

    @Override
    public Value maxVmsFull(Problem p, MigrationSolution s) {
        return IntValue.of(penaltyC);
    }

    @Override
    public Value maxVmsRuin(Problem p, MigrationSolution s, RuinDelta d) {
        Map<Integer, Integer> ruinCount = new HashMap<>();
        for (Vm vm : d.getVms()) {
            var pl = s.getPlacement(vm);
            if (pl == null) continue;
            ruinCount.merge(pl.getHost().getIndex(), 1, Integer::sum);
        }
        int projected = penaltyC;
        for (Map.Entry<Integer, Integer> e : ruinCount.entrySet()) {
            int h = e.getKey();
            int removed = e.getValue();
            projected += Math.max(0, totalVmCount[h] - removed - n3)
                       - Math.max(0, totalVmCount[h] - n3);
        }
        return IntValue.of(projected);
    }

    @Override
    public Value maxVmsRecreate(Problem p, MigrationSolution s, RecreateDelta d) {
        int projected = penaltyC;
        var oldPl = s.getPlacement(d.getVm());
        var newPl = d.getPlacement();
        if (oldPl != null) {
            int h = oldPl.getHost().getIndex();
            projected += Math.max(0, totalVmCount[h] - 1 - n3) - Math.max(0, totalVmCount[h] - n3);
        }
        if (newPl != null) {
            int h = newPl.getHost().getIndex();
            projected += Math.max(0, totalVmCount[h] + 1 - n3) - Math.max(0, totalVmCount[h] - n3);
        }
        return IntValue.of(projected);
    }
}
'''


def get_vm_initial_seeds() -> List[Tuple[str, str]]:
    """Return (idea, code) seed pairs for initial population bootstrap."""
    return [(_SEED_IDEA, _SEED_CODE)]
