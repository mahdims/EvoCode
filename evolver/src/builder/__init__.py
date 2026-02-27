"""
Builder Package — Backward-Compatibility Shim

The builder abstractions now live in:
  core.base_builder        → BaseBuilder
  domains.ails_vrp.builder → AILSBuilder

This shim re-exports them so that existing imports of the form
  from builder import BaseBuilder, AILSBuilder
continue to work without modification.
"""

from core.base_builder import BaseBuilder
from domains.ails_vrp.builder import AILSBuilder
from domains.ails_vrp.templates import get_ails_initial_seeds
