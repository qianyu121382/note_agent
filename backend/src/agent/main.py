"""
智能笔记 Agent 的主入口点。
该文件负责启动并运行一个交互式的命令行会话。
"""
import asyncio
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

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
    运行一个交互式的 Agent 会话，持续处理用户输入。
    """
    ui.display_welcome_message()

    while True:
        try:
            user_input = ui.prompt_for_input()
            ui.display_user_prompt_echo(user_input)
            if not user_input.strip():
                continue

            final_state = await agent_graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config={"configurable": {"thread_id": "cli_local_session"}},
            )

            intent = final_state.get("intent")
            messages = final_state.get("messages", [])
            response_to_user = ""
            for message in reversed(messages):
                if hasattr(message, "type") and message.type == "ai":
                    content = getattr(message, "content", "")
                    if isinstance(content, str) and content.strip():
                        response_to_user = content
                        break

            if intent == "exit":
                ui.display_exit_message()
                break

            if response_to_user:
                ui.display_agent_feedback(response_to_user)
            else:
                ui.display_error("Agent failed to generate a valid response.")

            print("-" * 30)

        except (KeyboardInterrupt, EOFError):
            ui.display_interrupt_message()
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred in the session loop: {e}", exc_info=True)
            ui.display_error("An unexpected error occurred. Please check the logs. The session will continue.")
            print("-" * 30)



def main():
    """
    程序主函数。
    """
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    generate_graph_image()
    asyncio.run(run_interactive_loop())


if __name__ == "__main__":
    main()
