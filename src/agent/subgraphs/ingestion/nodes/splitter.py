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
