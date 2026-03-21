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
