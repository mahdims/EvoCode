package com.vmscheduling;

import com.vmscheduling.value.FloatValue;
import com.vmscheduling.value.IntValue;
import com.vmscheduling.value.ListValue;
import com.vmscheduling.value.Value;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class ListValueTest {

    @Test
    void compareTo_firstDifference_wins() {
        Value a = ListValue.of(IntValue.of(-5), FloatValue.of(0.12f), IntValue.of(300));
        Value b = ListValue.of(IntValue.of(-5), FloatValue.of(0.09f), IntValue.of(450));
        assertThat(b.compareTo(a)).isLessThan(0); // B wins at position 1
        assertThat(a.compareTo(b)).isGreaterThan(0);
    }

    @Test
    void compareTo_identical_returnsZero() {
        Value a = ListValue.of(IntValue.of(-3), FloatValue.of(0.5f));
        Value b = ListValue.of(IntValue.of(-3), FloatValue.of(0.5f));
        assertThat(a.compareTo(b)).isEqualTo(0);
    }

    @Test
    void compareTo_firstElement_decides() {
        Value a = ListValue.of(IntValue.of(-5));
        Value b = ListValue.of(IntValue.of(-3));
        assertThat(a.compareTo(b)).isLessThan(0); // -5 < -3, A wins
    }

    @Test
    void compareToZero_allZero_returnsZero() {
        Value v = ListValue.of(IntValue.of(0), FloatValue.of(0.0f));
        assertThat(v.compareToZero()).isEqualTo(0);
    }

    @Test
    void compareToZero_firstNonZero_decides() {
        Value v = ListValue.of(IntValue.of(0), FloatValue.of(-0.5f));
        assertThat(v.compareToZero()).isLessThan(0); // improving
    }

    @Test
    void lowerIsBetter_negatedEmptyHosts() {
        Value fiveEmpty = IntValue.of(-5);
        Value threeEmpty = IntValue.of(-3);
        assertThat(fiveEmpty.compareTo(threeEmpty)).isLessThan(0);
    }
}
