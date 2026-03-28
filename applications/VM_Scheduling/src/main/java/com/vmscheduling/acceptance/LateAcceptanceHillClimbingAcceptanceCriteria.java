package com.vmscheduling.acceptance;

import com.vmscheduling.value.Value;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Late Acceptance Hill Climbing (LAHC).
 * Circular buffer of L historical values. Accepts if:
 *   newValue <= oldValue (at least as good as current), OR
 *   newValue < history[position] (strictly better than L steps ago).
 *
 * Default buffer length = 10 (unusually small — aggressive convergence).
 *
 * See MainWiki §7.3b / 10-acceptance-criterion.md.
 */
public class LateAcceptanceHillClimbingAcceptanceCriteria implements AcceptanceCriteria {

    private final Value[] values;  // circular buffer
    private int position;

    public LateAcceptanceHillClimbingAcceptanceCriteria(int length) {
        values = new Value[length];
    }

    @Override
    public void init(Value value) {
        Arrays.fill(values, value);
        position = 0;
    }

    @Override
    public boolean accept(Value oldValue, Value newValue,
                           SplittableRandom random, int stagnationSteps) {
        // Accept if improved over current OR strictly better than history[position]
        Value candidate;
        if (newValue.compareTo(oldValue) <= 0
                || newValue.compareTo(values[position]) < 0) {
            candidate = newValue;
        } else {
            candidate = oldValue; // reject — keep current
        }

        // CRITICAL FIX: Standard LAHC always rotates accepted value into history
        // (not just when better). This prevents monotonic thresholds and maintains diversification.
        values[position] = candidate;
        position = (position + 1) % values.length;

        return candidate == newValue; // true = accepted
    }
}
