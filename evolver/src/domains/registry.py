"""
Domain Plugin Registry

A simple class-registry that maps domain names (strings) to BaseDomainPlugin
subclasses, enabling config-driven domain instantiation.

Usage::

    # In a plugin module (runs once on import):
    DomainPluginRegistry.register("ails_vrp", AILSVRPPlugin)

    # In evo_agent.py:
    plugin = DomainPluginRegistry.create("ails_vrp", config)
    evolution = EvolutionLoop(domain_plugin=plugin, ...)
"""

from typing import Any, Dict, List, Type

from .base_domain_plugin import BaseDomainPlugin


class DomainPluginRegistry:
    """Registry mapping domain name strings to BaseDomainPlugin subclasses."""

    _registry: Dict[str, Type[BaseDomainPlugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_class: Type[BaseDomainPlugin]) -> None:
        """Register a plugin class under the given name.

        Args:
            name: Domain identifier (e.g. "ails_vrp")
            plugin_class: A BaseDomainPlugin subclass (not an instance)
        """
        if not (isinstance(plugin_class, type)
                and issubclass(plugin_class, BaseDomainPlugin)):
            raise TypeError(f"{plugin_class!r} is not a BaseDomainPlugin subclass")
        cls._registry[name] = plugin_class

    @classmethod
    def create(cls, name: str, config: Dict[str, Any] = None) -> BaseDomainPlugin:
        """Instantiate a registered plugin by name.

        Args:
            name: Domain identifier
            config: Full application config dict passed to the plugin constructor

        Returns:
            A BaseDomainPlugin instance

        Raises:
            ValueError: If the domain name is not registered
        """
        if name not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Unknown domain: '{name}'. "
                f"Available domains: {available}. "
                f"Make sure the domain's module has been imported."
            )
        return cls._registry[name](config=config or {})

    @classmethod
    def list_domains(cls) -> List[str]:
        """Return the names of all registered domains."""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Return True if the domain name is registered."""
        return name in cls._registry
