import asyncio
import os
import sys
from pathlib import Path

# 将 src 目录添加到 sys.path，以便将 'agent' 视为可导入的包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import graph
from agent.session import run_interactive_session
from agent.utils.logging import logger


def generate_graph_image():
    """
    生成并保存 Agent 工作流的 PNG 图像。
    """
    logger.info("Generating agent workflow graph...")
    try:
        # 获取图的PNG图像数据

        png_bytes = graph.get_graph(xray=True).draw_mermaid_png()

        # 定义输出路径到项目根目录
        output_path = Path(__file__).parent.parent.parent / "agent_graph.png"
        with open(output_path, "wb") as f:
            f.write(png_bytes)

        logger.info(f"Graph image saved to: {output_path}")

    except Exception as e:
        logger.error(f"An error occurred while generating the graph: {e}")
        logger.warning(
            "Please ensure 'pyppeteer' is installed (`pip install pyppeteer`) and internet connection is working. "
            "It may need to download a browser instance on first run."
        )


def main():
    """
    Agent 的主入口点。
    设置 asyncio 策略，生成工作流图，然后启动交互式会话。
    """
    # 在 Windows 平台上，为 pyppeteer 设置必需的 asyncio 事件循环策略
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 每次启动时都重新生成最新的工作流图，方便调试
    generate_graph_image()

    # 启动交互式会话循环
    asyncio.run(run_interactive_session())


if __name__ == "__main__":
    main()
