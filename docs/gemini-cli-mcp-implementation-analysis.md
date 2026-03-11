# Gemini CLI 的 MCP (Model Context Protocol) 实现机制深度拆解

> **项目地址**: [https://github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
>
> **分析版本**: v0.35.0-nightly
>
> **分析时间**: 2026-03-11

**相关文档**：
- [官方 MCP 介绍](./official-mcp-introduction.md) - MCP 协议的基础概念和原理
- [Kimi CLI MCP 实现](./kimi-cli-mcp-implementation-analysis.md) - 基于 fastmcp (Python) 的实现对比

## 目录

- [1. 项目概述](#1-项目概述)
- [2. MCP 架构总览](#2-mcp-架构总览)
- [3. 核心组件拆解](#3-核心组件拆解)
- [4. 完整工作流程](#4-完整工作流程)
- [5. 关键技术实现](#5-关键技术实现)
- [6. 安全机制](#6-安全机制)
- [7. 使用示例](#7-使用示例)
- [8. 与 Kimi CLI 对比](#8-与-kimi-cli-对比)
- [9. 总结与思考](#9-总结与思考)

---

## 1. 项目概述

### 1.1 什么是 Gemini CLI？

Gemini CLI 是由 Google 开发的开源 AI 命令行工具，将 Gemini 模型的强大能力直接带入终端。它提供了轻量级的 Gemini 访问方式，是直接从提示词到模型的最短路径。

### 1.2 核心特性

- **免费额度**: 使用个人 Google 账户可享受 60 次/分钟、1,000 次/天的请求
- **强大的 Gemini 3 模型**: 访问改进的推理能力和 1M token 上下文窗口
- **内置工具**: Google 搜索、文件操作、Shell 命令、网页抓取
- **MCP 支持**: 通过 Model Context Protocol 进行自定义集成
- **终端优先**: 为生活在命令行的开发者设计
- **开源**: Apache 2.0 许可证

### 1.3 技术栈

- **语言**: TypeScript/JavaScript (Node.js 20+)
- **MCP SDK**: `@modelcontextprotocol/sdk`
- **包管理**: npm/workspaces
- **构建工具**: esbuild, TypeScript
- **测试框架**: Vitest

---

## 2. MCP 架构总览

### 2.1 系统架构图

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

### 2.2 核心代码结构

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

## 3. 核心组件拆解

### 3.1 配置管理

#### 配置文件结构

MCP 服务器配置存储在 `settings.json` 中，支持用户级和项目级配置：

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

#### 配置属性详解

**传输类型配置**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `command` | string | Stdio 传输的命令 |
| `url` | string | SSE 传输的 URL |
| `httpUrl` | string | HTTP 流式传输的 URL |
| `type` | string | 传输类型：`stdio`、`sse`、`http` |

**通用配置**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `args` | string[] | 命令行参数 |
| `env` | object | 环境变量（支持 `$VAR` 扩展） |
| `headers` | object | HTTP 头（SSE/HTTP） |
| `cwd` | string | 工作目录 |
| `timeout` | number | 超时时间（毫秒，默认 600000） |
| `trust` | boolean | 信任服务器（绕过确认） |
| `description` | string | 服务器描述 |
| `includeTools` | string[] | 包含的工具列表 |
| `excludeTools` | string[] | 排除的工具列表 |

**认证配置**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `authProviderType` | string | 认证类型：`dynamic_discovery`、`google_credentials`、`service_account_impersonation` |
| `oauth` | object | OAuth 配置 |
| `targetAudience` | string | IAP 受保护应用的客户端 ID |
| `targetServiceAccount` | string | 要模拟的服务账号邮箱 |

#### CLI 命令实现

**添加服务器** (`packages/cli/src/commands/mcp/add.ts`):

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

**使用示例**:

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

### 3.2 MCP 客户端管理 (`mcp-client-manager.ts`)

**职责**: 管理多个 MCP 客户端的生命周期

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

#### 状态管理

**服务器状态** (`MCPServerStatus`):

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

**发现状态** (`MCPDiscoveryState`):

```typescript
export enum MCPDiscoveryState {
  NOT_STARTED = 'not_started',     // 未开始
  IN_PROGRESS = 'in_progress',     // 进行中
  COMPLETED = 'completed',         // 已完成
}
```

---

### 3.3 MCP 客户端 (`mcp-client.ts`)

**职责**: 管理单个 MCP 服务器的连接和交互

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

#### 连接建立

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

### 3.4 MCP 工具封装 (`mcp-tool.ts`)

**职责**: 将 MCP 工具封装为 Gemini CLI 可调用的工具

#### 工具命名规则

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

#### 工具类定义

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

#### 工具调用

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

#### 内容转换

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

## 4. 完整工作流程

### 4.1 启动流程图

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

### 4.2 工具调用流程图

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

### 4.3 OAuth 认证流程图

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

## 5. 关键技术实现

### 5.1 并发发现

**问题**: 如何高效发现多个 MCP 服务器的工具？

**解决方案**: 并发连接和发现

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

**优势**:
- 多个服务器同时连接，不阻塞启动
- 工具、提示词、资源并发获取
- 单个服务器失败不影响其他服务器

---

### 5.2 工具命名空间

**问题**: 如何避免来自不同服务器的工具名称冲突？

**解决方案**: 强制命名空间前缀

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

**警告**:

> 不要在 MCP 服务器名称中使用下划线（`_`）。例如，使用 `my-server` 而不是 `my_server`。
> 策略解析器会在 `mcp_` 前缀后的第一个下划线处拆分完全限定名称。
> 如果服务器名称包含下划线，解析器会错误地解释服务器身份，导致通配符规则和安全策略静默失败。

---

### 5.3 环境变量清理

**问题**: 如何防止敏感环境变量泄露给第三方 MCP 服务器？

**解决方案**: 自动环境变量清理

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

**安全原则**:

> 如果变量由用户在特定服务器的配置中明确指定，则构成知情同意，允许与该服务器共享该特定数据。

---

### 5.4 工具过滤

**问题**: 如何只启用 MCP 服务器的某些工具？

**解决方案**: `includeTools` 和 `excludeTools` 配置

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

**使用示例**:

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

**规则**:
- `excludeTools` 优先于 `includeTools`
- 如果工具同时在两个列表中，将被排除
- 如果未指定任何过滤器，默认包含所有工具

---

### 5.5 进度通知

**问题**: 如何处理长时间运行的 MCP 工具调用的进度更新？

**解决方案**: 进度 token 映射和通知路由

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

### 5.6 诊断消息去重

**问题**: 如何避免重复显示相同的 MCP 错误消息？

**解决方案**: 智能诊断去重系统

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

**行为**:
1. **静默模式**（默认）:
   - 每个唯一消息只显示一次
   - 日志输出，不显示通知
   - 如果有问题，显示提示："Run /mcp list for status"

2. **详细模式**（用户交互后）:
   - 用户运行 `/mcp` 命令后触发
   - 显示详细的通知
   - 仍然去重，但更明显

---

### 5.7 资源引用

**问题**: 如何在对话中引用 MCP 服务器暴露的资源？

**解决方案**: `@server://resource/path` 语法

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

**使用示例**:

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

## 6. 安全机制

### 6.1 信任机制

**服务器级别信任**:

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

**文件夹级别信任**:

```typescript
if (this.cliConfig?.isTrustedFolder() && this.trust) {
  return false; // 在信任的文件夹中，信任的服务器无需确认
}
```

### 6.2 工具调用确认

**确认选项**:

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

**确认界面**:

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

### 6.3 策略引擎

**策略文件** (`~/.gemini/policy.toml`):

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

### 6.4 环境变量清理

**自动清理敏感变量**:

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

## 7. 使用示例

### 7.1 添加 Context7 搜索工具

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

### 7.2 添加 Google Workspace 集成

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

### 7.3 添加本地 Python MCP 服务器

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

### 7.4 使用 MCP 提示词

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

### 7.5 引用 MCP 资源

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

## 8. 与 Kimi CLI 对比

### 8.1 架构对比

| 特性 | Gemini CLI | Kimi CLI |
|------|-----------|----------|
| **语言** | TypeScript/JavaScript | Python |
| **MCP SDK** | @modelcontextprotocol/sdk | fastmcp |
| **传输类型** | Stdio, SSE, HTTP | Stdio, HTTP |
| **OAuth** | ✅ 完整支持（自动发现） | ✅ 支持（手动配置） |
| **工具命名** | `mcp_server_tool`（强制） | 原始工具名 |
| **资源支持** | ✅ 完整支持 | ❌ 不支持 |
| **提示词支持** | ✅ 完整支持 | ❌ 不支持 |
| **进度通知** | ✅ 支持 | ❌ 不支持 |
| **工具过滤** | ✅ include/exclude | ❌ 不支持 |
| **环境清理** | ✅ 自动清理 | ❌ 不清理 |

### 8.2 配置对比

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

### 8.3 命令对比

| 操作 | Gemini CLI | Kimi CLI |
|------|-----------|----------|
| 添加服务器 | `gemini mcp add` | `kimi mcp add` |
| 列出服务器 | `gemini mcp list` | `kimi mcp list` |
| 移除服务器 | `gemini mcp remove` | `kimi mcp remove` |
| 启用服务器 | `gemini mcp enable` | ❌ 不支持 |
| 禁用服务器 | `gemini mcp disable` | ❌ 不支持 |
| OAuth 授权 | 自动触发 | `kimi mcp auth` |
| 测试连接 | `gemini mcp list` | `kimi mcp test` |

---

## 9. 总结与思考

### 9.1 架构亮点

1. **企业级设计**
   - 完整的 OAuth 支持（自动发现）
   - Google 认证集成
   - 服务账号模拟
   - IAP 保护的服务支持

2. **丰富的功能**
   - 工具、提示词、资源三大功能
   - 进度通知支持
   - 工具过滤（include/exclude）
   - 动态列表更新

3. **安全优先**
   - 自动环境变量清理
   - 多层确认机制
   - 策略引擎集成
   - 信任文件夹支持

4. **用户体验**
   - 智能诊断去重
   - 静默启动模式
   - 详细的错误报告
   - 资源引用语法

5. **可扩展性**
   - 扩展系统
   - 插件架构
   - 多租户支持

### 9.2 可借鉴的设计

1. **命名空间策略**
   - 强制 `mcp_` 前缀避免冲突
   - 完全限定名称格式
   - 清晰的层次结构

2. **智能诊断**
   - 静默/详细双模式
   - 去重机制
   - 用户交互感知

3. **环境清理**
   - 自动识别敏感变量
   - 模式匹配
   - 显式允许覆盖

4. **OAuth 集成**
   - 自动发现
   - 动态客户端注册
   - Token 刷新

### 9.3 改进空间

1. **性能优化**
   - 连接池复用
   - 工具调用缓存
   - 增量发现

2. **监控**
   - 性能指标收集
   - 错误率统计
   - 使用分析

3. **可观测性**
   - 结构化日志
   - 调试模式
   - 追踪支持

### 9.4 适用场景

Gemini CLI 的 MCP 实现特别适合以下场景：

1. **企业环境**
   - Google Workspace 集成
   - 内部 API 访问
   - 多层安全控制

2. **开发工作流**
   - GitHub/GitLab 集成
   - CI/CD 自动化
   - 代码审查

3. **数据处理**
   - 数据库查询
   - ETL 流程
   - 报告生成

4. **协作工具**
   - 文档管理
   - 任务跟踪
   - 知识库

---

## 10. LLM 调用 MCP 工具的完整代码流程

本节详细展示 Gemini CLI 中 LLM 如何调用 MCP 工具的完整代码链路，从 LLM 生成工具调用到最终执行 MCP 服务器调用。

### 10.1 核心调用链路

#### DiscoveredMCPToolInvocation.execute - MCP 工具执行器

**位置**: `packages/core/src/tools/mcp-tool.ts:262-325`

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

**关键点**：
- **取消支持**：通过 AbortSignal 支持工具调用的取消
- **错误检测**：检查 MCP 工具返回的 `isError` 标志
- **格式转换**：将 MCP ContentBlock 转换为 Gemini API Part 格式
- **用户交互标记**：记录用户与 MCP 的交互，影响诊断显示模式

#### getConfirmationDetails - 用户审批机制

**位置**: `packages/core/src/tools/mcp-tool.ts:193-231`

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

**关键点**：
- **信任文件夹**：在信任文件夹中，可以跳过确认
- **白名单机制**：内存中维护已批准的工具列表
- **细粒度控制**：可以批准整个服务器或单个工具
- **持久化选项**：支持将批准保存到策略文件

### 10.2 工具注册到 LLM 的过程

#### MCP 工具发现与注册

**位置**: `packages/core/src/tools/mcp-client.ts:800-900`

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

#### 工具定义转换为 LLM 格式

**位置**: `packages/core/src/tools/mcp-tool.ts:332-367`

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

### 10.3 完整的调用时序图

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

### 10.4 关键数据结构转换

#### MCP ContentBlock → Gemini Part

**位置**: `packages/core/src/tools/mcp-tool.ts:494-523`

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

**支持的 MCP 内容类型**：
1. **text**: 纯文本
2. **image/audio**: 媒体数据（base64）
3. **resource**: 嵌入资源（文本或二进制）
4. **resource_link**: 资源引用（URI）

#### 工具名称映射

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

### 10.5 与 Kimi CLI 的对比

| 特性 | Gemini CLI | Kimi CLI |
|------|-----------|----------|
| **工具名称格式** | `mcp_{server}_{tool}` | 原始工具名 |
| **LLM 集成** | Google GenAI SDK | kosong 框架 |
| **工具注册** | ToolRegistry.registerTool() | Toolset.add() |
| **用户审批** | getConfirmationDetails() | approval.request() |
| **取消支持** | AbortSignal 竞速 | asyncio.CancelledError |
| **结果转换** | transformMcpContentToParts() | convert_mcp_tool_result() |
| **内容类型** | 4 种（text, image, audio, resource） | 2 种（text, image） |
| **进度通知** | 支持（registerProgressToken） | 不支持 |
| **资源访问** | 支持 | 不支持 |
| **提示词模板** | 支持 | 不支持 |

---

## 参考资源

- **GitHub 仓库**: [https://github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
- **官方文档**: [https://geminicli.com/docs](https://geminicli.com/docs)
- **MCP 协议**: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
- **MCP SDK**: [https://github.com/modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)

---

## 附录

### A. 核心代码文件清单

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

### B. 配置文件示例

**~/.gemini/settings.json**:
```json
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

### C. 相关依赖

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

**文档版本**: 1.0
**最后更新**: 2026-03-11
**作者**: AI Assistant
**许可**: Apache 2.0 License
