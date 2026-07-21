"""Unit tests for plugin SDK"""

from backend.plugins.base import (
    Plugin, PluginMeta, PluginRegistry, AgentPlugin, ToolPlugin
)


class SimplePlugin(Plugin):
    meta = PluginMeta(
        name="test_plugin",
        version="1.0.0",
        description="A test plugin",
        author="Test",
    )

    def activate(self):
        return True

    def deactivate(self):
        return True


class TestPluginRegistry:
    def test_register_plugin(self):
        registry = PluginRegistry()
        plugin = SimplePlugin()
        result = registry.register(plugin)
        assert result is True

    def test_list_plugins(self):
        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin)
        plugins = registry.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "test_plugin"

    def test_unregister_plugin(self):
        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin)
        result = registry.unregister("test_plugin")
        assert result is True
        assert registry.get_plugin("test_plugin") is None

    def test_get_plugin(self):
        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin)
        assert registry.get_plugin("test_plugin") is plugin

    def test_register_hook(self):
        registry = PluginRegistry()
        called = []
        registry.register_hook("test_hook", lambda x: called.append(x))
        registry.trigger_hook("test_hook", "data")
        assert called == ["data"]


class TestPluginTypes:
    def test_agent_plugin(self):
        class MyAgent(AgentPlugin):
            meta = PluginMeta(name="my_agent", version="1.0.0", description="test", plugin_type="agent")
            def activate(self): return True
            def deactivate(self): return True
            def get_agent_class(self): return None

        plugin = MyAgent()
        assert plugin.meta.plugin_type == "agent"

    def test_tool_plugin(self):
        class MyTool(ToolPlugin):
            meta = PluginMeta(name="my_tool", version="1.0.0", description="test", plugin_type="tool")
            def activate(self): return True
            def deactivate(self): return True
            def get_tools(self): return []

        plugin = MyTool()
        assert plugin.meta.plugin_type == "tool"
