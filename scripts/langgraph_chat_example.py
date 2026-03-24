# -*- coding: utf-8 -*-
"""
langgraph_chat_example_simple.py

一个使用 LangGraph 实现的、纯粹的多轮对话机器人。
这个版本去除了所有工具调用的逻辑，专注于对话本身。
"""

import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# --- 1. 准备工作：加载依赖和配置 ---

# 加载 .env 文件中的环境变量
load_dotenv()

# 检查 API Key 是否设置
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

# 初始化一个标准的 LLM，这次我们不需要绑定任何工具
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, seed=42)


# --- 2. 定义 Agent 的状态 ---
# 状态依然是核心，用于保存和传递多轮对话的历史消息。
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# --- 3. 定义图的节点 ---
# 在这个简化版本中，我们只需要一个节点：调用 LLM。

def call_model(state: AgentState):
    """调用 LLM 进行对话"""
    print("--- 节点：调用 LLM ---")
    messages = state['messages']
    response = llm.invoke(messages)
    # 将 LLM 的回复添加到状态中，然后返回
    return {"messages": [response]}


# --- 4. 构建并编译图 ---
# 这个图现在是一个非常简单的线性流程。

# 创建一个 StateGraph 实例
workflow = StateGraph(AgentState)

# 添加唯一的节点
workflow.add_node("agent", call_model)

# 设置图的入口点
workflow.set_entry_point("agent")

# 设置图的终点：在 agent 节点执行完毕后，流程就结束了。
workflow.add_edge("agent", END)

# 编译图，生成可执行的应用
app = workflow.compile()


# --- 5. 运行多轮对话 ---

if __name__ == "__main__":
    print("纯聊天 Agent 已启动！输入 'quit' 或 'exit' 退出。")
    
    # 用于保存当前对话的完整状态
    # 在这个循环中，我们手动管理状态的传递
    current_state = {"messages": []}

    while True:
        # 获取用户输入
        user_input = input("你: ")
        if user_input.lower() in ["quit", "exit"]:
            print("Agent 已关闭。")
            break

        # 将用户的最新消息添加到当前状态中
        # 注意：这里我们使用了 `add_messages` 的原理，手动追加消息
        current_state["messages"].append(HumanMessage(content=user_input))

        # 调用图，并传入包含完整历史的当前状态
        final_state = app.invoke(current_state)
        
        # 从返回的最终状态中获取最新的 AI 回复
        ai_response = final_state["messages"][-1]
        
        # 打印 AI 回复
        print(f"Agent: {ai_response.content}")

        # 更新当前状态，为下一轮对话做准备
        current_state = final_state
