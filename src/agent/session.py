"""
定义并管理 Agent 的两种运行模式：交互式会话和单次文件输入。
"""
import asyncio
import json
from pathlib import Path
from agent.graph import graph
from agent import ui
from agent.utils.logging import logger


async def run_from_file():
    """
    从 data/inputs.json 文件读取输入，执行一次图处理，然后退出。
    主要用于开发和调试。
    """
    ui.display_welcome_message()

    inputs_file_path = Path(__file__).parent.parent.parent / "data" / "inputs.json"
    if not inputs_file_path.exists():
        logger.error(f"Input file not found at: {inputs_file_path}")
        ui.display_error(f"输入文件未找到: {inputs_file_path}")
        return

    logger.info(f"Loading single input from {inputs_file_path}")
    try:
        with open(inputs_file_path, 'r', encoding='utf-8') as f:
            initial_inputs = json.load(f)
        
        user_input = initial_inputs.get("user_input", "")
        
        if not user_input:
            logger.warning("inputs.json found but 'user_input' field is empty. Exiting.")
            ui.display_error("inputs.json 文件中 'user_input' 字段为空。")
            return

        logger.info("Processing input from inputs.json...")
        ui.display_user_prompt_echo(user_input)

        # 调用图处理
        final_state = await graph.ainvoke(initial_inputs)

        # 根据意图显示结果
        intent = final_state.get("intent")
        if intent == 'note_taking':
            final_note = final_state.get("final_note", "")
            ui.display_note_processed(final_note)
        elif intent == 'waiting':
            response = final_state.get("response_to_user") or "输入不合规，无法处理。"
            ui.display_agent_feedback(response)
        
        logger.info("Single file run complete. Exiting.")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse inputs.json: {e}", exc_info=True)
        ui.display_error(f"解析 inputs.json 文件失败: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during file processing: {e}", exc_info=True)
        ui.display_error(f"处理 inputs.json 时发生意外错误: {e}")


async def run_interactive_session():
    """
    运行一个交互式的Agent会话，处理用户的循环输入。
    """
    ui.display_welcome_message()
    print("-" * 30) 

    while True:
        try:
            user_input = ui.prompt_for_input()
            ui.display_user_prompt_echo(user_input)

            if not user_input.strip():
                continue

            # 调用图处理
            final_state = await graph.ainvoke({"user_input": user_input})

            intent = final_state.get("intent")

            if intent == 'exit':
                ui.display_exit_message()
                break
            elif intent == 'note_taking':
                final_note = final_state.get("final_note", "")
                ui.display_note_processed(final_note)
            elif intent == 'waiting':
                response = final_state.get("response_to_user") or "请提供有效输入。"
                ui.display_agent_feedback(response)

            print("-" * 30)

        except (KeyboardInterrupt, EOFError):
            ui.display_interrupt_message()
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred in the session loop: {e}", exc_info=True)
            ui.display_error("程序运行出现意外错误，请检查日志。")
            logger.info("Session loop will continue.")
            print("-" * 30)
