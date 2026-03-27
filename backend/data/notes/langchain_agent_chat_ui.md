# LangChain Documentation Index

Fetch the complete documentation index at: [LangChain Documentation Index](https://docs.langchain.com/llms.txt)

---

## Agent Chat UI

[Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) 是一个基于 Next.js 的应用程序，提供与任何 LangChain 代理的对话界面。它支持实时聊天、工具可视化以及时间旅行调试和状态分叉等高级功能。Agent Chat UI 与使用 [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) 创建的代理无缝协作，为您的代理提供互动体验，设置简单，无论是在本地运行还是在部署环境中（如 [LangSmith](/langsmith/home)）。

Agent Chat UI 是开源的，可以根据您的应用需求进行调整。

### 视频介绍

<iframe class="w-full aspect-video rounded-xl" src="https://www.youtube.com/embed/lInrwVnZ83o?si=Uw66mPtCERJm0EjU" title="Agent Chat UI" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe>

### 生成用户界面

您可以在 Agent Chat UI 中使用生成用户界面。有关更多信息，请参见 [使用 LangGraph 实现生成用户界面](/langsmith/generative-ui-react)。

### 快速开始

最快的入门方式是使用托管版本：
1. **访问 [Agent Chat UI](https://agentchat.vercel.app)**
2. **连接您的代理**，输入您的部署 URL 或本地服务器地址
3. **开始聊天** - UI 将自动检测并渲染工具调用和中断

### 本地开发

要进行自定义或本地开发，您可以在本地运行 Agent Chat UI：

```bash
# 创建一个新的 Agent Chat UI 项目
npx create-agent-chat-app --project-name my-chat-ui
cd my-chat-ui

# 安装依赖并启动
pnpm install
pnpm dev
```

```bash
# 克隆仓库
git clone https://github.com/langchain-ai/agent-chat-ui.git
cd agent-chat-ui

# 安装依赖并启动
pnpm install
pnpm dev
```

### 连接到您的代理

Agent Chat UI 可以连接到 [本地](/oss/python/langchain/studio#set-up-local-agent-server) 和 [已部署的代理](/oss/python/langchain/deploy)。

启动 Agent Chat UI 后，您需要配置它以连接到您的代理：
1. **图形 ID**：输入您的图形名称（在 `langgraph.json` 文件的 `graphs` 下找到）
2. **部署 URL**：您的代理服务器的端点（例如，本地开发使用 `http://localhost:2024`，或您的已部署代理的 URL）
3. **LangSmith API 密钥（可选）**：添加您的 LangSmith API 密钥（如果您使用本地代理服务器，则不需要）

配置完成后，Agent Chat UI 将自动获取并显示来自您代理的任何中断线程。

### 自定义

Agent Chat UI 具有开箱即用的支持，用于渲染工具调用和工具结果消息。要自定义显示的消息，请参见 [在聊天中隐藏消息](https://github.com/langchain-ai/agent-chat-ui?tab=readme-ov-file#hiding-messages-in-the-chat)。

---

### 资源链接
- [在 GitHub 上编辑此页面](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/ui.mdx) 或 [提交问题](https://github.com/langchain-ai/docs/issues/new/choose)。
- [通过 MCP 将这些文档连接到 Claude、VSCode 等，以获取实时答案](/use-these-docs)。