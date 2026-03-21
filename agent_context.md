# LangGraph 智能笔记 Agent 项目上下文

本文档为 AI 代码助手提供 LangGraph 智能笔记 Agent 项目的完整上下文，旨在帮助其理解项目架构、代码实现和开发目标，以便进行后续的代码修改和功能开发。

## 1. 项目计划书与顶层设计

`LangGraph 智能笔记 Agent 项目计划书.md` 是本项目的核心指导文件。

### 1.1. 核心定位
专为 Agent 岗位面试打造的实战型 LangGraph 项目，核心解决：多源文件 / 链接自动解析 + 个性化无重复笔记生成 + AI 配图一体化需求，完整体现 LLM Agent、工作流编排、工具调用、本地文件交互等核心能力。

### 1.2. 核心需求与现状
- **输入源**: ✅ 已实现网页链接和文本输入。
- **核心处理**: ✅ 已实现意图识别和数据提取。🟡 笔记生成部分为占位符。
- **关键能力 (去重)**: ❌ 未实现。
- **输出要求**: ✅ 已实现基础文本输出（非格式化 MD）。
- **个性化配置**: ❌ 未实现。
- **扩展能力 (AI 配图)**: ❌ 未实现。

### 1.3. 核心工作流
项目遵循一个清晰的、分阶段的流水线架构：
1.  **输入与意图分析 (Input & Dispatch)**: `[✅ 已实现]`
2.  **内容提取 (Content Ingestion)**: `[✅ 已实现]`
3.  **核心内容生成 (Core Content Generation)**: `[🟡 部分实现 - 占位符]`
4.  **初步结构化 (Initial Structuring)**: `[❌ 未实现]`
5.  **内容去重 (Content Deduplication)**: `[❌ 未实现]`
6.  **个性化与输出 (Personalization & Output)**: `[❌ 未实现]`

### 1.4. 下一步计划
1.  **实现核心内容生成**: 将 `notes_generator` 中的占位符替换为真实的 LLM 总结功能。
2.  **实现内容去重**: 引入向量数据库。
3.  **实现初步结构化**: 增加 LLM 节点，将原文整理成结构化的 Markdown。

---

## 2. 项目架构与文件解析

### 2.1. 项目结构
```
src/
└── agent/
    ├── __init__.py
    ├── graph.py            # 主工作流图
    ├── llm.py              # LLM 实例初始化
    ├── main.py             # 程序主入口
    ├── session.py          # 交互式会话逻辑
    ├── state.py            # Agent 全局状态定义
    ├── ui.py               # 终端 UI
    ├── subgraphs/
    │   ├── dispatcher/     # 1. 调度员子图 (意图分析)
    │   ├── ingestion/      # 2. 内容提取子图
    │   └── notes_generator/# 3. 笔记生成子图 (占位符)
    ├── tools/
    │   └── mcp_tools.py    # MCP 远程工具加载
    └── utils/
        └── logging.py      # 日志配置
```

### 2.2. Agent 核心文件

#### `src/agent/main.py`
**职责**: 程序的唯一入口点。负责初始化、生成工作流图并启动交互式会话。
```python
import asyncio
import os
import sys
from pathlib import Path

# 将 src 目录添加到 sys.path，以便将 'agent' 视为可导入的包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import graph
from agent.session import run_interactive_session
from agent.utils.logging import logger


def generate_graph_image():
    """
    生成并保存 Agent 工作流的 PNG 图像。
    """
    logger.info("Generating agent workflow graph...")
    try:
        # 获取图的PNG图像数据

        png_bytes = graph.get_graph(xray=True).draw_mermaid_png()

        # 定义输出路径到项目根目录
        output_path = Path(__file__).parent.parent.parent / "agent_graph.png"
        with open(output_path, "wb") as f:
            f.write(png_bytes)

        logger.info(f"Graph image saved to: {output_path}")

    except Exception as e:
        logger.error(f"An error occurred while generating the graph: {e}")
        logger.warning(
            "Please ensure 'pyppeteer' is installed (`pip install pyppeteer`) and internet connection is working. "
            "It may need to download a browser instance on first run."
        )


def main():
    """
    Agent 的主入口点。
    设置 asyncio 策略，生成工作流图，然后启动交互式会话。
    """
    # 在 Windows 平台上，为 pyppeteer 设置必需的 asyncio 事件循环策略
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 每次启动时都重新生成最新的工作流图，方便调试
    generate_graph_image()

    # 启动交互式会话循环
    asyncio.run(run_interactive_session())


if __name__ == "__main__":
    main()
```

#### `src/agent/session.py`
**职责**: 管理用户的交互式会话。处理循环输入、调用主图 (`graph.ainvoke`)、并根据最终状态显示结果。同时支持从 `inputs.json` 文件加载初始输入。
```python
import asyncio
import json
from pathlib import Path
from agent.graph import graph
from agent import ui
from agent.utils.logging import logger


async def run_interactive_session():
    """
    运行一个交互式的Agent会话，处理用户的循环输入。
    程序启动时会尝试读取 inputs.json 作为初始输入，处理完毕后进入交互模式。
    """
    ui.display_welcome_message()

    # --- NEW LOGIC: Process initial input from inputs.json ---
    initial_input_processed = False
    inputs_file_path = Path(__file__).parent.parent.parent / "inputs.json"
    if inputs_file_path.exists():
        logger.info(f"Attempting to load initial input from {inputs_file_path}")
        try:
            with open(inputs_file_path, 'r', encoding='utf-8') as f:
                initial_inputs = json.load(f)
            
            initial_user_input = initial_inputs.get("user_input", "")
            
            if initial_user_input:
                logger.info("Processing initial input from inputs.json...")
                ui.display_user_prompt_echo(initial_user_input) # Echo the input from file

                # Invoke the graph with the initial inputs (which can include user_input and user_preferences)
                final_state = await graph.ainvoke(initial_inputs)

                intent = final_state.get("intent")
                if intent == 'note_taking':
                    final_note = final_state.get("final_note", "")
                    ui.display_note_processed(final_note)
                elif intent == 'waiting':
                    response = final_state.get("response_to_user") or "输入不合规，无法处理。"
                    ui.display_agent_feedback(response)
                
                print("-" * 30) # Separator after initial run
                initial_input_processed = True
            else:
                logger.warning("inputs.json found but 'user_input' field is empty.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse inputs.json: {e}", exc_info=True)
            ui.display_error(f"加载或解析 inputs.json 文件失败: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during initial inputs.json processing: {e}", exc_info=True)
            ui.display_error(f"处理 initial inputs.json 时发生意外错误: {e}")

    if not initial_input_processed:
        logger.info("No valid initial input from inputs.json, starting interactive loop directly.")
        # If no initial input was processed, print separator to make it clear we're entering interactive mode.
        print("-" * 30) 
    # --- END NEW LOGIC ---

    # Existing interactive loop
    while True:
        try:
            user_input = ui.prompt_for_input()
            ui.display_user_prompt_echo(user_input) # Echo the interactive input

            if not user_input.strip():
                continue

            # Invoke the graph with the interactive user input
            # (user_preferences are not gathered interactively in this simplified version)
            final_state = await graph.ainvoke({"user_input": user_input})

            intent = final_state.get("intent")

            if intent == 'exit':
                ui.display_exit_message()
                break
            elif intent == 'note_taking':
                final_note = final_state.get("final_note", "")
                ui.display_note_processed(final_note)
            elif intent == 'waiting':
                response = final_state.get("response_to_user") or "请提供有效输入。"
                ui.display_agent_feedback(response)

            print("-" * 30)

        except (KeyboardInterrupt, EOFError):
            ui.display_interrupt_message()
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred in the session loop: {e}", exc_info=True)
            ui.display_error("程序运行出现意外错误，请检查日志。")
            logger.info("Session loop will continue.")
            print("-" * 30)
```

#### `src/agent/graph.py`
**职责**: 定义和构建项目的**主工作流图 (Main Graph)**。它像一个总指挥，负责将各个子图（dispatcher, ingestion, notes_generator）按照预设逻辑连接起来。
```python
"""
Defines the main workflow for the Note Agent by wiring together subgraphs.
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.utils.logging import logger

# Import the subgraphs and the dispatcher node
from agent.subgraphs.dispatcher import dispatch
from agent.subgraphs.ingestion import ingestion_graph
from agent.subgraphs.notes_generator import notes_graph

# --- Main Graph Routing Logic ---
def route_after_dispatch(state: AgentState):
    """
    After the dispatcher node, decide whether to start processing notes or end.
    """
    intent = state.get("intent")
    if intent == "note_taking":
        logger.info("Intent 'note_taking' received. Routing to ingestion sub-graph.")
        return "ingestion_subgraph"
    elif intent in ["waiting", "exit"]:
        logger.info(f"Intent '{intent}' received. Ending main graph run.")
        return END
    else:
        logger.warning(f"Unknown intent: '{intent}'. Ending graph execution.")
        return END

def route_after_ingestion(state: AgentState) -> str:
    """
    After the content ingestion sub-graph, route based on whether content was successfully parsed.
    """
    if state.get("has_successful_content"):
        logger.info("Ingestion successful. Routing to notes generation sub-graph.")
        return "notes_subgraph"
    else:
        logger.warning("Ingestion failed or produced no content. Routing back to dispatcher.")
        state["intent"] = "waiting" 
        errors = state.get("processing_errors", [])
        state["response_to_user"] = "抱歉，内容处理失败：" + "".join(f"- {e}" for e in errors)
        return "dispatch"

# --- Main Workflow Construction ---
workflow = StateGraph(AgentState)

# 1. Add nodes (the dispatcher and the compiled subgraphs)
workflow.add_node("dispatch", dispatch)
workflow.add_node("ingestion_subgraph", ingestion_graph)
workflow.add_node("notes_subgraph", notes_graph)

# 2. Set entry point
workflow.set_entry_point("dispatch")

# 3. Build connections (edges)
workflow.add_conditional_edges(
    "dispatch",
    route_after_dispatch,
    {
        "ingestion_subgraph": "ingestion_subgraph",
        END: END,
    },
)

workflow.add_conditional_edges(
    "ingestion_subgraph",
    route_after_ingestion,
    {
        "notes_subgraph": "notes_subgraph",
        "dispatch": "dispatch", # If ingestion fails, go back to the start
    },
)

workflow.add_edge("notes_subgraph", END)

# 4. Compile the workflow
graph = workflow.compile()
graph.name = "主协调 Agent"

# --- Helper function for visualization ---
def get_graph(xray: bool = False):
    """
    Returns the uncompiled workflow object to allow for visualization.
    """
    return workflow
```

#### `src/agent/state.py`
**职责**: 定义 Agent 在整个工作流中传递的**全局状态 `AgentState`**。这是 LangGraph 的核心，所有节点都通过读写这个 `TypedDict` 来共享信息和推进流程。
```python
"""
Defines the global state for the Note Agent.
"""
from typing import TypedDict, List, Any, Dict, Optional

# The ExtractedData schema is now part of the dispatcher subgraph
from agent.subgraphs.dispatcher.schemas import ExtractedData

class AgentState(TypedDict):
    """
    Manages the state of the Note Agent workflow.
    """
    # Initial input
    user_input: str

    # Output from the dispatcher subgraph
    intent: str
    extracted_data: Optional[List[ExtractedData]]
    response_to_user: Optional[str]

    # State for the ingestion subgraph
    urls_to_process: Optional[List[str]]
    texts_to_process: Optional[List[str]]
    parsed_url_contents: Optional[List[str]]
    parsed_text_contents: Optional[List[str]]
    all_raw_contents: Optional[str]

    # State for the notes generation process
    raw_content: str
    structured_content: str
    novel_content: str
    core_content: str
    final_note: str

    # Error handling and routing
    processing_errors: Optional[List[str]]
    has_successful_content: bool
    
    # Optional fields
    input_source: str
    user_preferences: Dict[str, Any]
    generated_images: List[str]

__all__ = ["AgentState"]
```

#### `src/agent/llm.py`
**职责**: 使用单例模式初始化并公开一个全局的 `ChatOpenAI` 实例。这确保整个应用使用同一个 LLM 连接，避免重复创建。
```python
"""
LLM Singleton Module for the Agent.

This module initializes and exports a single, reusable instance of the ChatOpenAI model,
configured with the necessary API keys and settings. This allows other parts of
the application to import and use the same LLM instance without re-initializing it.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent.utils.logging import logger

# --- LLM Definition ---

# Load environment variables from a .env file in the project root.
# This file should contain your OpenAI API key, e.g., OPENAI_API_KEY="sk-..."
logger.info("Loading environment variables from .env file...")
load_dotenv()

# Check for the API key and raise an error if it's not found.
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. "
        "Please create a .env file in the project root and add your key."
    )

# Initialize a single, reusable LLM instance for the entire application.
# Using a cost-effective and performant model like 'gpt-4o-mini' is a good start.
# The 'seed' parameter helps in achieving more reproducible outputs for the same inputs.
logger.info("Initializing ChatOpenAI model instance (gpt-4o-mini)...")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, seed=42)
```

---

### 2.3. 子图 (Subgraphs)

#### 2.3.1. `dispatcher` - 调度员子图

**职责**: 作为流程入口，分析用户输入，判断意图（`note_taking`, `waiting`, `exit`），并提取内容（URL 或文本）。

**`subgraphs/dispatcher/node.py`**:
```python
"""
定义调度员节点 (Dispatcher Node)，作为 Agent 的入口。
"""
from typing import Dict, Any

from agent.llm import llm
from .schemas import DispatcherOutput
from .prompts import create_dispatcher_prompt
from agent.utils.logging import logger

# 为调度员LLM创建一个结构化输出链
# Pydantic模型`DispatcherOutput`定义了我们希望LLM返回的JSON结构
structured_llm = llm.with_structured_output(DispatcherOutput)

# 从外部加载提示词，而不是在代码中硬编码
dispatcher_prompt = create_dispatcher_prompt()

# 将提示词和结构化输出的LLM链接起来，构成完整的调度链
dispatcher_chain = dispatcher_prompt | structured_llm


def dispatch(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点：调度员 (Dispatcher)

    功能：作为Agent的入口，分析用户输入，判断意图，提取数据，并生成引导性回复。
    """
    logger.info("--- Node: Dispatcher ---")
    user_input = state.get("user_input", "")
    if not user_input:
        logger.warning("User input is empty.")
        # 虽然当前循环不会让空输入进入，但保留此防御性代码
        return {"intent": "waiting", "extracted_data": []}

    logger.info(f"Analyzing user input: '{user_input[:80]}...'")

    # 调用调度链
    response: DispatcherOutput = dispatcher_chain.invoke({"user_input": user_input})

    logger.info(f"LLM analysis complete. Intent: '{response.intent}'")
    if response.intent == "waiting":
        logger.debug(f"LLM generated response for user: '{response.response_to_user}'")

    if response.data:
        # 详细的提取数据作为 DEBUG 信息，避免刷屏
        for item in response.data:
            logger.debug(f"Extracted data: type='{item.type}', content='{item.content[:100]}...'")

    return {
        "intent": response.intent,
        "extracted_data": response.data,
        "response_to_user": response.response_to_user,
    }
```

**`subgraphs/dispatcher/schemas.py`**:
```python
"""
定义调度员节点使用的 Pydantic 模型，用于 LLM 的结构化输出。
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ExtractedData(BaseModel):
    """定义从用户输入中提取的数据结构。"""
    type: Literal["url", "text"] = Field(description="提取的数据类型，只能是 'url' 或 'text'")
    content: str = Field(description="提取出的纯净内容（URL链接或文本）")


class DispatcherOutput(BaseModel):
    """定义调度员LLM输出的完整结构。"""
    intent: Literal["note_taking", "waiting", "exit"] = Field(
        description="用户的意图, 'note_taking'表示内容符合要求可以处理笔记, 'waiting'表示输入不合规、继续等待, 'exit'表示用户希望退出程序"
    )
    data: Optional[List[ExtractedData]] = Field(
        description="一个包含提取数据的列表，当意图是 'note_taking' 时不应为空"
    )
    response_to_user: Optional[str] = Field(
        default=None,
        description="当意图是 'waiting' 时，此处应包含一句对用户的友好回复，解释为何无法处理并引导用户提供正确输入。"
    )
```

**`subgraphs/dispatcher/prompts/system.txt`**:
```
你是一个AI助手的前端调度员。你的任务是严格分析用户的输入，判断其意图，并提取相关信息。这是一个无记忆的循环对话，只有当用户提供了有效的内容用于记笔记时，你才能将意图设为 'note_taking'。

根据以下规则，将你的分析结果构造成一个JSON对象：

1.  **意图 (intent) 为 "note_taking" 的条件（必须同时满足）：**
    - 用户的输入中明确包含**可直接用于制作笔记的内容**。
    - 支持的内容只有两种：**网页链接 (URL)** 或 **大段的复制文本**。
    - 此时，`intent` 设为 "note_taking"，并必须在 `data` 字段中提取内容。
        - **type**: 如果是网页链接，设为 "url"；如果是文本，设为 "text"。
        - **content**: 提取纯净的URL或完整的文本块。

2.  **意图 (intent) 为 "exit" 的条件：**
    - 用户输入的内容**完全是** "quit" 或 "exit" (不区分大小写)。
    - 此时，`intent` 设为 "exit"。

3.  **意图 (intent) 为 "waiting" 的条件：**
    - **除以上两种情况外的所有其他输入**。
    - 例如：打招呼、问候、提出问题、请求不被支持的笔记类型（如“帮我记下明天的日程”）、或者提供了不完整的信息（如“帮我整理一下”）。
    - 此时，`intent` 设为 "waiting"，`data` 字段必须为空或省略。
    - **同时，你必须在 `response_to_user` 字段中，根据用户的具体输入，生成一句对用户友好的、有指导性的回复。**
        - **核心原则**：你的回复必须清晰地引导用户提供一个有效的 URL 或一段文本。
        - **风格要求**：回复应自然、简洁、礼貌。**请不要每次都使用完全相同的句子**，让对话显得更真实。
        - **场景指导**：
            - 如果用户只是在打招呼，你应该在回应问候的同时，温和地表明你的功能。
            - 如果用户表达了记笔记的意图但没有提供内容（例如“帮我整理笔记”），你应该肯定他的意图，然后请他提供具体内容。
            - 如果用户在问你的能力，你应该解释你的核心功能是处理笔记。

请严格按照 `DispatcherOutput` 的JSON格式输出。你的职责是充当一个严格的过滤器和友好的引导员。
```

---

#### 2.3.2. `ingestion` - 内容提取子图

**职责**: 接收 `dispatcher` 提取的数据，通过并行处理获取所有内容的原始文本，并整合成单一的文本流。

**`subgraphs/ingestion/graph.py`**:
```python
"""
Ingestion Sub-Graph.

This graph is responsible for taking the data extracted by the dispatcher,
parsing it, and integrating the content.
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState

# Import nodes from the current subgraph
from .nodes.splitter import split_extracted_data
from .nodes.text_parser import parse_texts
from .nodes.url_parser import parse_urls
from .nodes.integrator import integrate_content

# --- Ingestion Sub-Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("split_data", split_extracted_data)
workflow.add_node("parse_urls", parse_urls)
workflow.add_node("parse_texts", parse_texts)
workflow.add_node("integrate_content", integrate_content)

workflow.set_entry_point("split_data")
workflow.add_edge("split_data", "parse_urls")
workflow.add_edge("split_data", "parse_texts")
workflow.add_edge("parse_urls", "integrate_content")
workflow.add_edge("parse_texts", "integrate_content")
workflow.add_edge("integrate_content", END) # End of sub-graph

ingestion_graph = workflow.compile()
ingestion_graph.name = "内容提取子图"
```

**`subgraphs/ingestion/nodes/splitter.py`**:
```python
"""
内容分离节点 (Splitter Node)

功能：将调度员提取的混合数据列表，按类型（URL或文本）进行分离。
"""
from typing import Dict, Any, List
from agent.subgraphs.dispatcher.schemas import ExtractedData # 导入 ExtractedData 以便类型检查
from agent.utils.logging import logger


def split_extracted_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点：分离提取的数据

    将 `extracted_data` 列表分离成 `urls_to_process` 和 `texts_to_process` 列表。
    """
    logger.info("--- Node: Split Extracted Data ---")
    extracted_data: List[ExtractedData] = state.get("extracted_data", [])

    urls_to_process: List[str] = []
    texts_to_process: List[str] = []

    if not extracted_data:
        logger.warning("No extracted data found to split.")
        return {
            "urls_to_process": urls_to_process,
            "texts_to_process": texts_to_process,
        }

    for item in extracted_data:
        if item.type == "url":
            urls_to_process.append(item.content)
        elif item.type == "text":
            texts_to_process.append(item.content)
        else:
            logger.warning(f"Unknown extracted data type: {item.type}. Skipping.")

    logger.info(f"Split results: {len(urls_to_process)} URLs, {len(texts_to_process)} Texts.")

    return {
        "urls_to_process": urls_to_process,
        "texts_to_process": texts_to_process,
    }
```

**`subgraphs/ingestion/nodes/url_parser.py`**:
```python
from typing import Dict, Any, List
from agent.tools import mcp_tools
from agent.utils.logging import logger

async def parse_urls(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点：URL 解析器 (URL Parser)

    功能：接收 URL 列表，通过 MCP 'fetch' 工具从每个 URL 提取原始文本内容。
    成功的内容放入 `parsed_url_contents`，失败的错误信息放入 `processing_errors`。
    """
    logger.info("--- Node: URL Parser ---")
    urls_to_process: List[str] = state.get("urls_to_process", [])
    # 从 state 中获取历史错误，并准备好添加新错误
    processing_errors: List[str] = state.get("processing_errors", []) or []
    parsed_url_contents: List[str] = []

    if not urls_to_process:
        logger.info("No URLs to process. Skipping URL parsing.")
        # 即使没有URL，也要返回正确的状态结构
        return {
            "parsed_url_contents": parsed_url_contents,
            "processing_errors": processing_errors
        }
        
    fetch_tool = mcp_tools.get("fetch")
    if not fetch_tool:
        error_msg = "MCP tool named 'fetch' was not found or failed to initialize."
        logger.error(error_msg)
        # 如果工具本身就失败，将这个系统级错误计入
        processing_errors.append(error_msg)
        return {
            "parsed_url_contents": parsed_url_contents,
            "processing_errors": processing_errors
        }

    for url in urls_to_process:
        logger.info(f"Extracting content from URL: '{url}' via MCP 'fetch' tool...")
        try:
            raw_content_from_tool = await fetch_tool.ainvoke({"url": url})
            extracted_text_content = "" # 初始化确保始终得到一个字符串

            if isinstance(raw_content_from_tool, str):
                extracted_text_content = raw_content_from_tool
            elif isinstance(raw_content_from_tool, list):
                extracted_text_content = "".join(str(item) for item in raw_content_from_tool)
            elif isinstance(raw_content_from_tool, dict):
                if 'text' in raw_content_from_tool and isinstance(raw_content_from_tool['text'], str):
                    extracted_text_content = raw_content_from_tool['text']
                elif 'content' in raw_content_from_tool and isinstance(raw_content_from_tool['content'], str):
                    extracted_text_content = raw_content_from_tool['content']
                else:
                    logger.warning(f"Dictionary from fetch tool for URL '{url}' does not contain 'text' or 'content' key, or their values are not strings. Using raw string representation.")
                    extracted_text_content = str(raw_content_from_tool)
            else:
                logger.warning(f"Unexpected content type from fetch tool for URL '{url}': {type(raw_content_from_tool)}. Attempting to convert to string.")
                extracted_text_content = str(raw_content_from_tool)
            
            parsed_url_contents.append(extracted_text_content)

        except Exception as e:
            error_msg = f"URL '{url}' 解析失败: {e}"
            logger.error(error_msg, exc_info=True)
            # 将错误信息添加到专门的列表中
            processing_errors.append(error_msg)

    # 返回包含成功内容和错误信息的新状态
    return {
        "parsed_url_contents": parsed_url_contents,
        "processing_errors": processing_errors
    }
```

**`subgraphs/ingestion/nodes/integrator.py`**:
```python
"""
内容整合节点 (Integration Node)

功能：收集所有解析器（如 URL 解析器、文本解析器）的输出，将它们合并成一个统一的原始内容字符串。
"""
from typing import Dict, Any, List
from agent.utils.logging import logger

async def integrate_content(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点：内容整合

    将 `parsed_url_contents` 和 `parsed_text_contents` 合并成 `all_raw_contents`。
    同时，根据是否有成功解析的内容，决定下一步的路由。
    """
    logger.info("--- Node: Content Integration ---")
    # 注意：即使上游节点失败，这些键也应该存在，并且其值为 空列表[]
    parsed_url_contents: List[str] = state.get("parsed_url_contents") or []
    parsed_text_contents: List[str] = state.get("parsed_text_contents") or []
    
    all_contents: List[str] = []
    
    if parsed_url_contents:
        logger.info(f"Integrating {len(parsed_url_contents)} items from URL parser.")
        all_contents.extend(parsed_url_contents)
        
    if parsed_text_contents:
        logger.info(f"Integrating {len(parsed_text_contents)} items from Text parser.")
        all_contents.extend(parsed_text_contents)

    # 决策逻辑：判断是否有任何成功的内容
    if not all_contents:
        logger.warning("No parsed content found for integration. All sources might have failed or were empty.")
        # 没有任何内容，返回空字符串和 False 标志
        return {"all_raw_contents": "", "has_successful_content": False}
        
    # 将所有内容用分隔符合并
    all_raw_contents = "---".join(all_contents)
    logger.info(f"Integrated total content length: {len(all_raw_contents)} characters.")

    # 有成功的内容，返回合并后的字符串和 True 标志
    return {"all_raw_contents": all_raw_contents, "has_successful_content": True}
```

---

#### 2.3.3. `notes_generator` - 笔记生成子图

**职责**: **(当前为占位符)** 接收整合后的原始文本流，并生成最终笔记。
**现状**: 这是一个待开发的**核心功能**。目前它只截取原文的前 500 个字符作为摘要。

**`subgraphs/notes_generator/graph.py`**:
```python
"""
Notes Generation Sub-Graph (Placeholder).
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.utils.logging import logger

def placeholder_notes_node(state: AgentState) -> dict:
    """A placeholder node that simulates note generation."""
    logger.info("--- Sub-Graph: Notes Generation (Placeholder) ---")
    all_raw_contents = state.get("all_raw_contents", "")
    if all_raw_contents:
        # Create a simple summary as a placeholder for the final note
        final_note = f"这是根据您的内容生成的笔记摘要：{all_raw_contents[:500]}..."
        logger.info("Generated a placeholder note.")
    else:
        final_note = ""
        logger.warning("No raw content available to generate notes.")
    return {"final_note": final_note}

notes_workflow = StateGraph(AgentState)
notes_workflow.add_node("generate_notes", placeholder_notes_node)
notes_workflow.set_entry_point("generate_notes")
notes_workflow.add_edge("generate_notes", END)
notes_graph = notes_workflow.compile()
notes_graph.name = "笔记生成子图"
```

### 2.4. 工具与辅助模块

#### `src/agent/tools/mcp_tools.py`
**职责**: 初始化 MCP (Model-Scope Cloud Platform) 客户端，并从远程服务地址获取 `fetch` 工具。这个工具被 `url_parser` 节点用来抓取网页内容。
```python
"""
This module initializes the MCP client and fetches tools from the remote server.
"""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from agent.utils.logging import logger

# User-provided MCP configuration.
# The key 'fetch' is a local alias for this server connection.
MCP_CONFIG = {
    "fetch": {
        # The client expects the key to be 'transport', not 'type'.
        "transport": "sse",
        "url": "https://mcp.api-inference.modelscope.net/6be788ed9cbf40/sse"
    }
}

async def _initialize_tools_from_mcp() -> dict[str, BaseTool]:
    """
    Initializes the MCP client and fetches all available tools,
    returning them in a dictionary keyed by their names.
    """
    tool_dict = {}
    try:
        logger.info("Initializing MCP client and fetching remote tools...")
        client = MultiServerMCPClient(MCP_CONFIG)
        tools = await client.get_tools()
        
        if not tools:
            raise RuntimeError("MCP server did not return any tools.")
            
        for tool in tools:
            logger.info(f"Successfully fetched tool: {tool.name}")
            tool_dict[tool.name] = tool
            
        return tool_dict
    except Exception as e:
        logger.error(f"Failed to initialize MCP tools: {e}")
        # In case of failure, return an empty dict.
        return {}

# Run the async initialization function at module load time.
# The result is a dictionary of tools that can be imported elsewhere.
# This ensures we only initialize the client and fetch tools once.
logger.info("Fetching MCP tools at module load...")
# Note: Using asyncio.run() here is a simple way to handle async initialization
# in a synchronous context. It creates a new event loop.
mcp_tools = asyncio.run(_initialize_tools_from_mcp())
```

#### `src/agent/ui.py`
**职责**: 封装所有面向用户的终端 UI 打印功能，如欢迎语、用户输入提示、错误信息等。
```python
"""
此模块负责所有面向用户的终端 UI 显示。
"""

def display_welcome_message():
    """打印初始欢迎信息和说明。"""
    print("--- 智能笔记 Agent 已启动 ---")
    print("请输入文本内容或URL以创建笔记。输入 'quit' 或 'exit' 退出。")
    print("-" * 30)

def prompt_for_input() -> str:
    """显示用户输入提示符并返回输入内容。"""
    return input("用户输入 > ")

def display_user_prompt_echo(user_input: str):
    """回显用户刚刚输入的内容。"""
    print(f"> {user_input}")

def display_exit_message():
    """打印退出时的告别信息。"""
    print("--- 感谢使用，再见！ ---")

def display_note_processed(final_note: str):
    """
    打印笔记处理完成后的最终笔记和后续提示。
    如果 final_note 为空（例如被过滤或生成失败），则会显示不同消息。
    """
    if final_note and final_note.strip():
        print("--- 最终生成的笔记 ---")
        print(final_note)
        print("--------------------")
        print("✅ 笔记处理完成。您可以输入新的内容，或使用 'quit' 退出。")
    else:
        print("ℹ️  内容已处理，但未生成最终笔记（可能因内容重复或不充分）。")
        print("您可以输入新的内容，或使用 'quit' 退出。")

def display_agent_feedback(message: str):
    """向用户显示来自 Agent 的通用反馈信息。"""
    # 统一加上一个前缀，让用户知道这是 Agent 的回复
    print(f"[Agent] {message}")

def display_error(message: str):
    """以统一格式向用户显示错误信息。"""
    print(f"❌ 发生错误: {message}")

def display_interrupt_message():
    """在用户强制中断 (Ctrl+C) 时打印消息。"""
    print("--- 检测到中断，强制退出。 ---")
```

#### `src/agent/utils/logging.py`
**职责**: 配置项目全局的日志记录器 `logger`。
```python
"""
配置项目专用的日志记录器。
"""
import logging
import os
import sys

# 1. 从环境变量获取日志级别，默认为 INFO
#    可以通过设置 LOG_LEVEL=DEBUG 来显示更详细的日志
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

# 2. 创建一个全局的 Logger 实例
logger = logging.getLogger("NoteAgent")
logger.setLevel(log_level)

# 3. 如果 logger 还没有 handlers，则为其添加一个
#    这可以防止在多次导入时重复添加 handler
if not logger.handlers:
    # 创建一个流处理器 (StreamHandler)，将日志输出到标准错误 (stderr)
    # 输出到 stderr 是日志记录的最佳实践，可以将日志与程序的标准输出分开
    handler = logging.StreamHandler(sys.stderr)
    
    # 4. 定义日志格式
    # 格式: [LEVEL] [file:line] message
    formatter = logging.Formatter(
        "[%(levelname)s] [%(module)s.py:%(lineno)d] %(message)s"
    )
    handler.setFormatter(formatter)
    
    # 5. 将处理器添加到 logger
    logger.addHandler(handler)

# 确保日志级别设置成功
logger.info(f"Logger initialized with level {log_level_name}")

__all__ = ["logger"]
```
