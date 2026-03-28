package com.vmscheduling.model;

import com.vmscheduling.delta.RecreateDelta;
import com.vmscheduling.value.Value;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.util.List;

/**
 * Tracks optimization progress across ALNS iterations.
 * Stores the sequence of accepted deltas and objective values.
 */
public class OptimizationTrackData {

    private final List<List<RecreateDelta>> deltaHistory;
    private final List<Value> valueHistory;

    public OptimizationTrackData() {
        this.deltaHistory = new ObjectArrayList<>();
        this.valueHistory = new ObjectArrayList<>();
    }

    public void addOptimizationTrackDataItem(List<RecreateDelta> deltas, Value value) {
        deltaHistory.add(deltas);
        valueHistory.add(value);
    }

    public List<List<RecreateDelta>> getDeltaHistory() {
        return deltaHistory;
    }

    public List<Value> getValueHistory() {
        return valueHistory;
    }
}
