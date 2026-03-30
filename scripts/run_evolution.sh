#!/bin/bash
#SBATCH --job-name=evolver
#SBATCH --account=${SLURM_ACCOUNT:-def-YOUR_ACCOUNT}
#SBATCH --time=4:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=slurm_logs/%x-%j.out
#SBATCH --error=slurm_logs/%x-%j.err

# Create logs directory
mkdir -p "$SLURM_SUBMIT_DIR/slurm_logs"

# Load modules
module load python/3.12 java/21

# Activate environment
source $HOME/envs/evolver/bin/activate

# Navigate to evolver/ inside the repo
cd "$SLURM_SUBMIT_DIR/evolver"

# Run evolution with config file
# Default: configs/default.json, or pass a path relative to evolver/: sbatch run_evolution.sh configs/quick_test.json
CONFIG=${1:-configs/default.json}
python evo_agent.py "$CONFIG"
