package com.vmscheduling.util;

import it.unimi.dsi.fastutil.objects.ObjectArrayList;

import java.util.List;

/**
 * Array of lists indexed by host index, used for tracking VMs per host.
 */
public class AssignmentList<T> {

    private final List<T>[] assignments;

    @SuppressWarnings("unchecked")
    public AssignmentList(int size) {
        assignments = new List[size];
        for (int i = 0; i < size; i++) {
            assignments[i] = new ObjectArrayList<>();
        }
    }

    @SuppressWarnings("unchecked")
    public AssignmentList(AssignmentList<T> other) {
        assignments = new List[other.assignments.length];
        for (int i = 0; i < assignments.length; i++) {
            assignments[i] = new ObjectArrayList<>(other.assignments[i]);
        }
    }

    public List<T> get(int index) {
        return assignments[index];
    }

    public void add(int index, T element) {
        assignments[index].add(element);
    }

    public void remove(int index, T element) {
        assignments[index].remove(element);
    }

    public int size() {
        return assignments.length;
    }
}
