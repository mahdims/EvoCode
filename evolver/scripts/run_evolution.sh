#!/bin/bash
#SBATCH --job-name=evolver
#SBATCH --account=def-YOUR_ACCOUNT  # CHANGE THIS
#SBATCH --time=4:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=slurm_logs/%x-%j.out
#SBATCH --error=slurm_logs/%x-%j.err

# Create logs directory
mkdir -p slurm_logs

# Load modules
module load python/3.12 java/21

# Activate environment
source $HOME/envs/evolver/bin/activate

# Navigate to project
cd $SLURM_SUBMIT_DIR

# Run evolution with config file
# Default: config.json, or specify: configs/full_small.json
CONFIG=${1:-config.json}
python evo_agent.py "$CONFIG"
