#!/bin/bash
#SBATCH --job-name=evolver-array
#SBATCH --account=def-YOUR_ACCOUNT  # CHANGE THIS
#SBATCH --time=4:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --array=0-4  # 5 independent runs with different seeds
#SBATCH --output=slurm_logs/%x-%A_%a.out
#SBATCH --error=slurm_logs/%x-%A_%a.err

# Create logs directory
mkdir -p slurm_logs

# Load modules
module load python/3.12 java/21

# Activate environment
source $HOME/envs/evolver/bin/activate

# Navigate to project
cd $SLURM_SUBMIT_DIR

# Use array task ID as random seed
SEED=$SLURM_ARRAY_TASK_ID

# Create temporary config with unique seed
CONFIG_TEMPLATE=${1:-config.json}
TEMP_CONFIG="slurm_logs/config_seed${SEED}.json"

# Modify seed in config using Python
python -c "
import json
with open('$CONFIG_TEMPLATE') as f:
    config = json.load(f)
config['seed'] = $SEED
config['experiment_name'] = config.get('experiment_name', 'run') + '_seed$SEED'
with open('$TEMP_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
print(f'Created config with seed=$SEED: $TEMP_CONFIG')
"

# Run evolution with modified config
python evo_agent.py "$TEMP_CONFIG"

echo "Array task $SLURM_ARRAY_TASK_ID (seed $SEED) completed"
