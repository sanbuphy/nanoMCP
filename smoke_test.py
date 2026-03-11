import importlib.util
import sys
import types
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import SimpleNamespace
from typing import cast


REPO_ROOT = Path(__file__).resolve().parent


def load_module(relative_path: str, module_name: str):
    fake_openai = types.ModuleType("openai")

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=None))

    setattr(fake_openai, "OpenAI", FakeOpenAI)
    previous_openai = sys.modules.get("openai")
    sys.modules["openai"] = fake_openai
    try:
        spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative_path)
        assert spec is not None
        module = importlib.util.module_from_spec(cast(ModuleSpec, spec))
        loader = spec.loader
        assert loader is not None
        loader.exec_module(module)
        return module
    finally:
        if previous_openai is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = previous_openai


def make_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def check_custom_registry() -> None:
    import nanomcp

    registry = nanomcp.build_default_registry()
    initialized = registry.initialize_all()
    assert "math" in initialized
    assert "utility" in initialized
    assert "meta" in initialized
    tools = registry.list_tools()
    qualified_names = {tool["qualified_name"] for tool in tools}
    assert "math.add" in qualified_names
    assert "utility.echo" in qualified_names
    result = registry.call_tool("math.add", {"a": 2, "b": 8})
    assert result["ok"] is True
    assert result["result"]["content"][0]["text"] == "10.0"


def check_official_registry() -> None:
    import officialmcp

    registry = officialmcp.build_official_fake_registry()
    tools = registry.list_tools()
    qualified_names = {tool["qualified_name"] for tool in tools}
    assert "math.add" in qualified_names
    assert "utility.search" in qualified_names
    result = registry.call_tool("meta.version", {"target": "mcp"})
    assert result["ok"] is True
    assert result["result"]["content"][0]["text"] == "mcp:0.1.0"


def check_agents() -> None:
    agent_custom = load_module("agent.py", "nanomcp_agent_custom")
    agent_official = load_module("agent-official.py", "nanomcp_agent_official")

    def fake_create_custom(*, model, messages, tools):
        if len(messages) <= 3:
            return make_response(
                SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="tc-1",
                            function=SimpleNamespace(
                                name="call_mcp_tool",
                                arguments='{"qualified_name":"math.add","arguments":{"a":3,"b":4}}',
                            ),
                        )
                    ],
                )
            )
        return make_response(SimpleNamespace(content="7", tool_calls=[]))

    setattr(
        agent_custom,
        "client",
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create_custom))),
    )
    result_custom = agent_custom.run_agent("计算 3+4", max_iterations=2)
    assert result_custom == "7"

    def fake_create_official(*, model, messages, tools):
        if len(messages) <= 3:
            return make_response(
                SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="tc-1",
                            function=SimpleNamespace(
                                name="call_mcp_tool",
                                arguments='{"qualified_name":"math.add","arguments":{"a":5,"b":2}}',
                            ),
                        )
                    ],
                )
            )
        return make_response(SimpleNamespace(content="7", tool_calls=[]))

    setattr(
        agent_official,
        "client",
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create_official))),
    )
    result_official = agent_official.run_agent("计算 5+2", max_iterations=2)
    assert result_official == "7"


def check_real_mcp_example_file() -> None:
    agent_real = load_module("agent_official_mcp.py", "nanomcp_agent_real_mcp")
    servers = agent_real.list_real_mcp_servers()
    assert "context7" in servers
    assert "tavily" in servers
    install_examples = agent_real.get_mcp_install_examples()
    assert "@upstash/context7-mcp" in install_examples
    assert "tavily-mcp" in install_examples
    call_example = agent_real.call_real_mcp_example("tavily", "nano mcp")
    assert '"ok": true' in call_example


def main() -> None:
    check_custom_registry()
    check_official_registry()
    check_agents()
    check_real_mcp_example_file()
    print("smoke test passed")


if __name__ == "__main__":
    main()
