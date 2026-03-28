package com.vmscheduling;

import com.vmscheduling.model.Host;
import com.vmscheduling.model.HostHealthyState;
import com.vmscheduling.model.NumaGroup;
import com.vmscheduling.model.Problem;
import com.vmscheduling.model.Rack;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class NumaGroupPlacementTest {

    @Test
    void singleNuma_generatesOnePlacement() {
        Problem problem = new Problem();
        Rack rack = problem.addRack();
        Host host = problem.addHost(rack, HostHealthyState.HEALTHY, List.of(), "fd1");
        NumaGroup group = problem.addNumaGroup(host);
        problem.addNuma(group, 96, 262144);

        assertThat(group.getPlacements(1)).hasSize(1);
        assertThat(group.getPlacements(1).get(0).getNumas()).hasSize(1);
    }

    @Test
    void twoNumas_generatesCorrectCombinations() {
        Problem problem = new Problem();
        Rack rack = problem.addRack();
        Host host = problem.addHost(rack, HostHealthyState.HEALTHY, List.of(), "fd1");
        NumaGroup group = problem.addNumaGroup(host);
        problem.addNuma(group, 96, 262144);
        problem.addNuma(group, 96, 262144);

        assertThat(group.getPlacements(1)).hasSize(2);  // C(2,1)
        assertThat(group.getPlacements(2)).hasSize(1);  // C(2,2)
    }

    @Test
    void fourNumas_combinatorialCorrectness() {
        Problem problem = new Problem();
        Rack rack = problem.addRack();
        Host host = problem.addHost(rack, HostHealthyState.HEALTHY, List.of(), "fd1");
        NumaGroup group = problem.addNumaGroup(host);
        for (int i = 0; i < 4; i++) {
            problem.addNuma(group, 96, 262144);
        }

        assertThat(group.getPlacements(1)).hasSize(4);  // C(4,1)
        assertThat(group.getPlacements(2)).hasSize(6);  // C(4,2)
        assertThat(group.getPlacements(3)).hasSize(4);  // C(4,3)
        assertThat(group.getPlacements(4)).hasSize(1);  // C(4,4)
    }
}
