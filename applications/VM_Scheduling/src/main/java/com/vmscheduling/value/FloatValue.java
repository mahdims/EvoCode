package com.vmscheduling.value;

import lombok.Getter;

/**
 * Float-based objective value for ratio-based metrics.
 * Lower values are better.
 */
@Getter
public class FloatValue implements Value {

    private final float value;

    private FloatValue(float value) {
        this.value = value;
    }

    public static FloatValue of(float value) {
        return new FloatValue(value);
    }

    @Override
    public int compareTo(Value other) {
        if (other instanceof FloatValue o) {
            return Float.compare(this.value, o.value);
        }
        throw new IllegalArgumentException("Cannot compare FloatValue with " + other.getClass().getSimpleName());
    }

    @Override
    public int compareToZero() {
        return Float.compare(value, 0.0f);
    }

    @Override
    public String toString() {
        return "FloatValue(" + value + ")";
    }
}
