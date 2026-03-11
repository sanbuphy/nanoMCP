# Official MCP (Model Context Protocol) introduction

> English translation generated from `./official-mcp-introduction.md`


> This document is based on the [MCP official document](https://modelcontextprotocol.io/docs/getting-started/intro) and is illustrated with actual project cases.

Make it clear in one sentence (points divided):
- **Problems targeted**: When the AI client connects to external systems, the protocols/parameters/returns/transmissions are independent of each other, resulting in a set of plug-ins having to be rewritten for each client. The ecosystem is fragmented and difficult to reuse.
- **What MCP defines**:
  - **(1) Message and Handshake**: Unified message format based on JSON-RPC 2.0 + life cycle initialization (initialize/initialized) + capabilities negotiation
  - **(2) Standard capability objects**: Tools/Resources/Prompts three types of primitives, as well as supporting list/read/get/call methods and data structures
  - **(3) Transport and notification conventions**: transport abstractions such as stdio, Streamable HTTP/SSE, and notification modes such as list_changed/updated
- **Achievements**: Server is implemented once, and multiple Host/Clients can communicate with each other; capabilities can be discovered, called, and subscribed, integration costs are significantly reduced, and permissions, security, and auditing are easier to implement

Why is it needed / what is done / what effect is achieved:
- **Problem**: When there is no unified standard, each AI client and each external system must be adapted separately (the tool name, parameter structure, return format, authentication, transmission, and error semantics are all inconsistent), and the ecosystem is fragmented and difficult to reuse.
- **Method**: Use JSON-RPC 2.0 to define a unified messaging shell and method set, and negotiate capabilities through the initialization phase, turning "what can be provided/what can be processed" into a declarable and verifiable contract
- **Effect**: Server is implemented once, multiple Hosts/Clients can be reused; tools/resources/prompt templates can be discovered, called, and subscribed, making it easier to do permissions, auditing, UI presentation, and security confirmation in engineering

**Related Documents**:
- [Kimi CLI MCP implementation analysis](./kimi-cli-mcp-implementation-analysis.en.md) - Implementation based on fastmcp (Python)
- [Gemini CLI MCP implementation analysis](./gemini-cli-mcp-implementation-analysis.en.md) - Implementation based on @modelcontextprotocol/sdk (TypeScript)

**Objective of this article**:
- Make it clear "what is MCP"
- Explain clearly "What JSON is transmitted in the MCP protocol" (data structure + example)
- Explain clearly "how to write MCP Server/Client" (from minimum usable to scalable)

---

## What is MCP?

MCP (Model Context Protocol) is an open source standard for connecting AI applications to external systems. Through MCP, AI applications such as Claude or ChatGPT can connect to:

- **Data source** (such as local file, database)
- **Tools** (such as search engines, calculators)
- **Workflow** (such as specialized prompt words)

This enables AI to access critical information and perform tasks.

### Analogy: USB-C interface

Think of MCP as a USB-C interface for AI applications. Just like USB-C provides a standardized way to connect electronic devices, MCP provides a standardized way to connect AI applications to external systems.

## What can MCP achieve?

1. **Personalized AI Assistant**: The AI ​​agent can access your Google Calendar and Notion to act as a more personalized AI assistant.

2. **Cross-platform development**: Claude Code can use Figma to design and generate complete web applications.

3. **Enterprise Data Analysis**: Enterprise chatbots can connect multiple databases within an organization, enabling users to analyze data through chat.

4. **Creative Design and Manufacturing**: AI models can create 3D designs on Blender and print them using a 3D printer.

## Why is MCP important?

MCP brings various benefits to different actors in the ecosystem:

### For developers

- Reduce development time and complexity when building AI applications or agents
- Simplified integration with existing systems

### For AI applications or agents

- Access an ecosystem of data sources, tools and applications
- Enhance capabilities and improve end-user experience
- Build once, integrate everywhere

### To the end user

- More powerful AI applications or agents
- AI can access your data and take action on your behalf if necessary

## Extensive ecosystem support

MCP is an open protocol supported in a wide range of clients and servers. Tools that support MCP include:

- **AI Assistant**: Claude, ChatGPT
- **Development Tools**: Visual Studio Code, Cursor, MCPJam, etc.

This broad support makes it possible to "build once, integrate anywhere."

## Start building

MCP provides three main build paths:

### 1. Build Servers
Create an MCP server to expose your data and tools to AI applications.

### 2. Build Clients
Develop applications that connect to MCP servers.

### 3. Build MCP Apps
Build interactive applications that run within the AI client.

## Core concepts

### Architecture components

The core architecture of MCP consists of three main components:

1. **Host**: Application that runs the AI model (such as IDE, chat interface)
2. **Client**: library that implements the MCP protocol
3. **Server**: An application that provides tools, resources and prompt words

### Connection method

MCP supports multiple connection methods:

- **Local process**: Connect to the locally running MCP server through stdio
- **HTTP/SSE**: Connect to a remote MCP server over the network
- **Direct Integration**: The server is embedded directly into the application as a library

### Data exchange

MCP uses standardized message formats for data exchange:

- **Tools**: Functions that can be called
- **Resources**: data that can be read
- **Prompts**: Reusable templates

## Protocol and data structure (emphasis)

MCP's "data layer" protocol is essentially a set of conventions of **JSON-RPC 2.0**: using a unified message encapsulation (request/response/notification), and then defining a set of standard `method` (such as `tools/list`, `resources/read`, etc.) and the `params/result` data structure corresponding to these methods.

Starting from the bottom JSON shell, the data structure of MCP will be explained layer by layer.

### 1) JSON-RPC shell: Request / Response / Notification

**Request (has id, must reply)**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```
**Response (same as id, choose one: result or error)**

success:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "tools": [] }
}
```
Failure (protocol-level error, typically invalid parameters/method does not exist):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": { "code": -32602, "message": "Invalid params" }
}
```
**Notification (no id, no replies allowed)**

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed"
}
```
**General Agreement**
- `jsonrpc` must be `"2.0"`
- `id` must be string/number and cannot be null
- `method` is a string, MCP convention is in the "namespace/action" format such as `tools/list`, `resources/read`
- `params` / `result` is usually a JSON Object
- `params._meta` is a reserved field: the protocol allows both parties to carry meta information (such as progress token), do not stuff business fields into `_meta`

### 2) Life cycle: initialize → notifications/initialized

Before any `tools/list` / `resources/list`, an initialization handshake must be done: **negotiate protocol version + capabilities**.

**initialize（Client → Server）**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    },
    "clientInfo": { "name": "ExampleClient", "version": "1.0.0" }
  }
}
```

**initialize result（Server → Client）**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "prompts": { "listChanged": true },
      "logging": {}
    },
    "serverInfo": { "name": "ExampleServer", "version": "1.0.0" }
  }
}
```

**notifications/initialized（Client → Server）**

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```
Key points in capability negotiation:
- Client declares "what server-side requests/notifications I can handle" in the `capabilities` of initialize (for example, whether it can handle client features such as roots, sampling, etc.)
- Server declares "what capabilities I provide" in initialize result (tools/resources/prompts/logging...)
- Only the capabilities successfully negotiated by both parties can be used in the future: for example, if the server does not declare `resources.subscribe=true`, the client should not send `resources/subscribe`

### 3) MCP three major primitives (Primitives): Tools / Resources / Prompts

MCP Server can be understood as "exposing three types of objects":
- Tools: executable actions (function calls)
- Resources: readable context data (located by URI)
- Prompts: reusable prompt templates (located by name)

These three types of objects have a consistent pattern: **list is used for discovery**, **get/read is used to obtain content**, and **call is used for execution (only for tools)**.

#### 3.1 Tools

**Tool definition structure (server is returned in tools/list)**

```json
{
  "name": "get_weather",
  "title": "Weather Information Provider",
  "description": "Get current weather information for a location",
  "inputSchema": {
    "type": "object",
    "properties": {
      "location": { "type": "string", "description": "City name or zip code" }
    },
    "required": ["location"]
  }
}
```
Field understanding:
- `name`: unique identifier of the tool (it is recommended to only use letters/numbers/underlines/dots/horizontal lines)
- `title` / `description`: Description for UI/people to read
- `inputSchema`: JSON Schema (defines the `arguments` shape of `tools/call`)
- (optional) `outputSchema`: constrain structured returns
-(Optional) `icons` / `annotations` / `execution`: used for UI rendering, priority, task execution, etc.

**List tools: tools/list**

ask:

```json
{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }
```
response:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": { "tools": [ { "name": "get_weather", "description": "...", "inputSchema": { "type": "object" } } ] }
}
```
**Calling tools: tools/call**

ask:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": { "location": "New York" }
  }
}
```
Response (note: this is the "tool execution result", not the JSON-RPC error):

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      { "type": "text", "text": "Current weather in New York: 72°F" }
    ],
    "isError": false
  }
}
```
##### ToolResult.content:ContentBlock (unified content block)

MCP uses `content: ContentBlock[]` to express "the content returned to the model/user". Common types:

**TextContent**

```json
{ "type": "text", "text": "hello" }
```

**ImageContent / AudioContent（base64）**

```json
{ "type": "image", "mimeType": "image/png", "data": "..." }
```
**ResourceLink (returns a resource link that can be read/subscribed)**

```json
{
  "type": "resource_link",
  "name": "readme",
  "uri": "file:///project/README.md",
  "mimeType": "text/markdown"
}
```
**EmbeddedResource (embed the resource content directly into the return)**

```json
{
  "type": "resource",
  "resource": {
    "uri": "file:///project/README.md",
    "mimeType": "text/markdown",
    "text": "# Project"
  }
}
```
#### 3.2 Resources

The core of Resource is: **Use URI for positioning** and read the content through `resources/read`.

**Resource definition structure (server returns in resources/list)**

```json
{
  "uri": "file:///project/src/main.rs",
  "name": "main.rs",
  "title": "Rust Software Application Main File",
  "description": "Primary application entry point",
  "mimeType": "text/x-rust"
}
```
**List resources: resources/list**

```json
{ "jsonrpc": "2.0", "id": 10, "method": "resources/list", "params": {} }
```
response:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": { "resources": [ { "uri": "file:///project/src/main.rs", "name": "main.rs" } ] }
}
```
**Read resources: resources/read**

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "resources/read",
  "params": { "uri": "file:///project/src/main.rs" }
}
```
Response (note that `contents` is an array, allowing multiple copies of shard content for the same uri):

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "contents": [
      {
        "uri": "file:///project/src/main.rs",
        "mimeType": "text/x-rust",
        "text": "fn main() { println!(\"Hello world!\"); }"
      }
    ]
  }
}
```
**(Optional) Subscribe to resource changes: resources/subscribe**

```json
{ "jsonrpc": "2.0", "id": 12, "method": "resources/subscribe", "params": { "uri": "file:///project/src/main.rs" } }
```
Resource update notification (server → client):

```json
{ "jsonrpc": "2.0", "method": "notifications/resources/updated", "params": { "uri": "file:///project/src/main.rs" } }
```
#### 3.3 Prompts (prompt word template)

The core of Prompt is: **Let the server provide a reusable message template**, which can be selected and used by the user/application, and parameters can be passed in when necessary.

**Prompt definition structure (server returns in prompts/list)**

```json
{
  "name": "code_review",
  "title": "Request Code Review",
  "description": "Asks the LLM to analyze code quality and suggest improvements",
  "arguments": [
    { "name": "code", "description": "The code to review", "required": true }
  ]
}
```
**List prompts: prompts/list**

```json
{ "jsonrpc": "2.0", "id": 20, "method": "prompts/list", "params": {} }
```
**Get prompt: prompts/get**

```json
{
  "jsonrpc": "2.0",
  "id": 21,
  "method": "prompts/get",
  "params": { "name": "code_review", "arguments": { "code": "print('hi')" } }
}
```
Response (key is `messages`, each message has role + content):

```json
{
  "jsonrpc": "2.0",
  "id": 21,
  "result": {
    "description": "Code review prompt",
    "messages": [
      { "role": "user", "content": { "type": "text", "text": "Please review this code: print('hi')" } }
    ]
  }
}
```
### 4) Error handling: protocol error vs execution error

The most confusing point when many people implement MCP for the first time is: **When to use JSON-RPC error and when to use ToolResult.isError**.

- **JSON-RPC error (error field)**: protocol level error (method does not exist, params structure is illegal, resource does not exist, permission denied, etc.)
- **ToolResult.isError=true**: The tool itself failed to execute (third-party API error, business verification failure, runtime exception, etc.), but the protocol call was completed successfully

Example: A non-existent tool was called (protocol error)

```json
{
  "jsonrpc": "2.0",
  "id": 30,
  "error": { "code": -32602, "message": "Unknown tool: invalid_tool_name" }
}
```
Example: The tool exists, but execution failed (execution error)

```json
{
  "jsonrpc": "2.0",
  "id": 31,
  "result": {
    "content": [ { "type": "text", "text": "API rate limit exceeded" } ],
    "isError": true
  }
}
```
## Development Guide: How to write MCP Server (from minimum usable to scalable)

### What is the minimum available server to do?

If you only support tools, you must implement at least 3 methods:
- `initialize`: returns server capabilities (including at least `tools`)
- `tools/list`: Return tools definition (including `inputSchema`)
- `tools/call`: execute the tool and return `content[]`

Three engineering requirements must be met at the same time:
- Parameter verification: Verify `arguments` according to `inputSchema` and business rules
- Output constraints: The output should be as structured and readable as possible, and avoid leaking sensitive information.
- Security design: Allow host applications to do "human confirmation" (especially write/delete/external network request tools)

### Use nanoMCP of this repository to write a minimal Server (in-memory)

This repository provides a minimalist example Server: `FakeMCPServer`, used to demonstrate MCP's JSON-RPC interaction (does not rely on real network/process).

Runnable examples categorized by transport are also provided:
- `stdio/mcp_stdio_server.py`：stdio server
- `sse/mcp_sse_server.py`：SSE server
- `streamable_http/mcp_streamable_http_server.py`: streamable_http server

Reference implementation: [server.py](file:///Users/sanbu/Code/2026 Important Open Source Project/nanoMCP/nanomcp/server.py)

```python
from nanomcp.server import FakeMCPServer


def add_handler(args: dict) -> dict:
    a = int(args["a"])
    b = int(args["b"])
    return {"type": "text", "text": str(a + b)}


server = FakeMCPServer(
    name="demo",
    version="0.1.0",
    tools=[
        {
            "name": "add",
            "description": "Add two integers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            },
        }
    ],
    handlers={"add": add_handler},
)
```
The behavior of this server corresponds to the key structure of MCP:
- `tools/list` returns `tools: [...]`
- `tools/call` returns `result: { content: [...], isError: false }`
- Non-existent tool returns JSON-RPC error (`-32602`)

### What else is usually needed for a production-level server?

- Resources: Use `resources/list`/`resources/read` to provide contextual data (more controllable and cacheable than "returning a large text in the tool")
- Prompts: Use `prompts/list`/`prompts/get` to provide reusable templates (convenient for UI to be exposed in the form of commands)
- Notifications and subscriptions: For example `notifications/tools/list_changed`, `resources/subscribe` + `notifications/resources/updated`
- Timeout/cancellation/progress: Use progress + canceled for long tasks (otherwise the host will easily get stuck)
- Authentication and permissions: Remote HTTP transport requires authentication strategy (usually OAuth or bearer token)

## Development Guide: How to write MCP Client/Host (from connection to call)

The "Client" here refers to the **MCP client component**: it is responsible for maintaining the connection with an MCP Server, sending and receiving JSON-RPC messages according to the protocol (initialize, tools/list, tools/call...), and handing the return results to **Host (host application)** for unified scheduling (for example, letting LLM select tools and write tool results back to the conversation context). Simple understanding:
- **Host**: Your AI application ontology (IDE, chat application, Agent framework), management model and the overall workflow of multiple servers
- **Client**: Each Server corresponds to a "protocol adapter + connection manager" (one-to-one maintenance of connections, request IDs, timeouts, etc.)
- **Server**: The provider that truly implements Tools/Resources/Prompts

The core responsibilities of Client can be broken down into 4 steps:
1. Establish a connection (stdio / http/sse / other transport)
2. Initialization handshake (initialize + notifications/initialized)
3. Discovery capabilities (tools/list / resources/list / prompts/list)
4. Organize the call (tools/call/resources/read/prompts/get) and hand the result to the host application/model

### Use nanoMCP in this repository to write a minimal Client

Reference implementation: [client.py](file:///Users/sanbu/Code/2026 Important Open Source Project/nanoMCP/nanomcp/client.py)

```python
from nanomcp.client import NanoMCPClient


client = NanoMCPClient(server_name="demo", server=server)
client.initialize()
tools = client.list_tools()
result = client.call_tool("add", {"a": 1, "b": 2})
```
### When you want to manage multiple MCP Servers: Registry

Host applications usually need to connect to multiple servers at the same time and integrate the tools of different servers into a "available tool pool".

Reference implementation: [registry.py](file:///Users/sanbu/Code/2026 Important Open Source Project/nanoMCP/nanomcp/registry.py)

```python
from nanomcp.registry import MCPRegistry


registry = MCPRegistry()
registry.register_server("math", server, transport="inmemory")

registry.initialize_all()
all_tools = registry.list_tools()

resp = registry.call_tool("math.add", {"a": 10, "b": 20})
```
### Transport intuition: stdio vs SSE/HTTP

MCP specifies "what the protocol looks like" (JSON-RPC) and also specifies common transports:
- **stdio**: local child process, most common with Claude Desktop/IDE integration
- **Streamable HTTP (optional SSE)**: remote service, suitable for service-oriented deployment within teams/enterprises

This repository provides a minimal transport demo client (simulating transport using serialization/deserialization):
[transport.py](file:///Users/sanbu/Code/2026 Important Open Source Project/nanoMCP/nanomcp/transport.py)

In addition, three sets of end-to-end examples divided by directory are provided:
- `stdio/mcp_stdio_client.py` + `stdio/mcp_stdio_server.py`
- `sse/mcp_sse_client.py` + `sse/mcp_sse_server.py`
- `streamable_http/mcp_streamable_http_client.py` + `streamable_http/mcp_streamable_http_server.py`

## Interaction timing (stringing everything together)

A typical conversation might look like this:

1. Client → Server：`initialize`
2. Server → Client：`initialize result`
3. Client → Server：`notifications/initialized`
4. Client → Server：`tools/list`
5. Server → Client：`tools/list result`
6. (The model determines which tool to use) Client → Server: `tools/call`
7. Server → Client: `tools/call result` (`content[]`)
8. (Optional) Server → Client: `notifications/tools/list_changed`

## Security

MCP incorporates security as a core design principle:

- The user must be explicitly authorized to connect to the MCP server
- Server can be enabled/disabled
- Support access control list (allowlist/excludelist)
- OAuth authentication supports remote servers

## Norms and Ecosystem

- **Open Specification**: The MCP specification is publicly available and can be implemented by anyone
- **Multi-language SDK**: Provides SDKs for TypeScript, Python and other languages
- **Server Registry**: Community maintained list of available MCP servers
- **Community Proposals (SEPs)**: Continuous improvement of the protocol through the SEP process

## Related resources

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [Detailed Architecture](https://modelcontextprotocol.io/docs/about/architecture)
- [SDK Documentation](https://modelcontextprotocol.io/docs/developing-mcp/sdk)
- [Server Registry](https://github.com/modelcontextprotocol/servers)
- [GitHub repository](https://github.com/modelcontextprotocol)

## Summarize

MCP solves the fragmentation problem when integrating AI applications with external systems by providing a standardized protocol. It makes:

1. **Developers** can build AI integrations more easily
2. **AI applications** have access to rich data and capabilities
3. **Users** can get a more powerful and personalized AI experience

Just like the USB-C port unified device connectivity, MCP is unifying how AI applications connect to the world.