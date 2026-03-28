package com.vmscheduling.input;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.vmscheduling.constraint.AntiAffinityMigrationConstraint;
import com.vmscheduling.constraint.BudgetLimitMigrationConstraint;
import com.vmscheduling.constraint.CpuMemMigrationConstraint;
import com.vmscheduling.constraint.HierarchicalMigrationConstraint;
import com.vmscheduling.constraint.IntraHostMigrationConstraint;
import com.vmscheduling.constraint.TenantMigrationConstraint;
import com.vmscheduling.model.Host;
import com.vmscheduling.model.HostHealthyState;
import com.vmscheduling.model.MigrationSolution;
import com.vmscheduling.model.Numa;
import com.vmscheduling.model.NumaGroup;
import com.vmscheduling.model.Placement;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Rack;
import com.vmscheduling.model.Vm;
import com.vmscheduling.objective.EmptyHostMigrationObjective;
import com.vmscheduling.objective.HierarchicalMigrationObjective;
import com.vmscheduling.objective.HighLevelTenantCountPenaltyObjective;
import com.vmscheduling.objective.HighLevelTenantVmCountPenaltyObjective;
import com.vmscheduling.objective.MaxVmsPerHostPenaltyObjective;
import com.vmscheduling.objective.MigrationCostMigrationObjective;
import com.vmscheduling.objective.MinLoadBalancingObjective;
import com.vmscheduling.plugin.TenantPlugin;
import com.vmscheduling.variable.AntiAffinityMigrationVariable;
import com.vmscheduling.variable.CpuMemMigrationVariable;
import com.vmscheduling.variable.EmptyHostMigrationVariable;
import com.vmscheduling.variable.HostVmsMigrationVariable;
import com.vmscheduling.variable.LoadVariable;
import com.vmscheduling.variable.MigrationCostMigrationVariable;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.TenantLevelMigrationVariable;
import com.vmscheduling.variable.TenantMigrationVariable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Builds a Problem from JSON instance data produced by generate_instance.py.
 * Infers host topology from VM in_host_id and in_numa_id fields.
 *
 * NUMA capacity is configurable (default: 96 CPU, 262144 MB per socket).
 */
public class ProblemBuilder {

    private float numaCpuCapacity = 96.0f;
    private float numaMemCapacity = 262144.0f;
    private int budgetLimit = 100000;

    // Soft constraint thresholds
    private int maxHighLevelTenantsPerHost = 10;       // n_1: max distinct high-level tenants per host
    private int maxVmsPerHighLevelTenantPerHost = 5;   // n_2: max VMs per high-level tenant per host
    private int maxVmsPerHost = 120;                    // n_3: max total VMs per host

    // Optional LLM-generated plugin (replaces stub tenant-level variable/objectives)
    private TenantPlugin tenantPlugin = null;
    private MigrationFetcher<TenantPlugin> tenantPluginFetcher = null;

    public ProblemBuilder numaCpuCapacity(float c) { this.numaCpuCapacity = c; return this; }
    public ProblemBuilder numaMemCapacity(float m) { this.numaMemCapacity = m; return this; }
    public ProblemBuilder budgetLimit(int b) { this.budgetLimit = b; return this; }

    public ProblemBuilder maxHighLevelTenantsPerHost(int n) {
        if (n < 1 || n > 100) {
            throw new IllegalArgumentException("n_1 must be in [1, 100], got: " + n);
        }
        this.maxHighLevelTenantsPerHost = n;
        return this;
    }

    public ProblemBuilder maxVmsPerHighLevelTenantPerHost(int n) {
        if (n < 1 || n > 50) {
            throw new IllegalArgumentException("n_2 must be in [1, 50], got: " + n);
        }
        this.maxVmsPerHighLevelTenantPerHost = n;
        return this;
    }

    public ProblemBuilder maxVmsPerHost(int n) {
        if (n < 10 || n > 500) {
            throw new IllegalArgumentException("n_3 must be in [10, 500], got: " + n);
        }
        this.maxVmsPerHost = n;
        return this;
    }

    /**
     * Set a TenantPlugin implementation (LLM-generated) to replace the stub
     * variable and objectives for tenant-level soft constraints.
     */
    public ProblemBuilder withTenantPlugin(TenantPlugin plugin) {
        this.tenantPlugin = plugin;
        return this;
    }

    /**
     * Returns the fetcher for the registered TenantPlugin variable.
     * Only valid after {@link #build(String)} has been called with a plugin set.
     */
    public MigrationFetcher<TenantPlugin> getTenantPluginFetcher() {
        return tenantPluginFetcher;
    }

    public Problem build(String json) {
        JsonObject root = JsonParser.parseString(json).getAsJsonObject();
        Problem problem = new Problem();

        // ── Read optional soft-constraint thresholds from JSON ──
        if (root.has("soft_constraint_config")) {
            JsonObject sc = root.getAsJsonObject("soft_constraint_config");
            if (sc.has("n1")) maxHighLevelTenantsPerHost      = sc.get("n1").getAsInt();
            if (sc.has("n2")) maxVmsPerHighLevelTenantPerHost = sc.get("n2").getAsInt();
            if (sc.has("n3")) maxVmsPerHost                   = sc.get("n3").getAsInt();
        }

        // ── Parse VMs and infer host topology ──
        JsonArray vmsArray = root.getAsJsonArray("vms");
        Map<String, Host> hostMap = new LinkedHashMap<>();
        Map<String, Map<Integer, Numa>> hostNumaMap = new HashMap<>();

        // First pass: discover hosts and numas
        Rack rack = problem.addRack(); // Single rack for simplicity
        for (JsonElement vmElem : vmsArray) {
            JsonObject vmObj = vmElem.getAsJsonObject();
            String hostId = vmObj.get("in_host_id").getAsString();
            int numaId = vmObj.get("in_numa_id").getAsInt();

            if (!hostMap.containsKey(hostId)) {
                Host host = problem.addHost(rack, HostHealthyState.HEALTHY,
                        new ArrayList<>(), "default");
                hostMap.put(hostId, host);
                problem.addNumaGroup(host);
                hostNumaMap.put(hostId, new HashMap<>());
            }

            Map<Integer, Numa> numaMap = hostNumaMap.get(hostId);
            if (!numaMap.containsKey(numaId)) {
                Host host = hostMap.get(hostId);
                NumaGroup group = host.getNumaGroups().get(0);
                Numa numa = problem.addNuma(group, numaCpuCapacity, numaMemCapacity);
                numaMap.put(numaId, numa);
            }
        }

        // Second pass: create VMs
        Map<String, Vm> vmIdMap = new LinkedHashMap<>();
        for (JsonElement vmElem : vmsArray) {
            JsonObject vmObj = vmElem.getAsJsonObject();
            Vm vm = problem.addVm();
            String vmId = vmObj.get("vm_id").getAsString();
            vmIdMap.put(vmId, vm);

            vm.setNumaCpu(vmObj.get("numa_cpu").getAsFloat());
            vm.setNumaMem(vmObj.get("numa_mem").getAsFloat());
            vm.setMigratable(vmObj.get("can_migration").getAsBoolean());
            vm.setTenantId(vmObj.get("tenant_id").getAsString());
            vm.setNumNumas(1); // All VMs from generator are single-NUMA

            if (vmObj.has("cutting_line_tag")) {
                vm.setCuttingLineTag(vmObj.get("cutting_line_tag").getAsString());
            }
            if (vmObj.has("flavor_id")) {
                vm.setFlavorId(vmObj.get("flavor_id").getAsString());
            }
            if (vmObj.has("tenant_level")) {
                vm.setTenantLevel(vmObj.get("tenant_level").getAsInt());
            }

            // Set initial placement using canonical placement from NumaGroup
            String hostId = vmObj.get("in_host_id").getAsString();
            int numaId = vmObj.get("in_numa_id").getAsInt();
            Numa numa = hostNumaMap.get(hostId).get(numaId);
            // CRITICAL: Use precomputed placement for identity-based isInitial() checks
            // CRITICAL FIX: Use numa.getLocalIndex(), NOT numaId from JSON (could differ)
            NumaGroup numaGroup = numa.getNumaGroup();
            Placement canonicalPlacement = numaGroup.getPlacements(1).get(numa.getLocalIndex());
            vm.setInitialPlacement(canonicalPlacement);
        }

        // ── Parse anti-affinity groups ──
        if (root.has("anti_affinity_groups")) {
            JsonArray aaGroups = root.getAsJsonArray("anti_affinity_groups");
            int groupIdx = 0;
            for (JsonElement groupElem : aaGroups) {
                JsonObject groupObj = groupElem.getAsJsonObject();
                JsonArray vmIds = groupObj.getAsJsonArray("vm_ids_in_group");
                String groupId = "aa_group_" + groupIdx++;
                for (JsonElement idElem : vmIds) {
                    String id = idElem.getAsString();
                    Vm vm = vmIdMap.get(id);
                    if (vm != null) {
                        vm.setAntiAffinityGroupId(groupId);
                    }
                }
            }
        }

        // ── Parse tenant distribution parameters ──
        Map<String, Integer> maxVmsPerGroup = new HashMap<>();
        if (root.has("tenant_dispersed_distribution_parameter")) {
            JsonObject distParam = root.getAsJsonObject("tenant_dispersed_distribution_parameter");
            if (distParam.has("tenant_distribution_parameters")) {
                JsonArray params = distParam.getAsJsonArray("tenant_distribution_parameters");
                for (JsonElement paramElem : params) {
                    JsonObject p = paramElem.getAsJsonObject();
                    String tenantId = p.get("tenant_id").getAsString();
                    int maxPerGroup = p.get("max_vm_num_per_group").getAsInt();
                    maxVmsPerGroup.put(tenantId, maxPerGroup);
                }
            }
        }

        // ── Wire variables, constraints, objectives ──
        MigrationFetcher<CpuMemMigrationVariable> cpuMemFetcher =
                problem.addMigrationVariable(CpuMemMigrationVariable::new);
        MigrationFetcher<HostVmsMigrationVariable> hostVmsFetcher =
                problem.addMigrationVariable(HostVmsMigrationVariable::new);
        MigrationFetcher<EmptyHostMigrationVariable> emptyHostFetcher =
                problem.addMigrationVariable(EmptyHostMigrationVariable::new);
        MigrationFetcher<AntiAffinityMigrationVariable> aaFetcher =
                problem.addMigrationVariable(AntiAffinityMigrationVariable::new);
        MigrationFetcher<MigrationCostMigrationVariable> costFetcher =
                problem.addMigrationVariable(MigrationCostMigrationVariable::new);
        MigrationFetcher<LoadVariable> loadFetcher =
                problem.addMigrationVariable(() -> new LoadVariable(cpuMemFetcher));
        MigrationFetcher<TenantMigrationVariable> tenantFetcher =
                problem.addMigrationVariable(TenantMigrationVariable::new);
        // Constraints
        HierarchicalMigrationConstraint.Builder constraintBuilder =
                HierarchicalMigrationConstraint.builder()
                        .constraint(new CpuMemMigrationConstraint(cpuMemFetcher))
                        .constraint(new IntraHostMigrationConstraint())
                        .constraint(new AntiAffinityMigrationConstraint(aaFetcher))
                        .constraint(new BudgetLimitMigrationConstraint(costFetcher, budgetLimit));

        if (!maxVmsPerGroup.isEmpty()) {
            constraintBuilder.constraint(new TenantMigrationConstraint(tenantFetcher, maxVmsPerGroup));
        }

        problem.setMigrationConstraint(constraintBuilder.build());

        // Objectives — either plugin-backed or stub implementations
        HierarchicalMigrationObjective.Builder objectiveBuilder = HierarchicalMigrationObjective.builder();

        if (tenantPlugin != null) {
            // Wire LLM-generated plugin: register as variable, use plugin objectives
            tenantPlugin.setThresholds(maxHighLevelTenantsPerHost, maxVmsPerHighLevelTenantPerHost, maxVmsPerHost);
            final TenantPlugin pluginRef = tenantPlugin;
            // Capture thresholds as locals so the lambda doesn't need protected-field access
            final int pluginN1 = maxHighLevelTenantsPerHost;
            final int pluginN2 = maxVmsPerHighLevelTenantPerHost;
            final int pluginN3 = maxVmsPerHost;
            this.tenantPluginFetcher = problem.addMigrationVariable(() -> {
                TenantPlugin fresh = pluginRef.createFresh();
                fresh.setThresholds(pluginN1, pluginN2, pluginN3);
                return fresh;
            });
            objectiveBuilder
                    .objective(tenantPlugin.tenantCountObjective(tenantPluginFetcher))
                    .objective(tenantPlugin.tenantVmCountObjective(tenantPluginFetcher))
                    .objective(tenantPlugin.maxVmsObjective(tenantPluginFetcher));
        } else {
            // Use stub implementations (all return 0)
            MigrationFetcher<TenantLevelMigrationVariable> tenantLevelFetcher =
                    problem.addMigrationVariable(() -> new TenantLevelMigrationVariable(hostVmsFetcher, problem));
            objectiveBuilder
                    .objective(new HighLevelTenantCountPenaltyObjective(tenantLevelFetcher, maxHighLevelTenantsPerHost))
                    .objective(new HighLevelTenantVmCountPenaltyObjective(tenantLevelFetcher, maxVmsPerHighLevelTenantPerHost))
                    .objective(new MaxVmsPerHostPenaltyObjective(hostVmsFetcher, maxVmsPerHost));
        }

        problem.setMigrationObjective(
                objectiveBuilder
                        // EXISTING: Consolidation objectives
                        .objective(new EmptyHostMigrationObjective(emptyHostFetcher))
                        .objective(new MinLoadBalancingObjective(loadFetcher))
                        .minorObjective(new MigrationCostMigrationObjective(costFetcher), true)
                        .build()
        );

        return problem;
    }

    /**
     * Returns the HostVmsMigrationVariable fetcher index (always slot 1
     * in the standard wiring order above).
     */
    public static MigrationFetcher<HostVmsMigrationVariable> getHostVmsFetcher(Problem problem) {
        return new MigrationFetcher<>(1);
    }

    /**
     * Creates an unbalanced solution WITHOUT modifying VM initial placements.
     * Forces VMs onto fewer hosts to create consolidation opportunity.
     *
     * CRITICAL: Does NOT call vm.setInitialPlacement() - preserves original placements
     * from JSON so migration cost tracking works correctly.
     *
     * @param problem Problem with balanced initial placements (from JSON)
     * @param random Random number generator for shuffling
     * @param clearHostRatio Fraction of hosts to clear (pack VMs onto remaining hosts)
     * @return Unbalanced MigrationSolution (VMs packed onto fewer hosts)
     */
    public static MigrationSolution unbalanceInitialPlacements(Problem problem, java.util.SplittableRandom random,
                                                               double clearHostRatio) {
        // Build placement array for the unbalanced solution
        Placement[] unbalancedPlacements = new Placement[problem.getVms().size()];

        // Collect migratable VMs with their original host indices
        java.util.List<Vm> migratableVms = new java.util.ArrayList<>();
        java.util.Map<Vm, Integer> originalHostMap = new java.util.HashMap<>();
        for (Vm vm : problem.getVms()) {
            if (vm.isMigratable()) {
                migratableVms.add(vm);
                int originalHostIdx = vm.getInitialPlacement().getHost().getIndex();
                originalHostMap.put(vm, originalHostIdx);
            } else {
                // Non-migratable VMs stay at their initial placement
                unbalancedPlacements[vm.getIndex()] = vm.getInitialPlacement();
            }
        }
        java.util.Collections.shuffle(migratableVms, new java.util.Random(random.nextLong()));

        // Determine which hosts to clear and which to pack VMs onto
        int numHostsToClear = Math.max(1, (int) (problem.getHosts().size() * clearHostRatio));
        int numPackingHosts = problem.getHosts().size() - numHostsToClear;

        // Shuffle hosts to randomize which ones get cleared
        java.util.List<Host> allHosts = new java.util.ArrayList<>(problem.getHosts());
        java.util.Collections.shuffle(allHosts, new java.util.Random(random.nextLong()));

        java.util.List<Host> packingHosts = allHosts.subList(0, numPackingHosts);
        java.util.Set<Integer> packingHostIndices = new java.util.HashSet<>();
        for (Host h : packingHosts) {
            packingHostIndices.add(h.getIndex());
        }

        // Track NUMA usage for capacity checking
        float[][] numaCpu = new float[problem.getHosts().size()][];
        float[][] numaMem = new float[problem.getHosts().size()][];
        for (Host host : problem.getHosts()) {
            int numaCount = host.getNumaGroups().get(0).getNumas().size();
            numaCpu[host.getIndex()] = new float[numaCount];
            numaMem[host.getIndex()] = new float[numaCount];
        }

        // Initialize tracking with non-migratable VMs (keep them in place)
        for (Vm vm : problem.getVms()) {
            if (!vm.isMigratable()) {
                Placement p = vm.getInitialPlacement();
                for (Numa numa : p.getNumas()) {
                    int hostIdx = numa.getNumaGroup().getHost().getIndex();
                    int numaIdx = numa.getLocalIndex();
                    numaCpu[hostIdx][numaIdx] += vm.getNumaCpu();
                    numaMem[hostIdx][numaIdx] += vm.getNumaMem();
                }
            }
        }

        // Pack migratable VMs onto packing hosts, FORCING them to move to different hosts
        int movedCount = 0;
        int keptOriginal = 0;
        int forcedToOriginal = 0;

        for (Vm vm : migratableVms) {
            int originalHostIdx = originalHostMap.get(vm);
            boolean vmPlaced = false;

            // FIRST PASS: Try to place on packing hosts that are NOT the original host
            for (Host packingHost : packingHosts) {
                if (packingHost.getIndex() == originalHostIdx) {
                    continue;  // Skip original host to force migration
                }

                NumaGroup numaGroup = packingHost.getNumaGroups().get(0);
                for (Numa numa : numaGroup.getNumas()) {
                    int hostIdx = packingHost.getIndex();
                    int numaIdx = numa.getLocalIndex();
                    float newCpu = numaCpu[hostIdx][numaIdx] + vm.getNumaCpu();
                    float newMem = numaMem[hostIdx][numaIdx] + vm.getNumaMem();

                    // Use 60% capacity for more aggressive packing - creates worse initial solutions
                    // This gives the solver more room to find improvements
                    if (newCpu <= numa.getCpu() * 0.60f && newMem <= numa.getMem() * 0.60f) {
                        // Place VM here (on a DIFFERENT host)
                        // CRITICAL: Use precomputed canonical placement from NumaGroup, not new Placement()
                        // This ensures placement identity works correctly for isInitial() checks
                        Placement canonicalPlacement = numaGroup.getPlacements(vm.getNumNumas()).get(numaIdx);
                        unbalancedPlacements[vm.getIndex()] = canonicalPlacement;
                        numaCpu[hostIdx][numaIdx] = newCpu;
                        numaMem[hostIdx][numaIdx] = newMem;
                        vmPlaced = true;
                        movedCount++;
                        break;
                    }
                }

                if (vmPlaced) break;
            }

            // SECOND PASS: If couldn't place on different host, try original host as fallback
            if (!vmPlaced && packingHostIndices.contains(originalHostIdx)) {
                Host originalHost = problem.getHosts().get(originalHostIdx);
                NumaGroup numaGroup = originalHost.getNumaGroups().get(0);
                for (Numa numa : numaGroup.getNumas()) {
                    int numaIdx = numa.getLocalIndex();
                    float newCpu = numaCpu[originalHostIdx][numaIdx] + vm.getNumaCpu();
                    float newMem = numaMem[originalHostIdx][numaIdx] + vm.getNumaMem();

                    if (newCpu <= numa.getCpu() * 0.75f && newMem <= numa.getMem() * 0.75f) {
                        // CRITICAL: Use canonical placement for identity-based checks
                        Placement canonicalPlacement = numaGroup.getPlacements(vm.getNumNumas()).get(numaIdx);
                        unbalancedPlacements[vm.getIndex()] = canonicalPlacement;
                        numaCpu[originalHostIdx][numaIdx] = newCpu;
                        numaMem[originalHostIdx][numaIdx] = newMem;
                        vmPlaced = true;
                        forcedToOriginal++;
                        break;
                    }
                }
            }

            // LAST RESORT: Keep at original placement (but track this as failure)
            if (!vmPlaced) {
                keptOriginal++;
                unbalancedPlacements[vm.getIndex()] = vm.getInitialPlacement();
                // Still need to track capacity for this VM
                Placement p = vm.getInitialPlacement();
                for (Numa numa : p.getNumas()) {
                    int hostIdx = numa.getNumaGroup().getHost().getIndex();
                    int numaIdx = numa.getLocalIndex();
                    numaCpu[hostIdx][numaIdx] += vm.getNumaCpu();
                    numaMem[hostIdx][numaIdx] += vm.getNumaMem();
                }
            }
        }

        System.out.printf("[Unbalance] Moved %d VMs to different hosts, " +
                        "forced %d back to original, kept %d at original (%.1f%% moved to different hosts)%n",
                movedCount, forcedToOriginal, keptOriginal,
                100.0 * movedCount / migratableVms.size());

        // Build and return unbalanced solution (does NOT modify vm.initialPlacement)
        return new MigrationSolution(problem, unbalancedPlacements);
    }
}
