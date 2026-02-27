#!/bin/bash
# One-time setup script for Nibi cluster
# Run interactively from the repo root: bash scripts/setup.sh

set -e

# Resolve repo root (parent of scripts/)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Setting up evolver environment on Nibi ==="
echo "    Repo root: $REPO_ROOT"

# Load required modules
module load python/3.12 java/21

# Create virtual environment
python -m venv $HOME/envs/evolver
source $HOME/envs/evolver/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r "$REPO_ROOT/evolver/requirements.txt"

echo "=== Setup complete ==="
echo "To activate: source \$HOME/envs/evolver/bin/activate"
echo ""
echo "IMPORTANT: Create .env file with your GEMINI_API_KEY"
echo "  cp $REPO_ROOT/.env.example $REPO_ROOT/evolver/.env"
echo "  nano $REPO_ROOT/evolver/.env  # add your key"
