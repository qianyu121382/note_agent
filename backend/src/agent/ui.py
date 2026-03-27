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
