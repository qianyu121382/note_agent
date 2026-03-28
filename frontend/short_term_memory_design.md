# Note Agent 短期记忆设计说明

## 1. 当前落地目标

本轮实现采用一个收敛后的最小方案：

- 保留已有的消息历史作为原始短期记忆
- 正式引入 `mode` 作为线程级会话控制状态
- 继续保留 `active_note_id` / `active_note_title` 作为当前对象状态
- 暂不引入 `current_task`、`working_note_constraints`、`last_user_goal`

这样做的原因很明确：

- 当前项目最需要的是稳定的多轮处理语境
- `mode` 已经能解决大部分 follow-up 解释问题
- 现在就同时引入更多任务字段，容易造成语义重叠和状态更新混乱

---

## 2. 当前项目里的短期记忆是什么

目前项目中的短期记忆分成三部分：

### 2.1 原始交互记忆

字段：

- `messages`
- `session_messages`

作用：

- 保留完整对话历史
- 给 dispatcher 和 ReAct agent 提供原始上下文

### 2.2 会话控制记忆

字段：

- `intent`
- `mode`

作用：

- `intent` 表示本轮输入的路由结果
- `mode` 表示当前线程的工作语境

它们的边界是：

- `intent` 回答“这一轮应该怎么走”
- `mode` 回答“这个线程现在按什么语境继续运行”

### 2.3 当前对象记忆

字段：

- `active_note_id`
- `active_note_title`

作用：

- 表示当前线程围绕哪篇笔记工作
- 让“这篇”“刚才那篇”“上一篇”有明确落点

---

## 3. 为什么当前先只实现 `mode`

因为 `mode` 是当前最关键、最不容易与别的状态重叠的字段。

`mode` 不负责描述完整任务内容，它只负责描述线程当前的处理语境：

- `idle`
- `create`
- `edit`
- `qa`

它的价值主要有三点：

1. 稳定 follow-up 的解释
2. 为主图和 ReAct agent 提供统一处理语境
3. 把多轮控制逻辑从“靠消息历史临时推断”升级成“显式状态驱动”

---

## 4. `intent` 和 `mode` 的区别

### `intent`

`intent` 是本轮输入的分类结果。

例如：

- `note_taking`
- `waiting`
- `exit`

它属于“当前这一轮”的路由变量。

### `mode`

`mode` 是当前线程的工作模式。

例如：

- `create`
- `edit`
- `qa`
- `idle`

它属于“跨轮保留的会话状态”。

所以：

- dispatcher 负责识别 `intent`
- dispatcher 同时根据当前输入和已有状态推导 `mode`
- session store 负责持久化 `mode`
- graph 和 ReAct agent 读取 `mode`

---

## 5. `mode` 是怎么变化的

在当前实现里，`mode` 的更新规则是显式的，而不是让模型自由发挥。

### 5.1 新资料进入

如果用户本轮提供了新的可处理资料，例如：

- URL
- 长文本
- 文件路径

则：

- `intent = note_taking`
- `mode = create`

### 5.2 围绕已有笔记提出修改要求

例如：

- “把这篇改详细一点”
- “翻译成中文”
- “重写第二部分”

则：

- `intent = note_taking`
- `mode = edit`

### 5.3 围绕已有笔记提出问答/总结请求

例如：

- “总结一下这篇笔记”
- “这篇主要讲什么”
- “解释一下第二部分”

则：

- `intent = note_taking`
- `mode = qa`

### 5.4 非笔记处理输入

例如：

- 寒暄
- 模糊请求
- 非主链输入

则：

- `intent = waiting`
- `mode` 保持当前值，不主动清空

这样做是为了保留当前线程语境，避免一条无关输入就把会话上下文抹掉。

---

## 6. `mode` 在系统里如何起作用

### 6.1 在 dispatcher 中起作用

当用户输入是 follow-up 短句时，例如：

- “再详细一点”
- “总结一下”
- “改成中文”

dispatcher 不仅要判断是否进入主链，还要决定当前线程属于：

- `create`
- `edit`
- `qa`

这一步的结果会写入 `mode`。

### 6.2 在主图中起作用

主图不会只把 `mode` 当临时变量，而会：

- 从 session 中恢复 `mode`
- 在本轮 dispatch 后接收更新后的 `mode`
- 在保存 session 时再次持久化 `mode`

### 6.3 在 ReAct agent 中起作用

ReAct agent 会读取当前 `mode`，并据此得到更明确的语境提示：

- `create`：优先围绕新资料创建新笔记
- `edit`：优先围绕当前笔记修改正文
- `qa`：优先围绕当前笔记回答问题，而不是修改正文

所以 `mode` 不是只给 dispatcher 用的，而是整条主链共享的短期记忆状态。

---

## 7. 当前为什么不实现 `last_user_goal`

这不是因为它没价值，而是因为在当前阶段它和 `mode`、当前输入之间容易形成语义重叠。

目前系统已经有：

- 当前输入
- `intent`
- `mode`
- `active_note_id`

这已经足够支撑最小可用的多轮短期记忆。

如果现在再加入 `last_user_goal`，会马上出现这些设计问题：

- 它和当前输入的边界如何区分
- 它和 `mode` 的更新先后如何定义
- 遇到 follow-up 时是覆盖、合并还是重写
- ReAct agent 应该优先看当前输入还是 `last_user_goal`

在这些规则没有被正式设计好之前，强行加入只会让状态系统变得更重。

因此当前版本采取的原则是：

> 先把 `mode` 这个最关键的线程级控制状态做扎实，再决定是否需要补任务摘要类状态。

---

## 8. 当前项目到底有没有短期记忆

有。

但当前版本更准确地说是：

> 项目已经具备“最小结构化短期记忆”。

具体包括：

- 原始消息历史
- 当前线程 `mode`
- 当前活动笔记对象
- 会话级持久化恢复

相比之前，变化在于：

- 短期记忆不再只是消息历史和 `active_note_id`
- 系统现在正式拥有一个显式的线程语境状态 `mode`

---

## 9. 当前实现的设计原则

为了避免“东补一块，西补一块”，当前实现遵循下面几条规则：

1. `mode` 是正式 state 字段，而不是节点内部临时变量
2. `mode` 的推导逻辑集中在专门的 session-state 模块里
3. `mode` 的恢复、传递、持久化走统一链路
4. ReAct agent 显式消费 `mode`
5. 暂不引入没有明确边界的新任务字段

---

## 10. 一句话总结

当前版本的短期记忆实现，不追求一步到位，而是先建立一个干净、稳定、可扩展的最小核心：

- `messages`
- `session_messages`
- `intent`
- `mode`
- `active_note_id`
- `active_note_title`

其中最关键的新能力是：

> 把线程当前处理语境正式建模为 `mode`，并让它在 dispatcher、主图、ReAct agent、session persistence 之间统一流转。
