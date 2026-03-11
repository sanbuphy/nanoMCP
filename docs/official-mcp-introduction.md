# 官方 MCP (Model Context Protocol) 介绍

> 本文档基于 [MCP 官方文档](https://modelcontextprotocol.io/docs/getting-started/intro) 编写，结合了实际项目案例进行说明。

**相关文档**：
- [Kimi CLI MCP 实现分析](./kimi-cli-mcp-implementation-analysis.md) - 基于 fastmcp (Python) 的实现
- [Gemini CLI MCP 实现分析](./gemini-cli-mcp-implementation-analysis.md) - 基于 @modelcontextprotocol/sdk (TypeScript) 的实现

---

## 什么是 MCP?

MCP (Model Context Protocol，模型上下文协议) 是一个开源标准，用于将 AI 应用程序连接到外部系统。通过 MCP，AI 应用程序（如 Claude 或 ChatGPT）可以连接到：

- **数据源**（如本地文件、数据库）
- **工具**（如搜索引擎、计算器）
- **工作流**（如专门的提示词）

这使得 AI 能够访问关键信息并执行任务。

### 类比：USB-C 接口

将 MCP 想象成 AI 应用程序的 USB-C 接口。就像 USB-C 提供了连接电子设备的标准化方式一样，MCP 提供了将 AI 应用程序连接到外部系统的标准化方式。

## MCP 能实现什么?

1. **个性化 AI 助手**：AI 代理可以访问你的 Google Calendar 和 Notion，充当更个性化的 AI 助手。

2. **跨平台开发**：Claude Code 可以使用 Figma 设计生成完整的 Web 应用程序。

3. **企业数据分析**：企业聊天机器人可以连接组织内的多个数据库，使用户能够通过聊天分析数据。

4. **创意设计与制造**：AI 模型可以在 Blender 上创建 3D 设计，并使用 3D 打印机打印出来。

## 为什么 MCP 重要?

MCP 为生态系统中的不同角色带来各种好处：

### 对开发者

- 减少构建 AI 应用程序或代理时的开发时间和复杂性
- 简化与现有系统的集成

### 对 AI 应用程序或代理

- 访问数据源、工具和应用程序的生态系统
- 增强能力并改善最终用户体验
- 一次构建，到处集成

### 对最终用户

- 更强大的 AI 应用程序或代理
- AI 可以访问你的数据并在必要时代表你采取行动

## 广泛的生态系统支持

MCP 是一个开放协议，在广泛的客户端和服务器中得到支持。支持 MCP 的工具包括：

- **AI 助手**：Claude、ChatGPT
- **开发工具**：Visual Studio Code、Cursor、MCPJam 等

这种广泛的支持使得"一次构建，随处集成"成为可能。

## 开始构建

MCP 提供三条主要的构建路径：

### 1. 构建服务器 (Build Servers)
创建 MCP 服务器以暴露你的数据和工具给 AI 应用程序使用。

### 2. 构建客户端 (Build Clients)
开发连接到 MCP 服务器的应用程序。

### 3. 构建 MCP 应用 (Build MCP Apps)
构建在 AI 客户端内运行的交互式应用程序。

## 核心概念

### 架构组件

MCP 的核心架构包括三个主要组件：

1. **Host（主机）**：运行 AI 模型的应用程序（如 IDE、聊天界面）
2. **Client（客户端）**：实现 MCP 协议的库
3. **Server（服务器）**：提供工具、资源和提示词的应用程序

### 连接方式

MCP 支持多种连接方式：

- **本地进程**：通过 stdio 连接本地运行的 MCP 服务器
- **HTTP/SSE**：通过网络连接远程 MCP 服务器
- **直接集成**：服务器作为库直接嵌入到应用程序中

### 数据交换

MCP 使用标准化的消息格式进行数据交换：

- **工具 (Tools)**：可以调用的函数
- **资源 (Resources)**：可以读取的数据
- **提示词 (Prompts)**：可重用的模板

## 安全性

MCP 将安全作为核心设计原则：

- 用户必须明确授权连接到 MCP 服务器
- 服务器可以被启用/禁用
- 支持访问控制列表（allowlist/excludelist）
- OAuth 认证支持远程服务器

## 规范与生态系统

- **开放规范**：MCP 规范公开可用，任何人都可以实现
- **多语言 SDK**：提供 TypeScript、Python 等多种语言的 SDK
- **服务器注册表**：社区维护的可用 MCP 服务器列表
- **社区提案 (SEPs)**：通过 SEP 流程持续改进协议

## 相关资源

- [MCP 规范](https://modelcontextprotocol.io/specification)
- [架构详解](https://modelcontextprotocol.io/docs/about/architecture)
- [SDK 文档](https://modelcontextprotocol.io/docs/developing-mcp/sdk)
- [服务器注册表](https://github.com/modelcontextprotocol/servers)
- [GitHub 仓库](https://github.com/modelcontextprotocol)

## 总结

MCP 通过提供一个标准化的协议，解决了 AI 应用程序与外部系统集成时的碎片化问题。它使得：

1. **开发者**可以更容易地构建 AI 集成
2. **AI 应用**可以访问丰富的数据和能力
3. **用户**可以获得更强大、更个性化的 AI 体验

就像 USB-C 接口统一了设备连接一样，MCP 正在统一 AI 应用与世界的连接方式。
