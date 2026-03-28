package com.vmscheduling.variable;

import com.vmscheduling.model.MigrationSolution;

/**
 * Typed wrapper around an array index for O(1) variable retrieval.
 * The fetcher knows the slot index into MigrationSolution's variable array.
 *
 * See MainWiki §4.4 / 02a-unified-interface-contract.md.
 */
public class MigrationFetcher<T extends MigrationVariable> {

    private final int index;

    public MigrationFetcher(int index) {
        this.index = index;
    }

    @SuppressWarnings("unchecked")
    public T fetch(MigrationSolution solution) {
        return (T) solution.getMigrationVariables()[index];
    }
}
