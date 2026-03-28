"""
Server Consolidation V2 — Synthetic Instance Data Generator
============================================================

Generates protobuf-text-format instance data matching the schema
reverse-engineered from client-provided data snippets.

Usage:
    python generate_instance.py --num-hosts 20 --vms-per-host 15 --seed 42 --output instance_01.textproto
    python generate_instance.py --preset small
    python generate_instance.py --preset large --output large_instance.textproto
    python generate_instance.py --batch 20 --output-dir ./instances/

Data characteristics observed from client data:
    - Host IDs follow pattern: "cnnorth4a-pod33-{cutting_line}-cna{6_digit_number}"
    - VM IDs are UUIDs
    - NUMA IDs are "0" or "1" (2-socket machines)
    - numa_cpu values: 4, 8, 12, 16, 24, 32, 48, 96 (powers-of-2-ish)
    - numa_mem values: 8192, 16384, 32768, 65536 (powers of 2, in MB)
    - cpu_util: 0-100, often 50-90 for active VMs
    - QoS scores: typically 100.0
    - Lifetimes: large integers (seconds), range ~1M to ~50M
    - Tenant IDs: mix of hex strings and readable names
    - Cutting line tags: "s6", "c6s", "c6", etc.
    - Flavor IDs: "{tag}.{size}.{ratio}" e.g. "s6.xlarge.2", "c6s.8xlarge.2"
    - Anti-affinity groups: 2-5 VMs each
    - Tenant dispersed distribution: max_vm_num_per_group typically 6
"""

import argparse
import json
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# =============================================================================
# Configuration Constants (derived from client data analysis)
# =============================================================================

# Host naming pattern
REGIONS = ["cnnorth4a", "cnnorth4b", "cneast3a"]
POD_PREFIXES = ["pod33", "pod34", "pod35"]

# VM flavor catalog (cutting_line_tag, flavor_sizes, resource_type_prefix)
FLAVOR_CATALOG = [
    {"tag": "s6",  "resource_prefix": "IOoptimizedS6",  "sizes": ["large", "xlarge", "2xlarge", "4xlarge", "8xlarge"]},
    {"tag": "c6s", "resource_prefix": "IOoptimizedC6S",  "sizes": ["large", "xlarge", "2xlarge", "4xlarge", "8xlarge"]},
    {"tag": "c6",  "resource_prefix": "ComputeC6",       "sizes": ["large", "xlarge", "2xlarge", "4xlarge"]},
    {"tag": "m6",  "resource_prefix": "MemOptimizedM6",  "sizes": ["large", "xlarge", "2xlarge", "4xlarge"]},
]

# CPU/Memory allocation profiles per flavor size (numa_cpu, numa_mem_mb)
SIZE_PROFILES = {
    "large":    (4,   8192),
    "xlarge":   (8,   16384),
    "2xlarge":  (16,  32768),
    "4xlarge":  (32,  65536),
    "8xlarge":  (96,  65536),   # large flavors observed in prefer_flavor
}

# Memory ratios (the ".2" in "s6.xlarge.2" means mem = 2x cpu in GB)
MEM_RATIOS = [1, 2, 4]

# Tenant generation
NAMED_TENANTS = [
    "chinatower-INF-HQ", "hw35620893", "eduop_facp", "yun_op_cdn",
    "cloud_ops_team1", "bigdata_platform", "ai_inference_pool"
]

NUMA_COUNT = 2  # 2-socket machines observed in data


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PressureStats:
    left: float
    right: float
    p95: float
    typical_value: float


@dataclass
class QosMetric:
    score: float
    pressure_stats: PressureStats


@dataclass
class VmMetrics:
    cpu_util: float
    cpu_qos: QosMetric
    cpu_power_qos: QosMetric


@dataclass
class Vm:
    vm_id: str
    in_host_id: str
    in_numa_id: str
    numa_cpu: float
    numa_mem: float
    resource_types: list[str]
    lifetime: int
    can_migration: bool
    tenant_id: str
    cutting_line_tag: str
    metrics: VmMetrics
    flavor_id: str


@dataclass
class AntiAffinityGroup:
    vm_ids: list[str]


@dataclass
class PreferFlavor:
    numa_cpu: float
    numa_mem: float
    cpu_ratio: float
    numa_num: int
    resource_types: list[str]
    flavor_id: str


@dataclass
class TenantSubhealthyParam:
    tenant_id: str
    vm_ids: list[str]


@dataclass
class TenantDistributionParam:
    tenant_id: str
    vm_ids: list[str]
    max_vm_num_per_group: int


@dataclass
class Instance:
    vms: list[Vm] = field(default_factory=list)
    anti_affinity_groups: list[AntiAffinityGroup] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    prefer_flavor: Optional[PreferFlavor] = None
    subhealthy_params: list[TenantSubhealthyParam] = field(default_factory=list)
    distribution_params: list[TenantDistributionParam] = field(default_factory=list)


# =============================================================================
# Generator
# =============================================================================

class InstanceGenerator:

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self._tenant_pool: list[str] = []
        self._host_ids: list[str] = []

    def _uuid(self) -> str:
        return str(uuid.UUID(int=self.rng.getrandbits(128), version=4))

    def _generate_host_id(self, cutting_tag: str, index: int) -> str:
        region = self.rng.choice(REGIONS)
        pod = self.rng.choice(POD_PREFIXES)
        return f"{region}-{pod}-{cutting_tag}-cna{index:06d}"

    def _generate_tenants(self, num_tenants: int) -> list[str]:
        tenants = []
        # Use some named tenants + random hex tenants
        named_count = min(len(NAMED_TENANTS), num_tenants // 2)
        tenants.extend(self.rng.sample(NAMED_TENANTS, named_count))
        for _ in range(num_tenants - named_count):
            tenants.append(self._uuid().replace("-", "")[:32])
        self.rng.shuffle(tenants)
        return tenants

    def _generate_pressure_stats(self, cpu_util: float) -> PressureStats:
        """Generate realistic pressure stats around a given cpu_util."""
        spread = self.rng.uniform(5, 20)
        left = max(0, cpu_util - spread - self.rng.uniform(0, 10))
        right = max(left, cpu_util - self.rng.uniform(0, 5))
        p95 = cpu_util
        typical = cpu_util
        return PressureStats(
            left=round(left, 5),
            right=round(right, 6),
            p95=round(p95, 5),
            typical_value=round(typical, 5),
        )

    def _generate_vm_metrics(self) -> VmMetrics:
        cpu_util = round(self.rng.uniform(5, 95), 5)
        cpu_qos = QosMetric(
            score=100.0,
            pressure_stats=self._generate_pressure_stats(cpu_util),
        )
        # cpu_power_qos often has empty pressure stats
        cpu_power_qos = QosMetric(
            score=0.0,
            pressure_stats=PressureStats(0.0, 0.0, 0.0, 0.0),
        )
        return VmMetrics(cpu_util=cpu_util, cpu_qos=cpu_qos, cpu_power_qos=cpu_power_qos)

    def _generate_vm(self, host_id: str, numa_id: int, tenant_id: str) -> Vm:
        flavor_def = self.rng.choice(FLAVOR_CATALOG)
        size = self.rng.choice(flavor_def["sizes"])
        numa_cpu, numa_mem = SIZE_PROFILES[size]
        mem_ratio = self.rng.choice(MEM_RATIOS)
        flavor_id = f"{flavor_def['tag']}.{size}.{mem_ratio}"

        # Resource types: 1-2 tags
        resource_types = [flavor_def["resource_prefix"]]
        if self.rng.random() < 0.3:
            suffix = f"_NV{self.rng.randint(601, 605)}"
            resource_types = [
                flavor_def["resource_prefix"] + suffix,
                flavor_def["resource_prefix"] + f"_NV{self.rng.randint(601, 605)}",
            ]

        return Vm(
            vm_id=self._uuid(),
            in_host_id=host_id,
            in_numa_id=str(numa_id),
            numa_cpu=float(numa_cpu),
            numa_mem=float(numa_mem),
            resource_types=resource_types,
            lifetime=self.rng.randint(1_000_000, 50_000_000),
            can_migration=self.rng.random() < 0.9,  # ~90% migratable
            tenant_id=tenant_id,
            cutting_line_tag=flavor_def["tag"],
            metrics=self._generate_vm_metrics(),
            flavor_id=flavor_id,
        )

    def generate(
        self,
        num_hosts: int = 20,
        vms_per_host: int = 15,
        num_tenants: int = 8,
        anti_affinity_pct: float = 0.1,
        subhealthy_tenant_pct: float = 0.3,
        dispersed_tenant_pct: float = 0.4,
    ) -> Instance:
        """
        Generate a full instance.

        Args:
            num_hosts: Number of physical hosts
            vms_per_host: Average VMs per host (actual count varies ±30%)
            num_tenants: Number of distinct tenants
            anti_affinity_pct: Fraction of VMs in anti-affinity groups
            subhealthy_tenant_pct: Fraction of tenants with subhealthy migration needs
            dispersed_tenant_pct: Fraction of tenants with dispersed distribution rules
        """
        instance = Instance()
        self._tenant_pool = self._generate_tenants(num_tenants)

        # Assign a primary cutting line tag per host (hosts tend to be homogeneous)
        host_flavors = [self.rng.choice(FLAVOR_CATALOG) for _ in range(num_hosts)]

        all_vms: list[Vm] = []
        tenant_vm_map: dict[str, list[str]] = {t: [] for t in self._tenant_pool}

        # --- Generate hosts and VMs ---
        for h_idx in range(num_hosts):
            tag = host_flavors[h_idx]["tag"]
            host_id = self._generate_host_id(tag, h_idx)
            self._host_ids.append(host_id)

            actual_vm_count = max(1, int(vms_per_host * self.rng.uniform(0.7, 1.3)))
            for _ in range(actual_vm_count):
                tenant = self.rng.choice(self._tenant_pool)
                numa_id = self.rng.randint(0, NUMA_COUNT - 1)
                vm = self._generate_vm(host_id, numa_id, tenant)
                all_vms.append(vm)
                tenant_vm_map[tenant].append(vm.vm_id)

        instance.vms = all_vms

        # --- Anti-affinity groups ---
        # Select a subset of VMs to form anti-affinity groups (2-5 VMs each)
        aa_candidates = [vm.vm_id for vm in all_vms if vm.can_migration]
        self.rng.shuffle(aa_candidates)
        num_aa_vms = int(len(aa_candidates) * anti_affinity_pct)
        idx = 0
        while idx < num_aa_vms:
            remaining = num_aa_vms - idx
            if remaining < 2:
                break
            group_size = self.rng.randint(2, min(5, remaining))
            group = aa_candidates[idx : idx + group_size]
            instance.anti_affinity_groups.append(AntiAffinityGroup(vm_ids=group))
            idx += group_size

        # --- Objectives ---
        instance.objectives = ["MAX_PREFERRED_FLAVOR"]

        # Pick the largest flavor as the preferred one
        largest = FLAVOR_CATALOG[1]  # c6s typically
        instance.prefer_flavor = PreferFlavor(
            numa_cpu=96.0,
            numa_mem=65536.0,
            cpu_ratio=1.0,
            numa_num=1,
            resource_types=[largest["resource_prefix"]],
            flavor_id=f"{largest['tag']}.8xlarge.2",
        )

        # --- Subhealthy host migration ---
        subhealthy_tenants = self.rng.sample(
            self._tenant_pool,
            k=max(1, int(len(self._tenant_pool) * subhealthy_tenant_pct)),
        )
        for tenant in subhealthy_tenants:
            tenant_vms = tenant_vm_map.get(tenant, [])
            if len(tenant_vms) >= 1:
                # Select a subset of this tenant's VMs as needing subhealthy migration
                count = self.rng.randint(1, max(1, len(tenant_vms) // 2))
                selected = self.rng.sample(tenant_vms, min(count, len(tenant_vms)))
                instance.subhealthy_params.append(
                    TenantSubhealthyParam(tenant_id=tenant, vm_ids=selected)
                )

        # --- Tenant dispersed distribution ---
        dispersed_tenants = self.rng.sample(
            self._tenant_pool,
            k=max(1, int(len(self._tenant_pool) * dispersed_tenant_pct)),
        )
        for tenant in dispersed_tenants:
            tenant_vms = tenant_vm_map.get(tenant, [])
            if len(tenant_vms) >= 2:
                instance.distribution_params.append(
                    TenantDistributionParam(
                        tenant_id=tenant,
                        vm_ids=tenant_vms,
                        max_vm_num_per_group=6,  # observed default
                    )
                )

        return instance


# =============================================================================
# Serialization — Protobuf Text Format
# =============================================================================

def to_textproto(instance: Instance) -> str:
    """Serialize an Instance to protobuf text format matching client data format."""
    lines = []

    # VMs
    for vm in instance.vms:
        lines.append("vms {")
        lines.append(f'  vm_id: "{vm.vm_id}"')
        lines.append(f'  in_host_id: "{vm.in_host_id}"')
        lines.append(f'  in_numa_id: "{vm.in_numa_id}"')
        lines.append(f"  numa_cpu: {vm.numa_cpu}")
        lines.append(f"  numa_mem: {vm.numa_mem}")
        for rt in vm.resource_types:
            lines.append(f'  resource_types: "{rt}"')
        lines.append(f"  lifetime: {vm.lifetime}")
        lines.append(f"  can_migration: {'true' if vm.can_migration else 'false'}")
        lines.append(f'  tenant_id: "{vm.tenant_id}"')
        lines.append(f'  cutting_line_tag: "{vm.cutting_line_tag}"')
        # Metrics
        lines.append("  metrics {")
        lines.append(f"    cpu_util: {vm.metrics.cpu_util}")
        # cpu_qos
        lines.append("    cpu_qos {")
        lines.append(f"      score: {vm.metrics.cpu_qos.score}")
        lines.append("      pressure_stats {")
        ps = vm.metrics.cpu_qos.pressure_stats
        if ps.left > 0:
            lines.append(f"        left: {ps.left}")
            lines.append(f"        right: {ps.right}")
            lines.append(f"        p95: {ps.p95}")
            lines.append(f"        typical_value: {ps.typical_value}")
        lines.append("      }")
        lines.append("    }")
        # cpu_power_qos
        lines.append("    cpu_power_qos {")
        lines.append("      pressure_stats {")
        lines.append("      }")
        lines.append("    }")
        lines.append("  }")
        lines.append(f'  flavor_id: "{vm.flavor_id}"')
        lines.append("}")

    # Anti-affinity groups
    for group in instance.anti_affinity_groups:
        lines.append("anti_affinity_groups {")
        for vm_id in group.vm_ids:
            lines.append(f'  vm_ids_in_group: "{vm_id}"')
        lines.append("}")

    # Objectives
    for obj in instance.objectives:
        lines.append(f"objective: {obj}")

    # Objective parameters
    if instance.prefer_flavor:
        pf = instance.prefer_flavor
        lines.append("objective_parameter {")
        lines.append("  max_prefer_flavor_parameter {")
        lines.append("    prefer_flavor {")
        lines.append(f"      numa_cpu: {pf.numa_cpu}")
        lines.append(f"      numa_mem: {pf.numa_mem}")
        lines.append(f"      cpu_ratio: {pf.cpu_ratio}")
        lines.append(f"      numa_num: {pf.numa_num}")
        for rt in pf.resource_types:
            lines.append(f'      resource_types: "{rt}"')
        lines.append(f'      flavor_id: "{pf.flavor_id}"')
        lines.append("    }")
        lines.append("  }")
        lines.append("}")

    # Subhealthy host migration
    if instance.subhealthy_params:
        lines.append("subhealthy_host_migration_parameter {")
        for param in instance.subhealthy_params:
            lines.append("  tenant_subhealthy_host_migration_parameters {")
            lines.append(f'    tenant_id: "{param.tenant_id}"')
            for vm_id in param.vm_ids:
                lines.append(f'    vm_id: "{vm_id}"')
            lines.append("  }")
        lines.append("}")

    # Tenant dispersed distribution
    if instance.distribution_params:
        lines.append("tenant_dispersed_distribution_parameter {")
        for param in instance.distribution_params:
            lines.append("  tenant_distribution_parameters {")
            lines.append(f'    tenant_id: "{param.tenant_id}"')
            for vm_id in param.vm_ids:
                lines.append(f'    vm_id: "{vm_id}"')
            lines.append(f"    max_vm_num_per_group: {param.max_vm_num_per_group}")
            lines.append("  }")
        lines.append("}")

    return "\n".join(lines)


def to_json(instance: Instance) -> str:
    """Serialize an Instance to JSON (for Python-side processing)."""
    def vm_to_dict(vm: Vm) -> dict:
        return {
            "vm_id": vm.vm_id,
            "in_host_id": vm.in_host_id,
            "in_numa_id": vm.in_numa_id,
            "numa_cpu": vm.numa_cpu,
            "numa_mem": vm.numa_mem,
            "resource_types": vm.resource_types,
            "lifetime": vm.lifetime,
            "can_migration": vm.can_migration,
            "tenant_id": vm.tenant_id,
            "cutting_line_tag": vm.cutting_line_tag,
            "metrics": {
                "cpu_util": vm.metrics.cpu_util,
                "cpu_qos": {
                    "score": vm.metrics.cpu_qos.score,
                    "pressure_stats": {
                        "left": vm.metrics.cpu_qos.pressure_stats.left,
                        "right": vm.metrics.cpu_qos.pressure_stats.right,
                        "p95": vm.metrics.cpu_qos.pressure_stats.p95,
                        "typical_value": vm.metrics.cpu_qos.pressure_stats.typical_value,
                    },
                },
                "cpu_power_qos": {
                    "score": vm.metrics.cpu_power_qos.score,
                    "pressure_stats": {
                        "left": vm.metrics.cpu_power_qos.pressure_stats.left,
                        "right": vm.metrics.cpu_power_qos.pressure_stats.right,
                        "p95": vm.metrics.cpu_power_qos.pressure_stats.p95,
                        "typical_value": vm.metrics.cpu_power_qos.pressure_stats.typical_value,
                    },
                },
            },
            "flavor_id": vm.flavor_id,
        }

    data = {
        "vms": [vm_to_dict(vm) for vm in instance.vms],
        "anti_affinity_groups": [{"vm_ids_in_group": g.vm_ids} for g in instance.anti_affinity_groups],
        "objectives": instance.objectives,
        "objective_parameter": {
            "max_prefer_flavor_parameter": {
                "prefer_flavor": {
                    "numa_cpu": instance.prefer_flavor.numa_cpu,
                    "numa_mem": instance.prefer_flavor.numa_mem,
                    "cpu_ratio": instance.prefer_flavor.cpu_ratio,
                    "numa_num": instance.prefer_flavor.numa_num,
                    "resource_types": instance.prefer_flavor.resource_types,
                    "flavor_id": instance.prefer_flavor.flavor_id,
                }
            }
        } if instance.prefer_flavor else {},
        "subhealthy_host_migration_parameter": {
            "tenant_subhealthy_host_migration_parameters": [
                {"tenant_id": p.tenant_id, "vm_ids": p.vm_ids}
                for p in instance.subhealthy_params
            ]
        },
        "tenant_dispersed_distribution_parameter": {
            "tenant_distribution_parameters": [
                {"tenant_id": p.tenant_id, "vm_ids": p.vm_ids, "max_vm_num_per_group": p.max_vm_num_per_group}
                for p in instance.distribution_params
            ]
        },
    }
    return json.dumps(data, indent=2)


# =============================================================================
# Instance Statistics Summary
# =============================================================================

def print_summary(instance: Instance) -> None:
    """Print a summary of the generated instance."""
    num_vms = len(instance.vms)
    hosts = set(vm.in_host_id for vm in instance.vms)
    tenants = set(vm.tenant_id for vm in instance.vms)
    migratable = sum(1 for vm in instance.vms if vm.can_migration)
    avg_cpu_util = sum(vm.metrics.cpu_util for vm in instance.vms) / num_vms if num_vms else 0
    cutting_tags = set(vm.cutting_line_tag for vm in instance.vms)

    print("=" * 60)
    print("Instance Summary")
    print("=" * 60)
    print(f"  Hosts:                {len(hosts)}")
    print(f"  VMs:                  {num_vms}")
    print(f"  Migratable VMs:       {migratable} ({100*migratable/num_vms:.0f}%)")
    print(f"  Tenants:              {len(tenants)}")
    print(f"  Cutting line tags:    {sorted(cutting_tags)}")
    print(f"  Avg CPU utilization:  {avg_cpu_util:.1f}%")
    print(f"  Anti-affinity groups: {len(instance.anti_affinity_groups)}")
    print(f"  Subhealthy tenants:   {len(instance.subhealthy_params)}")
    print(f"  Dispersed tenants:    {len(instance.distribution_params)}")
    print(f"  Objectives:           {instance.objectives}")
    print("=" * 60)


# =============================================================================
# Presets
# =============================================================================

PRESETS = {
    "tiny":   {"num_hosts": 5,   "vms_per_host": 8,  "num_tenants": 3},
    "small":  {"num_hosts": 10,  "vms_per_host": 12, "num_tenants": 5},
    "medium": {"num_hosts": 20,  "vms_per_host": 15, "num_tenants": 8},
    "large":  {"num_hosts": 50,  "vms_per_host": 20, "num_tenants": 15},
    "xlarge": {"num_hosts": 100, "vms_per_host": 25, "num_tenants": 25},
}


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic Server Consolidation V2 instance data"
    )
    parser.add_argument("--preset", choices=PRESETS.keys(), help="Use a preset configuration")
    parser.add_argument("--num-hosts", type=int, default=20, help="Number of hosts")
    parser.add_argument("--vms-per-host", type=int, default=15, help="Avg VMs per host")
    parser.add_argument("--num-tenants", type=int, default=8, help="Number of tenants")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    parser.add_argument("--format", choices=["textproto", "json", "both"], default="textproto",
                        help="Output format")
    parser.add_argument("--batch", type=int, default=None,
                        help="Generate N instances with different seeds")
    parser.add_argument("--output-dir", type=str, default="./instances",
                        help="Output directory for batch generation")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary output")
    args = parser.parse_args()

    # Apply preset if specified
    gen_kwargs = {}
    if args.preset:
        gen_kwargs = PRESETS[args.preset].copy()
    else:
        gen_kwargs = {
            "num_hosts": args.num_hosts,
            "vms_per_host": args.vms_per_host,
            "num_tenants": args.num_tenants,
        }

    # Batch mode
    if args.batch:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for i in range(args.batch):
            seed = args.seed + i
            gen = InstanceGenerator(seed=seed)
            instance = gen.generate(**gen_kwargs)

            if args.format in ("textproto", "both"):
                path = output_dir / f"instance_{i+1:03d}.textproto"
                path.write_text(to_textproto(instance))
            if args.format in ("json", "both"):
                path = output_dir / f"instance_{i+1:03d}.json"
                path.write_text(to_json(instance))

            if not args.quiet:
                print(f"[{i+1}/{args.batch}] seed={seed}")
                print_summary(instance)
                print()

        print(f"Generated {args.batch} instances in {output_dir}/")
        return

    # Single instance
    gen = InstanceGenerator(seed=args.seed)
    instance = gen.generate(**gen_kwargs)

    if not args.quiet:
        print_summary(instance)

    # Output
    def write_output(content: str, suffix: str):
        if args.output:
            path = Path(args.output).with_suffix(suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"Written to: {path}")
        else:
            print(content)

    if args.format in ("textproto", "both"):
        write_output(to_textproto(instance), ".textproto")
    if args.format in ("json", "both"):
        write_output(to_json(instance), ".json")


if __name__ == "__main__":
    main()
