package com.vmscheduling.model;

/**
 * Health state of a physical host server.
 */
public enum HostHealthyState {
    /** Normal operation, can send and receive VMs */
    HEALTHY,
    /** Degraded but still running; VMs may be migrated away */
    UNHEALTHY,
    /** Must be fully drained; all VMs must leave */
    EVACUATION
}
