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
