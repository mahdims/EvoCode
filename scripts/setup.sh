#!/bin/bash
# One-time setup script for Nibi cluster
# Run interactively: bash scripts/setup.sh

set -e

echo "=== Setting up evolver environment on Nibi ==="

# Load required modules
module load python/3.12 java/21

# Create virtual environment
python -m venv $HOME/envs/evolver
source $HOME/envs/evolver/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Setup complete ==="
echo "To activate: source \$HOME/envs/evolver/bin/activate"
echo ""
echo "IMPORTANT: Create .env file with your GEMINI_API_KEY"
echo "  cp .env.example .env"
echo "  nano .env  # add your key"
