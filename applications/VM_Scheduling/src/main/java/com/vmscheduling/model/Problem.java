package com.vmscheduling.model;

import com.vmscheduling.constraint.MigrationConstraint;
import com.vmscheduling.objective.MigrationObjective;
import com.vmscheduling.variable.MigrationFetcher;
import com.vmscheduling.variable.MigrationVariable;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import lombok.Getter;
import lombok.Setter;

import java.util.List;
import java.util.function.Supplier;

/**
 * Root container wiring all entities, registered variables, constraints, and objectives.
 * The single object passed through the entire framework.
 *
 * See MainWiki §3.7 / 01-data-structures.md.
 */
@Getter
public class Problem {

    private final List<Rack> racks;
    private final List<Host> hosts;
    private final List<Vm> vms;
    private final List<NumaGroup> numaGroups;
    private final List<Numa> numas;

    @Setter private MigrationConstraint migrationConstraint;
    @Setter private MigrationObjective migrationObjective;

    private final List<Supplier<? extends MigrationVariable>> migrationVariableSuppliers;

    public Problem() {
        this.racks = new ObjectArrayList<>();
        this.hosts = new ObjectArrayList<>();
        this.vms = new ObjectArrayList<>();
        this.numaGroups = new ObjectArrayList<>();
        this.numas = new ObjectArrayList<>();
        this.migrationVariableSuppliers = new ObjectArrayList<>();
    }

    public Rack addRack() {
        Rack rack = new Rack();
        racks.add(rack);
        return rack;
    }

    public Host addHost(Rack rack, HostHealthyState healthyState,
                        List<String> allowedTenantIds, String faultDomainId) {
        Host host = new Host(hosts.size(), rack);
        host.setHealthyState(healthyState);
        host.setAllowedTenantIds(allowedTenantIds);
        host.setFaultDomainId(faultDomainId);
        hosts.add(host);
        rack.getHosts().add(host);
        return host;
    }

    public NumaGroup addNumaGroup(Host host) {
        NumaGroup group = new NumaGroup(host);
        host.getNumaGroups().add(group);
        numaGroups.add(group);
        return group;
    }

    public Numa addNuma(NumaGroup group, float cpu, float mem) {
        Numa numa = group.addNuma(numas);
        numa.setCpu(cpu);
        numa.setMem(mem);
        return numa;
    }

    public Vm addVm() {
        Vm vm = new Vm(vms.size());
        vms.add(vm);
        return vm;
    }

    /**
     * Register a variable supplier. Returns a fetcher for O(1) retrieval
     * from any MigrationSolution's variable array.
     */
    public <T extends MigrationVariable> MigrationFetcher<T> addMigrationVariable(
            Supplier<T> supplier) {
        int index = migrationVariableSuppliers.size();
        migrationVariableSuppliers.add(supplier);
        return new MigrationFetcher<>(index);
    }
}
