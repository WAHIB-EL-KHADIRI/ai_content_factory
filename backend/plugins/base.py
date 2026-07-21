"""Plugin SDK - extensible plugin system"""

import importlib
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class PluginMeta:
    name: str
    version: str
    description: str
    author: str = ""
    plugin_type: str = "general"
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    meta: PluginMeta

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    def activate(self) -> bool:
        pass

    @abstractmethod
    def deactivate(self) -> bool:
        pass

    def get_config_schema(self) -> Dict[str, Any]:
        return self.meta.config_schema

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True


class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_metas: Dict[str, PluginMeta] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, plugin: Plugin) -> bool:
        try:
            name = plugin.meta.name
            if name in self._plugins:
                logger.warning(f"Plugin {name} already registered, replacing")

            if not plugin.validate_config(plugin.config):
                logger.error(f"Plugin {name} config validation failed")
                return False

            success = plugin.activate()
            if not success:
                logger.error(f"Plugin {name} activation failed")
                return False

            self._plugins[name] = plugin
            self._plugin_metas[name] = plugin.meta
            logger.info(f"Plugin {name} v{plugin.meta.version} registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False

    def unregister(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin is None:
            return False

        try:
            plugin.deactivate()
            del self._plugins[name]
            del self._plugin_metas[name]
            logger.info(f"Plugin {name} unregistered")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister plugin {name}: {e}")
            return False

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": meta.name,
                "version": meta.version,
                "description": meta.description,
                "author": meta.author,
                "type": meta.plugin_type,
                "active": meta.name in self._plugins,
            }
            for meta in self._plugin_metas.values()
        ]

    def register_hook(self, hook_name: str, callback: Callable):
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        results = []
        for callback in self._hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_name} callback failed: {e}")
        return results


class PluginLoader:
    def __init__(self, registry: PluginRegistry):
        self.registry = registry

    def load_from_module(self, module_path: str) -> bool:
        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, "Plugin", None)

            if plugin_class and issubclass(plugin_class, Plugin):
                plugin = plugin_class()
                return self.registry.register(plugin)

            logger.error(f"No valid Plugin class found in {module_path}")
            return False

        except ImportError as e:
            logger.error(f"Failed to import plugin module {module_path}: {e}")
            return False

    def load_from_directory(self, directory: str) -> int:
        import os
        loaded = 0

        if not os.path.isdir(directory):
            return 0

        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and os.path.exists(
                os.path.join(item_path, "__init__.py")
            ):
                try:
                    if self.load_from_module(item_path.replace(os.sep, ".")):
                        loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load plugin from {item_path}: {e}")

        return loaded


class AgentPlugin(Plugin):
    meta = PluginMeta(
        name="agent_plugin_base",
        version="1.0.0",
        description="Base class for agent plugins",
        plugin_type="agent",
    )

    def get_agent_class(self):
        raise NotImplementedError

    def activate(self) -> bool:
        return True

    def deactivate(self) -> bool:
        return True


class ToolPlugin(Plugin):
    meta = PluginMeta(
        name="tool_plugin_base",
        version="1.0.0",
        description="Base class for tool plugins",
        plugin_type="tool",
    )

    def get_tools(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def activate(self) -> bool:
        return True

    def deactivate(self) -> bool:
        return True


class IntegrationPlugin(Plugin):
    meta = PluginMeta(
        name="integration_plugin_base",
        version="1.0.0",
        description="Base class for integration plugins",
        plugin_type="integration",
    )

    def get_connector(self):
        raise NotImplementedError

    def activate(self) -> bool:
        return True

    def deactivate(self) -> bool:
        return True
