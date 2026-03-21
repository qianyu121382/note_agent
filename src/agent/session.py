"""
定义并管理 Agent 的交互式会话循环。
"""
import asyncio
import json
from pathlib import Path
from agent.graph import graph
from agent import ui
from agent.utils.logging import logger


async def run_interactive_session():
    """
    运行一个交互式的Agent会话，处理用户的循环输入。
    程序启动时会尝试读取 inputs.json 作为初始输入，处理完毕后进入交互模式。
    """
    ui.display_welcome_message()

    # --- NEW LOGIC: Process initial input from inputs.json ---
    initial_input_processed = False
    inputs_file_path = Path(__file__).parent.parent.parent / "inputs.json"
    if inputs_file_path.exists():
        logger.info(f"Attempting to load initial input from {inputs_file_path}")
        try:
            with open(inputs_file_path, 'r', encoding='utf-8') as f:
                initial_inputs = json.load(f)
            
            initial_user_input = initial_inputs.get("user_input", "")
            
            if initial_user_input:
                logger.info("Processing initial input from inputs.json...")
                ui.display_user_prompt_echo(initial_user_input) # Echo the input from file

                # Invoke the graph with the initial inputs (which can include user_input and user_preferences)
                final_state = await graph.ainvoke(initial_inputs)

                intent = final_state.get("intent")
                if intent == 'note_taking':
                    final_note = final_state.get("final_note", "")
                    ui.display_note_processed(final_note)
                elif intent == 'waiting':
                    response = final_state.get("response_to_user") or "输入不合规，无法处理。"
                    ui.display_agent_feedback(response)
                
                print("-" * 30) # Separator after initial run
                initial_input_processed = True
            else:
                logger.warning("inputs.json found but 'user_input' field is empty.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse inputs.json: {e}", exc_info=True)
            ui.display_error(f"加载或解析 inputs.json 文件失败: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during initial inputs.json processing: {e}", exc_info=True)
            ui.display_error(f"处理 initial inputs.json 时发生意外错误: {e}")

    if not initial_input_processed:
        logger.info("No valid initial input from inputs.json, starting interactive loop directly.")
        # If no initial input was processed, print separator to make it clear we're entering interactive mode.
        print("-" * 30) 
    # --- END NEW LOGIC ---

    # Existing interactive loop
    while True:
        try:
            user_input = ui.prompt_for_input()
            ui.display_user_prompt_echo(user_input) # Echo the interactive input

            if not user_input.strip():
                continue

            # Invoke the graph with the interactive user input
            # (user_preferences are not gathered interactively in this simplified version)
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
