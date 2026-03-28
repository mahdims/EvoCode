package com.vmscheduling.operator;

import com.vmscheduling.model.Vm;
import com.vmscheduling.util.AlgorithmUtil;

import java.util.Comparator;
import java.util.List;
import java.util.SplittableRandom;

/**
 * VM ordering strategies. All sorts are ascending (smallest first).
 * During ruin, this order is kept. During recreate, it is reversed (largest first).
 *
 * See MainWiki §7.3 / 07-operator-types.md.
 */
public enum VmSorterType {

    /** Sort by total CPU (ascending), break ties by total memory */
    CPU_MEM {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing((Vm vm) -> vm.getNumaCpu() * vm.getNumNumas())
                    .thenComparing(vm -> vm.getNumaMem() * vm.getNumNumas()));
        }
    },

    /** Sort by total memory (ascending), break ties by total CPU */
    MEM_CPU {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing((Vm vm) -> vm.getNumaMem() * vm.getNumNumas())
                    .thenComparing(vm -> vm.getNumaCpu() * vm.getNumNumas()));
        }
    },

    /** Sort by CPU × Memory × NUMA_count² (product of all resource dimensions) */
    CPU_MEM_PROD {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing(
                    (Vm vm) -> vm.getNumaCpu() * vm.getNumaMem() * vm.getNumNumas() * vm.getNumNumas()));
        }
    },

    /** Sort by number of NUMA nodes the VM spans (ascending — single-NUMA first) */
    NUM_NUMA {
        public void sort(List<Vm> vms, SplittableRandom random) {
            vms.sort(Comparator.comparing(Vm::getNumNumas));
        }
    },

    /** Shuffle randomly */
    RANDOM {
        public void sort(List<Vm> vms, SplittableRandom random) {
            AlgorithmUtil.shuffleList(vms, random);
        }
    };

    public abstract void sort(List<Vm> vms, SplittableRandom random);
}
