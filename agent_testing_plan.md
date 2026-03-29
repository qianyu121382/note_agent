# Note Agent 测试说明与测试方案

这份文档面向当前项目的核心目标：  
不是追求“覆盖率看起来很高”，而是验证这个 Agent 在**多轮会话、状态流转、笔记对象管理、历史记录展示**这几条关键链路上是否稳定。

---

## 一、这个项目到底该测什么

对这个项目来说，最重要的不是测试某个工具函数有没有返回字符串，而是测试：

1. 用户输入会不会被**正确理解**
2. 会话状态会不会被**正确更新**
3. 后续轮次会不会沿着**正确上下文继续**
4. 历史记录和笔记状态会不会与真实状态**保持一致**

所以测试重点应该放在：

- 多轮意图识别
- 澄清回复
- active note 续接
- session / history projection 一致性
- note store 的对象一致性与并发安全

---

## 二、为什么这里的测试很重要

普通 CRUD 项目里，很多测试都围绕“输入 A 输出 B”。

但 Agent 项目最大的风险不是单个函数算错，而是：

- 这一轮判断对了，但状态没写对
- 状态写对了，但下一轮没接上
- 会话流转对了，但历史展示错了
- 用户在回答澄清问题，系统却把它当成新请求

所以这类项目的测试价值在于：

- 证明它不是“偶尔能跑”
- 证明多轮行为是可预期的
- 证明系统边界是清楚的
- 证明你在做的是“工程化 Agent”，而不是 prompt demo

这也是面试时最容易加分的点。

---

## 三、测试思路：按状态流转分层，而不是按文件分层

推荐把测试分成 4 层。

### 1. 状态规则层

测试对象：

- `session_state.py`

目标：

- 关键词和规则是否能正确推断 `mode`
- 是否能正确推断 `operation`
- 是否会触发 `pending_clarification`

这一层特点：

- 快
- 稳
- 适合先补

这层本质上是在测：

**“状态判断规则是否合理”**

---

### 2. Dispatcher 层

测试对象：

- `dispatch(state)`

目标：

- 进入 `waiting` / `note_taking` / `exit` 是否正确
- 是否会设置：
  - `mode`
  - `operation`
  - `pending_clarification`
  - `pending_question`
  - `pending_context`

这一层最关键，因为它是：

**“用户输入 -> 会话状态更新”** 的第一道入口

如果这层稳，后续很多问题都会少。

---

### 3. Graph / Workflow 层

测试对象：

- 主图 `dispatch -> react_agent -> export_session`

目标：

- `waiting` 是否正确终止
- `note_taking` 是否正确进入 ReAct
- 会话状态是否沿图正确传递
- 导出环节是否能拿到正确 thread 状态

这一层不需要一开始写很多，只需要覆盖 1 到 3 条最关键路径。

---

### 4. 数据一致性层

测试对象：

- `note_store`
- session history projection
- active note 状态

目标：

- note 对象更新后，索引是否同步
- version 冲突是否生效
- session history 展示的数据是否和真实线程状态一致

这一层非常适合你这个项目，因为你已经有：

- LangGraph persistence
- note store
- PostgreSQL history projection

这三层如果能测清楚，项目工程感会明显增强。

---

## 四、当前最值得优先写的测试

如果时间有限，不要平均铺开。  
先写最能体现项目价值的 5 到 8 个测试。

### 第一优先级：澄清回复与 follow-up

这是当前最该补的。

#### 1. 已有 active note 的 follow-up 编辑

场景：

- 已有 `active_note_id`
- 用户输入：`把这篇改详细一点`

预期：

- `intent = note_taking`
- `mode = edit`
- `operation = expand_note`
- 不设置 `pending_clarification`

价值：

- 证明已有 note 的 follow-up 正常

---

#### 2. 模糊 note target 触发澄清

场景：

- 没有 `active_note_id`
- 用户输入：`帮我改一下这篇`

预期：

- `intent = waiting`
- `pending_clarification = note_target`
- 有 `pending_question`
- 有一条 AI 澄清消息

价值：

- 证明系统能识别“信息不足，需要先问清”

---

#### 3. 已有 active note 但编辑动作不明确时触发澄清

场景：

- 已有 `active_note_id`
- 用户输入：`帮我改一下这篇笔记`

预期：

- `intent = waiting`
- `pending_clarification = edit_operation`
- 不直接进 `general_follow_up`

价值：

- 证明系统能区分“普通 follow-up”和“需要补动作信息”

---

#### 4. 澄清回复补全 note target

场景：

- 当前状态：
  - `pending_clarification = note_target`
  - `pending_context` 已记录原始任务
- 用户输入：`RAG 那篇`

预期：

- `intent = note_taking`
- `operation = locate_note`
- `pending_clarification = none`
- `pending_question = None`
- `pending_context = None`

价值：

- 证明用户的澄清回复会被当作“补全上一轮任务”，而不是新请求

---

#### 5. 明确编辑动作不应误触发澄清

场景：

- 已有 `active_note_id`
- 用户输入：`把这篇翻译成中文`

预期：

- `intent = note_taking`
- `operation = translate_note`
- 不进入 `waiting`
- 不设置 `pending_clarification`

价值：

- 证明系统不会把明确请求误判成需要澄清

---

### 第二优先级：状态流转与线程续接

#### 6. session mode 在非 note_taking 时不被破坏

场景：

- 当前 `mode = edit`
- 用户输入：`你好`

预期：

- `intent = waiting`
- `mode` 不被异常重置

价值：

- 证明闲聊不会冲掉当前工作上下文

---

#### 7. locate -> read -> edit 的最小链路

场景：

- 用户先说：`帮我找一下 RAG 那篇笔记`
- 找到 note 后再说：`把这篇改详细一点`

预期：

- 第一轮进入 `locate_note`
- 第二轮进入 `expand_note`
- `active_note_id` 被正确续接

价值：

- 证明多轮“先定位再编辑”的主流程是闭环的

---

### 第三优先级：数据一致性

#### 8. note 更新后 version 正确增加

场景：

- 创建 note
- 更新 note

预期：

- `version + 1`
- `updated_at` 更新
- 索引同步更新

---

#### 9. note 冲突更新能正确报错

场景：

- 用旧 version 更新

预期：

- 抛出 `NoteConflictError`

---

#### 10. session history projection 与线程状态一致

场景：

- 导出 session history

预期：

- `thread_id`
- `mode`
- `active_note_title`
- `messages preview`

这些字段在 projection 中和线程状态对得上

价值：

- 证明前端展示不是“假数据”

---

## 五、推荐的测试实施顺序

按 ROI 建议这样做：

1. `session_state.py` 的规则测试
2. `dispatch(state)` 的状态测试
3. 1 到 2 个 graph integration test
4. note store / history projection 一致性测试

不要一开始就：

- 大量测前端 UI
- 大量测提示词文本
- 大量做端到端浏览器测试

这些当前 ROI 不高。

---

## 六、每类测试怎么写更合适

### 1. 规则测试

特点：

- 直接
- 快速
- 不依赖 LLM / 前端 / 外部服务

适合断言：

- `mode`
- `operation`
- `pending_clarification`

---

### 2. Dispatcher 测试

建议：

- 尽量 mock LLM structured output
- 把注意力放在返回状态而不是自然语言细节

重点断言：

- `intent`
- `mode`
- `operation`
- `pending_clarification`
- `pending_context`

---

### 3. Graph 测试

建议：

- 只选关键路径
- 尽量 mock ReAct 子图
- 不要把外部模型调用引进来

重点断言：

- 走了哪条边
- 最终状态是否正确

---

### 4. Projection / Store 测试

建议：

- 用临时数据库或测试 schema
- 或先做轻量 mock / isolated test

重点断言：

- 插入
- 更新
- 版本冲突
- 历史查询排序与字段完整性

---

## 七、面试时怎么讲这套测试

你可以这样讲：

> 这个项目不是单轮生成，而是多轮会话型 Agent，所以我没有把测试重点放在工具函数覆盖率上，而是优先测试了状态流转。  
> 我重点验证了 active note 的 follow-up、澄清回复、会话状态延续、以及 history projection 和业务状态的一致性。  
> 这样可以证明这个 Agent 的行为是可预期的，不是偶尔靠 prompt 碰巧成功。

这个说法会比“我写了很多测试”更强。

---

## 八、当前最建议你先落地的最小测试集

如果你现在只想先做一个面试可讲版本，我建议先完成这 6 个：

1. `test_follow_up_edit_with_active_note_routes_to_expand_note`
2. `test_ambiguous_note_reference_requests_note_target_clarification`
3. `test_generic_edit_request_on_active_note_requests_operation_clarification`
4. `test_clarification_reply_resolves_note_target_back_to_note_taking`
5. `test_specific_edit_operation_does_not_trigger_clarification`
6. `test_session_history_projection_matches_thread_state`

这 6 个就已经足够构成一条很清晰的“多轮 Agent 工程验证”故事线。

---

## 九、一句话总结

这个项目的测试核心不是：

- 某个函数有没有返回某个字符串

而是：

**用户输入 -> 会话状态 -> 笔记对象 -> 历史投影** 这条链是否稳定、可预期、可验证。
