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
