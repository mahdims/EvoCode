"""
evaluator_stub — Backward-Compatibility Shim

The AILS evaluation harness has moved to:
  domains/ails_vrp/evaluator_stub.py

This shim re-exports the Evaluator class so that any existing code that does
  from evaluator_stub import Evaluator
continues to work without modification.
"""

from domains.ails_vrp.evaluator_stub import Evaluator  # noqa: F401
