"""Mapping profile for agent-host application.

Configures AutoMapper-style mappings by discovering classes decorated with
@map_to or @map_from in specified modules.
"""

import inspect

from neuroglia.core.module_loader import ModuleLoader
from neuroglia.core.type_finder import TypeFinder
from neuroglia.mapping.mapper import MappingProfile


class Profile(MappingProfile):
    """Application mapping profile.

    Scans configured modules for classes with @map_to or @map_from decorators
    and registers them with the mapper.
    """

    def __init__(self):
        super().__init__()
        modules = [
            "application.commands",
            "application.queries",
            "domain.entities",  # AgentState -> AgentDto mapping
            "integration.models",
        ]
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            for type_ in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and (hasattr(cls, "__map_from__") or hasattr(cls, "__map_to__")),
            ):
                map_from = getattr(type_, "__map_from__", None)
                map_to = getattr(type_, "__map_to__", None)
                if map_from is not None:
                    self.create_map(map_from, type_)
                if map_to is not None:
                    self.create_map(type_, map_to)
