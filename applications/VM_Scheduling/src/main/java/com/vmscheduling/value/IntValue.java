package com.vmscheduling.value;

import lombok.Getter;

/**
 * Integer-based objective value for count-based metrics.
 * Lower values are better.
 */
@Getter
public class IntValue implements Value {

    private final int value;

    private IntValue(int value) {
        this.value = value;
    }

    public static IntValue of(int value) {
        return new IntValue(value);
    }

    @Override
    public int compareTo(Value other) {
        if (other instanceof IntValue o) {
            return Integer.compare(this.value, o.value);
        }
        throw new IllegalArgumentException("Cannot compare IntValue with " + other.getClass().getSimpleName());
    }

    @Override
    public int compareToZero() {
        return Integer.compare(value, 0);
    }

    @Override
    public String toString() {
        return "IntValue(" + value + ")";
    }
}
