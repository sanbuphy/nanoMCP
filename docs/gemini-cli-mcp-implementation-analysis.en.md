# In-depth dismantling of Gemini CLI’s MCP (Model Context Protocol) implementation mechanism

> English translation generated from `./gemini-cli-mcp-implementation-analysis.md`


> **Project address**: [https://github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
>
> **Analysis version**: v0.35.0-nightly
>
> **Analysis time**: 2026-03-11

**Related Documents**:
- [Official MCP Introduction](./official-mcp-introduction.en.md) - Basic concepts and principles of MCP protocol
- [Kimi CLI MCP implementation](./kimi-cli-mcp-implementation-analysis.en.md) - Implementation comparison based on fastmcp (Python)

## Table of contents

- 1. Project Overview
- 2. MCP Architecture Overview
- 3. Core Component Breakdown
- 4. End-to-End Workflow
- 5. Key Technical Implementations
- 6. Security Mechanisms
- 7. Usage Examples
- 8. Comparison with Kimi CLI
- 9. Summary and Takeaways

---

## 1. Project Overview

### 1.1 What is Gemini CLI?

Gemini CLI is an open source AI command line tool developed by Google that brings the powerful capabilities of Gemini models directly into the terminal. It provides lightweight access to Gemini and is the shortest path directly from prompt words to the model.

### 1.2 Core Features

- **Free Quota**: 60 requests/minute, 1,000 requests/day using a personal Google account
- **Powerful Gemini 3 Model**: Access improved inference capabilities and 1M token context window
- **Built-in Tools**: Google search, file operations, Shell commands, web scraping
- **MCP Support**: Custom integration via Model Context Protocol
- **Terminal First**: Designed for developers who live on the command line
- **Open Source**: Apache 2.0 License

### 1.3 Technology stack

- **Language**: TypeScript/JavaScript (Node.js 20+)
- **MCP SDK**: `@modelcontextprotocol/sdk`
- **Package Management**: npm/workspaces
- **Build Tools**: esbuild, TypeScript
- **Testing Framework**: Vitest

---

## 2. MCP architecture overview

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User interaction layer │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│ │ CLI Commands │ │ Interactive Shell │ │ VSCode Extensions │ │
│ │ gemini mcp │ │ /mcp command │ │ IDE integration │ │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│Configure management layer │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ ~/.gemini/settings.json (user configuration) │ │
│ │ .gemini/settings.json (project configuration) │ │
│ │ mcpServers configuration │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Core processing layer │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ McpClientManager │  │   McpClient      │  │ Discovered   │  │
│ │ (Life cycle management) │ │ (Single server management) │ │ MCPTool │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  ToolRegistry    │  │  PromptRegistry │  │Resource      │  │
│ │ (Tool Registry) │ │ (Prompt word registration) │ │Registry │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ MCP SDK Client Layer │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ @modelcontextprotocol/sdk/client/Client                │     │
│ │ - StdioClientTransport (local process) │ │
│  │ - SSEClientTransport (Server-Sent Events)              │     │
│ │ - StreamableHTTPClientTransport (HTTP streaming) │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ External MCP Server Layer │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│ │Custom Server│ │ GitHub │ │ Notion │ │ Google │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```
### 2.2 Core code structure

```
packages/core/src/
├── tools/
│ ├── mcp-client.ts # MCP client core (1000+ lines)
│ ├── mcp-client-manager.ts # MCP client manager (500+ lines)
│ ├── mcp-tool.ts # MCP tool package (600+ lines)
│ └── tool-registry.ts # Tool registry
├── mcp/
│ ├── google-auth-provider.ts # Google Authentication Provider
│ ├── sa-impersonation-provider.ts # Service account imitation
│ ├── oauth-provider.ts # OAuth provider
│ └── oauth-token-storage.ts # OAuth Token storage
├── prompts/
│ └── prompt-registry.ts # Prompt word registry
└── resources/
    └── resource-registry.ts # Resource registry

packages/cli/src/commands/mcp/
├── add.ts # Add server command
├── remove.ts # Remove server command
├── list.ts # List server commands
└── enableDisable.ts # Enable/disable command
```

---

## 3. Disassembly of core components

### 3.1 Configuration Management

#### Configuration file structure

MCP server configuration is stored in `settings.json` and supports user-level and project-level configuration:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/sse",
      "type": "sse",
      "headers": {
        "CONTEXT7_API_KEY": "your-key"
      },
      "timeout": 60000,
      "trust": false,
      "description": "Context7 search server"
    },
    "google-workspace": {
      "httpUrl": "https://my-gcp-service.run.app/mcp",
      "authProviderType": "google_credentials",
      "oauth": {
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
      }
    },
    "python-tools": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "env": {
        "API_KEY": "$MY_API_TOKEN",
        "LOG_LEVEL": "debug"
      },
      "cwd": "./mcp-servers/python",
      "includeTools": ["safe_tool", "file_reader"],
      "excludeTools": ["dangerous_tool"]
    }
  },
  "mcp": {
    "allowed": ["my-trusted-server"],
    "excluded": ["experimental-server"]
  }
}
```
#### Detailed explanation of configuration properties

**Transmission type configuration**:

|property|type|illustrate|
|------|------|------|
| `command` | string |Commands transmitted by Stdio|
| `url` | string |SSE transferred URL|
| `httpUrl` | string |URL for HTTP streaming|
| `type` | string |Transport type: `stdio`, `sse`, `http`|

**Common configuration**:

|property|type|illustrate|
|------|------|------|
| `args` | string[] |Command line parameters|
| `env` | object |Environment variables (supports `$VAR` expansion)|
| `headers` | object |HTTP headers (SSE/HTTP)|
| `cwd` | string |working directory|
| `timeout` | number |Timeout (milliseconds, default 600000)|
| `trust` | boolean |Trust the server (bypass confirmation)|
| `description` | string |Server description|
| `includeTools` | string[] |List of included tools|
| `excludeTools` | string[] |Excluded tools list|

**Authentication Configuration**:

|property|type|illustrate|
|------|------|------|
| `authProviderType` | string |Authentication type: `dynamic_discovery`, `google_credentials`, `service_account_impersonation`|
| `oauth` | object |OAuth configuration|
| `targetAudience` | string |Client ID of IAP protected app|
| `targetServiceAccount` | string |The email address of the service account to be simulated|

#### CLI command implementation

**Add server** (`packages/cli/src/commands/mcp/add.ts`):

```typescript
async function addMcpServer(
  name: string,
  commandOrUrl: string,
  args: Array<string | number> | undefined,
  options: {
    scope: string;           // 'user' | 'project'
    transport: string;       // 'stdio' | 'sse' | 'http'
    env: string[] | undefined;
    header: string[] | undefined;
    timeout?: number;
    trust?: boolean;
    description?: string;
    includeTools?: string[];
    excludeTools?: string[];
  },
) {
  const settings = loadSettings(process.cwd());
  const settingsScope = scope === 'user' ? SettingScope.User : SettingScope.Workspace;

  let newServer: Partial<MCPServerConfig> = {};

  // Parse headers
  const headers = header?.reduce((acc, curr) => {
    const [key, ...valueParts] = curr.split(':');
    const value = valueParts.join(':').trim();
    if (key.trim() && value) {
      acc[key.trim()] = value;
    }
    return acc;
  }, {} as Record<string, string>);

  // Build configuration based on transport type
  switch (transport) {
    case 'sse':
      newServer = {
        url: commandOrUrl,
        type: 'sse',
        headers,
        timeout,
        trust,
        description,
        includeTools,
        excludeTools,
      };
      break;
    case 'http':
      newServer = {
        url: commandOrUrl,
        type: 'http',
        headers,
        timeout,
        trust,
        description,
        includeTools,
        excludeTools,
      };
      break;
    case 'stdio':
    default:
      newServer = {
        command: commandOrUrl,
        args: args?.map(String),
        env: env?.reduce((acc, curr) => {
          const [key, value] = curr.split('=');
          if (key && value) {
            acc[key] = value;
          }
          return acc;
        }, {} as Record<string, string>),
        timeout,
        trust,
        description,
        includeTools,
        excludeTools,
      };
      break;
  }

  //Save configuration
  const mcpServers = settings.forScope(settingsScope).settings.mcpServers || {};
  mcpServers[name] = newServer as MCPServerConfig;
  settings.setValue(settingsScope, 'mcpServers', mcpServers);
}
```
**Usage Example**:

```bash
# Add stdio server
gemini mcp add python-server python -m my_mcp_server -- --port 8080

#Add SSE server
gemini mcp add --transport sse context7 https://mcp.context7.com/sse

# Add HTTP server (with authentication)
gemini mcp add --transport http \
  --header "Authorization: Bearer $TOKEN" \
  secure-server https://api.example.com/mcp

#Add trusted server
gemini mcp add --trust local-tools python server.py

# Add a server with tool filtering
gemini mcp add --include-tools safe_tool,read_file \
  --exclude-tools delete_file filtered-server python server.py
```

---

### 3.2 MCP client management (`mcp-client-manager.ts`)

**Responsibilities**: Manage the life cycle of multiple MCP clients

```typescript
export class McpClientManager {
  private clients: Map<string, McpClient> = new Map();
  private allServerConfigs: Map<string, MCPServerConfig> = new Map();
  private discoveryPromise: Promise<void> | undefined;
  private discoveryState: MCPDiscoveryState = MCPDiscoveryState.NOT_STARTED;
  private readonly blockedMcpServers: Array<{
    name: string;
    extensionName: string;
  }> = [];

  constructor(
    private readonly clientVersion: string,
    private readonly toolRegistry: ToolRegistry,
    private readonly cliConfig: Config,
    private readonly eventEmitter?: EventEmitter,
  ) {}

  /**
   * Discover all configured MCP servers
   */
  async discoverAllServers(): Promise<void> {
    if (this.discoveryState === MCPDiscoveryState.IN_PROGRESS) {
      return this.discoveryPromise;
    }

    this.discoveryState = MCPDiscoveryState.IN_PROGRESS;

    this.discoveryPromise = (async () => {
      const serverNames = Array.from(this.allServerConfigs.keys());

      // Connect to all servers concurrently
      await Promise.allSettled(
        serverNames.map((name) => this.maybeDiscoverMcpServer(name))
      );

      this.discoveryState = MCPDiscoveryState.COMPLETED;
    })();

    return this.discoveryPromise;
  }

  /**
   * Discover a single MCP server
   */
  private async maybeDiscoverMcpServer(
    serverName: string,
    config?: MCPServerConfig,
  ): Promise<void> {
    // Check if blocked
    if (this.isBlocked(serverName)) {
      this.blockedMcpServers.push({
        name: serverName,
        extensionName: config?.extension?.name || 'unknown',
      });
      return;
    }

    // Check if disabled
    if (this.isDisabled(serverName)) {
      return;
    }

    //Create or get client
    let client = this.clients.get(serverName);
    if (!client) {
      client = new McpClient(
        serverName,
        config || this.allServerConfigs.get(serverName)!,
        this.toolRegistry,
        this.promptRegistry,
        this.resourceRegistry,
        this.workspaceContext,
        this.cliConfig,
        this.debugMode,
        this.clientVersion,
        this.onContextUpdated,
      );
      this.clients.set(serverName, client);
    }

    // Connect and discover tools
    try {
      await client.connect();
      await client.discover(this.cliConfig);
    } catch (error) {
      this.emitDiagnostic('error', `Failed to connect to ${serverName}`, error);
    }
  }

  /**
   * Emit diagnostic messages
   */
  emitDiagnostic(
    severity: 'info' | 'warning' | 'error',
    message: string,
    error?: unknown,
    serverName?: string,
  ) {
    // Log errors
    if (severity === 'error' || severity === 'warning') {
      if (serverName) {
        this.lastErrors.set(serverName, message);
      }
    }

    // Remove duplicates
    const diagnosticKey = `${severity}:${message}`;
    const previousStatus = this.shownDiagnostics.get(diagnosticKey);

    // If the user has interacted, display detailed messages
    if (this.userInteractedWithMcp) {
      if (previousStatus === 'verbose') {
        return; //Already shown
      }
      this.shownDiagnostics.set(diagnosticKey, 'verbose');
      coreEvents.emitFeedback(severity, message, error);
      return;
    }

    // Silent mode to reduce interruptions
    if (previousStatus) {
      return;
    }
    this.shownDiagnostics.set(diagnosticKey, 'silent');
    debugLogger.log(`[MCP ${severity}] ${message}`, error);
  }
}
```
#### Status Management

**Server Status** (`MCPServerStatus`):

```typescript
export enum MCPServerStatus {
  DISCONNECTED = 'disconnected', // Not connected or error
  DISCONNECTING = 'disconnecting', // Disconnecting
  CONNECTING = 'connecting', // Connecting
  CONNECTED = 'connected', // Connected
  BLOCKED = 'blocked', // blocked
  DISABLED = 'disabled', // Disabled
}
```
**Discovery State** (`MCPDiscoveryState`):

```typescript
export enum MCPDiscoveryState {
  NOT_STARTED = 'not_started', // not started
  IN_PROGRESS = 'in_progress', // In progress
  COMPLETED = 'completed', // Completed
}
```

---

### 3.3 MCP client (`mcp-client.ts`)

**RESPONSIBILITIES**: Manage connections and interactions with a single MCP server

```typescript
export class McpClient implements McpProgressReporter {
  private client: Client | undefined;
  private transport: Transport | undefined;
  private status: MCPServerStatus = MCPServerStatus.DISCONNECTED;
  private readonly progressTokenToCallId = new Map<string | number, string>();

  constructor(
    private readonly serverName: string,
    private readonly serverConfig: MCPServerConfig,
    private readonly toolRegistry: ToolRegistry,
    private readonly promptRegistry: PromptRegistry,
    private readonly resourceRegistry: ResourceRegistry,
    private readonly workspaceContext: WorkspaceContext,
    private readonly cliConfig: McpContext,
    private readonly debugMode: boolean,
    private readonly clientVersion: string,
    private readonly onContextUpdated?: (signal?: AbortSignal) => Promise<void>,
  ) {}

  /**
   * Connect to MCP server
   */
  async connect(): Promise<void> {
    if (this.status !== MCPServerStatus.DISCONNECTED) {
      throw new Error(`Cannot connect: current state is ${this.status}`);
    }

    this.updateStatus(MCPServerStatus.CONNECTING);

    try {
      // Create client and transport
      this.client = await connectToMcpServer(
        this.clientVersion,
        this.serverName,
        this.serverConfig,
        this.debugMode,
        this.workspaceContext,
        this.cliConfig,
      );

      //Register notification handler
      this.registerNotificationHandlers();

      // error handling
      const originalOnError = this.client.onerror;
      this.client.onerror = (error) => {
        if (this.status !== MCPServerStatus.CONNECTED) {
          return;
        }
        if (originalOnError) originalOnError(error);
        this.cliConfig.emitMcpDiagnostic('error', `MCP ERROR (${this.serverName})`, error, this.serverName);
        this.updateStatus(MCPServerStatus.DISCONNECTED);
      };

      this.updateStatus(MCPServerStatus.CONNECTED);
    } catch (error) {
      this.updateStatus(MCPServerStatus.DISCONNECTED);
      throw error;
    }
  }

  /**
   * Discovery tools and hint words
   */
  async discover(cliConfig: McpContext): Promise<void> {
    this.assertConnected();

    // Concurrently obtain tools, prompt words and resources
    const prompts = await this.fetchPrompts();
    const tools = await this.discoverTools(cliConfig);
    const resources = await this.discoverResources();

    // Check if content is available
    if (prompts.length === 0 && tools.length === 0 && resources.length === 0) {
      throw new Error('No prompts, tools, or resources found on the server.');
    }

    //Register to the corresponding registry
    for (const prompt of prompts) {
      this.promptRegistry.registerPrompt(prompt);
    }
    for (const tool of tools) {
      this.toolRegistry.registerTool(tool);
    }
    this.toolRegistry.sortTools();

    //Update resource registry
    this.updateResourceRegistry(resources);

    //Verify MCP tool name in policy rules
    try {
      const discoveredToolNames = tools.map((t) => t.serverToolName);
      const policyRules = cliConfig.getPolicyEngine?.()?.getRules() ?? [];
      const warnings = validateMcpPolicyToolNames(
        this.serverName,
        discoveredToolNames,
        policyRules,
      );
      for (const warning of warnings) {
        coreEvents.emitFeedback('warning', warning);
      }
    } catch {
      // The policy engine may be unavailable and will be skipped silently.
    }
  }

  /**
   * Disconnect
   */
  async disconnect(): Promise<void> {
    if (this.status !== MCPServerStatus.CONNECTED) {
      return;
    }

    // Remove from all registries
    this.toolRegistry.removeMcpToolsByServer(this.serverName);
    this.promptRegistry.removePromptsByServer(this.serverName);
    this.resourceRegistry.removeResourcesByServer(this.serverName);

    this.updateStatus(MCPServerStatus.DISCONNECTING);

    const client = this.client;
    this.client = undefined;

    if (this.transport) {
      await this.transport.close();
    }
    if (client) {
      await client.close();
    }

    this.updateStatus(MCPServerStatus.DISCONNECTED);
  }
}
```
#### Connection established

```typescript
async function connectToMcpServer(
  clientVersion: string,
  serverName: string,
  serverConfig: MCPServerConfig,
  debugMode: boolean,
  workspaceContext: WorkspaceContext,
  cliConfig: McpContext,
): Promise<Client> {
  //Create transfer
  const transport = await createTransport(
    serverName,
    serverConfig,
    debugMode,
    workspaceContext,
    cliConfig,
  );

  //Create client
  const client = new Client({
    name: `gemini-cli-${clientVersion}`,
    version: clientVersion,
  }, {
    // Use Ajv for JSON Schema validation
    validator: new AjvJsonSchemaValidator(),
  });

  // connect
  await client.connect(transport);

  return client;
}

async function createTransport(
  serverName: string,
  serverConfig: MCPServerConfig,
  debugMode: boolean,
  workspaceContext: WorkspaceContext,
  cliConfig: McpContext,
): Promise<Transport> {
  let transport: Transport;

  //Create the corresponding transport according to the configuration
  if (serverConfig.url) {
    // SSE transport
    const options: SSEClientTransportOptions = {
      url: new URL(serverConfig.url),
      eventSourceOptions: {
        headers: serverConfig.headers,
      },
    };

    //Add OAuth authentication
    if (serverConfig.authProviderType) {
      const authProvider = createAuthProvider(serverConfig, cliConfig);
      options.eventSourceOptions.headers = {
        ...options.eventSourceOptions.headers,
        ...(await authProvider.getHeaders()),
      };
    }

    transport = new SSEClientTransport(options);
  } else if (serverConfig.httpUrl) {
    // HTTP streaming
    const options: StreamableHTTPClientTransportOptions = {
      url: new URL(serverConfig.httpUrl),
      headers: serverConfig.headers,
    };

    //Add OAuth authentication
    if (serverConfig.authProviderType) {
      const authProvider = createAuthProvider(serverConfig, cliConfig);
      options.headers = {
        ...options.headers,
        ...(await authProvider.getHeaders()),
      };
    }

    transport = new StreamableHTTPClientTransport(options);
  } else if (serverConfig.command) {
    // Stdio transfer
    const { command, args, env, cwd } = populateMcpServerCommand(
      serverConfig,
      workspaceContext,
      cliConfig,
    );

    const options = {
      command,
      args,
      env: sanitizeEnvironment(env, ENV_SANITIZATION_CONFIG),
      cwd,
    };

    transport = new StdioClientTransport(options);
  } else {
    throw new Error(`Invalid MCP server config for ${serverName}`);
  }

  return transport;
}
```

---

### 3.4 MCP tool package (`mcp-tool.ts`)

**Responsibility**: Encapsulate MCP tools into Gemini CLI callable tools

#### Tool naming rules

```typescript
export const MCP_QUALIFIED_NAME_SEPARATOR = '_';
export const MCP_TOOL_PREFIX = 'mcp_';

/**
 * Generate fully qualified name
 * Format: mcp_{serverName}_{toolName}
 *
 * Example:
 * - mcp_context7_search
 * - mcp_github_create_issue
 */
export function formatMcpToolName(
  serverName: string,
  toolName?: string,
): string {
  if (serverName === '*' && !toolName) {
    return `${MCP_TOOL_PREFIX}*`;
  } else if (serverName === '*') {
    return `${MCP_TOOL_PREFIX}*_${toolName}`;
  } else if (!toolName) {
    return `${MCP_TOOL_PREFIX}${serverName}_*`;
  } else {
    return `${MCP_TOOL_PREFIX}${serverName}_${toolName}`;
  }
}

/**
 * Generate valid tool names
 * - Force mcp_ prefix
 * - replace invalid characters with underscores
 * - make sure it starts with a letter or underscore
 * - truncate names that are too long (maximum 64 characters)
 */
export function generateValidName(name: string) {
  // Forced to add mcp_ prefix
  let validToolname = name.startsWith('mcp_') ? name : `mcp_${name}`;

  //Replace invalid characters
  validToolname = validToolname.replace(/[^a-zA-Z0-9_\-.:]/g, '_');

  // Make sure it starts with a letter or underscore
  if (/^[^a-zA-Z_]/.test(validToolname)) {
    validToolname = `_${validToolname}`;
  }

  //Truncate names that are too long
  const MAX_FUNCTION_NAME_LENGTH = 64;
  const safeLimit = MAX_FUNCTION_NAME_LENGTH - 1;
  if (validToolname.length > safeLimit) {
    debugLogger.warn(
      `Truncating MCP tool name "${validToolname}" to fit within the 64 character limit.`
    );
    validToolname =
      validToolname.slice(0, 30) + '...' + validToolname.slice(-30);
  }

  return validToolname;
}
```
#### Tool class definition

```typescript
export class DiscoveredMCPTool extends BaseDeclarativeTool<
  ToolParams,
  ToolResult
> {
  constructor(
    private readonly mcpTool: CallableTool,
    readonly serverName: string,
    readonly serverToolName: string,
    description: string,
    override readonly parameterSchema: unknown,
    messageBus: MessageBus,
    readonly trust?: boolean,
    isReadOnly?: boolean,
    nameOverride?: string,
    private readonly cliConfig?: McpContext,
    override readonly extensionName?: string,
    override readonly extensionId?: string,
    private readonly _toolAnnotations?: Record<string, unknown>,
  ) {
    super(
      // Tool name (with prefix)
      nameOverride ??
        generateValidName(
          `${serverName}${MCP_QUALIFIED_NAME_SEPARATOR}${serverToolName}`
        ),
      // display name
      `${serverToolName} (${serverName} MCP Server)`,
      description,
      Kind.Other,
      parameterSchema,
      messageBus,
      true,  // isOutputMarkdown
      false, // canUpdateOutput
      extensionName,
      extensionId,
    );
    this._isReadOnly = isReadOnly;
  }

  protected createInvocation(
    params: ToolParams,
    messageBus: MessageBus,
    _toolName?: string,
    _displayName?: string,
  ): ToolInvocation<ToolParams, ToolResult> {
    return new DiscoveredMCPToolInvocation(
      this.mcpTool,
      this.serverName,
      this.serverToolName,
      _displayName ?? this.displayName,
      messageBus,
      this.trust,
      params,
      this.cliConfig,
      this.description,
      this.parameterSchema,
      this._toolAnnotations,
    );
  }
}
```
#### Tool call

```typescript
export class DiscoveredMCPToolInvocation extends BaseToolInvocation<
  ToolParams,
  ToolResult
> {
  private static readonly allowlist: Set<string> = new Set();

  protected override async getConfirmationDetails(
    _abortSignal: AbortSignal,
  ): Promise<ToolCallConfirmationDetails | false> {
    const serverAllowListKey = this.serverName;
    const toolAllowListKey = `${this.serverName}.${this.serverToolName}`;

    // Trusted folder + trusted server
    if (this.cliConfig?.isTrustedFolder() && this.trust) {
      return false; // No confirmation required
    }

    // Check whitelist
    if (
      DiscoveredMCPToolInvocation.allowlist.has(serverAllowListKey) ||
      DiscoveredMCPToolInvocation.allowlist.has(toolAllowListKey)
    ) {
      return false; // Already in the whitelist
    }

    //Require user confirmation
    const confirmationDetails: ToolMcpConfirmationDetails = {
      type: 'mcp',
      title: 'Confirm MCP Tool Execution',
      serverName: this.serverName,
      toolName: this.serverToolName,
      toolDisplayName: this.displayName,
      toolArgs: this.params,
      toolDescription: this.toolDescription,
      toolParameterSchema: this.toolParameterSchema,
      onConfirm: async (outcome: ToolConfirmationOutcome) => {
        if (outcome === ToolConfirmationOutcome.ProceedAlwaysServer) {
          DiscoveredMCPToolInvocation.allowlist.add(serverAllowListKey);
        } else if (outcome === ToolConfirmationOutcome.ProceedAlwaysTool) {
          DiscoveredMCPToolInvocation.allowlist.add(toolAllowListKey);
        } else if (outcome === ToolConfirmationOutcome.ProceedAlwaysAndSave) {
          DiscoveredMCPToolInvocation.allowlist.add(toolAllowListKey);
          //Persistence policy updates are centrally processed by the scheduler
        }
      },
    };
    return confirmationDetails;
  }

  async execute(signal: AbortSignal): Promise<ToolResult> {
    this.cliConfig?.setUserInteractedWithMcp?.();

    const functionCalls: FunctionCall[] = [
      {
        name: this.serverToolName,
        args: this.params,
      },
    ];

    //Compete with abort signal
    const rawResponseParts = await new Promise<Part[]>((resolve, reject) => {
      if (signal.aborted) {
        const error = new Error('Tool call aborted');
        error.name = 'AbortError';
        reject(error);
        return;
      }

      const onAbort = () => {
        cleanup();
        const error = new Error('Tool call aborted');
        error.name = 'AbortError';
        reject(error);
      };

      const cleanup = () => {
        signal.removeEventListener('abort', onAbort);
      };

      signal.addEventListener('abort', onAbort, { once: true });

      this.mcpTool
        .callTool(functionCalls)
        .then((res) => {
          cleanup();
          resolve(res);
        })
        .catch((err) => {
          cleanup();
          reject(err);
        });
    });

    // Check if it is an error
    if (this.isMCPToolError(rawResponseParts)) {
      const errorMessage = `MCP tool '${this.serverToolName}' reported tool error`;
      return {
        llmContent: errorMessage,
        returnDisplay: `Error: MCP tool '${this.serverToolName}' reported an error.`,
        error: {
          message: errorMessage,
          type: ToolErrorType.MCP_TOOL_ERROR,
        },
      };
    }

    //Convert response
    const transformedParts = transformMcpContentToParts(rawResponseParts);

    return {
      llmContent: transformedParts,
      returnDisplay: getStringifiedResultForDisplay(rawResponseParts),
    };
  }

  /**
   * Check if the response contains tool errors
   */
  isMCPToolError(rawResponseParts: Part[]): boolean {
    const functionResponse = rawResponseParts?.[0]?.functionResponse;
    const response = functionResponse?.response;

    if (response) {
      // Check top-level isError (MCP specification compliant)
      const isErrorTop = (response as { isError?: boolean | string }).isError;
      if (isErrorTop === true || isErrorTop === 'true') {
        return true;
      }

      // Check for nested error objects (backward compatibility)
      const error = (response as { error?: { isError?: boolean | string } })?.error;
      const isError = error?.isError;
      if (error && (isError === true || isError === 'true')) {
        return true;
      }
    }
    return false;
  }
}
```
#### Content conversion

```typescript
/**
 * Convert MCP content block to GenAI Part array
 */
function transformMcpContentToParts(sdkResponse: Part[]): Part[] {
  const funcResponse = sdkResponse?.[0]?.functionResponse;
  const mcpContent = funcResponse?.response?.['content'] as McpContentBlock[];
  const toolName = funcResponse?.name || 'unknown tool';

  if (!Array.isArray(mcpContent)) {
    return [{ text: '[Error: Could not parse tool response]' }];
  }

  const transformed = mcpContent.flatMap(
    (block: McpContentBlock): Part | Part[] | null => {
      switch (block.type) {
        case 'text':
          return transformTextBlock(block);
        case 'image':
        case 'audio':
          return transformImageAudioBlock(block, toolName);
        case 'resource':
          return transformResourceBlock(block, toolName);
        case 'resource_link':
          return transformResourceLinkBlock(block);
        default:
          return null;
      }
    },
  );

  return transformed.filter((part): part is Part => part !== null);
}

function transformTextBlock(block: McpTextBlock): Part {
  return { text: block.text };
}

function transformImageAudioBlock(
  block: McpMediaBlock,
  toolName: string,
): Part[] {
  return [
    {
      text: `[Tool '${toolName}' provided the following ${block.type} data with mime-type: ${block.mimeType}]`,
    },
    {
      inlineData: {
        mimeType: block.mimeType,
        data: block.data,
      },
    },
  ];
}

function transformResourceBlock(
  block: McpResourceBlock,
  toolName: string,
): Part | Part[] | null {
  const resource = block.resource;
  if (resource?.text) {
    return { text: resource.text };
  }
  if (resource?.blob) {
    const mimeType = resource.mimeType || 'application/octet-stream';
    return [
      {
        text: `[Tool '${toolName}' provided the following embedded resource with mime-type: ${mimeType}]`,
      },
      {
        inlineData: {
          mimeType,
          data: resource.blob,
        },
      },
    ];
  }
  return null;
}

function transformResourceLinkBlock(block: McpResourceLinkBlock): Part {
  return {
    text: `Resource Link: ${block.title || block.name} at ${block.uri}`,
  };
}
```

---

## 4. Complete workflow

### 4.1 Startup flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User starts gemini │
│                  $ gemini                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Load configuration (settings.json) │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Loading source: │ │
│ │ • ~/.gemini/settings.json (user level) │ │
│ │ • .gemini/settings.json (project level) │ │
│ │ • Extended configuration │ │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Analysis configuration: │ │
│ │ • mcpServers: Server list │ │
│ │ • mcp.allowed: allowed servers │ │
│ │ • mcp.excluded: excluded servers │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Create McpClientManager and registry │
│  toolRegistry = new ToolRegistry()                              │
│  promptRegistry = new PromptRegistry()                          │
│  resourceRegistry = new ResourceRegistry()                      │
│  mcpManager = new McpClientManager(...)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Start MCP discovery (background asynchronous) │
│  mcpManager.discoverAllServers()                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Traverse the configured servers │
│  for serverName in Object.keys(mcpServers):                     │
│    ┌────────────────────────────────────────────────────────┐   │
│ │ Check: │ │
│ │ • Is it in the allowed list?                             │ │
│ │ • Is it in the excluded list?                            │ │
│ │ • Is it enabled?                                        │ │
│ │ • Blocked (admin policy)?                            │ │
│    └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Create McpClient for each server │
│  client = new McpClient(                                        │
│    serverName,                                                  │
│    serverConfig,                                                │
│    toolRegistry,                                                │
│    promptRegistry,                                              │
│    resourceRegistry,                                            │
│    ...                                                          │
│  )                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. Connect to all servers concurrently │
│  Promise.allSettled([                                          │
│    client1.connect(),                                           │
│    client2.connect(),                                           │
│    client3.connect(),                                           │
│    ...                                                          │
│  ])                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. For each successfully connected server │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Concurrent Discovery: │ │
│  │  • tools = client.discoverTools()                     │     │
│  │  • prompts = client.fetchPrompts()                    │     │
│  │  • resources = client.discoverResources()             │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 9. Tool discovery and registration │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ For each tool: │ │
│ │ 1. Get tool definition (name, description, parameter schema) │ │
│ │ 2. Apply filters (includeTools/excludeTools) │ │
│ │ 3. Generate fully qualified name: mcp_{server}_{tool} │ │
│ │ 4. Clean and validate schema │ │
│ │ 5. Create DiscoveredMCPTool instance │ │
│ │ 6. Register to ToolRegistry │ │
│ │ 7. Sorting Tools │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 10. Prompt word registration │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ For each prompt word: │ │
│ │ 1. Get the prompt word definition (name, parameters, template) │ │
│ │ 2. Register as slash command: /{promptName} │ │
│ │ 3. Add to PromptRegistry │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 11. Resource Registration │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ For each resource: │ │
│ │ 1. Get resource URI and metadata │ │
│ │ 2. Register to ResourceRegistry │ │
│ │ 3. Support @server://resource/path syntax │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 12. Complete the discovery │
│  discoveryState = MCPDiscoveryState.COMPLETED                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Display status: │ │
│ │ • "Connected" - Success │ │
│ │ • "Disconnected" - failed (silent mode) │ │
│  │  • "MCP issues detected. Run /mcp list for status."    │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 13. Waiting for user input │
└─────────────────────────────────────────────────────────────────┘
```
### 4.2 Tool calling flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│ User input issues │
│ > Search Python MCP tutorial using context7 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Gemini analyzes and decides to call tools │
│Identification requires the use of the mcp_context7_search tool │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Generate FunctionCall │
│  {                                                              │
│    "name": "mcp_context7_search",                               │
│    "args": {                                                    │
│      "query": "Python MCP tutorial",                            │
│      "limit": 10                                                │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            ToolRegistry.find("mcp_context7_search")             │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Search tool: │ │
│  │    tool = toolRegistry._toolDict["mcp_context7_search"]│     │
│  │                                                        │     │
│ │ 2. Find the DiscoveredMCPTool instance │ │
│  │    - serverName: "context7"                            │     │
│  │    - serverToolName: "search"                          │     │
│  │    - trust: false                                      │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         tool.createInvocation(params, messageBus)              │
│ Create DiscoveredMCPToolInvocation │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              invocation.getConfirmationDetails()               │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Check and confirm conditions: │ │
│ │ • isTrustedFolder() && trust → Skip confirmation │ │
│ │ • allowlist.has(serverName) → Skip confirmation │ │
│ │ • allowlist.has(toolName) → Skip confirmation │ │
│ │ • Otherwise → Show confirmation dialog │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ User confirmation (if required) │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ Confirmation dialog box: │ │
│  │ ┌────────────────────────────────────────────┐        │     │
│ │ │ MCP tool call is about to be executed │ │ │
│  │  │ ┌──────────────────────────────────────┐   │        │     │
│ │ │ │ Server: context7 │ │ │ │
│ │ │ │ Tools: search │ │ │ │
│ │ │ │ Parameters: {"query": "...", "limit": 10} │ │ │ │
│  │  │  └──────────────────────────────────────┘   │        │     │
│  │  │                                              │        │     │
│ │ │ [Execute once] [Always allow this tool] [Always allow this server] │ │ │ │
│ │ │ [Cancel] │ │ │ │
│  │  └────────────────────────────────────────────┘        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              invocation.execute(signal)                        │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Mark the user has interacted: │ │
│  │    cliConfig.setUserInteractedWithMcp()               │     │
│  │                                                        │     │
│ │ 2. Prepare function call: │ │
│  │    const functionCalls = [{                            │     │
│ │ name: "search", // Original tool name │ │
│  │      args: params                                      │     │
│  │    }]                                                  │     │
│  │                                                        │     │
│ │ 3. Set abort signal monitoring: │ │
│  │    signal.addEventListener('abort', onAbort)           │     │
│  │                                                        │     │
│ │ 4. Call the MCP tool: │ │
│  │    const rawResponse = await mcpTool.callTool(        │     │
│  │      functionCalls                                     │     │
│  │    )                                                   │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Check if the response is an error │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ if (isMCPToolError(rawResponse)):                     │     │
│  │   return {                                             │     │
│  │     error: {                                           │     │
│  │       type: ToolErrorType.MCP_TOOL_ERROR,              │     │
│  │       message: "MCP tool reported an error"            │     │
│  │     }                                                   │     │
│  │   }                                                     │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│Convert response content │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ transformedParts = transformMcpContentToParts(        │     │
│  │    rawResponse                                         │     │
│  │ )                                                      │     │
│  │                                                        │     │
│ │ Handles different types: │ │
│  │  • text → { text: "..." }                             │     │
│  │  • image → [{ text: "[Image...]" },                   │     │
│  │             { inlineData: { mimeType, data } }]       │     │
│  │  • audio → [{ text: "[Audio...]" },                   │     │
│  │             { inlineData: { mimeType, data } }]       │     │
│ │ • resource → { text: "..." } or │ │
│  │                [{ text: "[Resource...]" },            │     │
│  │                 { inlineData: { mimeType, data } }]   │     │
│  │  • resource_link → { text: "Resource Link: ..." }     │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Return results │
│  {                                                              │
│ llmContent: transformedParts, // Content for the model │
│    returnDisplay: getStringifiedResultForDisplay(rawResponse)  │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Gemini processes the results and returns them to the user │
└─────────────────────────────────────────────────────────────────┘
```
### 4.3 OAuth authentication flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Add OAuth server │
│  $ gemini mcp add --transport sse google-workspace \            │
│      https://workspace-mcp.googleapis.com/sse                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Save the configuration to settings.json │
│  {                                                              │
│    "mcpServers": {                                              │
│      "google-workspace": {                                      │
│        "url": "https://workspace-mcp.googleapis.com/sse",       │
│        "type": "sse",                                           │
│        "authProviderType": "dynamic_discovery"                  │
│      }                                                           │
│    }                                                             │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. First connection (without token) │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Create SSE transport (without authentication header) │ │
│ │ 2. Try to connect │ │
│ │ 3. The server returns 401 Unauthorized │ │
│ │ 4. Authentication error detected │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. OAuth Discovery │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Extract OAuth configuration from server error response │ │
│ │ 2. Discover the authorization endpoint: │ │
│  │    - authorizationUrl                                 │     │
│  │    - tokenUrl                                         │     │
│ │ 3. Dynamic client registration (if supported) │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Trigger OAuth process │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Open the browser to the authorization URL │ │
│  │    https://accounts.google.com/o/oauth2/v2/auth?...    │     │
│ │ 2. The user logs in and agrees to the permissions │ │
│ │ 3. Google redirects to: │ │
│  │    http://localhost:7777/oauth/callback?code=xxx       │     │
│ │ 4. The local server receives the authorization code │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Exchange Token │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Use authorization code to exchange access token and refresh token │ │
│  │ 2. POST to tokenUrl:                                   │     │
│  │    {                                                    │     │
│  │      "grant_type": "authorization_code",               │     │
│  │      "code": "xxx",                                     │     │
│  │      "redirect_uri": "http://localhost:7777/oauth/callback",│
│  │      "client_id": "...",                                │     │
│  │      ...                                                 │     │
│  │    }                                                    │     │
│ │ 3. Save token to ~/.gemini/mcp-oauth-tokens.json │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. Retry connection (with token) │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Load token from storage │ │
│ │ 2. Add authentication header: │ │
│  │    Authorization: Bearer {access_token}               │     │
│ │ 3. Create SSE transport (with authentication header) │ │
│ │ 4. Connection successful!                                          │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. Subsequent use │
│  ┌────────────────────────────────────────────────────────┐     │
│ │ 1. Automatically load token from storage │ │
│ │ 2. If the token expires: │ │
│ │ - Use refresh token to refresh │ │
│ │ - save new token │ │
│ │ 3. If the refresh token also expires: │ │
│ │ - Retrigger OAuth flow │ │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Key technology implementation

### 5.1 Concurrent discovery

**Question**: How to efficiently discover multiple MCP servers?

**Solution**: Concurrent connections and discovery

```typescript
async discoverAllServers(): Promise<void> {
  const serverNames = Array.from(this.allServerConfigs.keys());

  // Connect to all servers concurrently
  await Promise.allSettled(
    serverNames.map((name) => this.maybeDiscoverMcpServer(name))
  );
}

async discover(cliConfig: McpContext): Promise<void> {
  // Concurrently obtain tools, prompt words and resources
  const [prompts, tools, resources] = await Promise.all([
    this.fetchPrompts(),
    this.discoverTools(cliConfig),
    this.discoverResources(),
  ]);

  // Register everything
  for (const prompt of prompts) {
    this.promptRegistry.registerPrompt(prompt);
  }
  for (const tool of tools) {
    this.toolRegistry.registerTool(tool);
  }
  this.updateResourceRegistry(resources);
}
```
**Advantages**:
- Multiple servers are connected at the same time without blocking startup
- Concurrent acquisition of tools, prompt words, and resources
- Failure of a single server does not affect other servers

---

### 5.2 Tool namespace

**Question**: How to avoid tool name conflicts from different servers?

**Solution**: Force namespace prefix

```typescript
export const MCP_TOOL_PREFIX = 'mcp_';
export const MCP_QUALIFIED_NAME_SEPARATOR = '_';

/**
 * All MCP tools must use fully qualified names
 * Format: mcp_{serverName}_{toolName}
 *
 * Example:
 * - mcp_context7_search
 * - mcp_github_create_issue
 * - mcp_google-workspace_list_documents
 */
export function formatMcpToolName(
  serverName: string,
  toolName?: string,
): string {
  if (serverName === '*' && !toolName) {
    return `${MCP_TOOL_PREFIX}*`;
  } else if (serverName === '*') {
    return `${MCP_TOOL_PREFIX}*_${toolName}`;
  } else if (!toolName) {
    return `${MCP_TOOL_PREFIX}${serverName}_*`;
  } else {
    return `${MCP_TOOL_PREFIX}${serverName}_${toolName}`;
  }
}
```
**warn**:

> Do not use underscores (`_`) in MCP server names. For example, use `my-server` instead of `my_server`.
> The policy parser splits fully qualified names at the first underscore after the `mcp_` prefix.
> If the server name contains underscores, the parser incorrectly interprets the server identity, causing wildcard rules and security policies to fail silently.

---

### 5.3 Environment variable cleaning

**Question**: How to prevent sensitive environment variables from being leaked to third-party MCP servers?

**Solution**: Automatic environment variable cleaning

```typescript
const ENV_SANITIZATION_CONFIG: EnvironmentSanitizationConfig = {
  // Variables that are always removed
  alwaysRemove: [
    'GEMINI_API_KEY',
    'GOOGLE_API_KEY',
    'GOOGLE_APPLICATION_CREDENTIALS',
  ],
  // Variables removed by pattern
  patterns: [
    '*TOKEN*',
    '*SECRET*',
    '*PASSWORD*',
    '*KEY*',
    '*AUTH*',
    '*CREDENTIAL*',
    '*CERT*',
    '*PRIVATE*',
  ],
  // Explicitly allowed variables (specified by the user in the configuration)
  allowed: new Set<string>(),
};

function sanitizeEnvironment(
  env: Record<string, string> | undefined,
  config: EnvironmentSanitizationConfig,
): Record<string, string> {
  const baseEnv = process.env;
  const sanitized: Record<string, string> = {};

  // Only copy explicitly allowed variables
  for (const [key, value] of Object.entries(baseEnv)) {
    // Check if any removal pattern matches
    const shouldRemove = config.patterns.some((pattern) =>
      matchWildcard(pattern, key),
    );

    if (!shouldRemove) {
      sanitized[key] = value;
    }
  }

  // Add environment variables explicitly specified by the user (trusted)
  if (env) {
    for (const [key, value] of Object.entries(env)) {
      sanitized[key] = expandEnvVars(value);
    }
  }

  return sanitized;
}
```
**Safety Principles**:

> If the variable is explicitly specified by the user in the configuration of a specific server, this constitutes informed consent, allowing that specific data to be shared with that server.

---

### 5.4 Tool filtering

**Question**: How to enable only certain tools of the MCP server?

**Solution**: `includeTools` and `excludeTools` configuration

```typescript
async discoverTools(
  cliConfig: McpContext,
  options?: { timeout?: number; signal?: AbortSignal },
): Promise<DiscoveredMCPTool[]> {
  this.assertConnected();

  // Get all tools
  const response = await this.client!.listTools(
    { timeout: options?.timeout, signal: options?.signal },
  );

  const tools: DiscoveredMCPTool[] = [];

  for (const mcpTool of response.tools || []) {
    //Apply filter
    if (!this.shouldIncludeTool(mcpTool.name)) {
      continue;
    }

    //Create tool
    const tool = new DiscoveredMCPTool(
      this.callableTool,
      this.serverName,
      mcpTool.name,
      mcpTool.description || '',
      mcpTool.inputSchema,
      this.messageBus,
      this.serverConfig.trust,
      undefined,  // isReadOnly
      undefined,  // nameOverride
      this.cliConfig,
      this.extensionName,
      this.extensionId,
      this.getToolAnnotations(mcpTool),
    );

    tools.push(tool);
  }

  return tools;
}

/**
 * Check if tools should be included
 */
private shouldIncludeTool(toolName: string): boolean {
  const config = this.serverConfig;

  // excludeTools takes precedence over includeTools
  if (config.excludeTools && config.excludeTools.includes(toolName)) {
    return false;
  }

  // If includeTools is specified, only include tools in the list
  if (config.includeTools && config.includeTools.length > 0) {
    return config.includeTools.includes(toolName);
  }

  // Includes all tools by default
  return true;
}
```
**Usage Example**:

```json
{
  "mcpServers": {
    "filtered-server": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "includeTools": ["safe_tool", "file_reader", "data_processor"],
      "excludeTools": ["dangerous_tool", "file_deleter"]
    }
  }
}
```
**Rules**:
- `excludeTools` takes precedence over `includeTools`
- If the tool is in both lists at the same time, it will be excluded
- If no filter is specified, all tools are included by default

---

### 5.5 Progress Notification

**Question**: How to handle progress updates for long-running MCP tool calls?

**Solution**: Progress token mapping and notification routing

```typescript
export class McpClient implements McpProgressReporter {
  private readonly progressTokenToCallId = new Map<string | number, string>();

  registerProgressToken(token: string | number, callId: string): void {
    this.progressTokenToCallId.set(token, callId);
  }

  unregisterProgressToken(token: string | number): void {
    this.progressTokenToCallId.delete(token);
  }

  private registerNotificationHandlers(): void {
    //Listen to progress notifications
    this.client?.setNotificationHandler(
      ProgressNotificationSchema,
      (notification) => {
        const { progressToken, progress, total } = notification.params;

        // Find the corresponding tool call
        const callId = this.progressTokenToCallId.get(progressToken);
        if (callId) {
          //Route progress updated to tool call
          this.routeProgressToCall(callId, { progress, total });
        }
      },
    );

    // Listen for changes in the tool list
    this.client?.setNotificationHandler(
      ToolListChangedNotificationSchema,
      async () => {
        await this.refreshTools();
      },
    );

    // Monitor resource list changes
    this.client?.setNotificationHandler(
      ResourceListChangedNotificationSchema,
      async () => {
        await this.refreshResources();
      },
    );

    // Monitor changes in the prompt word list
    this.client?.setNotificationHandler(
      PromptListChangedNotificationSchema,
      async () => {
        await this.refreshPrompts();
      },
    );
  }
}
```

---

### 5.6 Diagnostic message deduplication

**Question**: How to avoid displaying the same MCP error message repeatedly?

**Solution**: Intelligent Diagnosis and Duplication Removal System

```typescript
export class McpClientManager {
  private shownDiagnostics: Map<string, 'silent' | 'verbose'> = new Map();
  private userInteractedWithMcp: boolean = false;

  emitDiagnostic(
    severity: 'info' | 'warning' | 'error',
    message: string,
    error?: unknown,
    serverName?: string,
  ) {
    // Log errors
    if (severity === 'error' || severity === 'warning') {
      if (serverName) {
        this.lastErrors.set(serverName, message);
      }
    }

    //Remove duplicate keys
    const diagnosticKey = `${severity}:${message}`;
    const previousStatus = this.shownDiagnostics.get(diagnosticKey);

    // If the user has interacted, display detailed messages
    if (this.userInteractedWithMcp) {
      if (previousStatus === 'verbose') {
        debugLogger.debug(`Deduplicated verbose MCP diagnostic: ${diagnosticKey}`);
        return;
      }
      this.shownDiagnostics.set(diagnosticKey, 'verbose');
      coreEvents.emitFeedback(severity, message, error);
      return;
    }

    // Silent mode to reduce interruptions
    if (previousStatus) {
      debugLogger.debug(`Deduplicated silent MCP diagnostic: ${diagnosticKey}`);
      return;
    }
    this.shownDiagnostics.set(diagnosticKey, 'silent');
    debugLogger.log(`[MCP ${severity}] ${message}`, error);

    // show prompt
    if (severity === 'error' || severity === 'warning') {
      if (!this.hintShown) {
        this.hintShown = true;
        coreEvents.emitFeedback(
          'info',
          'MCP issues detected. Run /mcp list for status.',
        );
      }
    }
  }

  setUserInteractedWithMcp() {
    this.userInteractedWithMcp = true;
  }
}
```
**BEHAVIOR**:
1. **Silent Mode** (Default):
   - Each unique message is displayed only once
   - Log output without displaying notifications
   - If there is a problem, the prompt is displayed: "Run /mcp list for status"

2. **Detailed Mode** (after user interaction):
   - Triggered after the user runs the `/mcp` command
   - Show detailed notifications
   - Still deduplication, but more noticeable

---

### 5.7 Resource Reference

**Question**: How to reference the resources exposed by the MCP server in the conversation?

**Solution**: `@server://resource/path` syntax

```typescript
export class ResourceRegistry {
  private resourcesByServer: Map<string, MCPResource[]> = new Map();

  registerResource(resource: MCPResource): void {
    const serverResources = this.resourcesByServer.get(resource.serverName) || [];
    serverResources.push(resource);
    this.resourcesByServer.set(resource.serverName, serverResources);
  }

  findResource(uri: string): MCPResource | undefined {
    // Parse server://resource/path format
    const match = uri.match(/^([^:]+):\/\/(.+)$/);
    if (!match) {
      return undefined;
    }

    const [, serverName, resourcePath] = match;
    const serverResources = this.resourcesByServer.get(serverName);

    if (!serverResources) {
      return undefined;
    }

    return serverResources.find((r) => r.uri === resourcePath);
  }

  getAllResources(): MCPResource[] {
    const allResources: MCPResource[] = [];
    for (const resources of this.resourcesByServer.values()) {
      allResources.push(...resources);
    }
    return allResources;
  }
}
```
**Usage Example**:

```
# Reference resources in conversations
> Please analyze @google-drive://documents/my-report.docx

# Autocompletion will show available resources
> Please analyze @<Tab>
@context7://web/page-1
@google-drive://documents/report.docx
@notion://pages/my-page
```

---

## 6. Security mechanism

### 6.1 Trust mechanism

**Server Level Trust**:

```json
{
  "mcpServers": {
    "trusted-local-server": {
      "command": "python",
      "args": ["server.py"],
      "trust": true // bypass all confirmations
    }
  }
}
```
**Folder Level Trust**:

```typescript
if (this.cliConfig?.isTrustedFolder() && this.trust) {
  return false; // In the trusted folder, the trusted server does not require confirmation
}
```
### 6.2 Tool call confirmation

**Confirm options**:

```typescript
export enum ToolConfirmationOutcome {
  /** Execute once */
  ProceedOnce = 'proceed_once',
  /** Always allow this tool (session level) */
  ProceedAlwaysTool = 'proceed_always_tool',
  /** Always allow this server (session level) */
  ProceedAlwaysServer = 'proceed_always_server',
  /** Always allow and save to policy (persistence) */
  ProceedAlwaysAndSave = 'proceed_always_and_save',
  /** Cancel */
  Cancel = 'cancel',
}
```
**Confirmation interface**:

```
┌──────────────────────────────────────────────────────────┐
│ MCP tool call is about to be executed │
├──────────────────────────────────────────────────────────┤
│ Server: context7 │
│ Tools: search │
│                                                           │
│ Description: │
│ Search the web using Context7 API                        │
│                                                           │
│ Parameters: │
│ {                                                         │
│   "query": "Python MCP tutorial",                         │
│   "limit": 10                                             │
│ }                                                         │
│                                                           │
│ [Do it once] [Always allow this tool] [Always allow this server] [Cancel] │
└──────────────────────────────────────────────────────────┘
```
### 6.3 Policy Engine

**Policy file** (`~/.gemini/policy.toml`):

```toml
#Always allow all tools of the context7 server
[[mcp_rules]]
name = "context7_*"
action = "auto_approve"

# Deny dangerous tools
[[mcp_rules]]
name = "mcp_*_delete_*"
action = "auto_deny"

# Ask for confirmation
[[mcp_rules]]
name = "mcp_github_*"
action = "manual_confirm"
```
### 6.4 Environment variable cleaning

**Automatically clean up sensitive variables**:

```typescript
const ENV_SANITIZATION_CONFIG: EnvironmentSanitizationConfig = {
  alwaysRemove: [
    'GEMINI_API_KEY',
    'GOOGLE_API_KEY',
    'GOOGLE_APPLICATION_CREDENTIALS',
  ],
  patterns: [
    '*TOKEN*',
    '*SECRET*',
    '*PASSWORD*',
    '*KEY*',
    '*AUTH*',
    '*CREDENTIAL*',
    '*CERT*',
    '*PRIVATE*',
  ],
};
```

---

## 7. Usage examples

### 7.1 Add Context7 search tool

```bash
# 1. Add Context7 SSE server
gemini mcp add --transport sse context7 https://mcp.context7.com/sse \
  --header "CONTEXT7_API_KEY: your-api-key"

# 2. List all servers
gemini mcp list

# 3. Start gemini
gemini

# 4. Search using Context7
> Search Python MCP tutorials using context7

# AI will call the mcp_context7_search tool and ask for your approval
# After approval, AI will display the search results
```
### 7.2 Add Google Workspace integration

```bash
# 1. Add Google Workspace MCP server
gemini mcp add google-workspace \
  https://workspace-mcp.googleapis.com/sse

# 2. The first connection will trigger OAuth
# The browser will open, log in and authorize

# 3. Use Google Tools
gemini

> List my Google Drive documents
> Create a new Google Doc: MCP Integration Guide
```
### 7.3 Add local Python MCP server

```bash
# 1. Add stdio server
gemini mcp add python-tools python -m my_mcp_server \
  --cwd ./mcp-servers/python \
  -e API_KEY="$MY_API_TOKEN" \
  -e LOG_LEVEL="debug" \
  --include-tools safe_tool,file_reader \
  --exclude-tools dangerous_tool

# 2. Test connection
gemini mcp list

# 3. Use Python tools
gemini

> Use safe_tool to process data
> Read files accessible by file_reader
```
### 7.4 Using MCP Prompt Words

```bash
# MCP servers can expose prompt words as slash commands
gemini

# List available prompt words
/mcp

# Use prompt words
/poem-writer --title="Gemini CLI" --mood="reverent"

# Or use positional parameters
/poem-writer "Gemini CLI" reverent
```
### 7.5 Reference MCP resources

```bash
gemini

# Reference documents in Google Drive
> Please summarize the contents of @google-drive://documents/my-report.docx

# Reference Notion page
> Analyze the tasks of @notion://pages/my-project-plan

# Reference the web page captured by Context7
> Compare @context7://web/page-1 and @context7://web/page-2
```

---

## 8. Comparison with Kimi CLI

### 8.1 Architecture comparison

|characteristic| Gemini CLI | Kimi CLI |
|------|-----------|----------|
|**language**| TypeScript/JavaScript | Python |
| **MCP SDK** | @modelcontextprotocol/sdk | fastmcp |
|**Transmission Type**| Stdio, SSE, HTTP | Stdio, HTTP |
| **OAuth** |✅ Full support (auto-discovery)|✅ Support (manual configuration)|
|**Tool naming**|`mcp_server_tool` (mandatory)|Original tool name|
|**Resource Support**|✅ Full support|❌ Not supported|
|**Prompt word support**|✅ Full support|❌ Not supported|
|**Progress Notification**|✅ Support|❌ Not supported|
|**Tool filter**| ✅ include/exclude |❌ Not supported|
|**Environmental Cleanup**|✅Automatic cleaning|❌ Not cleaning|

### 8.2 Configuration comparison

**Gemini CLI**:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/sse",
      "type": "sse",
      "headers": {"CONTEXT7_API_KEY": "your-key"},
      "timeout": 60000,
      "trust": false,
      "description": "Context7 search server",
      "includeTools": ["search"],
      "excludeTools": ["advanced_search"]
    }
  }
}
```

**Kimi CLI**:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "transport": "http",
      "headers": {"CONTEXT7_API_KEY": "your-key"}
    }
  }
}
```
### 8.3 Command comparison

|operate| Gemini CLI | Kimi CLI |
|------|-----------|----------|
|Add server| `gemini mcp add` | `kimi mcp add` |
|List servers| `gemini mcp list` | `kimi mcp list` |
|Remove server| `gemini mcp remove` | `kimi mcp remove` |
|Enable server| `gemini mcp enable` |❌ Not supported|
|Disable server| `gemini mcp disable` |❌ Not supported|
|OAuth authorization|Automatic trigger| `kimi mcp auth` |
|test connection| `gemini mcp list` | `kimi mcp test` |

---

## 9. Summary and reflections

### 9.1 Architecture Highlights

1. **Enterprise-level design**
   - Full OAuth support (auto-discovery)
   - Google certification integration
   - Service account simulation
   - IAP protected service support

2. **Rich functions**
   - Three major functions: tools, prompt words, and resources
   - Progress notification support
   - Tool filtering (include/exclude)
   - Dynamic list updates

3. **Safety first**
   - Automatic environment variable cleaning
   - Multi-layer confirmation mechanism
   - Strategy engine integration
   - Trust folder support

4. **User Experience**
   - Intelligent diagnosis and deduplication
   - Silent boot mode
   - Detailed error reporting
   - Resource reference syntax

5. **Scalability**
   - Expansion system
   - Plug-in architecture
   - Multi-tenant support

### 9.2 Designs that can be learned from

1. **Namespace Strategy**
   - Force `mcp_` prefix to avoid conflicts
   - Fully qualified name format
   - Clear hierarchy

2. **Intelligent Diagnosis**
   - Silent/verbose dual mode
   - Deduplication mechanism
   - User interaction awareness

3. **Environmental Cleanup**
   - Automatically identify sensitive variables
   - Pattern matching
   - Explicitly allow overrides

4. **OAuth integration**
   - Automatic discovery
   - Dynamic client registration
   - Token refresh

### 9.3 Room for improvement

1. **Performance Optimization**
   - Connection pool reuse
   - Tool call cache
   - Incremental discovery

2. **Monitoring**
   - Performance indicator collection
   - Error rate statistics
   - Usage analytics

3. **Observability**
   - Structured logs
   - Debug mode
   - Tracking support

### 9.4 Applicable scenarios

Gemini CLI's MCP implementation is particularly suitable for the following scenarios:

1. **Corporate Environment**
   - Google Workspace integration
   - Internal API access
   -Multi-layered security controls

2. **Development Workflow**
   - GitHub/GitLab integration
   - CI/CD automation
   - Code review

3. **Data processing**
   - Database query
   - ETL process
   - Report generation

4. **Collaboration Tools**
   - Document management
   - Task tracking
   - Knowledge base

---

## 10. The complete code flow of LLM calling MCP tool

This section shows in detail the complete code link of how LLM calls the MCP tool in Gemini CLI, from the LLM generation tool call to the final execution of the MCP server call.

### 10.1 Core call link

#### DiscoveredMCPToolInvocation.execute - MCP tool executor

**Location**: `packages/core/src/tools/mcp-tool.ts:262-325`

```typescript
async execute(signal: AbortSignal): Promise<ToolResult> {
    // 1. Mark user interaction with MCP (for diagnostic display)
    this.cliConfig?.setUserInteractedWithMcp?.();

    // 2. Build FunctionCall (MCP tool call format)
    const functionCalls: FunctionCall[] = [
      {
        name: this.serverToolName, //Original MCP tool name (without mcp_ prefix)
        args: this.params, // Parsed parameters
      },
    ];

    // 3. Racing with AbortSignal to support cancellation operations
    const rawResponseParts = await new Promise<Part[]>((resolve, reject) => {
      if (signal.aborted) {
        const error = new Error('Tool call aborted');
        error.name = 'AbortError';
        reject(error);
        return;
      }

      const onAbort = () => {
        cleanup();
        const error = new Error('Tool call aborted');
        error.name = 'AbortError';
        reject(error);
      };

      const cleanup = () => {
        signal.removeEventListener('abort', onAbort);
      };

      signal.addEventListener('abort', onAbort, { once: true });

      // 4. Call the underlying MCP tool
      this.mcpTool
        .callTool(functionCalls)
        .then((res) => {
          cleanup();
          resolve(res);
        })
        .catch((err) => {
          cleanup();
          reject(err);
        });
    });

    // 5. Check MCP tool errors
    if (this.isMCPToolError(rawResponseParts)) {
      const errorMessage = `MCP tool '${
        this.serverToolName
      }' reported tool error for function call: ${safeJsonStringify(
        functionCalls[0],
      )} with response: ${safeJsonStringify(rawResponseParts)}`;

      return {
        llmContent: errorMessage,
        returnDisplay: `Error: MCP tool '${this.serverToolName}' reported an error.`,
        error: {
          message: errorMessage,
          type: ToolErrorType.MCP_TOOL_ERROR,
        },
      };
    }

    // 6. Convert MCP response to LLM format
    const transformedParts = transformMcpContentToParts(rawResponseParts);

    return {
      llmContent: transformedParts,
      returnDisplay: getStringifiedResultForDisplay(rawResponseParts),
    };
  }
```
**Key Points**:
- **Cancellation Support**: Cancellation of tool calls via AbortSignal support
- **Error Detection**: Check the `isError` flag returned by the MCP tool
- **Format Conversion**: Convert MCP ContentBlock to Gemini API Part format
- **User interaction flag**: records user interaction with MCP, affecting diagnostic display mode

#### getConfirmationDetails - User approval mechanism

**Location**: `packages/core/src/tools/mcp-tool.ts:193-231`

```typescript
protected override async getConfirmationDetails(
  _abortSignal: AbortSignal,
): Promise<ToolCallConfirmationDetails | false> {
  const serverAllowListKey = this.serverName;
  const toolAllowListKey = `${this.serverName}.${this.serverToolName}`;

  // 1. Check the trust folder
  if (this.cliConfig?.isTrustedFolder() && this.trust) {
    return false; // The server has been trusted, no confirmation is required
  }

  // 2. Check the whitelist
  if (
    DiscoveredMCPToolInvocation.allowlist.has(serverAllowListKey) ||
    DiscoveredMCPToolInvocation.allowlist.has(toolAllowListKey)
  ) {
    return false; // Already in the whitelist, no confirmation required
  }

  // 3. User confirmation is required
  const confirmationDetails: ToolMcpConfirmationDetails = {
    type: 'mcp',
    title: 'Confirm MCP Tool Execution',
    serverName: this.serverName,
    toolName: this.serverToolName, // Original tool name
    toolDisplayName: this.displayName, // Fully qualified name (mcp_server_tool)
    toolArgs: this.params,
    toolDescription: this.toolDescription,
    toolParameterSchema: this.toolParameterSchema,
    onConfirm: async (outcome: ToolConfirmationOutcome) => {
      // 4. Handle user selection
      if (outcome === ToolConfirmationOutcome.ProceedAlwaysServer) {
        // Allow all tools for the entire server
        DiscoveredMCPToolInvocation.allowlist.add(serverAllowListKey);
      } else if (outcome === ToolConfirmationOutcome.ProceedAlwaysTool) {
        // Only allow this specific tool
        DiscoveredMCPToolInvocation.allowlist.add(toolAllowListKey);
      } else if (outcome === ToolConfirmationOutcome.ProceedAlwaysAndSave) {
        // Permanently allow and save to policy file
        DiscoveredMCPToolInvocation.allowlist.add(toolAllowListKey);
        // Policy updates are handled by the scheduler center
      }
    },
  };

  return confirmationDetails;
}
```
**Key Points**:
- **Trust Folder**: In trust folders, confirmation can be skipped
- **Whitelist Mechanism**: Maintain a list of approved tools in memory
- **Fine-grained control**: can approve the entire server or individual tools
- **Persistence Option**: Supports saving approvals to policy files

### 10.2 Process of tool registration to LLM

#### MCP tool discovery and registration

**Location**: `packages/core/src/tools/mcp-client.ts:800-900`

```typescript
async discover(config: Config): Promise<void> {
  // 1. List all tools of MCP server
  const response = await this.client?.listTools({});

  if (!response?.tools) {
    return;
  }

  // 2. Create DiscoveredMCPTool for each MCP tool
  const discoveredTools: DiscoveredMCPTool[] = [];

  for (const mcpTool of response.tools) {
    // 3. Generate fully qualified tool name (mcp_server_tool)
    const fullyQualifiedName = generateValidName(
      `${this.serverName}${MCP_QUALIFIED_NAME_SEPARATOR}${mcpTool.name}`
    );

    // 4. Create tool instance
    const tool = new DiscoveredMCPTool(
      this.createCallableTool(mcpTool), // CallableTool wrapper
      this.serverName, // server name
      mcpTool.name, // Original tool name
      mcpTool.description, // description
      mcpTool.inputSchema, // JSON Schema parameters
      this.messageBus,
      this.serverConfig?.trust, // Trust flag
      mcpTool.name?.startsWith('read_'), // read-only judgment
      undefined,                          // nameOverride
      this.cliConfig,
      this.serverConfig?.extension?.name,
      this.serverConfig?.extension?.id,
      {
        _serverName: this.serverName, // Tool annotation
      },
    );

    discoveredTools.push(tool);
  }

  // 5. Register to ToolRegistry
  for (const tool of discoveredTools) {
    this.toolRegistry.registerTool(tool);
  }
}
```
#### Convert tool definition to LLM format

**Location**: `packages/core/src/tools/mcp-tool.ts:332-367`

```typescript
export class DiscoveredMCPTool extends BaseDeclarativeTool<ToolParams, ToolResult> {
  constructor(
    private readonly mcpTool: CallableTool,
    readonly serverName: string,
    readonly serverToolName: string,
    description: string,
    override readonly parameterSchema: unknown,  // JSON Schema
    messageBus: MessageBus,
    readonly trust?: boolean,
    isReadOnly?: boolean,
    nameOverride?: string,
    private readonly cliConfig?: McpContext,
    override readonly extensionName?: string,
    override readonly extensionId?: string,
    override readonly _toolAnnotations?: Record<string, unknown>,
  ) {
    super(
      // Tool name: mcp_server_tool format
      nameOverride ??
        generateValidName(
          `${serverName}${MCP_QUALIFIED_NAME_SEPARATOR}${serverToolName}`
        ),

      // Display name: toolName (serverName MCP Server)
      `${serverToolName} (${serverName} MCP Server)`,

      description,
      Kind.Other,
      parameterSchema, // Directly pass the JSON Schema of MCP
      messageBus,
      true,  // isOutputMarkdown
      false, // canUpdateOutput
      extensionName,
      extensionId,
    );

    this._isReadOnly = isReadOnly;
  }

  // Return the FunctionDeclaration format of the tool
  getFunctionDeclaration(): FunctionDeclaration {
    return {
      name: this.name,
      description: this.description,
      parameters: this.parameterSchema as FunctionDeclaration['parameters'],
    };
  }
}
```
### 10.3 Complete call sequence diagram

```
User input "Search for Python MCP tutorial using context7"
    ↓
Gemini CLI scheduler
    ↓
LLM generates response
    ↓
Gemini API calls
    POST /v1/models/gemini-2.0-flash-exp:generateContent
{
    "tools": [
        {
            "functionDeclarations": [
                {
                    "name": "mcp_context7_search",
                    "description": "search (context7 MCP Server)",
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
    ]
}
    ↓
Gemini API returns response
    ├── Content: "Okay, let me search for you..."
    └── FunctionCall: {
            "name": "mcp_context7_search",
            "args": {"query": "Python MCP Tutorial", "limit": 10}
         }
    ↓
Scheduler parsing FunctionCall
    ↓
Create DiscoveredMCPToolInvocation
    ↓
getConfirmationDetails()
    ↓
Check trust/whitelist
    ↓
Confirmation required → Show confirmation dialog
    ↓
User clicks "Allow"
    ↓
execute(abortSignal)
    ↓
mcpTool.callTool([{
    name: "search", // Original tool name
    args: {query: "Python MCP Tutorial", limit: 10}
}])
    ↓
MCP server returns results
    {
        "content": [
            {"type": "text", "text": "10 related results found..."}
        ]
    }
    ↓
transformMcpContentToParts()
    ↓
Convert to Gemini Part format
    ↓
ToolResult {
    llmContent: [{text: "10 related results found..."}],
    returnDisplay: "10 related results found..."
}
    ↓
Add to LLM context
    ↓
Continue to next round of LLM calls (containing tool results)
```
### 10.4 Key data structure conversion

#### MCP ContentBlock → Gemini Part

**Location**: `packages/core/src/tools/mcp-tool.ts:494-523`

```typescript
function transformMcpContentToParts(sdkResponse: Part[]): Part[] {
  const funcResponse = sdkResponse?.[0]?.functionResponse;
  const mcpContent = funcResponse?.response?.['content'] as McpContentBlock[];
  const toolName = funcResponse?.name || 'unknown tool';

  if (!Array.isArray(mcpContent)) {
    return [{ text: '[Error: Could not parse tool response]' }];
  }

  const transformed = mcpContent.flatMap(
    (block: McpContentBlock): Part | Part[] | null => {
      switch (block.type) {
        case 'text':
          // text content
          return { text: block.text };

        case 'image':
        case 'audio':
          // Media content: add description + inlineData
          return [
            {
              text: `[Tool '${toolName}' provided the following ${
                block.type
              } data with mime-type: ${block.mimeType}]`,
            },
            {
              inlineData: {
                mimeType: block.mimeType,
                data: block.data,
              },
            },
          ];

        case 'resource':
          // Resource content
          const resource = block.resource;
          if (resource?.text) {
            return { text: resource.text };
          }
          if (resource?.blob) {
            return [
              {
                text: `[Tool '${toolName}' provided embedded resource with mime-type: ${resource.mimeType || 'unknown'}]`,
              },
              {
                inlineData: {
                  mimeType: resource.mimeType || 'application/octet-stream',
                  data: resource.blob,
                },
              },
            ];
          }
          return null;

        case 'resource_link':
          // Resource link
          return {
            text: `Resource Link: ${block.title || block.name} at ${block.uri}`,
          };

        default:
          return null;
      }
    },
  );

  return transformed.filter((part): part is Part => part !== null);
}
```
**Supported MCP content types**:
1. **text**: plain text
2. **image/audio**: media data (base64)
3. **resource**: embedded resource (text or binary)
4. **resource_link**: Resource reference (URI)

#### Tool name mapping

```typescript
//Tool name returned by MCP server
const serverToolName = "search";

// Fully qualified name generated by Gemini CLI
const fullyQualifiedName = "mcp_context7_search";

//Tool name seen by LLM
const toolName = "mcp_context7_search";

// Use the original name when calling the MCP server
const mcpCallName = "search";
```
### 10.5 Comparison with Kimi CLI

|characteristic| Gemini CLI | Kimi CLI |
|------|-----------|----------|
|**Tool name format**| `mcp_{server}_{tool}` |Original tool name|
|**LLM Integration**| Google GenAI SDK |kosong frame|
|**Tool Registration**| ToolRegistry.registerTool() | Toolset.add() |
|**User Approval**| getConfirmationDetails() | approval.request() |
|**Support withdrawn**|AbortSignal Racing| asyncio.CancelledError |
|**Result Conversion**| transformMcpContentToParts() | convert_mcp_tool_result() |
|**Content Type**|4 types (text, image, audio, resource)|2 types (text, image)|
|**Progress Notification**|Support (registerProgressToken)|Not supported|
|**RESOURCE ACCESS**|support|Not supported|
|**Prompt word template**|support|Not supported|

---

## Reference resources

- **GitHub repository**: [https://github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
- **Official Documents**: [https://geminicli.com/docs](https://geminicli.com/docs)
- **MCP protocol**: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
- **MCP SDK**: [https://github.com/modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)

---

## Appendix

### A. Core code file list

```
packages/core/src/
├── tools/
│ ├── mcp-client.ts # MCP client core (1000+ lines)
│ ├── mcp-client-manager.ts # MCP client manager (500+ lines)
│ ├── mcp-tool.ts # MCP tool package (600+ lines)
│ └── tool-registry.ts # Tool registry
├── mcp/
│ ├── google-auth-provider.ts # Google Authentication
│ ├── sa-impersonation-provider.ts # Service account imitation
│ ├── oauth-provider.ts # OAuth provider
│ └── oauth-token-storage.ts # Token storage
├── prompts/
│ └── prompt-registry.ts # Prompt word registry
└── resources/
    └── resource-registry.ts # Resource registry

packages/cli/src/commands/mcp/
├── add.ts # Add server (250+ lines)
├── remove.ts # Remove server
├── list.ts # List servers
└── enableDisable.ts # Enable/disable server
```
### B. Configuration file example

**~/.gemini/settings.json**:```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/sse",
      "type": "sse",
      "headers": {
        "CONTEXT7_API_KEY": "your-key"
      }
    },
    "google-workspace": {
      "httpUrl": "https://my-gcp-service.run.app/mcp",
      "authProviderType": "google_credentials",
      "oauth": {
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
      }
    }
  },
  "mcp": {
    "allowed": ["my-trusted-server"],
    "excluded": ["experimental-server"]
  }
}
```
### C. Related dependencies

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.4",
    "@google/gemini-cli-core": "workspace:*",
    "google-auth-library": "^9.0.0"
  }
}
```

---

**Documentation version**: 1.0
**Last updated**: 2026-03-11
**Author**: AI Assistant
**License**: Apache 2.0 License
