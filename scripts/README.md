# SLURM Scripts for the Nibi Cluster

Job scripts for running EvoCode on Nibi.

| Script | Purpose |
|--------|---------|
| `setup.sh` | One-time environment setup — venv at `$HOME/envs/evolver` plus dependencies |
| `run_evolution.sh` | Submit a single evolution run |

## Setup (one-time)

Run from the **repo root** — `setup.sh` resolves paths relative to its own parent directory:

```bash
ssh nibi.alliancecan.ca
cd $PROJECT/EvoCode

bash scripts/setup.sh    # loads python/3.12 + java/21, installs evolver/requirements.txt
```

Then add your API key. The `.env` file must live in `evolver/`, since the run starts from there:

```bash
cp .env.example evolver/.env
nano evolver/.env        # add GEMINI_API_KEY
```

## Running jobs

Submit from the repo root — the job script does `cd "$SLURM_SUBMIT_DIR/evolver"` before running:

```bash
mkdir -p slurm_logs      # SBATCH --output needs this to exist at submit time

# Single run (uses configs/default.json)
sbatch scripts/run_evolution.sh

# With a specific config — path is relative to evolver/
sbatch scripts/run_evolution.sh configs/quick_test.json

# Check status
squeue -u $USER

# Cancel
scancel <job_id>
```

## Configuration

Evolution parameters live in the JSON config you pass to `run_evolution.sh` — see [`evolver/configs/`](../evolver/configs) and the [Configuration section](../README.md#configuration) of the main README.

Scheduler settings are the SBATCH directives at the top of `run_evolution.sh`:

| Directive | Default | Notes |
|-----------|---------|-------|
| `--account` | `def-YOUR_ACCOUNT` | Your allocation — set this before the first run |
| `--time` | `4:00:00` | Walltime limit |
| `--cpus-per-task` | `4` | Should be at least `max_parallel_evals` from your config |
| `--mem` | `8G` | |

> SLURM reads `#SBATCH` lines before the shell runs, so they do not expand variables. Set `--account` to a literal value rather than relying on `$SLURM_ACCOUNT`.

## Internet access

Nibi has full internet access on all nodes. No proxy configuration is needed for API calls.
