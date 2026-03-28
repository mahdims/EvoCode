package com.vmscheduling.model;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

/**
 * A Virtual Machine — the entity being placed.
 * Has per-NUMA resource demands and metadata used by constraints.
 *
 * A single-NUMA VM needs 1 Numa node. A multi-NUMA VM spans 2+ nodes and
 * demands numaCpu and numaMem on each node it occupies.
 */
@Getter
@Setter
public class Vm {

    private final int index;

    private boolean migratable;
    private float numaCpu;          // CPU demand per NUMA node
    private float numaMem;          // Memory demand per NUMA node
    private Placement initialPlacement;  // M₀(p) — where it starts
    private int numNumas;           // 1 for single-socket, 2+ for multi-socket

    private List<String> traits;
    private String tenantId;
    private int tenantLevel;        // Tenant importance level (0-10). Level ≥ 5 = high-level tenant
    private String antiAffinityGroupId;
    private int migrationCost;
    private String flavorId;
    private String cuttingLineTag;

    public Vm(int index) {
        this.index = index;
        this.migratable = true;
        this.numNumas = 1;
        this.migrationCost = 1;
        this.tenantLevel = 0;       // Default: not a high-level tenant
    }

    /**
     * Set tenant level with validation.
     * @param level Tenant importance level (0-10 scale)
     * @throws IllegalArgumentException if level is out of valid range
     */
    public void setTenantLevel(int level) {
        if (level < 0 || level > 10) {
            throw new IllegalArgumentException("Tenant level must be in [0, 10], got: " + level);
        }
        this.tenantLevel = level;
    }

    @Override
    public String toString() {
        return "Vm(" + index + ", cpu=" + numaCpu + ", mem=" + numaMem
                + ", numas=" + numNumas + ")";
    }
}
