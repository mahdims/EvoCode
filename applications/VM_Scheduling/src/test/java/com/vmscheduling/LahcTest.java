package com.vmscheduling;

import com.vmscheduling.acceptance.LateAcceptanceHillClimbingAcceptanceCriteria;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.Value;
import org.junit.jupiter.api.Test;

import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.*;

class LahcTest {

    private final SplittableRandom random = new SplittableRandom(42);

    @Test
    void accept_betterThanCurrent() {
        LateAcceptanceHillClimbingAcceptanceCriteria lahc =
                new LateAcceptanceHillClimbingAcceptanceCriteria(10);
        Value init = IntValue.of(100);
        lahc.init(init);
        assertThat(lahc.accept(init, IntValue.of(90), random, 0)).isTrue();
    }

    @Test
    void accept_equalToCurrent() {
        LateAcceptanceHillClimbingAcceptanceCriteria lahc =
                new LateAcceptanceHillClimbingAcceptanceCriteria(10);
        Value init = IntValue.of(100);
        lahc.init(init);
        assertThat(lahc.accept(init, IntValue.of(100), random, 0)).isTrue();
    }

    @Test
    void accept_worseThanCurrentButBetterThanHistory() {
        // Buffer length=5, init all to 100. Position starts at 0.
        LateAcceptanceHillClimbingAcceptanceCriteria lahc =
                new LateAcceptanceHillClimbingAcceptanceCriteria(5);
        Value init = IntValue.of(100);
        lahc.init(init);
        // Call 1: accept(100, 50) → accepted, buffer[0]=50, pos=1. Buffer: [50,100,100,100,100]
        lahc.accept(IntValue.of(100), IntValue.of(50), random, 0);
        // Call 2: accept(50, 80) → 80>50 but 80<buffer[1]=100 → accepted
        assertThat(lahc.accept(IntValue.of(50), IntValue.of(80), random, 0)).isTrue();
    }

    @Test
    void reject_worseThanBothCurrentAndHistory() {
        LateAcceptanceHillClimbingAcceptanceCriteria lahc =
                new LateAcceptanceHillClimbingAcceptanceCriteria(3);
        Value init = IntValue.of(50);
        lahc.init(init);
        lahc.accept(IntValue.of(50), IntValue.of(50), random, 0);
        lahc.accept(IntValue.of(50), IntValue.of(50), random, 0);
        lahc.accept(IntValue.of(50), IntValue.of(50), random, 0);
        // newValue=80 > current=50 AND > history=50 → reject
        assertThat(lahc.accept(IntValue.of(50), IntValue.of(80), random, 0)).isFalse();
    }
}
