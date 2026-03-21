"""
文本解析节点 (Text Parser Node)

功能：接收文本列表，直接将其内容作为解析结果。
"""
from typing import Dict, Any, List
from agent.utils.logging import logger

async def parse_texts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    节点：文本解析器

    将 `texts_to_process` 列表中的文本内容作为解析结果返回。
    """
    logger.info("--- Node: Text Parser ---")
    texts_to_process: List[str] = state.get("texts_to_process", [])
    parsed_text_contents: List[str] = []

    if not texts_to_process:
        logger.info("No texts to process. Skipping text parsing.")
        return {"parsed_text_contents": parsed_text_contents}

    for text in texts_to_process:
        logger.info(f"Processing text content (length: {len(text)})...")
        # 对于文本，目前直接返回即可，无需额外解析
        parsed_text_contents.append(text)
    
    logger.info(f"Processed {len(parsed_text_contents)} text items.")

    return {"parsed_text_contents": parsed_text_contents}
