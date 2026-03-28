package com.vmscheduling.model;

import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import lombok.Getter;
import lombok.Setter;

import java.util.List;

/**
 * A physical server in the data center.
 * Contains NumaGroups and has a health state.
 */
@Getter
public class Host {

    private final int index;
    private final Rack rack;
    private final List<NumaGroup> numaGroups;

    @Setter private HostHealthyState healthyState;
    @Setter private String faultDomainId;
    @Setter private List<String> allowedTenantIds;
    @Setter private boolean migrationInRestricted;

    public Host(int index, Rack rack) {
        this.index = index;
        this.rack = rack;
        this.numaGroups = new ObjectArrayList<>();
        this.healthyState = HostHealthyState.HEALTHY;
        this.allowedTenantIds = new ObjectArrayList<>();
    }

    public NumaGroup addNumaGroup() {
        NumaGroup group = new NumaGroup(this);
        numaGroups.add(group);
        return group;
    }

    @Override
    public String toString() {
        return "Host(" + index + ")";
    }
}
