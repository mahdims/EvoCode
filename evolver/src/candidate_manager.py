"""
Candidate Manager for LLM-Generated Destroy Strategies

Handles:
- Compilation of LLM-generated DestroyStrategy implementations
- Auto-generation of Perturbation adapter wrappers
- JAR packaging
- Caching by code hash
- Metadata tracking (parent IDs, prompts, timestamps)
"""

import os
import json
import hashlib
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class CandidateManager:
    """Manages compilation and caching of plugin candidates."""

    def __init__(self,
                 candidates_dir: str = "candidates",
                 ails_jar: str = "AILS/AILSII.jar",
                 cache_file: str = "candidates/cache.json"):
        """
        Initialize candidate manager.

        Args:
            candidates_dir: Directory for storing candidate files
            ails_jar: Path to AILS JAR for compilation classpath
            cache_file: Path to cache database
        """
        self.candidates_dir = Path(candidates_dir)
        self.ails_jar = Path(ails_jar)
        self.cache_file = Path(cache_file)

        # Create directories
        self.candidates_dir.mkdir(exist_ok=True)

        # Load cache
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load cache from disk."""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        self.cache_file.parent.mkdir(exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def extract_class_name(self, java_code: str) -> Optional[str]:
        """
        Extract class name from Java code.

        Args:
            java_code: Java source code

        Returns:
            Class name or None if not found
        """
        # Look for: public class ClassName implements DestroyStrategy
        match = re.search(r'public\s+class\s+(\w+)\s+implements\s+DestroyStrategy', java_code)
        if match:
            return match.group(1)

        # Fallback: just find public class
        match = re.search(r'public\s+class\s+(\w+)', java_code)
        if match:
            return match.group(1)

        return None

    def generate_wrapper(self, strategy_class_name: str, candidate_id: int) -> str:
        """
        Generate Perturbation adapter wrapper code.

        Args:
            strategy_class_name: Name of the DestroyStrategy implementation class
            candidate_id: Unique candidate ID

        Returns:
            Java source code for wrapper
        """
        wrapper_class = f"EvoPlugin_Gen{candidate_id:04d}"

        code = f"""package Perturbation;

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
        return code

    def compile_candidate(self,
                         strategy_code: str,
                         candidate_id: int,
                         parent_id: Optional[int] = None,
                         mutation_type: str = "initial") -> Optional[Dict[str, Any]]:
        """
        Compile a candidate plugin.

        Args:
            strategy_code: Java source code for DestroyStrategy implementation
            candidate_id: Unique candidate ID
            parent_id: Parent candidate ID (if mutation/crossover)
            mutation_type: Type of generation (initial, mutation, crossover)

        Returns:
            Dictionary with compilation result or None if failed
        """
        # Check cache
        code_hash = hashlib.sha256(strategy_code.encode()).hexdigest()
        if code_hash in self.cache:
            print(f"[CACHE HIT] Candidate {candidate_id} matches cached code")
            cached = self.cache[code_hash].copy()
            cached["candidate_id"] = candidate_id  # Update ID
            return cached

        # Extract class name
        strategy_class = self.extract_class_name(strategy_code)
        if not strategy_class:
            print(f"[COMPILE ERROR] Could not extract class name from code")
            return None

        # Create candidate directory
        candidate_dir = self.candidates_dir / f"gen_{candidate_id:04d}"
        candidate_dir.mkdir(exist_ok=True)

        src_dir = candidate_dir / "src"
        (src_dir / "EvoDestroy").mkdir(parents=True, exist_ok=True)
        (src_dir / "Perturbation").mkdir(parents=True, exist_ok=True)

        classes_dir = candidate_dir / "classes"
        classes_dir.mkdir(exist_ok=True)

        # Write LLM strategy code
        strategy_file = src_dir / "EvoDestroy" / f"{strategy_class}.java"
        with open(strategy_file, 'w') as f:
            f.write(strategy_code)

        # Generate wrapper
        wrapper_code = self.generate_wrapper(strategy_class, candidate_id)
        wrapper_class = f"EvoPlugin_Gen{candidate_id:04d}"
        wrapper_file = src_dir / "Perturbation" / f"{wrapper_class}.java"
        with open(wrapper_file, 'w') as f:
            f.write(wrapper_code)

        # Compile
        compile_log = candidate_dir / "compile.log"
        result = subprocess.run([
            "javac",
            "-cp", str(self.ails_jar),
            "-d", str(classes_dir),
            str(strategy_file),
            str(wrapper_file)
        ], capture_output=True, text=True)

        # Save compile log
        with open(compile_log, 'w') as f:
            f.write(result.stdout + result.stderr)

        if result.returncode != 0:
            print(f"[COMPILE ERROR] Candidate {candidate_id} failed to compile")
            print(f"See: {compile_log}")
            return None

        # Package JAR
        jar_file = candidate_dir / "plugin.jar"
        subprocess.run([
            "jar", "cf", str(jar_file),
            "-C", str(classes_dir), "."
        ], capture_output=True)

        if not jar_file.exists():
            print(f"[JAR ERROR] Failed to create JAR for candidate {candidate_id}")
            return None

        # Save metadata
        metadata = {
            "candidate_id": candidate_id,
            "parent_id": parent_id,
            "mutation_type": mutation_type,
            "strategy_class": strategy_class,
            "wrapper_class": wrapper_class,
            "code_hash": code_hash,
            "timestamp": datetime.now().isoformat(),
            "jar_path": str(jar_file),
            "candidate_dir": str(candidate_dir)
        }

        metadata_file = candidate_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Update cache
        self.cache[code_hash] = metadata
        self._save_cache()

        print(f"[COMPILED] Candidate {candidate_id} -> {jar_file}")
        return metadata

    def get_candidate_info(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a candidate by ID."""
        candidate_dir = self.candidates_dir / f"gen_{candidate_id:04d}"
        metadata_file = candidate_dir / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file) as f:
                return json.load(f)
        return None

    def update_evaluation_results(self,
                                   candidate_id: int,
                                   eval_results: list,
                                   fitness: float,
                                   base_fitness: float,
                                   generation: int = 0) -> bool:
        """
        Update candidate metadata with evaluation results.

        Args:
            candidate_id: Candidate ID
            eval_results: List of evaluation results per instance
            fitness: Final fitness (with penalty)
            base_fitness: Base fitness (without penalty)
            generation: Generation when evaluated

        Returns:
            True if update successful
        """
        candidate_dir = self.candidates_dir / f"gen_{candidate_id:04d}"
        metadata_file = candidate_dir / "metadata.json"

        if not metadata_file.exists():
            return False

        with open(metadata_file) as f:
            metadata = json.load(f)

        # Add evaluation data
        metadata["evaluation"] = {
            "generation": generation,
            "fitness": fitness,
            "fitness_pct": fitness * 100,  # For readability
            "base_fitness": base_fitness,
            "base_fitness_pct": base_fitness * 100,
            "num_instances": len(eval_results),
            "instances": []
        }

        for result in eval_results:
            metadata["evaluation"]["instances"].append({
                "name": result.get("instance", "unknown"),
                "warmstart_cost": result.get("warmstart_cost", 0),
                "final_cost": result.get("final_cost", 0),
                "improvement": result.get("improvement", 0),
                "improvement_pct": result.get("improvement", 0) * 100,
                "runtime": result.get("runtime", 0),
                "success": result.get("success", False)
            })

        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Update cache
        code_hash = metadata.get("code_hash")
        if code_hash and code_hash in self.cache:
            self.cache[code_hash] = metadata
            self._save_cache()

        return True

    def list_candidates(self) -> list:
        """List all compiled candidates."""
        candidates = []
        for candidate_dir in sorted(self.candidates_dir.glob("gen_*")):
            metadata_file = candidate_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    candidates.append(json.load(f))
        return candidates
