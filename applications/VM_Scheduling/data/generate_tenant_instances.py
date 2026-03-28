"""
Generator for VM Scheduling instances WITH tenant_level fields.

Produces instances where high-level tenants (level >= 5) are placed densely
on hosts so that the INITIAL placement violates the soft constraints:

  Constraint A (n1): distinct high-level tenants per host <= n1
  Constraint B (n2): VMs from one high-level tenant per host <= n2
  Constraint C (n3): total VMs per host <= n3

Thresholds used:  n1=2, n2=3, n3=12
These are embedded in the generated file name and config.

Usage:
    python generate_tenant_instances.py
"""

import json
import random
import uuid
from pathlib import Path

# ── Defaults ──────────────────────────────────────────────────────────────────

# Soft-constraint thresholds (must match ProblemBuilder config)
N1 = 2   # max distinct high-level tenants per host
N2 = 3   # max VMs from one high-level tenant per host
N3 = 12  # max total VMs per host

NUMA_CPU_CAP = 96.0
NUMA_MEM_CAP = 262144.0

HIGH_LEVEL_TENANT_LEVEL = 6   # >= 5 → high-level

# VM size profiles (numa_cpu, numa_mem_mb)
SIZE_PROFILES = [
    (4,   8192),
    (8,   16384),
    (16,  32768),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def make_host_id(idx: int) -> str:
    return f"host-{idx:04d}"


def make_vm(vm_id: str, host_id: str, numa_id: int,
            tenant_id: str, tenant_level: int,
            numa_cpu: float, numa_mem: float,
            rng: random.Random) -> dict:
    return {
        "vm_id": vm_id,
        "in_host_id": host_id,
        "in_numa_id": str(numa_id),
        "numa_cpu": numa_cpu,
        "numa_mem": numa_mem,
        "resource_types": ["ComputeC6"],
        "lifetime": rng.randint(1_000_000, 50_000_000),
        "can_migration": rng.random() < 0.85,
        "tenant_id": tenant_id,
        "cutting_line_tag": "c6",
        "tenant_level": tenant_level,
        "metrics": {
            "cpu_util": round(rng.uniform(5, 80), 3),
            "cpu_qos": {
                "score": 100.0,
                "pressure_stats": {"left": 0, "right": 0, "p95": 0, "typical_value": 0},
            },
            "cpu_power_qos": {
                "score": 0.0,
                "pressure_stats": {"left": 0.0, "right": 0.0, "p95": 0.0, "typical_value": 0.0},
            },
        },
        "flavor_id": "c6.xlarge.1",
    }


# ── Instance generator ────────────────────────────────────────────────────────

def generate(
    num_hosts: int,
    vms_per_host: int,
    num_high_tenants: int,
    num_low_tenants: int,
    seed: int,
    n1: int = N1,
    n2: int = N2,
    n3: int = N3,
) -> dict:
    """
    Generate an instance where initial placement violates A and B constraints.

    Strategy:
      - Place (n1+1) distinct high-level tenants on EACH host → violates A on every host.
      - Place (n2+1) VMs from one of those tenants on each host → violates B.
      - Fill remaining slots with low-level tenant VMs.
    """
    rng = random.Random(seed)

    # Create tenant IDs
    high_tenants = [f"ht-{i:04d}" for i in range(num_high_tenants)]
    low_tenants  = [f"lt-{i:04d}" for i in range(num_low_tenants)]

    # Track per-host CPU usage (two NUMA sockets)
    host_ids = [make_host_id(h) for h in range(num_hosts)]
    # numa_cpu[h][socket] consumed
    numa_cpu_used = [[0.0, 0.0] for _ in range(num_hosts)]
    numa_mem_used = [[0.0, 0.0] for _ in range(num_hosts)]

    vms = []

    def try_place(host_idx: int, cpu: float, mem: float) -> int:
        """Return NUMA socket index if fits, else -1."""
        for sock in range(2):
            if (numa_cpu_used[host_idx][sock] + cpu <= NUMA_CPU_CAP and
                    numa_mem_used[host_idx][sock] + mem <= NUMA_MEM_CAP):
                numa_cpu_used[host_idx][sock] += cpu
                numa_mem_used[host_idx][sock] += mem
                return sock
        return -1

    def add_vm(host_idx: int, tenant_id: str, level: int, cpu: float, mem: float) -> bool:
        sock = try_place(host_idx, cpu, mem)
        if sock < 0:
            return False
        vm_id = make_uuid(rng)
        vms.append(make_vm(vm_id, host_ids[host_idx], sock,
                           tenant_id, level, cpu, mem, rng))
        return True

    # ── Phase 1: Force constraint violations on each host ─────────────────────
    # Place (n1+1) distinct high-level tenants per host, each with (n2+1) VMs
    # → violates A (distinct > n1) and B (count > n2)
    high_pool = high_tenants[:n1 + 1]  # exactly n1+1 different tenants per host

    for h in range(num_hosts):
        for t_idx, tenant in enumerate(high_pool):
            # Place (n2+1) VMs from this tenant on this host
            for _ in range(n2 + 1):
                cpu, mem = rng.choice(SIZE_PROFILES)
                add_vm(h, tenant, HIGH_LEVEL_TENANT_LEVEL, float(cpu), float(mem))

    # ── Phase 2: Fill remaining capacity with low-level VMs ──────────────────
    for h in range(num_hosts):
        current_count = sum(1 for vm in vms if vm["in_host_id"] == host_ids[h])
        target = vms_per_host
        while current_count < target:
            tenant = rng.choice(low_tenants)
            cpu, mem = rng.choice(SIZE_PROFILES)
            if add_vm(h, tenant, rng.randint(0, 3), float(cpu), float(mem)):
                current_count += 1
            else:
                break  # host full

    total_vms = len(vms)
    a_violations = 0
    b_violations = 0
    c_violations = 0

    # Compute actual initial violations
    from collections import defaultdict
    host_tenant_vm_count: dict = defaultdict(lambda: defaultdict(int))  # host → tenant → count
    host_vm_count: dict = defaultdict(int)

    for vm in vms:
        h = vm["in_host_id"]
        t = vm["tenant_id"]
        lvl = vm.get("tenant_level", 0)
        host_vm_count[h] += 1
        if lvl >= 5:
            host_tenant_vm_count[h][t] += 1

    for h in host_ids:
        hi_tenants_on_host = host_tenant_vm_count[h]
        distinct = len(hi_tenants_on_host)
        a_violations += max(0, distinct - n1)
        for t, cnt in hi_tenants_on_host.items():
            b_violations += max(0, cnt - n2)
        c_violations += max(0, host_vm_count[h] - n3)

    print(f"  Hosts={num_hosts}, VMs={total_vms} (avg {total_vms/num_hosts:.1f}/host)")
    print(f"  Initial violations: A={a_violations}, B={b_violations}, C={c_violations}")

    instance = {
        "vms": vms,
        "anti_affinity_groups": [],
        "objectives": ["MAX_PREFERRED_FLAVOR"],
        "objective_parameter": {},
        "subhealthy_host_migration_parameter": {
            "tenant_subhealthy_host_migration_parameters": []
        },
        "tenant_dispersed_distribution_parameter": {
            "tenant_distribution_parameters": []
        },
        # Soft constraint thresholds — read by ProblemBuilder.build() in Java
        "soft_constraint_config": {"n1": n1, "n2": n2, "n3": n3},
        # Metadata (informational only)
        "_meta": {
            "n1": n1, "n2": n2, "n3": n3,
            "initial_violation_A": a_violations,
            "initial_violation_B": b_violations,
            "initial_violation_C": c_violations,
            "seed": seed,
        },
    }
    return instance


# ── Batch generation ──────────────────────────────────────────────────────────

def main():
    out_dir = Path(__file__).parent

    configs = [
        # (name_prefix, num_hosts, vms_per_host, num_high_tenants, num_low_tenants, seeds)
        ("smoke_h8_v5",  8,  5,  4, 4, [1]),
        ("tenant_h10_v8",  10, 8,  4, 4, [1, 2, 3]),
        ("tenant_h15_v10", 15, 10, 5, 5, [1, 2, 3]),
        ("tenant_h20_v12", 20, 12, 5, 5, [1, 2, 3]),
    ]

    for (prefix, num_hosts, vms_per_host, nh, nl, seeds) in configs:
        for seed in seeds:
            name = f"{prefix}_s{seed}"
            path = out_dir / f"{name}.json"
            print(f"Generating {name}...")
            inst = generate(
                num_hosts=num_hosts,
                vms_per_host=vms_per_host,
                num_high_tenants=nh,
                num_low_tenants=nl,
                seed=seed,
            )
            path.write_text(json.dumps(inst, indent=2))
            print(f"  -> {path}")


if __name__ == "__main__":
    main()
