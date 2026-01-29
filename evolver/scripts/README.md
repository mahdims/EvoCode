# SLURM Scripts for Nibi Cluster

## Setup (one-time)

```bash
# Clone/transfer project to Nibi
ssh nibi.alliancecan.ca
cd $PROJECT/evolver

# Run setup
bash scripts/setup.sh

# Configure API key
cp .env.example .env
nano .env  # add GEMINI_API_KEY
```

## Running Jobs

```bash
# Create logs directory
mkdir -p slurm_logs

# Single run
sbatch scripts/run_evolution.sh

# Multiple runs (job array)
sbatch scripts/run_array.sh

# Check status
squeue -u $USER

# Cancel jobs
scancel <job_id>
```

## Configuration

Edit the scripts to change:
- `--account=def-YOUR_ACCOUNT` - your allocation account
- `--time` - walltime limit
- `--array=0-4` - number of parallel runs (0-N means N+1 jobs)
- Evolution parameters in the Python code block

## Internet Access

Nibi has full internet access on all nodes. No proxy configuration needed for API calls.
