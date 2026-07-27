"""Auto-discovers BaseAgent subclasses under agents/ and instantiates the
ones present in config.yaml. Adding a new provider is drop-a-file only:
no changes needed here.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil

import agents as agents_package
from agents.base import BaseAgent
from core.config import AppConfig
from core.logger import get_logger

logger = get_logger(__name__)


def discover_agent_classes() -> dict[str, type[BaseAgent]]:
    classes: dict[str, type[BaseAgent]] = {}
    for _, module_name, _ in pkgutil.iter_modules(agents_package.__path__):
        if module_name in ("base", "registry") or module_name.startswith("_"):
            continue
        module = importlib.import_module(f"agents.{module_name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseAgent) and obj is not BaseAgent and obj.__module__ == module.__name__:
                classes[obj.name] = obj
    return classes


def build_agents(config: AppConfig) -> list[BaseAgent]:
    classes = discover_agent_classes()
    instances: list[BaseAgent] = []
    for agent_name, agent_cfg in config.agents.items():
        cls = classes.get(agent_name)
        if cls is None:
            logger.warning("No adapter class found for configured agent '%s' — skipping", agent_name)
            continue
        instances.append(cls(agent_cfg))

    missing = [name for name in classes if name not in config.agents]
    if missing:
        logger.debug("Adapters discovered but not present in config.yaml: %s", missing)

    return instances
