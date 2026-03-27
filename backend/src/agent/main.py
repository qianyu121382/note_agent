"""
鏅鸿兘绗旇 Agent 鐨勪富鍏ュ彛鐐广€?
璇ユ枃浠惰礋璐ｅ惎鍔ㄥ苟杩愯涓€涓氦浜掑紡鐨勫懡浠よ浼氳瘽銆?
"""
import asyncio
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage

# 灏?src 鐩綍娣诲姞鍒?sys.path 浠ョ‘淇濇ā鍧楀彲琚纭鍏?
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import graph as agent_graph
from agent.utils.logging import logger
from agent import ui

def generate_graph_image():
    """
    鐢熸垚骞朵繚瀛?Agent 宸ヤ綔娴佺殑 PNG 鍥惧儚锛岀敤浜庡彲瑙嗗寲璋冭瘯銆?
    """
    logger.info("Generating agent workflow graph...")
    try:
        # get_graph() 杩斿洖鏈紪璇戠殑鍥撅紝浠ヤ究璋冪敤 draw_mermaid_png
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
    杩愯涓€涓氦浜掑紡鐨?Agent 浼氳瘽锛屾寔缁鐞嗙敤鎴风殑寰幆杈撳叆銆?    """
    ui.display_welcome_message()
    conversation_history = []

    while True:
        try:
            # 1. 浠庣敤鎴峰鑾峰彇杈撳叆
            user_input = ui.prompt_for_input()

            # 2. 鍥炴樉鐢ㄦ埛杈撳叆骞舵鏌ユ槸鍚︿负绌?
            ui.display_user_prompt_echo(user_input)
            if not user_input.strip():
                continue

            # 3. 璋冪敤鏍稿績鐨?Agent 鍥炬潵澶勭悊杈撳叆
            initial_state = {
                "messages": conversation_history + [HumanMessage(content=user_input)],
            }
            final_state = await agent_graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": "cli_local_session"}},
            )
            conversation_history = final_state.get("messages", conversation_history)

            # 4. 浠庤繑鍥炵殑鐘舵€佷腑鑾峰彇鎰忓浘鍜屽洖澶?            intent = final_state.get("intent")
            response_to_user = ""
            for message in reversed(conversation_history):
                if hasattr(message, "type") and message.type == "ai":
                    content = getattr(message, "content", "")
                    if isinstance(content, str) and content.strip():
                        response_to_user = content
                        break

            # 5. 鏍规嵁鎰忓浘鍐冲畾涓嬩竴姝ユ搷浣?            if intent == 'exit':
                ui.display_exit_message()
                break  # 閫€鍑哄惊鐜?
            # 瀵逛簬浠讳綍鍏朵粬鎯呭喌锛坣ote_taking, waiting, 鎴栭敊璇級锛岄兘鏄剧ず agent 鐨勫洖澶?
            if response_to_user:
                ui.display_agent_feedback(response_to_user)
            else:
                # 浣滀负鍚庡锛屼互闃蹭竾涓€娌℃湁鍥炲
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
    绋嬪簭涓诲嚱鏁般€?
    """
    # 鍦?Windows 涓婁负 asyncio 璁剧疆姝ｇ‘鐨勪簨浠跺惊鐜瓥鐣?
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 鍚姩鏃剁敓鎴愭渶鏂扮殑鍥剧粨鏋勫浘
    generate_graph_image()

    # 鍚姩涓讳氦浜掑惊鐜?
    asyncio.run(run_interactive_loop())


if __name__ == "__main__":
    main()



