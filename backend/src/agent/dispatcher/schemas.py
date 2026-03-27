"""
定义调度员节点使用的 Pydantic 模型，用于 LLM 的结构化输出。
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ExtractedData(BaseModel):
    """定义从用户输入中提取的数据结构。"""
    type: Literal["url", "text", "file_path"] = Field(description="提取的数据类型，只能是 'url', 'text', 或 'file_path'")
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
