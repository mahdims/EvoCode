package com.vmscheduling.model;

import lombok.Getter;
import lombok.Setter;

/**
 * A single NUMA (Non-Uniform Memory Access) node with its own CPU and memory capacity.
 * Part of a NumaGroup within a Host.
 */
@Getter
public class Numa {

    private final NumaGroup numaGroup;
    private final int localIndex;   // index within the NumaGroup
    private final int globalIndex;  // index across all NUMAs in the problem

    @Setter private float cpu;      // total CPU capacity (cores)
    @Setter private float mem;      // total memory capacity (MB)

    public Numa(NumaGroup numaGroup, int localIndex, int globalIndex) {
        this.numaGroup = numaGroup;
        this.localIndex = localIndex;
        this.globalIndex = globalIndex;
    }

    @Override
    public String toString() {
        return "Numa(" + globalIndex + ", cpu=" + cpu + ", mem=" + mem + ")";
    }
}
