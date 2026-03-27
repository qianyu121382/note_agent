"""
Houses all prompts and chains for the notes generator graph.
"""
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agent.llm import llm

# --- Prompt Definitions (Inlined) ---

# 1. Initial Draft Generator
draft_system_prompt = """你是一位专业的笔记整理大师。你的任务是根据用户提供的原始、杂乱的文本内容，将其整理成一份结构清晰、重点突出、格式精美的 Markdown 笔记。
请遵循以下要求：
1.  **识别核心主题**：准确判断文本的核心议题或主题，并以此为基础构建笔记结构。
2.  **结构化整理**：灵活运用 Markdown 的各级标题、列表、引用、代码块和强调等元素来组织内容。
3.  **提炼关键信息**：精准地提取和总结文本中的关键概念、核心论点、重要定义和实例。过滤掉无关紧要的口语化表达和冗余信息。
4.  **保持中立客观**：严格忠实于原文，不添加主观臆断或原文未提及的信息。
5.  **格式优美**：确保最终输出的 Markdown 格式干净、排版合理、易于阅读。"""
draft_human_template = ("{existing_content_section}这是需要你整理和总结的原始文本，请开始处理：---{raw_content}")
draft_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(draft_system_prompt),
    HumanMessagePromptTemplate.from_template(draft_human_template)
])
draft_chain = draft_prompt | llm | StrOutputParser()

# 2. Reviewer Chains
review_human_template = "原始文本:---{raw_content}---待评审的笔记草稿:---{draft}---"

fact_checker_system_prompt = """你是一个只负责事实核查的AI。你的唯一任务是：将AI生成的笔记草稿与原始文本进行逐一比对。
你的职责：
1. 找出并列出所有事实性错误、信息曲解、或无中生有（幻觉）的内容。
2. 如果笔记草稿在事实上与原文完全一致，没有任何错误，请只输出关键词 `[FACTS_OK]`。
严格禁止对笔记的风格、语法、格式或简洁性发表任何评论。"""
fact_checker_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(fact_checker_system_prompt),
    HumanMessagePromptTemplate.from_template(review_human_template)
])
fact_checker_chain = fact_checker_prompt | llm | StrOutputParser()

structure_reviewer_system_prompt = """你是一个只负责评估笔记可用性的AI。你的唯一任务是：审查笔记草稿的结构和Markdown格式。
你的职责：
1. 检查笔记的结构是否逻辑清晰，Markdown格式是否被有效使用。
2. 提出具体的、可操作的修改建议以改善笔记的整体结构和排版。
3. 如果笔记的结构和格式都非常清晰、无需修改，请只输出关键词 `[STRUCTURE_OK]`。
严格禁止评论笔记的事实准确性或内容简洁性。"""
structure_reviewer_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(structure_reviewer_system_prompt),
    HumanMessagePromptTemplate.from_template(review_human_template)
])
structure_reviewer_chain = structure_reviewer_prompt | llm | StrOutputParser()
novelty_reviewer_system_prompt = """你是一个只负责评估笔记简洁性的AI。你的唯一任务是：审查笔记草稿是否足够简洁。

你的职责：
1.  **简洁度**: 找出所有冗余信息、重复的观点和可以被精简的啰嗦句子。
2.  如果笔记足够简洁，没有任何冗余，请只输出关键词 `[CONCISENESS_OK]`。

**严格禁止**：
*   评论笔记的事实准确性、Markdown格式或新颖性。"""
novelty_reviewer_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(novelty_reviewer_system_prompt),
    HumanMessagePromptTemplate.from_template(review_human_template)
])
novelty_reviewer_chain = novelty_reviewer_prompt | llm | StrOutputParser()
revise_system_prompt = """你是一位顶级的AI笔记优化师。你的任务是根据评审员提供的反馈来修订一份笔记草稿。你将获得三项输入：原始的源文本、初步的笔记草稿，以及一份来自评审员的批评列表。
你的目标是产出一个全新的、更优版本的笔记，该版本需智能地整合所有指定的反馈。
* 仔细分析反馈中的每一个要点。
* 回顾原始的源文本，以确保修订的准确性和上下文的正确性。
* 重写笔记草稿中的相关部分，以解决所有批评。
* 确保最终修订的笔记是一个单一、连贯的 Markdown 文档。"""
revise_human_template = ("原始文本:---{raw_content}---上一版笔记草稿:---{draft}---评审委员会的综合修改意见:---{feedback}---")
revise_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(revise_system_prompt),
    HumanMessagePromptTemplate.from_template(revise_human_template)
])
revise_chain = revise_prompt | llm | StrOutputParser()
