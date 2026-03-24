import operator
from typing import TypedDict, Annotated, List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.utils.logging import logger
from agent.llm import llm
from agent.tools import all_tools

# --- 新的 LangGraph 原生 Agent ---

# 1. 为 Agent 内部循环定义独立的状态
#    这只在 Agent 内部使用，用于追踪消息历史
class IngestionLoopState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

# 2. 设置工具和绑定到模型的 Agent
#    动态地从 all_tools 中查找所需的工具
read_tool = all_tools.get("read_local_document")
if not read_tool:
    raise ValueError("The required 'read_local_document' tool was not found.")

# 通过排除已知工具来推断远程工具的名称
# 这假设此 Agent 只需要一个本地工具和一个远程工具
fetch_tool = None
for name, tool in all_tools.items():
    if name != "read_local_document":
        fetch_tool = tool
        logger.info(f"Inferred remote tool name to be '{name}'. Using it as the fetch tool.")
        break

if not fetch_tool:
    raise ValueError("Could not infer the fetch tool from the list of all tools.")

tools = [fetch_tool, read_tool]

# 从 prompts/system.txt 加载简化的系统提示
# (我们将在下一步修改这个文件)
from pathlib import Path
prompt_path = Path(__file__).parent / "prompts" / "system.txt"
system_prompt = prompt_path.read_text(encoding="utf-8")

# 将工具绑定到 LLM，使其成为一个 Tool-Calling Agent
agent = llm.bind_tools(tools)

# 3. 为 Agent 循环定义图节点
async def call_model(state: IngestionLoopState) -> dict:
    """调用 LLM，LLM 会决定是调用工具还是直接回答"""
    logger.info("--- Ingestion Agent: Calling Model ---")
    response = await agent.ainvoke(state["messages"])
    # Agent 的响应是一个新的消息，可能包含工具调用
    return {"messages": [response]}

# ToolNode 会自动执行工具调用
tool_node = ToolNode(tools)

def should_continue(state: IngestionLoopState) -> str:
    """根据模型的最新响应，决定下一步是调用工具还是结束"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        logger.info("--- Ingestion Agent: Tool Call Detected. Routing to tools. ---")
        return "continue"
    logger.info("--- Ingestion Agent: No Tool Call. Ending subgraph. ---")
    return "end"

# 4. 构建 Agent 的内部执行图
agent_loop_workflow = StateGraph(IngestionLoopState)
agent_loop_workflow.add_node("call_model", call_model)
agent_loop_workflow.add_node("call_tool", tool_node)

agent_loop_workflow.set_entry_point("call_model")

agent_loop_workflow.add_conditional_edges(
    "call_model",
    should_continue,
    {"continue": "call_tool", "end": END},
)
agent_loop_workflow.add_edge("call_tool", "call_model")

# 编译成一个可执行的图
agent_loop_graph = agent_loop_workflow.compile()
agent_loop_graph.name = "内容提取循环"


# 5. 定义一个包装节点，以便与主图（Main Graph）兼容
async def run_ingestion_agent(state: AgentState) -> dict:
    """
    此节点运行整个内容提取子图。
    它负责将主图的状态转换为子图的输入，并处理最终输出。
    """
    logger.info("--- Subgraph: Ingestion Agent ---")
    extracted_data = state.get("extracted_data", [])
    if not extracted_data:
        logger.warning("No extracted data to process. Skipping ingestion agent.")
        return {"all_raw_contents": "", "has_successful_content": False, "processing_errors": ["No data provided."]}

    # 格式化 Agent 的初始输入
    input_str = "请从以下来源提取内容:"
    for i, item in enumerate(extracted_data):
        input_str += f"{i+1}. 类型: '{item.type}', 内容: '{item.content}'"
    
    logger.info(f"Invoking ingestion agent with task: {input_str.strip()}")
    
    # 构建初始消息列表
    initial_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_str),
    ]
    
    try:
        # 调用上面定义的 Agent 循环图
        final_state = await agent_loop_graph.ainvoke(
            {"messages": initial_messages},
            config={"recursion_limit": 25} # 设置递归限制以防无限循环
        )
        
        # 从最终状态中提取 Agent 的回答
        final_output = final_state["messages"][-1].content
        all_raw_contents = final_output.strip()

        if all_raw_contents:
            logger.info(f"Ingestion agent successfully extracted content (total length: {len(all_raw_contents)}).")
            return {"all_raw_contents": all_raw_contents, "has_successful_content": True, "processing_errors": []}
        else:
            logger.warning("Ingestion agent finished but returned no content.")
            return {"all_raw_contents": "", "has_successful_content": False, "processing_errors": ["Agent failed to extract any content."]}

    except Exception as e:
        logger.error(f"An error occurred during ingestion agent execution: {e}", exc_info=True)
        return {"all_raw_contents": "", "has_successful_content": False, "processing_errors": [str(e)]}

# --- 用于导出的最终图 ---
# 保持与主图兼容的结构：一个只包含单个节点的图
workflow = StateGraph(AgentState)
workflow.add_node("run_ingestion_agent", run_ingestion_agent)
workflow.set_entry_point("run_ingestion_agent")
workflow.add_edge("run_ingestion_agent", END)

ingestion_agent_graph = workflow.compile()
# 更新图的名称以反映其新实现
ingestion_agent_graph.name = "内容提取智能体 (LangGraph)"
