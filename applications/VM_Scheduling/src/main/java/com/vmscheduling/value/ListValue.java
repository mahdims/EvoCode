package com.vmscheduling.value;

import java.util.Arrays;
import java.util.stream.Collectors;

/**
 * Lexicographic list of values for hierarchical objective comparison.
 * Compares element by element from left to right — the first position
 * where they differ determines the winner. Lower is better.
 */
public class ListValue implements Value {

    private final Value[] values;

    private ListValue(Value[] values) {
        this.values = values;
    }

    public static ListValue of(Value... values) {
        return new ListValue(values);
    }

    public Value[] getValues() {
        return values;
    }

    @Override
    public int compareTo(Value other) {
        if (other instanceof ListValue o) {
            int minLen = Math.min(this.values.length, o.values.length);
            for (int i = 0; i < minLen; i++) {
                int cmp = this.values[i].compareTo(o.values[i]);
                if (cmp != 0) return cmp;
            }
            // If all shared positions are equal, shorter list is "better" (or equal if same length)
            return Integer.compare(this.values.length, o.values.length);
        }
        throw new IllegalArgumentException("Cannot compare ListValue with " + other.getClass().getSimpleName());
    }

    @Override
    public int compareToZero() {
        for (Value value : values) {
            int cmp = value.compareToZero();
            if (cmp != 0) return cmp;
        }
        return 0;
    }

    @Override
    public String toString() {
        return "ListValue[" + Arrays.stream(values)
                .map(Object::toString)
                .collect(Collectors.joining(", ")) + "]";
    }
}
