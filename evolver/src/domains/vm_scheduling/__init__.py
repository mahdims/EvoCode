"""
VM Scheduling domain plugin for EvoCode.
Importing this module auto-registers "vm_scheduling" with DomainPluginRegistry.
"""

from .plugin import VmSchedulingPlugin  # noqa: F401  triggers registration
