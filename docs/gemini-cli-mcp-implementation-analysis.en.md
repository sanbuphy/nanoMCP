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
│                         用户交互层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ CLI 命令     │  │ 交互式 Shell │  │ VSCode 扩展  │          │
│  │ gemini mcp   │  │  /mcp 命令   │  │  IDE 集成    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         配置管理层                               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ ~/.gemini/settings.json (用户配置)                     │     │
│  │ .gemini/settings.json (项目配置)                       │     │
│  │ mcpServers 配置                                         │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         核心处理层                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ McpClientManager │  │   McpClient      │  │ Discovered   │  │
│  │  (生命周期管理)  │  │  (单服务器管理)  │  │ MCPTool      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  ToolRegistry    │  │  PromptRegistry │  │Resource      │  │
│  │  (工具注册表)    │  │  (提示词注册)   │  │Registry      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      MCP SDK 客户端层                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ @modelcontextprotocol/sdk/client/Client                │     │
│  │ - StdioClientTransport (本地进程)                       │     │
│  │ - SSEClientTransport (Server-Sent Events)              │     │
│  │ - StreamableHTTPClientTransport (HTTP 流式传输)        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      外部 MCP 服务器层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │自定义服务器│  │ GitHub   │  │ Notion   │  │ Google   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```
### 2.2 Core code structure

```
packages/core/src/
├── tools/
│   ├── mcp-client.ts           # MCP 客户端核心 (1000+ 行)
│   ├── mcp-client-manager.ts   # MCP 客户端管理器 (500+ 行)
│   ├── mcp-tool.ts             # MCP 工具封装 (600+ 行)
│   └── tool-registry.ts        # 工具注册表
├── mcp/
│   ├── google-auth-provider.ts         # Google 认证提供者
│   ├── sa-impersonation-provider.ts    # 服务账号模拟
│   ├── oauth-provider.ts               # OAuth 提供者
│   └── oauth-token-storage.ts          # OAuth Token 存储
├── prompts/
│   └── prompt-registry.ts      # 提示词注册表
└── resources/
    └── resource-registry.ts    # 资源注册表

packages/cli/src/commands/mcp/
├── add.ts                      # 添加服务器命令
├── remove.ts                   # 移除服务器命令
├── list.ts                     # 列出服务器命令
└── enableDisable.ts            # 启用/禁用命令
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

  // 解析 headers
  const headers = header?.reduce((acc, curr) => {
    const [key, ...valueParts] = curr.split(':');
    const value = valueParts.join(':').trim();
    if (key.trim() && value) {
      acc[key.trim()] = value;
    }
    return acc;
  }, {} as Record<string, string>);

  // 根据传输类型构建配置
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

  // 保存配置
  const mcpServers = settings.forScope(settingsScope).settings.mcpServers || {};
  mcpServers[name] = newServer as MCPServerConfig;
  settings.setValue(settingsScope, 'mcpServers', mcpServers);
}
```
**Usage Example**:

```bash
# 添加 stdio 服务器
gemini mcp add python-server python -m my_mcp_server -- --port 8080

# 添加 SSE 服务器
gemini mcp add --transport sse context7 https://mcp.context7.com/sse

# 添加 HTTP 服务器（带认证）
gemini mcp add --transport http \
  --header "Authorization: Bearer $TOKEN" \
  secure-server https://api.example.com/mcp

# 添加信任的服务器
gemini mcp add --trust local-tools python server.py

# 添加带工具过滤的服务器
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
   * 发现所有配置的 MCP 服务器
   */
  async discoverAllServers(): Promise<void> {
    if (this.discoveryState === MCPDiscoveryState.IN_PROGRESS) {
      return this.discoveryPromise;
    }

    this.discoveryState = MCPDiscoveryState.IN_PROGRESS;

    this.discoveryPromise = (async () => {
      const serverNames = Array.from(this.allServerConfigs.keys());

      // 并发连接所有服务器
      await Promise.allSettled(
        serverNames.map((name) => this.maybeDiscoverMcpServer(name))
      );

      this.discoveryState = MCPDiscoveryState.COMPLETED;
    })();

    return this.discoveryPromise;
  }

  /**
   * 发现单个 MCP 服务器
   */
  private async maybeDiscoverMcpServer(
    serverName: string,
    config?: MCPServerConfig,
  ): Promise<void> {
    // 检查是否被阻止
    if (this.isBlocked(serverName)) {
      this.blockedMcpServers.push({
        name: serverName,
        extensionName: config?.extension?.name || 'unknown',
      });
      return;
    }

    // 检查是否已禁用
    if (this.isDisabled(serverName)) {
      return;
    }

    // 创建或获取客户端
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

    // 连接并发现工具
    try {
      await client.connect();
      await client.discover(this.cliConfig);
    } catch (error) {
      this.emitDiagnostic('error', `Failed to connect to ${serverName}`, error);
    }
  }

  /**
   * 发射诊断消息
   */
  emitDiagnostic(
    severity: 'info' | 'warning' | 'error',
    message: string,
    error?: unknown,
    serverName?: string,
  ) {
    // 记录错误
    if (severity === 'error' || severity === 'warning') {
      if (serverName) {
        this.lastErrors.set(serverName, message);
      }
    }

    // 去重
    const diagnosticKey = `${severity}:${message}`;
    const previousStatus = this.shownDiagnostics.get(diagnosticKey);

    // 如果用户已交互，显示详细消息
    if (this.userInteractedWithMcp) {
      if (previousStatus === 'verbose') {
        return; // 已显示过
      }
      this.shownDiagnostics.set(diagnosticKey, 'verbose');
      coreEvents.emitFeedback(severity, message, error);
      return;
    }

    // 静默模式，减少打扰
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
  DISCONNECTED = 'disconnected',   // 未连接或错误
  DISCONNECTING = 'disconnecting', // 正在断开
  CONNECTING = 'connecting',       // 正在连接
  CONNECTED = 'connected',         // 已连接
  BLOCKED = 'blocked',             // 被阻止
  DISABLED = 'disabled',           // 已禁用
}
```
**Discovery State** (`MCPDiscoveryState`):

```typescript
export enum MCPDiscoveryState {
  NOT_STARTED = 'not_started',     // 未开始
  IN_PROGRESS = 'in_progress',     // 进行中
  COMPLETED = 'completed',         // 已完成
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
   * 连接到 MCP 服务器
   */
  async connect(): Promise<void> {
    if (this.status !== MCPServerStatus.DISCONNECTED) {
      throw new Error(`Cannot connect: current state is ${this.status}`);
    }

    this.updateStatus(MCPServerStatus.CONNECTING);

    try {
      // 创建客户端和传输
      this.client = await connectToMcpServer(
        this.clientVersion,
        this.serverName,
        this.serverConfig,
        this.debugMode,
        this.workspaceContext,
        this.cliConfig,
      );

      // 注册通知处理器
      this.registerNotificationHandlers();

      // 错误处理
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
   * 发现工具和提示词
   */
  async discover(cliConfig: McpContext): Promise<void> {
    this.assertConnected();

    // 并发获取工具、提示词和资源
    const prompts = await this.fetchPrompts();
    const tools = await this.discoverTools(cliConfig);
    const resources = await this.discoverResources();

    // 检查是否有可用内容
    if (prompts.length === 0 && tools.length === 0 && resources.length === 0) {
      throw new Error('No prompts, tools, or resources found on the server.');
    }

    // 注册到相应的注册表
    for (const prompt of prompts) {
      this.promptRegistry.registerPrompt(prompt);
    }
    for (const tool of tools) {
      this.toolRegistry.registerTool(tool);
    }
    this.toolRegistry.sortTools();

    // 更新资源注册表
    this.updateResourceRegistry(resources);

    // 验证策略规则中的 MCP 工具名称
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
      // 策略引擎可能不可用，静默跳过
    }
  }

  /**
   * 断开连接
   */
  async disconnect(): Promise<void> {
    if (this.status !== MCPServerStatus.CONNECTED) {
      return;
    }

    // 从所有注册表中移除
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
  // 创建传输
  const transport = await createTransport(
    serverName,
    serverConfig,
    debugMode,
    workspaceContext,
    cliConfig,
  );

  // 创建客户端
  const client = new Client({
    name: `gemini-cli-${clientVersion}`,
    version: clientVersion,
  }, {
    // 使用 Ajv 进行 JSON Schema 验证
    validator: new AjvJsonSchemaValidator(),
  });

  // 连接
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

  // 根据配置创建相应的传输
  if (serverConfig.url) {
    // SSE 传输
    const options: SSEClientTransportOptions = {
      url: new URL(serverConfig.url),
      eventSourceOptions: {
        headers: serverConfig.headers,
      },
    };

    // 添加 OAuth 认证
    if (serverConfig.authProviderType) {
      const authProvider = createAuthProvider(serverConfig, cliConfig);
      options.eventSourceOptions.headers = {
        ...options.eventSourceOptions.headers,
        ...(await authProvider.getHeaders()),
      };
    }

    transport = new SSEClientTransport(options);
  } else if (serverConfig.httpUrl) {
    // HTTP 流式传输
    const options: StreamableHTTPClientTransportOptions = {
      url: new URL(serverConfig.httpUrl),
      headers: serverConfig.headers,
    };

    // 添加 OAuth 认证
    if (serverConfig.authProviderType) {
      const authProvider = createAuthProvider(serverConfig, cliConfig);
      options.headers = {
        ...options.headers,
        ...(await authProvider.getHeaders()),
      };
    }

    transport = new StreamableHTTPClientTransport(options);
  } else if (serverConfig.command) {
    // Stdio 传输
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
 * 生成完全限定名称
 * 格式: mcp_{serverName}_{toolName}
 *
 * 示例:
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
 * 生成有效的工具名称
 * - 强制添加 mcp_ 前缀
 * - 替换无效字符为下划线
 * - 确保以字母或下划线开头
 * - 截断过长的名称（最大 64 字符）
 */
export function generateValidName(name: string) {
  // 强制添加 mcp_ 前缀
  let validToolname = name.startsWith('mcp_') ? name : `mcp_${name}`;

  // 替换无效字符
  validToolname = validToolname.replace(/[^a-zA-Z0-9_\-.:]/g, '_');

  // 确保以字母或下划线开头
  if (/^[^a-zA-Z_]/.test(validToolname)) {
    validToolname = `_${validToolname}`;
  }

  // 截断过长的名称
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
      // 工具名称（带前缀）
      nameOverride ??
        generateValidName(
          `${serverName}${MCP_QUALIFIED_NAME_SEPARATOR}${serverToolName}`
        ),
      // 显示名称
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

    // 信任的文件夹 + 信任的服务器
    if (this.cliConfig?.isTrustedFolder() && this.trust) {
      return false; // 无需确认
    }

    // 检查白名单
    if (
      DiscoveredMCPToolInvocation.allowlist.has(serverAllowListKey) ||
      DiscoveredMCPToolInvocation.allowlist.has(toolAllowListKey)
    ) {
      return false; // 已在白名单中
    }

    // 需要用户确认
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
          // 持久化策略更新由调度器集中处理
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

    // 与中止信号竞争
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

    // 检查是否为错误
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

    // 转换响应
    const transformedParts = transformMcpContentToParts(rawResponseParts);

    return {
      llmContent: transformedParts,
      returnDisplay: getStringifiedResultForDisplay(rawResponseParts),
    };
  }

  /**
   * 检查响应是否包含工具错误
   */
  isMCPToolError(rawResponseParts: Part[]): boolean {
    const functionResponse = rawResponseParts?.[0]?.functionResponse;
    const response = functionResponse?.response;

    if (response) {
      // 检查顶层 isError（MCP 规范兼容）
      const isErrorTop = (response as { isError?: boolean | string }).isError;
      if (isErrorTop === true || isErrorTop === 'true') {
        return true;
      }

      // 检查嵌套错误对象（向后兼容）
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
 * 将 MCP 内容块转换为 GenAI Part 数组
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
│                   1. 用户启动 gemini                            │
│                  $ gemini                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               2. 加载配置 (settings.json)                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 加载源：                                               │     │
│  │  • ~/.gemini/settings.json (用户级)                   │     │
│  │  • .gemini/settings.json (项目级)                     │     │
│  │  • 扩展配置                                           │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 解析配置：                                             │     │
│  │  • mcpServers: 服务器列表                             │     │
│  │  • mcp.allowed: 允许的服务器                          │     │
│  │  • mcp.excluded: 排除的服务器                         │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│           3. 创建 McpClientManager 和注册表                      │
│  toolRegistry = new ToolRegistry()                              │
│  promptRegistry = new PromptRegistry()                          │
│  resourceRegistry = new ResourceRegistry()                      │
│  mcpManager = new McpClientManager(...)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              4. 开始 MCP 发现 (后台异步)                         │
│  mcpManager.discoverAllServers()                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         5. 遍历配置的服务器                                      │
│  for serverName in Object.keys(mcpServers):                     │
│    ┌────────────────────────────────────────────────────────┐   │
│    │ 检查：                                                  │   │
│    │  • 是否在 allowed 列表中？                             │   │
│    │  • 是否在 excluded 列表中？                            │   │
│    │  • 是否被启用？                                        │   │
│    │  • 是否被阻止（管理策略）？                            │   │
│    └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         6. 为每个服务器创建 McpClient                            │
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
│              7. 并发连接所有服务器                               │
│  Promise.allSettled([                                          │
│    client1.connect(),                                           │
│    client2.connect(),                                           │
│    client3.connect(),                                           │
│    ...                                                          │
│  ])                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         8. 对于每个连接成功的服务器                              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 并发发现：                                             │     │
│  │  • tools = client.discoverTools()                     │     │
│  │  • prompts = client.fetchPrompts()                    │     │
│  │  • resources = client.discoverResources()             │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              9. 工具发现和注册                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 对于每个工具：                                          │     │
│  │  1. 获取工具定义（名称、描述、参数 schema）             │     │
│  │  2. 应用过滤器（includeTools/excludeTools）            │     │
│  │  3. 生成完全限定名称：mcp_{server}_{tool}             │     │
│  │  4. 清理和验证 schema                                  │     │
│  │  5. 创建 DiscoveredMCPTool 实例                        │     │
│  │  6. 注册到 ToolRegistry                                │     │
│  │  7. 排序工具                                           │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              10. 提示词注册                                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 对于每个提示词：                                        │     │
│  │  1. 获取提示词定义（名称、参数、模板）                  │     │
│  │  2. 注册为斜杠命令：/{promptName}                      │     │
│  │  3. 添加到 PromptRegistry                              │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              11. 资源注册                                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 对于每个资源：                                          │     │
│  │  1. 获取资源 URI 和元数据                              │     │
│  │  2. 注册到 ResourceRegistry                            │     │
│  │  3. 支持 @server://resource/path 语法                  │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              12. 完成发现                                        │
│  discoveryState = MCPDiscoveryState.COMPLETED                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 显示状态：                                             │     │
│  │  • "Connected" - 成功                                  │     │
│  │  • "Disconnected" - 失败（静默模式）                   │     │
│  │  • "MCP issues detected. Run /mcp list for status."    │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              13. 等待用户输入                                    │
└─────────────────────────────────────────────────────────────────┘
```
### 4.2 Tool calling flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│                  用户输入问题                                    │
│  > 使用 context7 搜索 Python MCP 教程                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Gemini 分析并决定调用工具                           │
│  识别需要使用 mcp_context7_search 工具                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    生成 FunctionCall                             │
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
│  │ 1. 查找工具：                                          │     │
│  │    tool = toolRegistry._toolDict["mcp_context7_search"]│     │
│  │                                                        │     │
│  │ 2. 找到 DiscoveredMCPTool 实例                        │     │
│  │    - serverName: "context7"                            │     │
│  │    - serverToolName: "search"                          │     │
│  │    - trust: false                                      │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         tool.createInvocation(params, messageBus)              │
│         创建 DiscoveredMCPToolInvocation                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              invocation.getConfirmationDetails()               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 检查确认条件：                                         │     │
│  │  • isTrustedFolder() && trust → 跳过确认              │     │
│  │  • allowlist.has(serverName) → 跳过确认               │     │
│  │  • allowlist.has(toolName) → 跳过确认                 │     │
│  │  • 否则 → 显示确认对话框                              │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              用户确认（如需要）                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 确认对话框：                                           │     │
│  │ ┌────────────────────────────────────────────┐        │     │
│  │  │ 即将执行 MCP 工具调用                   │        │     │
│  │  │ ┌──────────────────────────────────────┐   │        │     │
│  │  │  │ 服务器: context7                    │   │        │     │
│  │  │  │ 工具: search                         │   │        │     │
│  │  │  │ 参数: {"query": "...", "limit": 10} │   │        │     │
│  │  │  └──────────────────────────────────────┘   │        │     │
│  │  │                                              │        │     │
│  │  │ [执行一次] [总是允许此工具] [总是允许此服务器] │   │        │     │
│  │  │ [取消]                                       │   │        │     │
│  │  └────────────────────────────────────────────┘        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              invocation.execute(signal)                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 标记用户已交互：                                    │     │
│  │    cliConfig.setUserInteractedWithMcp()               │     │
│  │                                                        │     │
│  │ 2. 准备函数调用：                                      │     │
│  │    const functionCalls = [{                            │     │
│  │      name: "search",  // 原始工具名称                  │     │
│  │      args: params                                      │     │
│  │    }]                                                  │     │
│  │                                                        │     │
│  │ 3. 设置中止信号监听：                                  │     │
│  │    signal.addEventListener('abort', onAbort)           │     │
│  │                                                        │     │
│  │ 4. 调用 MCP 工具：                                     │     │
│  │    const rawResponse = await mcpTool.callTool(        │     │
│  │      functionCalls                                     │     │
│  │    )                                                   │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              检查响应是否为错误                                  │
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
│              转换响应内容                                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ transformedParts = transformMcpContentToParts(        │     │
│  │    rawResponse                                         │     │
│  │ )                                                      │     │
│  │                                                        │     │
│  │ 处理不同类型：                                         │     │
│  │  • text → { text: "..." }                             │     │
│  │  • image → [{ text: "[Image...]" },                   │     │
│  │             { inlineData: { mimeType, data } }]       │     │
│  │  • audio → [{ text: "[Audio...]" },                   │     │
│  │             { inlineData: { mimeType, data } }]       │     │
│  │  • resource → { text: "..." } 或                      │     │
│  │                [{ text: "[Resource...]" },            │     │
│  │                 { inlineData: { mimeType, data } }]   │     │
│  │  • resource_link → { text: "Resource Link: ..." }     │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              返回结果                                            │
│  {                                                              │
│    llmContent: transformedParts,   // 给模型的内容              │
│    returnDisplay: getStringifiedResultForDisplay(rawResponse)  │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Gemini 处理结果并返回给用户                          │
└─────────────────────────────────────────────────────────────────┘
```
### 4.3 OAuth authentication flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│         1. 添加 OAuth 服务器                                     │
│  $ gemini mcp add --transport sse google-workspace \            │
│      https://workspace-mcp.googleapis.com/sse                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         2. 配置保存到 settings.json                              │
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
│         3. 首次连接（无 token）                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 创建 SSE 传输（无认证头）                            │     │
│  │ 2. 尝试连接                                            │     │
│  │ 3. 服务器返回 401 Unauthorized                         │     │
│  │ 4. 检测到认证错误                                      │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         4. OAuth 发现                                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 从服务器错误响应中提取 OAuth 配置                    │     │
│  │ 2. 发现授权端点：                                       │     │
│  │    - authorizationUrl                                 │     │
│  │    - tokenUrl                                         │     │
│  │ 3. 动态客户端注册（如支持）                            │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         5. 触发 OAuth 流程                                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 打开浏览器到授权 URL                                │     │
│  │    https://accounts.google.com/o/oauth2/v2/auth?...    │     │
│  │ 2. 用户登录并同意权限                                  │     │
│  │ 3. Google 重定向到：                                   │     │
│  │    http://localhost:7777/oauth/callback?code=xxx       │     │
│  │ 4. 本地服务器接收授权码                                │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         6. 交换 Token                                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 使用授权码交换 access token 和 refresh token        │     │
│  │ 2. POST to tokenUrl:                                   │     │
│  │    {                                                    │     │
│  │      "grant_type": "authorization_code",               │     │
│  │      "code": "xxx",                                     │     │
│  │      "redirect_uri": "http://localhost:7777/oauth/callback",│
│  │      "client_id": "...",                                │     │
│  │      ...                                                 │     │
│  │    }                                                    │     │
│  │ 3. 保存 token 到 ~/.gemini/mcp-oauth-tokens.json       │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         7. 重试连接（带 token）                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 从存储加载 token                                    │     │
│  │ 2. 添加认证头：                                        │     │
│  │    Authorization: Bearer {access_token}               │     │
│  │ 3. 创建 SSE 传输（带认证头）                           │     │
│  │ 4. 连接成功！                                          │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         8. 后续使用                                              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 自动从存储加载 token                                │     │
│  │ 2. 如果 token 过期：                                   │     │
│  │    - 使用 refresh token 刷新                          │     │
│  │    - 保存新 token                                      │     │
│  │ 3. 如果 refresh token 也过期：                         │     │
│  │    - 重新触发 OAuth 流程                               │     │
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

  // 并发连接所有服务器
  await Promise.allSettled(
    serverNames.map((name) => this.maybeDiscoverMcpServer(name))
  );
}

async discover(cliConfig: McpContext): Promise<void> {
  // 并发获取工具、提示词和资源
  const [prompts, tools, resources] = await Promise.all([
    this.fetchPrompts(),
    this.discoverTools(cliConfig),
    this.discoverResources(),
  ]);

  // 注册所有内容
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
 * 所有 MCP 工具必须使用完全限定名称
 * 格式: mcp_{serverName}_{toolName}
 *
 * 示例:
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
  // 始终移除的变量
  alwaysRemove: [
    'GEMINI_API_KEY',
    'GOOGLE_API_KEY',
    'GOOGLE_APPLICATION_CREDENTIALS',
  ],
  // 按模式移除的变量
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
  // 明确允许的变量（用户在配置中指定的）
  allowed: new Set<string>(),
};

function sanitizeEnvironment(
  env: Record<string, string> | undefined,
  config: EnvironmentSanitizationConfig,
): Record<string, string> {
  const baseEnv = process.env;
  const sanitized: Record<string, string> = {};

  // 只复制明确允许的变量
  for (const [key, value] of Object.entries(baseEnv)) {
    // 检查是否匹配任何移除模式
    const shouldRemove = config.patterns.some((pattern) =>
      matchWildcard(pattern, key),
    );

    if (!shouldRemove) {
      sanitized[key] = value;
    }
  }

  // 添加用户明确指定的环境变量（信任的）
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

  // 获取所有工具
  const response = await this.client!.listTools(
    { timeout: options?.timeout, signal: options?.signal },
  );

  const tools: DiscoveredMCPTool[] = [];

  for (const mcpTool of response.tools || []) {
    // 应用过滤器
    if (!this.shouldIncludeTool(mcpTool.name)) {
      continue;
    }

    // 创建工具
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
 * 检查是否应该包含工具
 */
private shouldIncludeTool(toolName: string): boolean {
  const config = this.serverConfig;

  // excludeTools 优先于 includeTools
  if (config.excludeTools && config.excludeTools.includes(toolName)) {
    return false;
  }

  // 如果指定了 includeTools，只包含列表中的工具
  if (config.includeTools && config.includeTools.length > 0) {
    return config.includeTools.includes(toolName);
  }

  // 默认包含所有工具
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
    // 监听进度通知
    this.client?.setNotificationHandler(
      ProgressNotificationSchema,
      (notification) => {
        const { progressToken, progress, total } = notification.params;

        // 查找对应的工具调用
        const callId = this.progressTokenToCallId.get(progressToken);
        if (callId) {
          // 路由进度更新到工具调用
          this.routeProgressToCall(callId, { progress, total });
        }
      },
    );

    // 监听工具列表变化
    this.client?.setNotificationHandler(
      ToolListChangedNotificationSchema,
      async () => {
        await this.refreshTools();
      },
    );

    // 监听资源列表变化
    this.client?.setNotificationHandler(
      ResourceListChangedNotificationSchema,
      async () => {
        await this.refreshResources();
      },
    );

    // 监听提示词列表变化
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
    // 记录错误
    if (severity === 'error' || severity === 'warning') {
      if (serverName) {
        this.lastErrors.set(serverName, message);
      }
    }

    // 去重键
    const diagnosticKey = `${severity}:${message}`;
    const previousStatus = this.shownDiagnostics.get(diagnosticKey);

    // 如果用户已交互，显示详细消息
    if (this.userInteractedWithMcp) {
      if (previousStatus === 'verbose') {
        debugLogger.debug(`Deduplicated verbose MCP diagnostic: ${diagnosticKey}`);
        return;
      }
      this.shownDiagnostics.set(diagnosticKey, 'verbose');
      coreEvents.emitFeedback(severity, message, error);
      return;
    }

    // 静默模式，减少打扰
    if (previousStatus) {
      debugLogger.debug(`Deduplicated silent MCP diagnostic: ${diagnosticKey}`);
      return;
    }
    this.shownDiagnostics.set(diagnosticKey, 'silent');
    debugLogger.log(`[MCP ${severity}] ${message}`, error);

    // 显示提示
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
    // 解析 server://resource/path 格式
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
# 在对话中引用资源
> 请分析 @google-drive://documents/my-report.docx

# 自动补全会显示可用的资源
> 请分析 @<Tab>
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
      "trust": true  // 绕过所有确认
    }
  }
}
```
**Folder Level Trust**:

```typescript
if (this.cliConfig?.isTrustedFolder() && this.trust) {
  return false; // 在信任的文件夹中，信任的服务器无需确认
}
```
### 6.2 Tool call confirmation

**Confirm options**:

```typescript
export enum ToolConfirmationOutcome {
  /** 执行一次 */
  ProceedOnce = 'proceed_once',
  /** 总是允许此工具（会话级） */
  ProceedAlwaysTool = 'proceed_always_tool',
  /** 总是允许此服务器（会话级） */
  ProceedAlwaysServer = 'proceed_always_server',
  /** 总是允许并保存到策略（持久化） */
  ProceedAlwaysAndSave = 'proceed_always_and_save',
  /** 取消 */
  Cancel = 'cancel',
}
```
**Confirmation interface**:

```
┌──────────────────────────────────────────────────────────┐
│ 即将执行 MCP 工具调用                                     │
├──────────────────────────────────────────────────────────┤
│ 服务器: context7                                          │
│ 工具: search                                              │
│                                                           │
│ 描述:                                                      │
│ Search the web using Context7 API                        │
│                                                           │
│ 参数:                                                      │
│ {                                                         │
│   "query": "Python MCP tutorial",                         │
│   "limit": 10                                             │
│ }                                                         │
│                                                           │
│ [执行一次] [总是允许此工具] [总是允许此服务器] [取消]      │
└──────────────────────────────────────────────────────────┘
```
### 6.3 Policy Engine

**Policy file** (`~/.gemini/policy.toml`):

```toml
# 总是允许 context7 服务器的所有工具
[[mcp_rules]]
name = "context7_*"
action = "auto_approve"

# 拒绝危险工具
[[mcp_rules]]
name = "mcp_*_delete_*"
action = "auto_deny"

# 要求确认
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
# 1. 添加 Context7 SSE 服务器
gemini mcp add --transport sse context7 https://mcp.context7.com/sse \
  --header "CONTEXT7_API_KEY: your-api-key"

# 2. 列出所有服务器
gemini mcp list

# 3. 启动 gemini
gemini

# 4. 使用 Context7 搜索
> 使用 context7 搜索 Python MCP 教程

# AI 会调用 mcp_context7_search 工具，并请求你的批准
# 批准后，AI 会显示搜索结果
```
### 7.2 Add Google Workspace integration

```bash
# 1. 添加 Google Workspace MCP 服务器
gemini mcp add google-workspace \
  https://workspace-mcp.googleapis.com/sse

# 2. 首次连接会触发 OAuth
# 浏览器会打开，登录并授权

# 3. 使用 Google 工具
gemini

> 列出我的 Google Drive 文档
> 创建一个新的 Google Doc：MCP 集成指南
```
### 7.3 Add local Python MCP server

```bash
# 1. 添加 stdio 服务器
gemini mcp add python-tools python -m my_mcp_server \
  --cwd ./mcp-servers/python \
  -e API_KEY="$MY_API_TOKEN" \
  -e LOG_LEVEL="debug" \
  --include-tools safe_tool,file_reader \
  --exclude-tools dangerous_tool

# 2. 测试连接
gemini mcp list

# 3. 使用 Python 工具
gemini

> 使用 safe_tool 处理数据
> 读取 file_reader 可以访问的文件
```
### 7.4 Using MCP Prompt Words

```bash
# MCP 服务器可以暴露提示词作为斜杠命令
gemini

# 列出可用的提示词
/mcp

# 使用提示词
/poem-writer --title="Gemini CLI" --mood="reverent"

# 或使用位置参数
/poem-writer "Gemini CLI" reverent
```
### 7.5 Reference MCP resources

```bash
gemini

# 引用 Google Drive 中的文档
> 请总结 @google-drive://documents/my-report.docx 的内容

# 引用 Notion 页面
> 分析 @notion://pages/my-project-plan 的任务

# 引用 Context7 抓取的网页
> 比较 @context7://web/page-1 和 @context7://web/page-2
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
    // 1. 标记用户与 MCP 交互（用于诊断显示）
    this.cliConfig?.setUserInteractedWithMcp?.();

    // 2. 构建 FunctionCall（MCP 工具调用格式）
    const functionCalls: FunctionCall[] = [
      {
        name: this.serverToolName,  // 原始 MCP 工具名（不带 mcp_ 前缀）
        args: this.params,          // 已解析的参数
      },
    ];

    // 3. 与 AbortSignal 竞速，支持取消操作
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

      // 4. 调用底层 MCP 工具
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

    // 5. 检查 MCP 工具错误
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

    // 6. 转换 MCP 响应为 LLM 格式
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

  // 1. 检查信任文件夹
  if (this.cliConfig?.isTrustedFolder() && this.trust) {
    return false; // 服务器已信任，无需确认
  }

  // 2. 检查白名单
  if (
    DiscoveredMCPToolInvocation.allowlist.has(serverAllowListKey) ||
    DiscoveredMCPToolInvocation.allowlist.has(toolAllowListKey)
  ) {
    return false; // 已在白名单中，无需确认
  }

  // 3. 需要用户确认
  const confirmationDetails: ToolMcpConfirmationDetails = {
    type: 'mcp',
    title: 'Confirm MCP Tool Execution',
    serverName: this.serverName,
    toolName: this.serverToolName,  // 原始工具名
    toolDisplayName: this.displayName,  // 完全限定名（mcp_server_tool）
    toolArgs: this.params,
    toolDescription: this.toolDescription,
    toolParameterSchema: this.toolParameterSchema,
    onConfirm: async (outcome: ToolConfirmationOutcome) => {
      // 4. 处理用户选择
      if (outcome === ToolConfirmationOutcome.ProceedAlwaysServer) {
        // 允许整个服务器的所有工具
        DiscoveredMCPToolInvocation.allowlist.add(serverAllowListKey);
      } else if (outcome === ToolConfirmationOutcome.ProceedAlwaysTool) {
        // 仅允许此特定工具
        DiscoveredMCPToolInvocation.allowlist.add(toolAllowListKey);
      } else if (outcome === ToolConfirmationOutcome.ProceedAlwaysAndSave) {
        // 永久允许并保存到策略文件
        DiscoveredMCPToolInvocation.allowlist.add(toolAllowListKey);
        // 策略更新由调度器中心处理
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
  // 1. 列出 MCP 服务器的所有工具
  const response = await this.client?.listTools({});

  if (!response?.tools) {
    return;
  }

  // 2. 为每个 MCP 工具创建 DiscoveredMCPTool
  const discoveredTools: DiscoveredMCPTool[] = [];

  for (const mcpTool of response.tools) {
    // 3. 生成完全限定工具名（mcp_server_tool）
    const fullyQualifiedName = generateValidName(
      `${this.serverName}${MCP_QUALIFIED_NAME_SEPARATOR}${mcpTool.name}`
    );

    // 4. 创建工具实例
    const tool = new DiscoveredMCPTool(
      this.createCallableTool(mcpTool),  // CallableTool 包装器
      this.serverName,                   // 服务器名
      mcpTool.name,                       // 原始工具名
      mcpTool.description,                // 描述
      mcpTool.inputSchema,                // JSON Schema 参数
      this.messageBus,
      this.serverConfig?.trust,           // 信任标志
      mcpTool.name?.startsWith('read_'), // 只读判断
      undefined,                          // nameOverride
      this.cliConfig,
      this.serverConfig?.extension?.name,
      this.serverConfig?.extension?.id,
      {
        _serverName: this.serverName,     // 工具注解
      },
    );

    discoveredTools.push(tool);
  }

  // 5. 注册到 ToolRegistry
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
      // 工具名：mcp_server_tool 格式
      nameOverride ??
        generateValidName(
          `${serverName}${MCP_QUALIFIED_NAME_SEPARATOR}${serverToolName}`
        ),

      // 显示名：toolName (serverName MCP Server)
      `${serverToolName} (${serverName} MCP Server)`,

      description,
      Kind.Other,
      parameterSchema,  // 直接传递 MCP 的 JSON Schema
      messageBus,
      true,  // isOutputMarkdown
      false, // canUpdateOutput
      extensionName,
      extensionId,
    );

    this._isReadOnly = isReadOnly;
  }

  // 返回工具的 FunctionDeclaration 格式
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
用户输入 "使用 context7 搜索 Python MCP 教程"
    ↓
Gemini CLI 调度器
    ↓
LLM 生成响应
    ↓
Gemini API 调用
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
Gemini API 返回响应
    ├── Content: "好的，我来帮你搜索..."
    └── FunctionCall: {
            "name": "mcp_context7_search",
            "args": {"query": "Python MCP 教程", "limit": 10}
         }
    ↓
调度器解析 FunctionCall
    ↓
创建 DiscoveredMCPToolInvocation
    ↓
getConfirmationDetails()
    ↓
检查信任/白名单
    ↓
需要确认 → 显示确认对话框
    ↓
用户点击"允许"
    ↓
execute(abortSignal)
    ↓
mcpTool.callTool([{
    name: "search",  // 原始工具名
    args: {query: "Python MCP 教程", limit: 10}
}])
    ↓
MCP 服务器返回结果
    {
        "content": [
            {"type": "text", "text": "找到 10 个相关结果..."}
        ]
    }
    ↓
transformMcpContentToParts()
    ↓
转换为 Gemini Part 格式
    ↓
ToolResult {
    llmContent: [{text: "找到 10 个相关结果..."}],
    returnDisplay: "找到 10 个相关结果..."
}
    ↓
添加到 LLM 上下文
    ↓
继续下一轮 LLM 调用（包含工具结果）
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
          // 文本内容
          return { text: block.text };

        case 'image':
        case 'audio':
          // 媒体内容：添加描述 + inlineData
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
          // 资源内容
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
          // 资源链接
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
// MCP 服务器返回的工具名
const serverToolName = "search";

// Gemini CLI 生成的完全限定名
const fullyQualifiedName = "mcp_context7_search";

// LLM 看到的工具名
const toolName = "mcp_context7_search";

// 调用 MCP 服务器时使用原始名
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
│   ├── mcp-client.ts           # MCP 客户端核心 (1000+ 行)
│   ├── mcp-client-manager.ts   # MCP 客户端管理器 (500+ 行)
│   ├── mcp-tool.ts             # MCP 工具封装 (600+ 行)
│   └── tool-registry.ts        # 工具注册表
├── mcp/
│   ├── google-auth-provider.ts         # Google 认证
│   ├── sa-impersonation-provider.ts    # 服务账号模拟
│   ├── oauth-provider.ts               # OAuth 提供者
│   └── oauth-token-storage.ts          # Token 存储
├── prompts/
│   └── prompt-registry.ts      # 提示词注册表
└── resources/
    └── resource-registry.ts    # 资源注册表

packages/cli/src/commands/mcp/
├── add.ts                      # 添加服务器 (250+ 行)
├── remove.ts                   # 移除服务器
├── list.ts                     # 列出服务器
└── enableDisable.ts            # 启用/禁用服务器
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
