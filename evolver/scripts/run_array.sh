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

# Run evolution with unique seed
python -c "
from src.evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=4,
    elite_ratio=0.25,
    dataset_dir='Vrp_Set_X',
    target_instances=['X-n101-k25', 'X-n106-k14'],
    use_vrpagent=True,
    seed=$SEED
)

evolution.initialize_population(num_seeds=2)
evolution.evolve(num_generations=5, reflection_frequency=2)
"

echo "Array task $SLURM_ARRAY_TASK_ID (seed $SEED) completed"
