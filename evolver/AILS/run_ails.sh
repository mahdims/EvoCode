#!/bin/bash
#
# Run AILS-II algorithm on VRP instances
# Usage: ./run_ails.sh
#
# Configure the parameters below before running
#

# ==============================================================================
# CONFIGURABLE PARAMETERS - Modify these as needed
# ==============================================================================

# Dataset directory containing .vrp files (relative to script location)
DATASET="data/Vrp_Set_X"
# Alternative: DATASET="data/XL"

# Warmstart settings
# USE_WARMSTART: "true" or "false" (default: false)
# Note: If WARMSTART_DIR is set and file exists, useWarmStart is auto-enabled
USE_WARMSTART="false"

# Warmstart directory containing .sol files (relative to script location)
# Set to empty string "" to disable warmstart
# WARMSTART_DIR="warm_start/Vrp_Set_X"
# Alternative: WARMSTART_DIR="warm_start/XL"

# Output directory for solution files
OUTPUT_DIR="output"

# Random seed
SEED=42

# Stopping criterion: "Iteration" or "Time"
STOPPING_CRITERION="Iteration"

# Limit value (iterations if STOPPING_CRITERION=Iteration, seconds if Time)
LIMIT=10

# Best known solution cost (0 to disable)
BEST=0

# Rounding: "true" or "false"
ROUNDED="true"

# Algorithm parameters
VARPHI=40    # KNN neighborhood size
GAMMA=30     # Iterations between omega adjustments
DMAX=30      # Initial reference distance threshold
DMIN=15      # Final reference distance threshold

# Optional: Custom destroy plugin (leave empty for original AILS)
DESTROY_PLUGIN=""
DESTROY_CLASS=""

# ==============================================================================
# SCRIPT LOGIC - No need to modify below this line
# ==============================================================================

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR_PATH="$SCRIPT_DIR/AILSII.jar"

# Check if jar exists
if [ ! -f "$JAR_PATH" ]; then
    echo "Error: AILSII.jar not found at $JAR_PATH"
    exit 1
fi

# Create output directory
mkdir -p "$SCRIPT_DIR/$OUTPUT_DIR"

# Get all .vrp files in dataset directory
INSTANCE_FILES=("$SCRIPT_DIR/$DATASET"/*.vrp)

if [ ${#INSTANCE_FILES[@]} -eq 0 ] || [ ! -f "${INSTANCE_FILES[0]}" ]; then
    echo "Error: No .vrp files found in $SCRIPT_DIR/$DATASET"
    exit 1
fi

echo "============================================================"
echo "AILS-II Runner"
echo "============================================================"
echo "Dataset:           $DATASET"
echo "Instances found:   ${#INSTANCE_FILES[@]}"
echo "Seed:              $SEED"
echo "Stopping:          $STOPPING_CRITERION"
echo "Limit:             $LIMIT"
echo "UseWarmStart:      $USE_WARMSTART"
echo "Output:            $OUTPUT_DIR"
echo "============================================================"
echo ""

# Counter for summary
TOTAL=0
SUCCESS=0

# Loop through all instances
for INSTANCE_FILE in "${INSTANCE_FILES[@]}"; do
    # Extract instance name (without path and extension)
    INSTANCE_NAME=$(basename "$INSTANCE_FILE" .vrp)

    TOTAL=$((TOTAL + 1))

    echo "----------------------------------------"
    echo "[$TOTAL/${#INSTANCE_FILES[@]}] Running: $INSTANCE_NAME"
    echo "----------------------------------------"

    # Build output path
    SOL_OUTPUT="$SCRIPT_DIR/$OUTPUT_DIR/${INSTANCE_NAME}_seed${SEED}.sol"

    # Build command with required parameters
    CMD="java -jar \"$JAR_PATH\""
    CMD="$CMD -file \"$INSTANCE_FILE\""
    CMD="$CMD -seed $SEED"
    CMD="$CMD -stoppingCriterion $STOPPING_CRITERION"
    CMD="$CMD -limit $LIMIT"
    CMD="$CMD -rounded $ROUNDED"
    CMD="$CMD -solOutput \"$SOL_OUTPUT\""
    CMD="$CMD -varphi $VARPHI"
    CMD="$CMD -gamma $GAMMA"
    CMD="$CMD -dMax $DMAX"
    CMD="$CMD -dMin $DMIN"

    # Add useWarmStart flag if explicitly set to true
    if [ "$USE_WARMSTART" = "true" ]; then
        CMD="$CMD -useWarmStart true"
    fi

    # Add warmstart path if directory is set and file exists
    # Note: providing -warmStart automatically enables useWarmStart in Java
    if [ -n "$WARMSTART_DIR" ]; then
        WARMSTART_FILE="$SCRIPT_DIR/$WARMSTART_DIR/${INSTANCE_NAME}.sol"
        if [ -f "$WARMSTART_FILE" ]; then
            CMD="$CMD -warmStart \"$WARMSTART_FILE\""
        else
            echo "  Warning: Warmstart file not found: $WARMSTART_FILE"
        fi
    fi

    # Add best known if set
    if [ "$BEST" != "0" ]; then
        CMD="$CMD -best $BEST"
    fi

    # Add destroy plugin if set
    if [ -n "$DESTROY_PLUGIN" ] && [ -n "$DESTROY_CLASS" ]; then
        CMD="$CMD -destroyPlugin \"$DESTROY_PLUGIN\""
        CMD="$CMD -destroyClass \"$DESTROY_CLASS\""
    fi

    # Print command (truncated for readability)
    echo "  Command: java -jar AILSII.jar -file ... -seed $SEED -limit $LIMIT"

    # Run the command
    cd "$SCRIPT_DIR"
    eval $CMD

    # Check if output was created
    if [ -f "$SOL_OUTPUT" ]; then
        COST=$(grep "^Cost" "$SOL_OUTPUT" | awk '{print $2}')
        echo "  Result: SUCCESS - Cost = $COST"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "  Result: FAILED - No output generated"
    fi

    echo ""
done

echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo "Total instances:   $TOTAL"
echo "Successful runs:   $SUCCESS"
echo "Failed runs:       $((TOTAL - SUCCESS))"
echo "Output directory:  $SCRIPT_DIR/$OUTPUT_DIR"
echo "============================================================"
