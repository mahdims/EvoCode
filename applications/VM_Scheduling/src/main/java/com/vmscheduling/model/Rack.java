package com.vmscheduling.model;

import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import lombok.Getter;

import java.util.List;

/**
 * A physical rack housing multiple hosts.
 * Unit for rack-level power constraints.
 */
@Getter
public class Rack {

    private final List<Host> hosts;

    public Rack() {
        this.hosts = new ObjectArrayList<>();
    }
}
