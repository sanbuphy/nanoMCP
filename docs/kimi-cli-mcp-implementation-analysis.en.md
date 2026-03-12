# In-depth dismantling of Kimi CLI’s MCP (Model Context Protocol) implementation mechanism

> English translation generated from `./kimi-cli-mcp-implementation-analysis.md`


> **Project address**: [https://github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)
>
> **Analysis version**: v1.3
>
> **Analysis time**: 2026-03-11

**Related Documents**:
- [Official MCP Introduction](./official-mcp-introduction.en.md) - Basic concepts and principles of MCP protocol
- [Gemini CLI MCP Implementation](./gemini-cli-mcp-implementation-analysis.en.md) - Implementation comparison based on TypeScript SDK

## Table of contents

- 1. Project Overview
- 2. MCP Architecture Overview
- 3. Core Component Breakdown
- 4. End-to-End Workflow
- 5. Key Technical Implementations
- 6. Security Mechanisms
- 7. Usage Examples
- 8. Summary and Takeaways

---

## 1. Project Overview

### 1.1 What is Kimi CLI?

Kimi Code CLI is a terminal AI assistant developed by Moonshot AI. It not only helps you complete software development tasks, but also serves as a powerful shell environment. Kimi CLI supports functions such as reading and editing code, executing shell commands, searching web pages, and more.

### 1.2 What is MCP?

**MCP (Model Context Protocol)** is an open protocol that allows AI models to safely interact with external tools and data sources. Through MCP, Kimi CLI can:

- Access a specific API or database
- Control browsers or other applications
- Integrate with third-party services (GitHub, Linear, Notion, etc.)
- Expand the boundaries of AI capabilities

### 1.3 Technology stack

- **Language**: Python 3.12+
- **MCP client**: `fastmcp==2.12.5`
- **Configuration Management**: Pydantic
- **Asynchronous Framework**: asyncio
- **CLI Framework**: Typer

---

## 2. MCP architecture overview

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User interaction layer │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│ │ CLI Commands │ │ ACP Protocol │ │ Web UI │ │
│ │ kimi mcp │ │ IDE integration │ │ Interface │ │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│Configure management layer │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ ~/.kimi/mcp.json (default configuration) │ │
│ │ --mcp-config-file (custom configuration) │ │
│ │ --mcp-config (inline configuration) │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Core processing layer │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ KimiToolset  │  │  MCPTool     │  │ MCPServerInfo│          │
│ │ Tool Set Management │ │ Tool Encapsulation │ │ Connection Status │ │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ MCP Client Layer │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  fastmcp.Client                                         │     │
│ │ - stdio transfer (local process) │ │
│ │ - http transport (remote server) │ │
│ │ - OAuth Authentication │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ External MCP Server Layer │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│ │context7 │ │ Linear │ │Notion │ │Custom... │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```
### 2.2 Core code structure

```
src/kimi_cli/
├── cli/
│ └── mcp.py # MCP CLI command implementation
├── soul/
│ └── toolset.py # Toolset core logic
├── acp/
│ └── mcp.py # MCP adaptation of ACP protocol
├── config.py # Configuration definition
└── exception.py #Exception definition

Main document responsibilities:
- cli/mcp.py: Provides kimi mcp command line tool
- soul/toolset.py: Tool loading, management, and calling core logic
- acp/mcp.py: bridging of ACP protocol and MCP
```

---

## 3. Disassembly of core components

### 3.1 Configuration management (`cli/mcp.py`)

#### Configuration file structure

MCP configuration is stored in `~/.kimi/mcp.json` and supports two transmission modes:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "transport": "http",
      "headers": {
        "CONTEXT7_API_KEY": "your-key"
      },
      "auth": "oauth"
    },
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest"],
      "env": {
        "NODE_ENV": "production"
      },
      "transport": "stdio"
    }
  }
}
```
#### Configuration loading process

```python
# cli/mcp.py: _load_mcp_config()

def _load_mcp_config() -> dict[str, Any]:
    """Load MCP configuration from global configuration file"""
    mcp_file = get_global_mcp_config_file()  # ~/.kimi/mcp.json

    if not mcp_file.exists():
        return {"mcpServers": {}}

    # 1. Read and parse JSON
    config = json.loads(mcp_file.read_text(encoding="utf-8"))

    # 2. Use Pydantic to verify the configuration format
    try:
        MCPConfig.model_validate(config)
    except ValidationError as e:
        raise typer.BadParameter(f"Invalid MCP config: {e}")

    return config
```
#### CLI command implementation

```bash
#Add HTTP server
kimi mcp add --transport http context7 https://mcp.context7.com/mcp \
  --header "CONTEXT7_API_KEY: your-key"

#Add OAuth authentication server
kimi mcp add --transport http --auth oauth linear https://mcp.linear.app/mcp

# Add stdio server
kimi mcp add --transport stdio chrome-devtools -- npx chrome-devtools-mcp@latest

# List all servers
kimi mcp list

# Test connection
kimi mcp test context7

#OAuth authorization
kimi mcp auth linear

# Remove server
kimi mcp remove context7
```
**Code implementation** (`cli/mcp.py:83-193`):

```python
@cli.command("add")
def mcp_add(
    name: str,
    server_args: list[str] | None,
    transport: Literal["stdio", "http"] = "stdio",
    env: list[str] | None = None,
    header: list[str] | None = None,
    auth: str | None = None,
):
    """Add MCP server"""
    config = _load_mcp_config()

    if transport == "stdio":
        # stdio mode: command line tool
        command, *command_args = server_args
        server_config = {
            "command": command,
            "args": command_args,
            "env": _parse_key_value_pairs(env, "env")
        }
    else:
        # http mode: remote server
        server_config = {
            "url": server_args[0],
            "transport": "http",
            "headers": _parse_key_value_pairs(header, "header", separator=":"),
        }
        if auth:
            server_config["auth"] = auth

    config["mcpServers"][name] = server_config
    _save_mcp_config(config)
```

---

### 3.2 Toolset management (`soul/toolset.py`)

#### KimiToolset Class

**Responsibilities**: Manage all tools (built-in tools + MCP tools)

```python
class KimiToolset:
    def __init__(self) -> None:
        self._tool_dict: dict[str, ToolType] = {} # All tool dictionaries
        self._mcp_servers: dict[str, MCPServerInfo] = {} # MCP server
        self._mcp_loading_task: asyncio.Task[None] | None = None

    def add(self, tool: ToolType) -> None:
        """Add tools to toolset"""
        self._tool_dict[tool.name] = tool

    def find(self, tool_name: str) -> ToolType | None:
        """Find tool"""
        return self._tool_dict.get(tool_name)

    def handle(self, tool_call: ToolCall) -> HandleResult:
        """Handling tool calls"""
        tool = self._tool_dict.get(tool_call.function.name)
        if not tool:
            return ToolResult(return_value=ToolNotFoundError(tool_name))

        # Asynchronous calling tool
        async def _call():
            ret = await tool.call(arguments)
            return ToolResult(tool_call_id=tool_call.id, return_value=ret)

        return asyncio.create_task(_call())
```
#### MCP server information

```python
@dataclass
class MCPServerInfo:
    """MCP server connection information"""
    status: Literal["pending", "connecting", "connected", "failed", "unauthorized"]
    client: fastmcp.Client[Any] # fastmcp client
    tools: list[MCPTool[Any]] # List of tools provided by this server
```
**State Machine**:

```
pending (initial state)
   ↓
connecting (start connecting)
   ↓
   ├─→ connected (connection successful, tool loaded)
   ├─→ failed (connection failed)
   └─→ unauthorized (OAuth unauthorized)
```

---

### 3.3 MCP tool package (`soul/toolset.py`)

#### MCPTool class

**Responsibility**: Encapsulate MCP tools into tools callable by Kimi CLI

```python
class MCPTool[T: ClientTransport](CallableTool):
    def __init__(
        self,
        server_name: str, # Server name
        mcp_tool: mcp.Tool, # MCP original tool
        client: fastmcp.Client[T], # fastmcp client
        *,
        runtime: Runtime, # runtime context
        **kwargs: Any,
    ):
        # Call parent class initialization
        super().__init__(
            name=mcp_tool.name,
            description=(
                f"This is an MCP (Model Context Protocol) tool "
                f"from MCP server `{server_name}`.\n\n"
                f"{mcp_tool.description or 'No description provided.'}"
            ),
            parameters=mcp_tool.inputSchema,  # JSON Schema
        )
        self._mcp_tool = mcp_tool
        self._client = client
        self._runtime = runtime
        self._timeout = timedelta(
            milliseconds=runtime.config.mcp.client.tool_call_timeout_ms
        )
        self._action_name = f"mcp:{mcp_tool.name}"
```
#### Tool calling process

```python
async def __call__(self, **kwargs) -> ToolReturnValue:
    # 1. User approval
    description = f"Call MCP tool `{self._mcp_tool.name}`."
    if not await self._runtime.approval.request(
        self.name, self._action_name, description
    ):
        return ToolRejectedError()

    # 2. Call MCP server
    try:
        async with self._client as client:
            result = await client.call_tool(
                self._mcp_tool.name,
                kwargs,
                timeout=self._timeout,
                raise_on_error=False
            )
            return convert_mcp_tool_result(result)
    except Exception as e:
        # 3. Error handling
        if "timeout" in str(e).lower():
            return ToolError(
                message=f"Timeout while calling MCP tool `{self._mcp_tool.name}`",
                brief="Timeout"
            )
        raise
```

---

### 3.4 Configuration definition (`config.py`)

```python
class MCPClientConfig(BaseModel):
    """MCP Client Configuration"""
    tool_call_timeout_ms: int = 60000 # Tool call timeout (milliseconds)

class MCPConfig(BaseModel):
    """MCP Configuration"""
    client: MCPClientConfig = Field(
        default_factory=MCPClientConfig
    )

class Config(BaseModel):
    """Main configuration"""
    mcp: MCPConfig = Field(
        default_factory=MCPConfig,
        description="MCP configuration"
    )
```

---

## 4. Complete workflow

### 4.1 Startup flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User starts kimi │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Load configuration (app.py: KimiCLI.create) │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Loading source: │ │
│ │ • ~/.kimi/mcp.json (default) │ │
│ │ • --mcp-config-file <path> (specify file) │ │
│ │ • --mcp-config <json> (inline configuration) │ │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Verify configuration: │ │
│  │  MCPConfig.model_validate(config)                      │     │
│ │ Parse server configuration (stdio/http) │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Create Runtime and KimiToolset │
│  runtime = await Runtime.create(config, ...)                    │
│  toolset = runtime.toolset                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Load MCP tools (toolset.load_mcp_tools) │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ for each mcp_config:                                  │     │
│  │   for server_name, server_config in mcpServers:        │     │
│ │ 1. Create MCPServerInfo (status: pending) │ │
│ │ 2. Create fastmcp.Client │ │
│ │ 3. Check OAuth authorization status │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Connect to all servers asynchronously │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ asyncio.gather(*tasks)                                │     │
│  │   for each server:                                    │     │
│  │     status: pending → connecting                      │     │
│ │ ├─ Unauthorized → unauthorized │ │
│ │ └─ Authorized → Connect and get the tool list │ │
│ │ ├─ Success → Create MCPTool → Add to toolset │ │
│  │         │         → status: connected                 │     │
│ │ └─ failed → status: failed │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Display connection results │
│ • "mcp servers connected" (success) │
│ • "mcp authorization needed" │
│ • "mcp connection failed" │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. Wait for user input │
└─────────────────────────────────────────────────────────────────┘
```
### 4.2 Tool calling flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│ User input issues │
│ "Search Python MCP tutorial using context7" │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│AI analyzes and decides to call tools │
│Identification requires the use of context7_search tool │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Generate ToolCall │
│  {                                                              │
│    "id": "call_abc123",                                         │
│    "function": {                                                │
│      "name": "context7_search",                                 │
│      "arguments": {                                             │
│        "query": "Python MCP tutorial",                          │
│        "limit": 10                                              │
│      }                                                           │
│    }                                                             │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            toolset.handle(tool_call)                            │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Search tool: │ │
│  │    tool = toolset._tool_dict["context7_search"]        │     │
│  │                                                        │     │
│ │ 2. Analysis parameters: │ │
│  │    kwargs = json.loads(arguments)                     │     │
│  │                                                        │     │
│ │ 3. Asynchronous call: │ │
│  │    result = await tool.call(kwargs)                   │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              MCPTool.__call__(**kwargs)                         │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. User approval: │ │
│  │    await runtime.approval.request(                     │     │
│  │      "context7_search",                                │     │
│  │      "mcp:context7_search",                            │     │
│  │      "Call MCP tool `context7_search`"                 │     │
│  │    )                                                    │     │
│  │                                                        │     │
│  │  ┌────────────────────────────────────────────┐        │     │
│ │ │ A confirmation dialog box pops up: │ │ │
│  │  │ ┌──────────────────────────────────┐     │        │     │
│ │ │ │ MCP tool call is about to be executed │ │ │ │
│ │ │ │ Tools: context7_search │ │ │ │
│ │ │ │ Description: Search the web... │ │ │ │
│ │ │ │ [Allow] [Deny] │ │ │ │
│  │  │  └──────────────────────────────────┘     │        │     │
│  │  └────────────────────────────────────────────┘        │     │
│  │                                                        │     │
│ │ 2. Call the MCP server: │ │
│  │    async with client as client:                       │     │
│  │      result = await client.call_tool(                 │     │
│  │        "context7_search",                             │     │
│  │        kwargs,                                        │     │
│  │        timeout=60s                                    │     │
│  │      )                                                 │     │
│  │                                                        │     │
│ │ 3. Conversion result: │ │
│  │    return convert_mcp_tool_result(result)             │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│          convert_mcp_tool_result(result)                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ for part in result.content:                            │     │
│  │   if part.type == "text":                              │     │
│  │     content.append(ContentPart(text=part.text))        │     │
│  │   elif part.type == "image":                           │     │
│  │     content.append(ContentPart(image=part.data))       │     │
│  │   elif part.type == "resource":                        │     │
│  │     content.append(ContentPart(resource=...))          │     │
│  │                                                        │     │
│  │ if result.is_error:                                    │     │
│  │   return ToolError(output=content)                     │     │
│  │ else:                                                  │     │
│  │   return ToolOk(output=content)                        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ AI processes the results and returns them to the user │
└─────────────────────────────────────────────────────────────────┘
```
### 4.3 OAuth authorization flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Add OAuth server │
│  kimi mcp add --transport http --auth oauth linear \           │
│    https://mcp.linear.app/mcp                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Save the configuration to ~/.kimi/mcp.json │
│  {                                                              │
│    "mcpServers": {                                              │
│      "linear": {                                                │
│        "url": "https://mcp.linear.app/mcp",                    │
│        "transport": "http",                                     │
│        "auth": "oauth"                                          │
│      }                                                           │
│    }                                                             │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Execute authorization │
│  kimi mcp auth linear                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Open browser authorization │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Create fastmcp.Client │ │
│  │ 2. async with client as client:                       │     │
│  │ 3. await client.list_tools()                          │     │
│ │ → Trigger OAuth process │ │
│ │ → Open browser │ │
│ │ → User login and authorization │ │
│ │ → Token is saved to the file system │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Authorization successful │
│ ✓ Token has been saved, subsequent use does not require re-authorization │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Key technology implementation

### 5.1 Asynchronous concurrent loading

**Question**: How to efficiently load multiple MCP servers?

**Solution**: Use `asyncio.gather` to connect to all servers concurrently

```python
# soul/toolset.py: load_mcp_tools()

async def load_mcp_tools(self, mcp_configs, runtime, in_background=True):
    # 1. Create a connection task for each server
    tasks = [
        asyncio.create_task(_connect_server(server_name, server_info))
        for server_name, server_info in self._mcp_servers.items()
        if server_info.status == "pending"
    ]

    # 2. Execute all connections concurrently
    results = await asyncio.gather(*tasks) if tasks else []

    # 3. Collect failed servers
    failed_servers = {name: error for name, error in results if error is not None}

    if failed_servers:
        raise MCPRuntimeError(f"Failed to connect MCP servers: {failed_servers}")
```
**Advantages**:
- Multiple servers are connected at the same time without blocking startup
- Failure of a single server does not affect other servers
- Quick feedback on connection status

---

### 5.2 Background loading strategy

**Question**: The MCP server connection may be slow, how to avoid blocking user startup?

**Solution**: Support background loading

```python
# soul/toolset.py: load_mcp_tools()

async def load_mcp_tools(self, mcp_configs, runtime, in_background=True):
    async def _connect():
        # Connect to all servers
        ...

    if in_background:
        # Background loading, no blocking startup
        self._mcp_loading_task = asyncio.create_task(_connect())
    else:
        # Synchronously wait for loading to complete
        await _connect()

# Wait for loading to complete when you need to use the MCP tool
async def wait_for_mcp_tools(self) -> None:
    task = self._mcp_loading_task
    if task:
        await task
```
**User Experience**:
- Fast startup
- Show loading progress notification
- Completed silently in the background

---

### 5.3 Content type conversion

**Issue**: The content type returned by MCP is inconsistent with the Kimi CLI internal format

**Solution**: Unify conversion functions

```python
# soul/toolset.py: convert_mcp_tool_result()

def convert_mcp_tool_result(result: CallToolResult) -> ToolReturnValue:
    """Convert MCP tool results to Kimi tool return values"""
    content: list[ContentPart] = []

    # Traverse the content returned by MCP
    for part in result.content:
        content.append(convert_mcp_content(part))

    # Return different types depending on whether there is an error or not
    if result.is_error:
        return ToolError(
            output=content,
            message="Tool returned an error. The output may be error message",
            brief=""
        )
    else:
        return ToolOk(output=content)


# kosong/tooling/mcp.py: convert_mcp_content()

def convert_mcp_content(content) -> ContentPart:
    """Convert single MCP content"""
    if isinstance(content, mcp.TextContent):
        return ContentPart(text=content.text)
    elif isinstance(content, mcp.ImageContent):
        return ContentPart(image=content.data)
    elif isinstance(content, mcp.ResourceContents):
        return ContentPart(resource=...)
    else:
        raise ValueError(f"Unsupported content type: {type(content)}")
```

---

### 5.4 Timeout control

**Issue**: MCP server may be slow or unresponsive

**Solution**: Configure timeout + exception catching

```python
# soul/toolset.py: MCPTool.__call__()

async def __call__(self, **kwargs) -> ToolReturnValue:
    # Read timeout from configuration (default 60 seconds)
    self._timeout = timedelta(
        milliseconds=runtime.config.mcp.client.tool_call_timeout_ms
    )

    try:
        async with self._client as client:
            result = await client.call_tool(
                self._mcp_tool.name,
                kwargs,
                timeout=self._timeout, # Set timeout
                raise_on_error=False
            )
            return convert_mcp_tool_result(result)
    except Exception as e:
        #Catch timeout exception
        exc_msg = str(e).lower()
        if "timeout" in exc_msg or "timed out" in exc_msg:
            return ToolError(
                message=(
                    f"Timeout while calling MCP tool `{self._mcp_tool.name}`. "
                    "You may explain to the user that the timeout config is set too low."
                ),
                brief="Timeout"
            )
        raise
```
**Configuration** (`~/.kimi/config.yaml`):

```yaml
mcp:
  client:
    tool_call_timeout_ms: 60000 # 60 seconds
```

---

### 5.5 Error isolation

**Issue**: Failure of one MCP server should not affect other servers

**Solution**: Independent connection task + state management

```python
# soul/toolset.py: _connect_server()

async def _connect_server(
    server_name: str, server_info: MCPServerInfo
) -> tuple[str, Exception | None]:
    """Connect to a single server without affecting other servers"""
    if server_info.status != "pending":
        return server_name, None

    server_info.status = "connecting"

    try:
        async with server_info.client as client:
            # Get the tool list
            for tool in await client.list_tools():
                server_info.tools.append(
                    MCPTool(server_name, tool, client, runtime=runtime)
                )

            # Add to toolset
            for tool in server_info.tools:
                self.add(tool)

            server_info.status = "connected"
            logger.info(f"Connected MCP server: {server_name}")
            return server_name, None

    except Exception as e:
        # Log errors but do not throw exceptions
        logger.error(f"Failed to connect MCP server: {server_name}, error: {e}")
        server_info.status = "failed"
        return server_name, e
```

---

## 6. Security mechanism

### 6.1 User approval mechanism

**All MCP tool calls require user confirmation**

```python
# soul/toolset.py: MCPTool.__call__()

async def __call__(self, **kwargs) -> ToolReturnValue:
    description = f"Call MCP tool `{self._mcp_tool.name}`."

    # Request user approval
    if not await self._runtime.approval.request(
        self.name, # Tool name
        self._action_name, # Action name (mcp:xxx)
        description # description
    ):
        return ToolRejectedError()

    # Execute only after user approval
    ...
```
**Approval Interface**:

```
┌─────────────────────────────────────────┐
│ MCP tool call is about to be executed │
├─────────────────────────────────────────┤
│ Tool: context7_search │
│ Type: MCP Tool │
│                                         │
│ Description: │
│ Search the web using Context7 API...    │
│                                         │
│ Parameters: │
│ {                                       │
│   "query": "Python MCP tutorial",       │
│   "limit": 10                           │
│ }                                       │
│                                         │
│ [Allow] [Deny] [Always Allow] │
└─────────────────────────────────────────┘
```
### 6.2 YOLO mode

**Note**: Even in YOLO mode, MCP tools require approval

```python
# YOLO mode only affects built-in tools and does not affect MCP tools
# The documentation clearly states:
# "In YOLO mode, MCP tool operations will also be auto-approved.
#  It is recommended to use YOLO mode only when you fully trust the MCP server."
```
### 6.3 OAuth Token secure storage

```python
# fastmcp uses keyring to securely store OAuth tokens
from fastmcp.client.auth.oauth import FileTokenStorage

storage = FileTokenStorage(server_url=server_url)
tokens = await storage.get_tokens() # Read from secure storage
```
### 6.4 Prompt word injection protection

Content returned by MCP tools is tagged to help the AI ​​differentiate between tool output and user instructions:

```python
# The tool return content will be marked as "tool output"
# AI can recognize that this is not a user command
```
**Documentation Warning**:

> Content returned by MCP tools may contain malicious instructions that attempt to induce the AI ​​to perform dangerous operations.
> Kimi Code CLI tags tool return content to help AI distinguish tool output from user instructions.

**Suggestion**:
- Only use MCP servers from trusted sources
- Check whether the actions proposed by the AI are reasonable
- Maintain manual approvals for high-risk operations

---

## 7. Usage examples

### 7.1 Add Context7 search tool

```bash
# 1. Add Context7 HTTP server
kimi mcp add --transport http context7 https://mcp.context7.com/mcp \
  --header "CONTEXT7_API_KEY: your-api-key"

# 2. Test connection
kimi mcp test context7

# 3. List all servers
kimi mcp list

# 4. Start kimi
kimi

# 5. Search using Context7
> Search Python MCP tutorials using context7

# AI will call the context7_search tool and ask for your approval
# After approval, AI will display the search results
```
### 7.2 Add Linear integration

```bash
# 1. Add Linear OAuth server
kimi mcp add --transport http --auth oauth linear https://mcp.linear.app/mcp

# 2. Perform OAuth authorization
kimi mcp auth linear
# The browser will open, log in and authorize

# 3. Test connection
kimi mcp test linear

# 4. Use Linear tool
kimi

> List my Linear issues
> Create a new Linear issue: fix MCP connection timeout issue
```
### 7.3 Add local Chrome DevTools

```bash
# 1. Add stdio server
kimi mcp add --transport stdio chrome-devtools -- npx chrome-devtools-mcp@latest

# 2. Test connection
kimi mcp test chrome-devtools

# 3. Use Chrome DevTools
kimi

> Open your browser and visit https://github.com/MoonshotAI/kimi-cli
> Take a screenshot of the current page
```
### 7.4 Temporarily load configuration

```bash
#Load from file
kimi --mcp-config-file /path/to/custom-mcp.json

# Inline configuration
kimi --mcp-config '{
  "mcpServers": {
    "test": {
      "url": "https://test.mcp.server",
      "transport": "http"
    }
  }
}'
```

---

## 8. Summary and reflections

### 8.1 Architecture Highlights

1. **Standardized Design**
   - Fully compliant with MCP protocol specifications
   - Integrates with any MCP server
   - Configuration format compatible with other clients such as Claude Desktop

2. **Asynchronous Concurrency**
   - Multiple server concurrent connections
   - Background loading does not block startup
   - Efficient resource utilization

3. **Safety first**
   - All tool calls require approval
   - OAuth Token secure storage
   - Prompt word injection protection

4. **User Experience**
   - Clear command line interface
   - Real-time status notifications
   - Detailed error message

5. **Fault Tolerance**
   - Failure of a single server does not affect others
   - Perfect error handling
   - Timeout protection

### 8.2 Designs that can be learned from

1. **Layered Architecture**
   -Clear separation of CLI layer, configuration layer, core layer and client layer
   - Each layer has clear responsibilities and is easy to maintain

2. **Status Management**
   - State machine design of MCPServerInfo
   - Clear state transition logic

3. **Tool Encapsulation**
   - MCPTool unified encapsulation MCP tool
   - Hide underlying communication details

4. **Configuration Verification**
   - Verify configuration using Pydantic
   - Early detection of configuration errors

### 8.3 Room for improvement

1. **Tool Discovery**
   - Can add tool recommendation function
   - Recommend relevant MCP servers based on user behavior

2. **Performance Monitoring**
   - Record the response time of each server
   - Automatically adjust timeout configuration

3. **Caching mechanism**
   - Cache the call results of commonly used tools
   - Reduce duplicate requests

4. **Batch operation**
   -Support adding/removing servers in batches
   - Batch test connections

### 8.4 Applicable scenarios

Kimi CLI's MCP implementation is particularly suitable for the following scenarios:

1. **Development tool chain integration**
   - Integrates with GitHub, GitLab, Jira and more
   - Automated development process

2. **Data Analysis**
   - Connect to database MCP server
   - Perform SQL queries and analysis

3. **Content Creation**
   - Integrated search, translation and summarization tools
   - Improve creative efficiency

4. **Operation and Maintenance Automation**
   - Connect to monitoring and alarm systems
   - Automated operation and maintenance operations

---

## 9. The complete code flow of LLM calling MCP tool

This section shows in detail the complete code link of how LLM calls the MCP tool in Kimi CLI, from the LLM generation tool call to the final execution of the MCP server call.

### 9.1 Core call link

#### kosong.step - The core engine called by LLM tools

**Location**: `packages/kosong/src/kosong/__init__.py:104-180`

```python
async def step(
    chat_provider: ChatProvider, # LLM provider (such as Kimi API)
    system_prompt: str, # system prompt word
    toolset: Toolset, # Toolset (including MCP tools)
    history: Sequence[Message], #Conversation history
    *,
    on_message_part: Callback[[StreamedMessagePart], None] | None = None, # Streaming callback
    on_tool_result: Callable[[ToolResult], None] | None = None, # Tool result callback
) -> "StepResult":
    """
    Run an agent "step"

    Core process:
    1. Call LLM to generate a response (may include tool calls)
    2. Handle tool calls (via toolset.handle)
    3. Return the result (Future containing the tool result)
    """
    tool_calls: list[ToolCall] = []
    tool_result_futures: dict[str, ToolResultFuture] = {}

    # Tool call callback
    async def on_tool_call(tool_call: ToolCall):
        """
        Triggered when the LLM generation tool is called

        Args:
            tool_call: tool call generated by LLM
                {
                    "id": "call_123",
                    "function": {
                        "name": "mcp_context7_search",
                        "arguments": '{"query": "..."}'
                    }
                }
        """
        tool_calls.append(tool_call)

        # Core: Distribute tool calls to toolset
        # toolset.handle() will:
        # 1. Find tools (including MCP tools)
        # 2. Parse parameters
        # 3. Asynchronous execution tool
        result = toolset.handle(tool_call)

        if isinstance(result, ToolResult):
            #Results returned synchronously (such as tool not found, parameter parsing failed)
            future = ToolResultFuture()
            future.add_done_callback(future_done_callback)
            future.set_result(result)
            tool_result_futures[tool_call.id] = future
        else:
            # Tasks executed asynchronously (actual tool calls)
            result.add_done_callback(future_done_callback)
            tool_result_futures[tool_call.id] = result

    try:
        # Call generate, passing in the tool definition and tool call callback
        result = await generate(
            chat_provider, # LLM provider
            system_prompt, # system prompt word
            toolset.tools, # Tool definitions (including MCP tools)
            history, # conversation history
            on_message_part=on_message_part, # Streaming output callback
            on_tool_call=on_tool_call, # Tool call callback
        )
    except (ChatProviderError, asyncio.CancelledError):
        # Cleanup: Cancel all outstanding tool calls
        for future in tool_result_futures.values():
            future.remove_done_callback(future_done_callback)
            future.cancel()
        await asyncio.gather(*tool_result_futures.values(), return_exceptions=True)
        raise

    return StepResult(
        result.id, #Message ID
        result.message, # LLM generated message
        result.usage, # Token usage
        tool_calls, # Tool call list
        tool_result_futures, # tool results Future
    )
```
**Key Points**:
- The `step()` function is the core bridge between LLM and tools.
- It calls the LLM API, passing in the definitions of all available tools
- When LLM decides to call a tool, it is handled through the `on_tool_call` callback
- Dispatching tool calls to `toolset.handle()` which will route to the correct tool (including MCP tools)

#### KimiToolset.handle - Tool call dispatcher

**Location**: `src/kimi_cli/soul/toolset.py:97-124`

```python
def handle(self, tool_call: ToolCall) -> HandleResult:
    """
    Entry point for processing tool calls

    Input: ToolCall generated by LLM
    Output: HandleResult (synchronous or asynchronous result)
    """
    #Set the current tool calling context (used to obtain information during approval)
    token = current_tool_call.set(tool_call)

    try:
        # 1. Find tool
        if tool_call.function.name not in self._tool_dict:
            # Tool not found
            return ToolResult(
                tool_call_id=tool_call.id,
                return_value=ToolNotFoundError(tool_call.function.name),
            )

        # 2. Get the tool instance (probably MCPTool)
        tool = self._tool_dict[tool_call.function.name]

        # 3. Parse parameters
        try:
            arguments: JsonType = json.loads(
                tool_call.function.arguments or "{}"
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                return_value=ToolParseError(str(e))
            )

        # 4. Asynchronous calling tool
        # The tool here may be MCPTool, which will:
        # - Request user approval
        # - Call MCP server
        # - Convert result format
        async def _call():
            try:
                ret = await tool.call(arguments)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    return_value=ret
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    return_value=ToolRuntimeError(str(e))
                )

        # Return to asynchronous task
        return asyncio.create_task(_call())

    finally:
        # Clean up context
        current_tool_call.reset(token)
```
**Key Points**:
- `handle()` is the central dispatcher of tool calls
- It finds tools, parses parameters, and creates asynchronous tasks
- Supports all types of tools (built-in tools, MCP tools, user-defined tools)

#### MCPTool.call - MCP tool executor

**Location**: `src/kimi_cli/soul/toolset.py:380-405`

```python
async def __call__(self, **kwargs) -> ToolReturnValue:
    """
    Execute MCP tool call

    Call chain:
    LLM → kosong.step → KimiToolset.handle → MCPTool.__call__
                                                            ↓
                                                    Call MCP server
    """
    # 1. User approval (key security mechanism)
    description = f"Call MCP tool `{self._mcp_tool.name}`."
    if not await self._runtime.approval.request(
        self.name, # Tool name
        self._action_name, # Action name
        description # description
    ):
        return ToolRejectedError() # User rejected

    # 2. Call fastmcp client
    try:
        async with self._client as client:
            result = await client.call_tool(
                self._mcp_tool.name, # MCP tool name
                kwargs, # parameters
                timeout=self._timeout, # Timeout control
                raise_on_error=False #Do not throw an error, return an error response
            )
            # 3. Convert MCP results to Kimi format
            return convert_mcp_tool_result(result)
    except Exception as e:
        # 4. Handle timeouts and errors
        exc_msg = str(e).lower()
        if "timeout" in exc_msg or "timed out" in exc_msg:
            return ToolError(
                message=(
                    f"Timeout while calling MCP tool `{self._mcp_tool.name}`. "
                    "You may explain to the user that the timeout config is set too low."
                ),
                brief="Timeout"
            )
        raise
```
**Key Points**:
- **User Approval**: The MCP tool must be confirmed by the user before being called.
- **fastmcp client**: Use the fastmcp library to communicate with the MCP server
- **Timeout Control**: Prevent long-running tools from blocking
- **Error Handling**: Capture and convert various error conditions

#### kimisoul._step - Complete Step execution process

**Location**: `src/kimi_cli/soul/kimisoul.py:383-456`

```python
async def _step(self) -> StepOutcome | None:
    """
    Perform a single inference step

    Returns: StepOutcome or None (continue)
    """
    assert self._runtime.llm is not None
    chat_provider = self._runtime.llm.chat_provider

    # 1. Call kosong.step (including LLM call and tool distribution)
    result = await kosong.step(
        chat_provider,
        self._agent.system_prompt, # system prompt word
        self._agent.toolset, # Toolset (including MCP tools)
        self._context.history, #Conversation history
        on_message_part=wire_send, # Streaming output callback
        on_tool_result=wire_send, # Tool result callback
    )

    # 2. Wait for all tool calls to complete
    results = await result.tool_results()

    # 3. Add the result to the context
    await self._grow_context(result, results)

    # 4. Check if there is a tool call
    if result.tool_calls:
        return None # There is a tool call, continue the loop

    # 5. No tool calls, stop
    return StepOutcome(
        stop_reason="no_tool_calls",
        assistant_message=result.message
    )
```
### 9.2 Process of tool registration to LLM

#### Tool definition conversion

```python
# kosong extracts tool definitions from Toolset
# Location: packages/kosong/src/kosong/_generate.py

async def generate(
    chat_provider: ChatProvider,
    system_prompt: str,
    tools: Sequence[Tool], # Pass in all tool definitions here
    history: Sequence[Message],
    ...
) -> "GenerateResult":

    # Convert tool to LLM API format
    tool_declarations = [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters  # JSON Schema
        }
        for tool in tools
    ]

    # Call LLM API
    response = await chat_provider.generate_content({
        "system_instruction": system_prompt,
        "contents": history,
        "tools": tool_declarations, # Tell LLM what tools are available
        "tool_config": {
            "function_calling_config": {
                "mode": "ANY" # Allow LLM to automatically call tools
            }
        }
    })

    # Handle streaming responses and tool calls
    ...
```
**Key Points**:
- MCP tools are converted to standard LLM Function Calling format
- Tool parameters are described using JSON Schema
- LLM can call MCP tools just like built-in tools

#### How to register the MCP tool

```python
# 1. MCP tool creation (mcp-client.py)
async def discover_tools() -> list[DiscoveredMCPTool]:
    tools = []
    for mcp_tool in await client.list_tools():
        tool = MCPTool(
            server_name,
            mcp_tool,
            client,
            runtime=runtime
        )
        tools.append(tool)
    return tools

# 2. Register the tool to Toolset (toolset.py:230-233)
for tool in tools:
    self.add(tool) # Add to _tool_dict

# 3. LLM can see these tools
# toolset.tools returns the Tool definitions of all tools
```
### 9.3 Complete call sequence diagram

```
User input "Search for Python MCP tutorial using context7"
    ↓
kimisoul._turn()
    ↓
kimisoul._agent_loop()
    ↓
kosong.step(
    chat_provider=KimiChatProvider,
    system_prompt=...,
    toolset=KimiToolset{
        _tool_dict={
            "context7_search": MCPTool(...),
            "read_file": ReadFile(...),
            ...
        }
    },
    history=[...]
)
    ↓
generate()
    ↓
Kimi API calls
    POST /chat/completions
{
    "messages": [...],
    "tools": [
        {
            "name": "context7_search",
            "description": "This is an MCP (Model Context Protocol) tool...",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"}
                }
            }
        },
        ...
    ]
}
    ↓
Kimi API returns streaming response
    ├── Content: "Okay, let me search for you..."
    └── FunctionCall: {
            "id": "call_abc123",
            "function": {
                "name": "context7_search",
                "arguments": '{"query": "Python MCP Tutorial", "limit": 10}'
            }
         }
    ↓
on_tool_call(tool_call)
    ↓
toolset.handle(tool_call)
    ↓
Find MCPTool("context7_search")
    ↓
MCPTool.__call__(**{"query": "Python MCP Tutorial", "limit": 10})
    ↓
runtime.approval.request(...)
    ↓
[User Approval Interface]
    ↓
User clicks "Allow"
    ↓
client.call_tool("search", {"query": "Python MCP Tutorial", "limit": 10})
    ↓
MCP server returns results
    ↓
convert_mcp_tool_result(result)
    ↓
ToolResult(return_value=ToolOk(output=[...]))
    ↓
Return to kosong.step
    ↓
_kimisoul._grow_context(result, results)
    ↓
Add to conversation history
    ↓
Continue to next round of LLM calls (containing tool results)
```
### 9.4 Key data structure conversion

#### LLM FunctionCall → Kimi ToolCall

```python
# LLM return format
function_call = {
    "id": "call_abc123",
    "function": {
        "name": "context7_search", # The name of the tool seen by LLM
        "arguments": '{"query": "...", "limit": 10}'
    }
}

# Convert to Kimi ToolCall
tool_call = ToolCall(
    id=function_call["id"],
    function=FunctionCall(
        name=function_call["function"]["name"],
        arguments=function_call["function"]["arguments"]
    )
)
```

#### Tool Result → LLM Context

```python
# Raw results returned by the MCP tool
mcp_result = {
    "content": [
        {"type": "text", "text": "10 related results found..."},
        {"type": "image", "data": "base64...", "mimeType": "image/png"}
    ]
}

# Convert to Kimi ContentPart
content_parts = [
    ContentPart(text="10 related results found..."),
    ContentPart(image="base64...")
]

# Convert to LLM FunctionResponse
tool_result_message = Message(
    role="tool",
    content=[
        FunctionResponse(
            name="context7_search",
            response=content_parts
        )
    ]
)

# Add to conversation history
history.append(tool_result_message)
```
### 9.5 Comparison with Gemini CLI

|characteristic| Kimi CLI | Gemini CLI |
|------|----------|------------|
|**Tool name format**|Original tool name (e.g. `context7_search`)|`mcp_{server}_{tool}` (such as `mcp_context7_search`)|
|**LLM Integration Layer**|kosong frame| Google GenAI SDK |
|**Tool Registration**|via Toolset.add()|By ToolRegistry|
|**User Approval**|In MCPTool.call()|In DiscoveredMCPToolInvocation|
|**Result Conversion**| convert_mcp_tool_result() | transformMcpContentToParts() |
|**Error handling**| ToolError | ToolErrorType |

---

## Reference resources

- **GitHub repository**: [https://github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)
- **Official Document**: [https://moonshotai.github.io/kimi-cli/](https://moonshotai.github.io/kimi-cli/)
- **MCP protocol**: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
- **fastmcp library**: [https://github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)

---

## Appendix

### A. Core code file list

```
src/kimi_cli/
├── cli/mcp.py # MCP CLI command (line 350)
├── soul/toolset.py # Toolset core (line 467)
├── acp/mcp.py # ACP protocol adaptation (line 47)
├── config.py # Configuration definition (200+ lines)
└── exception.py #Exception definition

Key categories:
- KimiToolset: Toolset management
- MCPTool: MCP tool package
- MCPServerInfo: server connection information
- MCPConfig: configuration definition
```
### B. Configuration file example

**~/.kimi/mcp.json**:```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "transport": "http",
      "headers": {
        "CONTEXT7_API_KEY": "your-key"
      }
    },
    "linear": {
      "url": "https://mcp.linear.app/mcp",
      "transport": "http",
      "auth": "oauth"
    }
  }
}
```

**~/.kimi/config.yaml**:```yaml
mcp:
  client:
    tool_call_timeout_ms: 60000
```
### C. Related dependencies

```toml
[dependencies]
fastmcp = "2.12.5"
agent-client-protocol = "0.7.0"
pydantic = "2.12.5"
```

---

**Documentation version**: 1.0
**Last updated**: 2026-03-11
**Author**: AI Assistant
**License**: MIT License
