"""
Domains — Problem-Specific Plugin Implementations

Importing this package auto-registers all built-in domains with
DomainPluginRegistry so they are available by name in config.
"""

from . import ails_vrp        # noqa: F401  triggers DomainPluginRegistry.register("ails_vrp", ...)
from . import vm_scheduling   # noqa: F401  triggers DomainPluginRegistry.register("vm_scheduling", ...)
