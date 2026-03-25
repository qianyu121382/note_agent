"""
智能笔记 Agent 的主入口点。
该文件负责启动并运行一个交互式的命令行会话。
"""
import asyncio
import sys
from pathlib import Path

# 将 src 目录添加到 sys.path 以确保模块可被正确导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import graph as agent_graph
from agent.utils.logging import logger
from agent import ui

def generate_graph_image():
    """
    生成并保存 Agent 工作流的 PNG 图像，用于可视化调试。
    """
    logger.info("Generating agent workflow graph...")
    try:
        # get_graph() 返回未编译的图，以便调用 draw_mermaid_png
        # We pass xray=True to see the inner ReAct agent graph
        png_bytes = agent_graph.get_graph(xray=True).draw_mermaid_png()
        output_path = Path(__file__).parent.parent.parent / "agent_graph.png"
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        logger.info(f"Graph image saved to: {output_path}")
    except Exception as e:
        logger.error(f"An error occurred while generating the graph: {e}", exc_info=True)
        logger.warning(
            "Graph visualization may fail if 'pyppeteer' is not installed "
            "or if there are internet connection issues for downloading Chromium."
        )

async def run_interactive_loop():
    """
    运行一个交互式的 Agent 会话，持续处理用户的循环输入。
    """
    ui.display_welcome_message()

    while True:
        try:
            # 1. 从用户处获取输入
            user_input = ui.prompt_for_input()

            # 2. 回显用户输入并检查是否为空
            ui.display_user_prompt_echo(user_input)
            if not user_input.strip():
                continue

            # 3. 调用核心的 Agent 图来处理输入
            # The initial state must now include an empty 'messages' list
            initial_state = {"user_input": user_input, "messages": []}
            final_state = await agent_graph.ainvoke(initial_state)

            # 4. 从返回的状态中获取意图和回复
            intent = final_state.get("intent")
            response_to_user = final_state.get("response_to_user")

            # 5. 根据意图决定下一步操作
            if intent == 'exit':
                ui.display_exit_message()
                break  # 退出循环

            # 对于任何其他情况（note_taking, waiting, 或错误），都显示 agent 的回复
            if response_to_user:
                ui.display_agent_feedback(response_to_user)
            else:
                # 作为后备，以防万一没有回复
                ui.display_error("Agent 未能生成有效回复。")

            print("-" * 30)

        except (KeyboardInterrupt, EOFError):
            ui.display_interrupt_message()
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred in the session loop: {e}", exc_info=True)
            ui.display_error("程序运行出现意外错误，请检查日志。会话将继续。")
            print("-" * 30)


def main():
    """
    程序主函数。
    """
    # 在 Windows 上为 asyncio 设置正确的事件循环策略
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 启动时生成最新的图结构图
    generate_graph_image()

    # 启动主交互循环
    asyncio.run(run_interactive_loop())


if __name__ == "__main__":
    main()
