"""
VM Scheduling Builder

Compiles LLM-generated TenantPlugin Java code into plugin JARs that can be
loaded by com.vmscheduling.Main via Class.forName().
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from building.base_builder import BaseBuilder
from .templates import (
    VM_CONSTRAINTS,
    VM_PROBLEM_DESCRIPTION,
    VM_DATA_STRUCTURES,
    get_vm_initial_seeds,
)


class VmSchedulingBuilder(BaseBuilder):
    """Builds TenantPlugin JARs from LLM-generated Java source code.

    Handles:
    - Extracting package.ClassName from Java source
    - Compiling against vmscheduling.jar
    - Packaging compiled classes into a candidate JAR
    """

    def __init__(self, vm_scheduling_jar: str):
        """
        Args:
            vm_scheduling_jar: Path to vm-scheduling-1.0-SNAPSHOT.jar
        """
        self.vm_scheduling_jar = Path(vm_scheduling_jar)

    # ------------------------------------------------------------------
    # BaseBuilder interface
    # ------------------------------------------------------------------

    def extract_entry_point(self, source_code: str) -> Optional[str]:
        """Return fully-qualified class name (package.ClassName)."""
        return self._extract_fqn(source_code)

    def build(self,
              source_code: str,
              candidate_id: int,
              candidate_dir: str) -> Optional[Dict[str, Any]]:
        """Compile TenantPlugin subclass into a candidate JAR.

        Returns:
            {"artifact_path": str, "entry_point": str, "class_name": str}
            or None on failure.
        """
        candidate_dir = Path(candidate_dir)

        fqn = self._extract_fqn(source_code)
        if not fqn:
            logger.warning(f"[VM BUILD] Could not extract class name from code")
            return None

        # class_name is the simple name; package is the rest
        parts = fqn.rsplit(".", 1)
        class_name = parts[-1]
        package = parts[0] if len(parts) > 1 else ""

        # Create directory structure
        src_dir = candidate_dir / "src"
        if package:
            pkg_dir = src_dir / package.replace(".", "/")
        else:
            pkg_dir = src_dir
        pkg_dir.mkdir(parents=True, exist_ok=True)

        classes_dir = candidate_dir / "classes"
        classes_dir.mkdir(exist_ok=True)

        # Write source
        source_file = pkg_dir / f"{class_name}.java"
        source_file.write_text(source_code, encoding="utf-8")

        # Compile
        compile_log = candidate_dir / "compile.log"
        result = subprocess.run(
            [
                "javac",
                "-cp", str(self.vm_scheduling_jar),
                "-d", str(classes_dir),
                str(source_file),
            ],
            capture_output=True,
            text=True,
        )
        compile_log.write_text(result.stdout + result.stderr, encoding="utf-8")

        if result.returncode != 0:
            logger.warning(f"[VM BUILD] Compilation failed for candidate {candidate_id}")
            logger.warning(f"[VM BUILD] See: {compile_log}")
            return None

        # Package JAR
        jar_file = candidate_dir / "plugin.jar"
        subprocess.run(
            ["jar", "cf", str(jar_file), "-C", str(classes_dir), "."],
            capture_output=True,
        )

        if not jar_file.exists():
            logger.warning(f"[VM BUILD] JAR creation failed for candidate {candidate_id}")
            return None

        logger.debug(f"[VM BUILD] Compiled candidate {candidate_id} -> {jar_file} ({fqn})")
        return {
            "artifact_path": str(jar_file),
            "entry_point": fqn,
            "class_name": class_name,
        }

    def get_source_path(self,
                        candidate_dir: Path,
                        metadata: Dict[str, Any]) -> Optional[Path]:
        """Return path to Java source for resume."""
        fqn = metadata.get("entry_point", "")
        if not fqn:
            return None
        parts = fqn.rsplit(".", 1)
        class_name = parts[-1]
        package = parts[0] if len(parts) > 1 else ""
        pkg_path = package.replace(".", "/") if package else ""
        source = candidate_dir / "src" / pkg_path / f"{class_name}.java"
        return source if source.exists() else None

    def get_llm_context(self) -> Dict[str, Any]:
        """Return VM Scheduling domain context for LLM prompts."""
        return {
            "constraints": VM_CONSTRAINTS,
            "problem_description": VM_PROBLEM_DESCRIPTION,
            "data_structures": VM_DATA_STRUCTURES,
            "language": "java",
            "initial_seeds": get_vm_initial_seeds(),
            "mutation_guidance": (
                "Focus on improving incremental delta projections (Ruin/Recreate methods). "
                "Try alternative state representations: arrays vs maps, different grouping strategies. "
                "Explore different penalty weighting between A, B, C constraints."
            ),
            "crossover_guidance": (
                "Preserve the state tracking pattern of the elite parent (update methods). "
                "Explicitly take ~75% from the elite parent's update() and copy() logic."
            ),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fqn(java_code: str) -> Optional[str]:
        """Extract fully-qualified class name (package.ClassName) from Java source."""
        # Extract package
        pkg_match = re.search(r'^\s*package\s+([\w.]+)\s*;', java_code, re.MULTILINE)
        package = pkg_match.group(1) if pkg_match else ""

        # Extract class name (must extend TenantPlugin)
        cls_match = re.search(
            r'public\s+class\s+(\w+)\s+extends\s+TenantPlugin', java_code
        )
        if not cls_match:
            # Fallback: any public class
            cls_match = re.search(r'public\s+class\s+(\w+)', java_code)
        if not cls_match:
            return None

        class_name = cls_match.group(1)
        return f"{package}.{class_name}" if package else class_name
