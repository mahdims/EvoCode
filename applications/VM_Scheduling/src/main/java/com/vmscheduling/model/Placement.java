package com.vmscheduling.model;

import java.util.Arrays;

/**
 * Fully specifies where a VM lives: which host, which NUMA group, and which
 * specific NUMA nodes. Host and NumaGroup are derived from the Numa parent chain.
 *
 * Placements are pre-built combinatorially by NumaGroup.addNuma() and retrieved
 * at O(1) via NumaGroup.getPlacements(numNumas).
 */
public class Placement {

    private final Numa[] numas;

    public Placement(Numa[] numas) {
        this.numas = numas;
    }

    public Host getHost() {
        return numas[0].getNumaGroup().getHost();
    }

    public NumaGroup getNumaGroup() {
        return numas[0].getNumaGroup();
    }

    public Numa[] getNumas() {
        return numas;
    }

    @Override
    public String toString() {
        return "Placement(" + getHost() + ", numas=" + Arrays.toString(numas) + ")";
    }
}
