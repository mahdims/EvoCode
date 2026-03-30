"""
AILS Builder

Compiles LLM-generated DestroyStrategy Java code into AILS-compatible plugin JARs.
All AILS-specific compilation logic lives here.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from building.base_builder import BaseBuilder
from .templates import (
    AILS_CONSTRAINTS,
    AILS_PROBLEM_DESCRIPTION,
    AILS_DATA_STRUCTURES,
    get_ails_initial_seeds,
)


class AILSBuilder(BaseBuilder):
    """Builds AILS plugin JARs from LLM-generated Java DestroyStrategy code.

    Handles:
    - Extracting class name from Java source
    - Auto-generating the Perturbation adapter wrapper
    - Compiling Java sources against the AILS JAR
    - Packaging compiled classes into a plugin JAR
    """

    def __init__(self, ails_jar: str):
        """
        Args:
            ails_jar: Path to AILSII.jar (used as compilation classpath)
        """
        self.ails_jar = Path(ails_jar)

    # ------------------------------------------------------------------
    # BaseBuilder interface
    # ------------------------------------------------------------------

    def extract_entry_point(self, source_code: str) -> Optional[str]:
        """Extract Java class name from source.  Entry point = wrapper class name."""
        return self._extract_strategy_class(source_code)

    def build(self,
              source_code: str,
              candidate_id: int,
              candidate_dir: str) -> Optional[Dict[str, Any]]:
        """Compile strategy + wrapper into a plugin JAR.

        Returns:
            {"artifact_path": str, "entry_point": str, "strategy_class": str}
            or None on failure.
        """
        candidate_dir = Path(candidate_dir)

        # Extract strategy class name
        strategy_class = self._extract_strategy_class(source_code)
        if not strategy_class:
            logger.warning("[AILS BUILD] Could not extract class name from code")
            return None

        # Create directory structure
        src_dir = candidate_dir / "src"
        (src_dir / "EvoDestroy").mkdir(parents=True, exist_ok=True)
        (src_dir / "Perturbation").mkdir(parents=True, exist_ok=True)
        classes_dir = candidate_dir / "classes"
        classes_dir.mkdir(exist_ok=True)

        # Write strategy source
        strategy_file = src_dir / "EvoDestroy" / f"{strategy_class}.java"
        strategy_file.write_text(source_code, encoding="utf-8")

        # Generate and write wrapper
        wrapper_class = f"EvoPlugin_Gen{candidate_id:04d}"
        wrapper_code = self._generate_wrapper(strategy_class, candidate_id)
        wrapper_file = src_dir / "Perturbation" / f"{wrapper_class}.java"
        wrapper_file.write_text(wrapper_code, encoding="utf-8")

        # Compile
        compile_log = candidate_dir / "compile.log"
        result = subprocess.run(
            [
                "javac",
                "-cp", str(self.ails_jar),
                "-d", str(classes_dir),
                str(strategy_file),
                str(wrapper_file),
            ],
            capture_output=True,
            text=True,
        )
        compile_log.write_text(result.stdout + result.stderr, encoding="utf-8")

        if result.returncode != 0:
            logger.warning(f"[AILS BUILD] Compilation failed for candidate {candidate_id}")
            logger.warning(f"[AILS BUILD] See: {compile_log}")
            return None

        # Package JAR
        jar_file = candidate_dir / "plugin.jar"
        subprocess.run(
            ["jar", "cf", str(jar_file), "-C", str(classes_dir), "."],
            capture_output=True,
        )

        if not jar_file.exists():
            logger.warning(f"[AILS BUILD] JAR creation failed for candidate {candidate_id}")
            return None

        logger.debug(f"[AILS BUILD] Compiled candidate {candidate_id} -> {jar_file}")
        return {
            "artifact_path": str(jar_file),
            "entry_point": wrapper_class,
            "strategy_class": strategy_class,  # kept for backward compat / resume
        }

    def get_source_path(self,
                        candidate_dir: Path,
                        metadata: Dict[str, Any]) -> Optional[Path]:
        """Return path to the Java strategy source file for resume."""
        strategy_class = metadata.get("strategy_class", "Unknown")
        source = candidate_dir / "src" / "EvoDestroy" / f"{strategy_class}.java"
        return source if source.exists() else None

    def get_llm_context(self) -> Dict[str, Any]:
        """Return AILS VRP domain context for LLM prompts."""
        return {
            "constraints": AILS_CONSTRAINTS,
            "problem_description": AILS_PROBLEM_DESCRIPTION,
            "data_structures": AILS_DATA_STRUCTURES,
            "language": "java",
            "initial_seeds": get_ails_initial_seeds(),
            "mutation_guidance": (
                "Focus on node selection logic: KNN, cost-based, route-aware. "
                "Make targeted changes to the selection criterion."
            ),
            "crossover_guidance": (
                "Preserve the spatial locality mechanism of the elite parent. "
                "Explicitly take ~75% from the elite parent."
            ),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_strategy_class(java_code: str) -> Optional[str]:
        """Extract class name from Java source code."""
        match = re.search(
            r'public\s+class\s+(\w+)\s+implements\s+DestroyStrategy', java_code
        )
        if match:
            return match.group(1)
        # Fallback: find any public class
        match = re.search(r'public\s+class\s+(\w+)', java_code)
        return match.group(1) if match else None

    def _generate_wrapper(self, strategy_class_name: str, candidate_id: int) -> str:
        """Generate the Perturbation adapter wrapper for the strategy class."""
        wrapper_class = f"EvoPlugin_Gen{candidate_id:04d}"
        return f"""package Perturbation;

import EvoDestroy.*;
import java.util.*;
import Data.Instance;
import DiversityControl.OmegaAdjustment;
import Improvement.IntraLocalSearch;
import SearchMethod.Config;
import Solution.Node;
import Solution.Solution;

/**
 * AUTO-GENERATED WRAPPER for {strategy_class_name}
 * Bridges simple DestroyStrategy to AILS Perturbation pattern
 * Includes validation for LLM-generated strategy outputs
 *
 * Generated: {datetime.now().isoformat()}
 * Candidate ID: {candidate_id}
 */
public class {wrapper_class} extends Perturbation {{

    private DestroyStrategy strategy;
    private static int invocationCount = 0;
    private static final int LOG_INTERVAL = 100;  // Log every 100 invocations

    public {wrapper_class}(
        Instance instance,
        Config config,
        HashMap<String, OmegaAdjustment> omegaSetup,
        IntraLocalSearch intraLocalSearch
    ) {{
        super(instance, config, omegaSetup, intraLocalSearch);
        this.perturbationType = PerturbationType.Sequential; // Reuse type for plugins
        this.strategy = new {strategy_class_name}();
    }}

    @Override
    public void applyPerturbation(Solution s) {{
        // Standard AILS pattern
        setSolution(s);

        // DESTROY: Use LLM-generated strategy
        Node[] toRemove = strategy.selectNodesToRemove(
            (int) omega,        // Adaptive parameter from OmegaAdjustment
            routes,
            numRoutes,
            solution,
            instance,
            rand
        );

        // === VALIDATION: Check LLM strategy output ===
        int requestedOmega = (int) omega;
        int nullCount = 0;
        int invalidCount = 0;  // not belonging or depot
        int duplicateCount = 0;
        Set<Integer> seenNodes = new HashSet<>();

        // Validate and cap at omega
        int validCount = 0;
        for (int i = 0; i < toRemove.length && validCount < requestedOmega; i++) {{
            Node node = toRemove[i];

            if (node == null) {{
                nullCount++;
                continue;
            }}

            if (!node.nodeBelong || node.name == 0) {{
                invalidCount++;
                continue;
            }}

            if (seenNodes.contains(node.name)) {{
                duplicateCount++;
                continue;
            }}

            // Valid node - add to removal set
            seenNodes.add(node.name);
            candidates[countCandidates++] = node;
            validCount++;

            // Save old positions for potential restoration
            node.prevOld = node.prev;
            node.nextOld = node.next;

            // Remove from route and update cost
            f += node.route.remove(node);
        }}

        // === VALIDATION GATE: Fail if strategy violates contract ===
        boolean hasErrors = (nullCount > 0 || invalidCount > 0 || duplicateCount > 0 || toRemove.length > requestedOmega);

        if (hasErrors || validCount == 0) {{
            String errorMsg = "[VALIDATION FAILURE] {wrapper_class}: omega=" + requestedOmega +
                ", returned=" + toRemove.length + ", valid=" + validCount +
                ", nulls=" + nullCount + ", invalid=" + invalidCount + ", dups=" + duplicateCount;
            System.err.println(errorMsg);

            // Fail immediately - don't waste cycles on invalid strategies
            throw new RuntimeException(errorMsg + " - Strategy violates AILS adapter contract");
        }}

        // Log omega adaptivity (periodic sampling for analysis)
        invocationCount++;
        if (invocationCount % LOG_INTERVAL == 0) {{
            System.err.println("[OMEGA] {wrapper_class} #" + invocationCount +
                ": omega=" + String.format("%.2f", omega) +
                ", removed=" + validCount + "/" + requestedOmega);
        }}

        // REPAIR: Use standard AILS repair logic (unchanged)
        setOrder();           // Randomize insertion order
        addCandidates();      // Greedy KNN-based insertion

        // Finalize changes
        assignSolution(s);
    }}
}}
"""
