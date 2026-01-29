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

# Run evolution
python -c "
from src.evolution_loop import EvolutionLoop

evolution = EvolutionLoop(
    population_size=4,
    elite_ratio=0.25,
    dataset_dir='Vrp_Set_X',
    target_instances=['X-n101-k25', 'X-n106-k14'],
    use_vrpagent=True
)

evolution.initialize_population(num_seeds=2)
evolution.evolve(num_generations=5, reflection_frequency=2)
"
