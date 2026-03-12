# MCP in-depth analysis: from principle to practice

> English translation generated from `./mcp-deep-dive-guide.md`


> This article explains in detail how Model Context Protocol (MCP) works, including the basics of JSON Schema, the difference between MCP and Function Calling, how to solve the problem of NxM integration complexity, and complete code examples.

---

## Table of contents

- 1. MCP Core Concepts
- 2. JSON Schema Fundamentals
- 3. MCP vs Function Calling
- 4. The NxM Integration Problem
- 5. MCP Runtime Mechanics
- 6. How Configuration Works
- 7. Why "Write Once" Is Possible
- 8. Complete Code Examples
- 9. Summary

---

## 1. MCP core concepts

### What is MCP?

**Model Context Protocol (MCP)** is an open protocol used to establish standardized connections between LLM (Large Language Model) applications and external data sources/tools.

#### Analogy: MCP is like the USB standard in the AI ​​world

```
┌─────────────────────────────────────────────────────────┐
│ USB Ecosystem │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Mouse manufacturer ──[Follow USB protocol]──> USB standard │
│                                ↓                        │
│ Windows ──[Implement USB driver]──> Recognize and use the mouse │
│ Mac ──[Implement USB driver]──> Recognize and use the mouse │
│ Linux ──[Implement USB driver]──> Recognize and use the mouse │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MCP Ecosystem │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Tavily ──[Comply with MCP protocol]──> MCP standard │
│                            ↓                            │
│ Claude Desktop ──[Implementing MCP client]──> Using Tavily │
│ Cursor IDE ──[Implementing MCP client]──> Using Tavily │
│ Custom application ──[Implementing MCP client]──> Using Tavily │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
### Core components of MCP

```
┌──────────────────────────────────────────────────────────┐
│ MCP Architecture │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐         ┌─────────────┐                │
│ │ MCP Server │ │ MCP Client │ │
│  │             │         │             │                │
│ │ • Exposure tools │<------->│ • Connect to server │ │
│ │ • Exposed resources │ JSON-RPC│ • Get tools │ │
│ │ • Exposure tips │ │ • Call tools │ │
│ │ │ │ • Format conversion │ │
│  └─────────────┘         └─────────────┘                │
│       ↓                        ↓                         │
│ Tavily/GitHub/Slack Claude/Cursor/Custom Application │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 2. JSON Schema basics

### What is JSON Schema?

**JSON Schema** is a format used to describe the structure of JSON data. It defines:
- Type of data (string, number, object, array, etc.)
- required fields
- Constraints on fields (minimum value, maximum value, enumeration value, etc.)

### Basic example

#### Simple JSON Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "user name"
    },
    "age": {
      "type": "integer",
      "description": "User age",
      "minimum": 0,
      "maximum": 150
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "User Email"
    }
  },
  "required": ["name", "email"]
}
```
#### Corresponding valid JSON data

```json
{
  "name": "Zhang San",
  "age": 25,
  "email": "zhangsan@example.com"
}
```
#### Invalid JSON data

```json
{
  "age": 25,
  "email": "zhangsan@example.com"
  // ❌ Missing required "name" field
}
```
### Application in MCP

MCP uses JSON Schema to describe the input parameters of the tool:

```python
# MCP server definition tool

@mcp.tool()
def search_web(
    query: str, # string type
    max_results: int = 10, # integer type, default value 10
    search_depth: str = "basic" # string type, default value "basic"
) -> str:
    """
    Search the web for the latest information

    This function will be automatically converted to the following JSON Schema:
    """
    pass

# Automatically converted to:
{
  "name": "search_web",
  "description": "Search the web for the latest information",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search keywords"
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum number of results",
        "default": 10
      },
      "search_depth": {
        "type": "string",
        "description": "Search depth",
        "default": "basic",
        "enum": ["basic", "advanced"]
      }
    },
    "required": ["query"]
  }
}
```
### Why is JSON Schema important?

1. **Uniformity**: All major LLMs use JSON Schema description tools
2. **Verifiable**: Can verify whether the parameters meet the requirements
3. **Self-describing**: Contains type and description information, LLM can understand
4. **Interoperability**: Tool definitions can be exchanged between different systems

---

## 3. MCP vs Function Calling

### Core differences

```
┌─────────────────────────────────────────────────────────┐
│ MCP vs Function Calling                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ MCP (Protocol Standard) │
│  ────────────────────                                  │
│ • Define how to expose tools │
│ • Define communication protocol (JSON-RPC) │
│ • Define tool description format (JSON Schema) │
│ • Similar to USB interface standard │
│                                                         │
│ Function Calling (Execution Mechanism) │
│  ─────────────────────────────                         │
│ • How to call tools in LLM │
│ • How to pass parameters │
│ • How to receive return results │
│ • Similar device drivers │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
### Detailed comparison

|aspect| MCP | Function Calling |
|------|-----|------------------|
|**nature**|protocol standards|Execution mechanism|
|**definer**|MCP official specification|Various LLM providers|
|**effect**|Unified tool exposure method|How LLM calls tools|
|**protocol**| JSON-RPC 2.0 |Varies (HTTP/WebSocket)|
|**Tool Format**|Unified `inputSchema`| Claude: `input_schema`<br>OpenAI: `parameters`<br>Gemini: `parameters` |
|**relation**|MCP uses Function Calling as the underlying execution mechanism|Function Calling can call MCP tools|

### Collaboration between MCP and Function Calling

```
┌─────────────────────────────────────────────────────────┐
│ How MCP uses Function Calling │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. MCP server exposure tool │
│     ↓                                                   │
│ 2. MCP client acquisition tool list │
│     ↓                                                   │
│ 3. The client converts the MCP tool to LLM format │
│     ↓                                                   │
│ 4. LLM uses Function Calling to decide which tool to call │
│     ↓                                                   │
│ 5. The client intercepts the tool call and forwards it to the MCP server │
│     ↓                                                   │
│ 6. MCP server executes and returns results │
│     ↓                                                   │
│ 7. The client transfers the results to LLM │
│     ↓                                                   │
│ 8. LLM generates final answer │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. NxM problem solved by MCP

### Problem description: Integration complexity of traditional methods

Let's say you have 3 LLM applications and 3 tools that need to be integrated:

#### ❌ Traditional method (without MCP)

```
Integration to be done:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Claude Desktop → Tavily API (needs to write 1 integration code)
Claude Desktop → GitHub API (needs to write 1 integration code)
Claude Desktop → Slack API (needs to write 1 integration code)

Cursor IDE → Tavily API (need to write 1 integration code)
Cursor IDE → GitHub API (needs to write 1 integration code)
Cursor IDE → Slack API (needs to write 1 integration code)

Custom application → Tavily API (need to write 1 integration code)
Custom application → GitHub API (needs to write 1 integration code)
Custom application → Slack API (needs to write 1 integration code)

Total: 3 × 3 = 9 integrations 🫠
```
#### Problem details

**1. The tool definition format is not uniform**

```typescript
// Claude format
const claudeTool = {
  name: 'search',
  description: 'Search network',
  input_schema: { // ← Note: input_schema
    type: 'object',
    properties: {
      query: { type: 'string' }
    }
  }
};

// OpenAI format
const openaiTool = {
  type: 'function',
  function: {
    name: 'search',
    description: 'Search network',
    parameters: { // ← Note: parameters
      type: 'object',
      properties: {
        query: { type: 'string' }
      }
    }
  }
};

// Gemini format
const geminiTool = {
  name: 'search',
  description: 'Search network',
  parameters: { // ← Note: parameters
    type: 'object',
    properties: {
      query: { type: 'string' },
      maxResults: { type: 'integer' } // ← Note: camelCase
    }
  }
};
```
**2. API calling methods are different**

```typescript
//Claude API call
const response = await anthropic.messages.create({
  model: 'claude-3-5-sonnet-20241022',
  tools: [claudeTool],
  messages: [...]
});

// OpenAI API call
const response = await openai.chat.completions.create({
  model: 'gpt-4-turbo',
  tools: [openaiTool],
  messages: [...]
});

// Gemini API call
const model = genAI.getGenerativeModel({ model: 'gemini-pro' });
const response = await model.generateContent(prompt);
```
**3. The tool calling structure is different**

```typescript
// Claude's tool call
{
  type: 'tool_use',
  id: 'toolu_xxx',
  name: 'search',
  input: { query: 'test' }
}

// OpenAI tool call
{
  id: 'call_xxx',
  type: 'function',
  function: {
    name: 'search',
    arguments: '{"query":"test"}' // ← JSON string!
  }
}

// Gemini tool call
{
  name: 'search',
  args: { query: 'test' } // ← directly object
}
```
#### ✅ MCP method

```
Tool providers only need to write to the MCP server once:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tavily MCP Server (write 1 time, supports stdio/HTTP)
GitHub MCP Server (write 1 time, supports stdio/HTTP)
Slack MCP Server (written 1 time, supports stdio/HTTP)

Any client that supports MCP will work:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Claude Desktop → Configure .mcp.json → Automatically connect to all servers
Cursor IDE → Configure .mcp.json → Automatically connect to all servers
Custom application → Configure .mcp.json → Automatically connect to all servers

Total: 3 servers + N client configurations = 3 + N 🎉
```
### Complexity comparison

```
┌─────────────────────────────────────────────────────────┐
│ Traditional method: two-way adaptation (NxM complexity) │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Tool Provider LLM Client │
│      ↓                      ↓                           │
│ Tavily Team Claude Desktop │
│ ├─ Claude adaptation ├─ Implementing Claude tool system │
│ ├─ OpenAI adaptation ├─ Writing adaptation for Tavily │
│ └─ Gemini adaptation ├─ Write adaptation for GitHub │
│ └─Write an adaptation for Slack │
│                                                          │
│ GitHub Team Cursor IDE │
│ ├─ Claude adaptation ├─ Implementing OpenAI tool system │
│ ├─ OpenAI adaptation ├─ Writing adaptation for Tavily │
│ └─ Gemini adaptation ├─ Write adaptation for GitHub │
│ └─Write an adaptation for Slack │
│                                                          │
│ Slack Team Custom App │
│ ├─ Claude adaptation ├─ Implementing Gemini tool system │
│ ├─ OpenAI adaptation ├─ Writing adaptation for Tavily │
│ └─ Gemini adaptation ├─ Write adaptation for GitHub │
│ └─Write an adaptation for Slack │
│                                                          │
│ Result: Chaos, duplication, difficult to maintain │
│ Total code size: ~450 lines × 3 = 1350+ lines │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MCP method: one-way responsibility (N+M complexity) │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Tool Provider LLM Client │
│      ↓                      ↓                           │
│ Tavily Team Claude Desktop │
│ └─ MCP Server └─ MCP Client Adapter │
│ (50 lines of code) (200 lines of code) │
│                             ↓                           │
│ GitHub Team automatically works with all │
│ └─ MCP Server MCP Server!                    │
│ (100 lines of code) │
│                             ↓                           │
│ Slack Team Cursor IDE │
│ └─ MCP Server └─ MCP Client Adapter │
│ (80 lines of code) (200 lines of code) │
│                             ↓                           │
│ Automatically available for all │
│MCP Server!                     │
│                                                          │
│ Result: clear, reusable, easy to maintain │
│ Total code size: ~230 lines (server) + 600 lines (client) = 830 lines │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Detailed explanation of MCP working principle

### Complete workflow

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Claude Desktop Launch │
│ - Read ~/.claude/config.json or the project's .mcp.json │
│ - Parse out the list of MCP servers to be started │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Start MCP Server │
│ - Execution: npx -y tavily-mcp │
│ - Establish communication pipeline through stdio (standard input/output) │
│ - Server process starts, waiting for JSON-RPC request │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Initial Handshake (JSON-RPC) │
│                                                              │
│ Claude → Tavily:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 1,                                                  │
│   "method": "initialize",                                   │
│   "params": {                                               │
│     "protocolVersion": "2025-06-18",                        │
│     "capabilities": {                                       │
│       "roots": { "listChanged": true }                      │
│     },                                                      │
│     "clientInfo": {                                         │
│       "name": "claude-desktop",                             │
│       "version": "1.0.0"                                    │
│     }                                                       │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Tavily → Claude:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 1,                                                  │
│   "result": {                                               │
│     "protocolVersion": "2025-06-18",                        │
│     "capabilities": {                                       │
│ "tools": {} // ← Declare support for tools │
│     },                                                      │
│     "serverInfo": {                                         │
│       "name": "tavily-mcp",                                 │
│       "version": "1.0.0"                                    │
│     }                                                       │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Get a list of tools │
│                                                              │
│ Claude → Tavily:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 2,                                                  │
│ "method": "tools/list" // ← MCP standard method │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Tavily → Claude:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 2,                                                  │
│   "result": {                                               │
│     "tools": [                                               │
│       {                                                      │
│ "name": "tavily_search", // ← Tool name │
│ "description": "Search the web for the latest information", │
│         "inputSchema": {                                     │
│           "type": "object",                                  │
│           "properties": {                                    │
│             "query": {                                       │
│               "type": "string",                              │
│ "description": "Search keywords" │
│             },                                               │
│             "max_results": {                                 │
│               "type": "integer",                             │
│ "description": "Maximum number of results", │
│               "default": 10                                  │
│             }                                                │
│           },                                                  │
│           "required": ["query"]                              │
│         }                                                     │
│       },                                                      │
│       {                                                      │
│         "name": "tavily_extract",                            │
│ "description": "Extract web content", │
│         "inputSchema": { ... }                               │
│       },                                                      │
│       {                                                      │
│         "name": "tavily_research",                           │
│ "description": "In-depth research", │
│         "inputSchema": { ... }                               │
│       }                                                      │
│     ]                                                        │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Claude converts the tool definition into his own function definition │
│                                                              │
│ MCP tool format → Claude function format: │
│                                                              │
│ {                                                            │
│   "name": "tavily_search",                                   │
│ "description": "Search the web for the latest information", │
│   "input_schema": { ... }                                    │
│ }                                                            │
│ ↓ Convert │
│                                                              │
│ This definition was added to Claude's system prompt words!                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: User questions │
│                                                              │
│ User: "Search MCP related information" │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Claude decides to call the tool │
│                                                              │
│ Claude’s system prompt words include: │
│                                                              │
│ You can use the following tools: │
│ - mcp__tavily__tavily_search: Search the web for the latest information │
│ - mcp__tavily__tavily_extract: Extract web page content │
│ - ...                                                       │
│                                                              │
│ Claude analyzes user intent → decides to call tavily_search │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Function Calling (Claude API call) │
│                                                              │
│ Claude generated: │
│ {                                                            │
│   "type": "tool_use",                                       │
│   "id": "toolu_xxx",                                        │
│ "name": "mcp__tavily__tavily_search", // ← mcp__server name__tool name │
│   "input": {                                                │
│     "query": "MCP",                                         │
│     "max_results": 5                                        │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 9: Claude Desktop Interception Tool Call │
│                                                              │
│ Claude Desktop sees "mcp__tavily__tavily_search": │
│ 1. Parse out: server = tavily, tool = tavily_search │
│ 2. Send JSON-RPC to Tavily MCP via stdio: │
│                                                              │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 3,                                                  │
│ "method": "tools/call", // ← MCP standard method │
│   "params": {                                               │
│     "name": "tavily_search",                                │
│     "arguments": {                                          │
│       "query": "MCP",                                       │
│       "max_results": 5                                      │
│     }                                                       │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 10: Tavily MCP Performs Search │
│                                                              │
│ - Tavily MCP calls Tavily API │
│ - Get search results │
│ - Return via stdio: │
│                                                              │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 3,                                                  │
│   "result": {                                               │
│     "content": [                                            │
│       {                                                      │
│         "type": "text",                                     │
│ "text": "Search results..." │
│       }                                                      │
│     ],                                                      │
│     "isError": false                                        │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 11: Claude Desktop Transfer results to Claude │
│                                                              │
│ Claude Desktop converts MCP results to Claude API format: │
│                                                              │
│ {                                                            │
│   "type": "tool_result",                                    │
│   "tool_use_id": "toolu_xxx",                               │
│ "content": "Search results..." │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 12: Claude generates the final answer based on the tool results │
└─────────────────────────────────────────────────────────────┘
```
### Key protocol: JSON-RPC 2.0

MCP uses JSON-RPC 2.0 as the communication protocol. JSON-RPC is a lightweight remote procedure call protocol.

#### Basic structure

```json
{
  "jsonrpc": "2.0",
  "method": "method name",
  "params": { /* parameters */ },
  "id": 1
}
```
#### Standard methods defined by MCP

```javascript
// 1. Initialization
{ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...} }

// 2. List tools
{ "jsonrpc": "2.0", "id": 2, "method": "tools/list" }

// 3. Call the tool
{ "jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {...} }

// 4. List resources
{ "jsonrpc": "2.0", "id": 4, "method": "resources/list" }

// 5. Read resources
{ "jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {...} }
```

---

## 6. How configuration files work

### Configuration file structure

```json
{
  "mcpServers": {
    "tavily": { // Server name (custom)
      "command": "npx", // Start command
      "args": ["-y", "tavily-mcp"], // command parameters
      "env": { // environment variables
        "TAVILY_API_KEY": "tvly-..."
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```
### Configuration file location

|application|Configuration file location|
|------|------------|
| Claude Desktop | `~/.claude/config.json` |
| Cursor | `~/.cursor/mcp.json` |
|project specific|`.mcp.json` (project root directory)|

### Configuration file parsing process

```typescript
// Pseudocode: How Claude Desktop reads configuration

async function loadMCPServers() {
  // 1. Read global configuration
  const globalConfig = await readFile('~/.claude/config.json');

  // 2. Read the project configuration (if it exists)
  const projectConfig = await readFile('.mcp.json');

  // 3. Merge configuration
  const allServers = {
    ...globalConfig.mcpServers,
    ...projectConfig.mcpServers
  };

  // 4. Start all servers
  for (const [name, config] of Object.entries(allServers)) {
    await startMCPServer(name, config);
  }
}

async function startMCPServer(name, config) {
  // 1. Create a child process
  const process = spawn(config.command, config.args, {
    env: { ...process.env, ...config.env }
  });

  // 2. Create MCP client
  const client = new Client({
    name: "claude-desktop",
    version: "1.0.0"
  });

  // 3. Connect to the stdio of the server
  const transport = new StdioClientTransport({
    stdout: process.stdout,
    stdin: process.stdin
  });

  // 4. Connect and initialize
  await client.connect(transport);
  await client.initialize();

  // 5. Get the tool list
  const tools = await client.listTools();

  // 6. Registration tool
  registerTools(name, tools.tools);
}
```

---

## 7. Why you only need to write it once

### Core principle: protocol standardization + client adaptation layer

#### Tavily only needs to implement the MCP standard

```python
# tavily_mcp_server.py
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("Tavily Search Server")

@mcp.tool()
def tavily_search(
    query: str,
    max_results: int = 10
) -> str:
    """
    Use the Tavily API to search the web for the latest information
    """
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": max_results
        }
    )
    return response.json()

# Start the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
```
**that's all! Tavily's job is over. **

#### The client is responsible for protocol conversion

```typescript
// Claude Desktop internal MCP adapter

class ClaudeMCPAdapter {
  async connectToMCP(serverConfig: any) {
    // 1. Connect to MCP server
    const mcpClient = new Client({
      name: "claude-desktop",
      version: "1.0.0"
    });

    const transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args,
      env: serverConfig.env
    });

    await mcpClient.connect(transport);

    // 2. Get the MCP tool list
    const toolsResult = await mcpClient.listTools();

    // 3. [Key] Convert MCP format → Claude format
    const claudeTools = toolsResult.tools.map(tool => ({
      name: `mcp__${serverName}__${tool.name}`,
      description: tool.description,
      input_schema: tool.inputSchema // ← MCP's inputSchema is directly compatible!
    }));

    return claudeTools;
  }

  async callTool(toolName: string, args: any) {
    const [prefix, serverName, toolName] = toolName.split('__');

    // Call the MCP server
    const result = await this.mcpClient.callTool({
      name: toolName,
      arguments: args
    });

    //Convert result format
    return {
      type: 'tool_result',
      tool_use_id: this.generateId(),
      content: result.content.map(item => ({
        type: 'text',
        text: item.text
      }))
    };
  }
}
```
### Why is the MCP format automatically compatible?

```typescript
// MCP's inputSchema is very well designed

{
  "type": "object",
  "properties": {
    "query": { "type": "string" },
    "max_results": { "type": "integer" }
  },
  "required": ["query"]
}

// Claude format
input_schema: { ... } // ← Use directly

// OpenAI format
parameters: { ... } // ← Use directly (only change the field name)

// Gemini format
parameters: { ... } // ← Use directly
```
**This is why MCP is successful: its JSON Schema design is highly compatible with the tool definition formats of major LLMs! **

---

## 8. Complete code example

### Comparison of traditional method vs MCP method

#### ❌ Traditional method: each client must write an adaptation

**Claude Desktop adaptation code**

```typescript
// claude-tavily-integration.ts

import Anthropic from '@anthropic-ai/sdk';

const tavilySearchTool = {
  name: 'tavily_search',
  description: 'Search the Internet for the latest information',
  input_schema: { // ← Claude format
    type: 'object',
    properties: {
      query: { type: 'string' },
      max_results: { type: 'integer', default: 10 }
    },
    required: ['query']
  }
};

async function callTavilyAPI(params: any) {
  const response = await fetch('https://api.tavily.com/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: process.env.TAVILY_API_KEY,
      query: params.query,
      max_results: params.max_results || 10
    })
  });
  return await response.json();
}

async function handleClaudeResponse(userMessage: string) {
  const anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY
  });

  const message = await anthropic.messages.create({
    model: 'claude-3-5-sonnet-20241022',
    max_tokens: 1024,
    tools: [tavilySearchTool],
    messages: [{ role: 'user', content: userMessage }]
  });

  for (const block of message.content) {
    if (block.type === 'tool_use' && block.name === 'tavily_search') {
      const toolResult = await callTavilyAPI(block.input);

      const finalMessage = await anthropic.messages.create({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 1024,
        tools: [tavilySearchTool],
        messages: [
          { role: 'user', content: userMessage },
          { role: 'assistant', content: message.content },
          {
            role: 'user',
            content: [{
              type: 'tool_result',
              tool_use_id: block.id,
              content: JSON.stringify(toolResult)
            }]
          }
        ]
      });

      return finalMessage.content;
    }
  }

  return message.content;
}
```
**Cursor IDE adaptation code**

```typescript
// cursor-tavily-integration.ts

import OpenAI from 'openai';

const tavilySearchTool = {
  type: 'function' as const,
  function: {
    name: 'tavily_search',
    description: 'Search the Internet for the latest information',
    parameters: { // ← OpenAI format (different!)
      type: 'object',
      properties: {
        query: { type: 'string' },
        max_results: { type: 'integer' }
      },
      required: ['query']
    }
  }
};

async function callTavilyAPI(params: any) { // ← Repeat implementation
  const response = await fetch('https://api.tavily.com/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: process.env.TAVILY_API_KEY,
      query: params.query,
      max_results: params.max_results || 10
    })
  });
  return await response.json();
}

async function handleOpenAIResponse(userMessage: string) {
  const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
  });

  const response = await openai.chat.completions.create({
    model: 'gpt-4-turbo',
    messages: [{ role: 'user', content: userMessage }],
    tools: [tavilySearchTool],
    tool_choice: 'auto'
  });

  const assistantMessage = response.choices[0].message;

  if (assistantMessage.tool_calls) {
    for (const toolCall of assistantMessage.tool_calls) {
      if (toolCall.function.name === 'tavily_search') {
        const args = JSON.parse(toolCall.function.arguments);
        const toolResult = await callTavilyAPI(args);

        const finalResponse = await openai.chat.completions.create({
          model: 'gpt-4-turbo',
          messages: [
            { role: 'user', content: userMessage },
            assistantMessage,
            {
              role: 'tool',
              tool_call_id: toolCall.id,
              content: JSON.stringify(toolResult)
            }
          ]
        });

        return finalResponse.choices[0].message.content;
      }
    }
  }

  return assistantMessage.content;
}
```
#### ✅ MCP method: write only once

**Tavily MCP Server**

```python
# tavily_mcp_server.py
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("Tavily Search Server")

@mcp.tool()
def tavily_search(
    query: str,
    max_results: int = 10,
    search_depth: str = "basic"
) -> str:
    """
    Use the Tavily API to search the web for the latest information

    Args:
        query: search keyword
        max_results: Maximum number of results (1-20)
        search_depth: search depth (basic/advanced)

    Returns:
        JSON string of search results
    """
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth
        },
        timeout=30.0
    )
    return response.json()

@mcp.tool()
def tavily_extract(urls: list[str]) -> str:
    """
    Extract content from a specified URL

    Args:
        urls: list of URLs to extract

    Returns:
        Extracted content
    """
    response = httpx.post(
        "https://api.tavily.com/extract",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "urls": urls
        },
        timeout=30.0
    )
    return response.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
```
**Configuration of each client**

```json
// Claude Desktop: ~/.claude/config.json
{
  "mcpServers": {
    "tavily": {
      "command": "uvx",
      "args": ["tavily-mcp"],
      "env": {
        "TAVILY_API_KEY": "tvly-your-api-key"
      }
    }
  }
}
```

```json
// Cursor IDE: ~/.cursor/mcp.json
{
  "mcpServers": {
    "tavily": {
      "command": "uvx",
      "args": ["tavily-mcp"],
      "env": {
        "TAVILY_API_KEY": "tvly-your-api-key"
      }
    }
  }
}
```

```typescript
// Custom application: custom-mcp-client.ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

async function connectToTavilyMCP() {
  const client = new Client({
    name: "my-custom-app",
    version: "1.0.0"
  });

  const transport = new StdioClientTransport({
    command: "uvx",
    args: ["tavily-mcp"],
    env: {
      TAVILY_API_KEY: process.env.TAVILY_API_KEY!
    }
  });

  await client.connect(transport);

  // Get the list of available tools
  const toolsResult = await client.listTools();

  console.log("Available tools:", toolsResult.tools);

  return client;
}
```
### Comparison of code size

|Way|Amount of code|Maintenance cost|
|------|-------|---------|
|**Traditional way**|450 rows × 3 clients = 1350+ rows|API changes require 3 changes|
|**MCP method**|50 lines (server) + 3 config files|The API has changed and only 1 server has been changed.|

---

## 9. Summary

### Core Points

1. **MCP is a protocol standard, not an implementation**
   - MCP defines a unified tool exposure method
   - MCP defines a standard communication protocol (JSON-RPC 2.0)
   - MCP defines a unified tool description format (JSON Schema)

2. **MCP ≠ Function Calling**
   - MCP is a protocol standard (how to expose tools)
   - Function Calling is the execution mechanism (how LLM calls tools)
   - MCP uses Function Calling as the underlying execution mechanism

3. **MCP solves the NxM complexity problem**
   - Traditional method: each tool needs to write an adaptation for each client (N×M)
   - MCP method: The tool writes the MCP server once, and the client writes the MCP adapter once (N+M)

4. **Why do you only need to write it once? **
   - Tool providers only need to implement the MCP standard (unified JSON Schema + JSON-RPC)
   - Each LLM client internally implements the MCP adapter (MCP format → own format)
   - Clear responsibilities: the tool side is responsible for implementing MCP, and the client is responsible for adapting MCP

5. **JSON Schema is key**
   - JSON Schema is a standard format for describing JSON data structure
   - All major LLMs use JSON Schema description tools
   - MCP's inputSchema design is highly compatible with major LLMs

### Best Practice Suggestions

#### For tool providers

```python
# 1. Use MCP SDK definition tool
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Tool Server")

@mcp.tool()
def my_tool(param1: str, param2: int = 10) -> str:
    """
    Clear tool description

    Args:
        param1: parameter description
        param2: parameter description

    Returns:
        Return value description
    """
    return "result"

# 2. Start the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
```
#### For client developers

```typescript
// 1. Implement MCP adapter
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class MyMCPAdapter {
  async connect(serverConfig: any) {
    const client = new Client({
      name: "my-app",
      version: "1.0.0"
    });

    const transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args,
      env: serverConfig.env
    });

    await client.connect(transport);

    // 2. Convert MCP format to your own LLM format
    const toolsResult = await client.listTools();
    const myFormatTools = toolsResult.tools.map(tool => ({
      // Conversion logic
    }));

    return { client, tools: myFormatTools };
  }
}
```
#### For users

```json
// 1. Configure MCP server
{
  "mcpServers": {
    "tool-name": {
      "command": "Start command",
      "args": ["parameters"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}

// 2. Restart the LLM application
// 3. Use the tool directly!
```
### Further reading

- [MCP official document](https://modelcontextprotocol.io/)
- [MCP Specification](https://modelcontextprotocol.io/specification/)
- [JSON Schema official specification](https://json-schema.org/)
- [MCP Server Development Guide](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP Client Development Guide](https://modelcontextprotocol.io/docs/develop/build-client)

---

**Summary in one sentence:**

> **Traditional approach**: Each tool provider needs to write different adaptation code for each LLM client, resulting in N×M complexity.
>
> **MCP method**: MCP defines a unified tool registration format (based on JSON Schema). Tool providers only need to implement the MCP server once, and each LLM client only needs to implement the MCP adapter once to achieve universal access to tools.

---

*This document is generated with AI assistance and is based on MCP official documents and best practices. *
