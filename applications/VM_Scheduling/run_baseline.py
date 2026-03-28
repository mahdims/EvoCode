"""
Baseline measurement script for VM Scheduling.

Runs the solver in two modes on all tenant instances:
  1. Stub mode (no plugin): records consolidation metrics without constraint guidance
  2. Seed plugin mode: records initial/final violations with the reference implementation

Saves results to baseline_stub.csv and baseline_seed.csv.
"""

import csv
import os
import subprocess
import time
from pathlib import Path

VM_JAR = Path(__file__).parent / "target" / "vm-scheduling-1.0-SNAPSHOT.jar"
DATA_DIR = Path(__file__).parent / "data"

INSTANCES = [
    "smoke_h8_v5_s1",
    "tenant_h10_v8_s1",
    "tenant_h10_v8_s2",
    "tenant_h10_v8_s3",
    "tenant_h15_v10_s1",
    "tenant_h15_v10_s2",
    "tenant_h15_v10_s3",
    "tenant_h20_v12_s1",
    "tenant_h20_v12_s2",
    "tenant_h20_v12_s3",
]

KEY_FIELDS = [
    "INITIAL_PENALTY_A", "INITIAL_PENALTY_B", "INITIAL_PENALTY_C",
    "FINAL_PENALTY_A",   "FINAL_PENALTY_B",   "FINAL_PENALTY_C",
    "EMPTY_HOSTS_INITIAL", "EMPTY_HOSTS_FINAL",
    "MIGRATIONS", "RUNTIME_MS",
]

SEED = 42
SEED_PLUGIN_JAR = Path(__file__).parent.parent.parent / "_test_seed" / "plugin.jar"
SEED_PLUGIN_CLASS = "plugin.TenantPluginRef"


def parse_output(stdout: str) -> dict:
    result = {}
    for line in stdout.splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("["):
            key, _, val = line.partition("=")
            key = key.strip()
            if key in KEY_FIELDS:
                try:
                    result[key] = int(val.strip())
                except ValueError:
                    pass
    return result


def run_instance(instance_name: str, seed: int = SEED,
                 plugin_jar: Path = None, plugin_class: str = None) -> dict:
    path = DATA_DIR / f"{instance_name}.json"
    if not path.exists():
        return {"instance": instance_name, "success": False, "error": "file not found"}

    if plugin_jar and plugin_class and plugin_jar.exists():
        sep = ";" if os.name == "nt" else ":"
        cp = f"{plugin_jar}{sep}{VM_JAR}"
        cmd = ["java", "-cp", cp, "com.vmscheduling.Main",
               str(path), str(seed), plugin_class]
    else:
        cmd = ["java", "-jar", str(VM_JAR), str(path), str(seed)]

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        elapsed = time.time() - t0
        parsed = parse_output(proc.stdout)
        result = {"instance": instance_name, "seed": seed,
                  "success": proc.returncode == 0,
                  "wall_time_s": round(elapsed, 2)}
        result.update(parsed)
        if proc.returncode != 0:
            result["error"] = proc.stderr[:300]
        return result
    except subprocess.TimeoutExpired:
        return {"instance": instance_name, "success": False, "error": "timeout", "wall_time_s": 120}
    except Exception as e:
        return {"instance": instance_name, "success": False, "error": str(e)}


def summarize(r: dict, mode: str):
    if r.get("success"):
        a0 = r.get("INITIAL_PENALTY_A", 0)
        b0 = r.get("INITIAL_PENALTY_B", 0)
        c0 = r.get("INITIAL_PENALTY_C", 0)
        af = r.get("FINAL_PENALTY_A",   0)
        bf = r.get("FINAL_PENALTY_B",   0)
        cf = r.get("FINAL_PENALTY_C",   0)
        total_i = a0 + b0 + c0
        total_f = af + bf + cf
        reduction = (total_i - total_f) / max(1, total_i) if total_i > 0 else 0.0
        ei = r.get("EMPTY_HOSTS_INITIAL", "?")
        ef = r.get("EMPTY_HOSTS_FINAL", "?")
        migs = r.get("MIGRATIONS", "?")
        rt = r.get("wall_time_s", "?")
        print(f"  [{mode:5}] ({rt}s) Violations: [{a0}+{b0}+{c0}={total_i}] -> "
              f"[{af}+{bf}+{cf}={total_f}] reduction={reduction:.1%}  "
              f"Empty: {ei}->{ef}  Migs: {migs}")
    else:
        print(f"  [{mode:5}] FAILED: {r.get('error', 'unknown')}")


def write_csv(rows: list, path: Path):
    all_keys = ["instance", "seed", "success", "wall_time_s"] + KEY_FIELDS + ["error"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Saved: {path}")


def main():
    print("VM Scheduling Baseline Measurements")
    print(f"JAR:         {VM_JAR}")
    print(f"Seed plugin: {SEED_PLUGIN_JAR} (exists={SEED_PLUGIN_JAR.exists()})")
    print("=" * 80)

    stub_rows = []
    seed_rows = []

    for name in INSTANCES:
        print(f"\n{name}:")
        stub_rows.append(run_instance(name))
        summarize(stub_rows[-1], "stub")
        if SEED_PLUGIN_JAR.exists():
            r = run_instance(name, plugin_jar=SEED_PLUGIN_JAR,
                             plugin_class=SEED_PLUGIN_CLASS)
            seed_rows.append(r)
            summarize(r, "seed")

    print("\n" + "=" * 80)
    out_dir = Path(__file__).parent
    write_csv(stub_rows, out_dir / "baseline_stub.csv")
    if seed_rows:
        write_csv(seed_rows, out_dir / "baseline_seed.csv")

    if seed_rows:
        print("\n=== Seed Plugin Summary ===")
        print(f"{'Instance':<25} {'Init':>6} {'Final':>6} {'Reduc':>7} {'Empty':>8} {'Migs':>5}")
        print("-" * 60)
        for r in seed_rows:
            if not r.get("success"):
                continue
            ti = sum(r.get(f"INITIAL_PENALTY_{x}", 0) for x in "ABC")
            tf = sum(r.get(f"FINAL_PENALTY_{x}", 0) for x in "ABC")
            red = (ti - tf) / max(1, ti)
            ei = r.get("EMPTY_HOSTS_INITIAL", 0)
            ef = r.get("EMPTY_HOSTS_FINAL", 0)
            mig = r.get("MIGRATIONS", 0)
            print(f"{r['instance']:<25} {ti:>6} {tf:>6} {red:>6.1%} {ei}->{ef:<4} {mig:>5}")


if __name__ == "__main__":
    main()
