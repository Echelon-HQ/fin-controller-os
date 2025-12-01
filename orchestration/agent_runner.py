from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
import openai

from orchestration.agent_prompts import BASE_SYSTEM_PROMPT
from orchestration.controller_adapter import (
    tool_run_daily_digest_impl,
    tool_run_weekly_summary_impl,
    tool_simulate_scenario_impl,
    tool_explain_log_entry_impl,
)
from orchestration.tool_schemas import (
    run_daily_digest_input_schema,
    run_weekly_summary_input_schema,
    simulate_scenario_input_schema,
    explain_log_entry_input_schema,
)


def _get_client() -> openai.OpenAI:
    """
    Initialize and return an OpenAI client.
    This function expects OPENAI_API_KEY to be set in the environment.
    """
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Please configure it in your environment."
        )

    client = openai.OpenAI(api_key=api_key)
    return client


def _build_tools(config_dir: Path, data_dir: Path, log_dir: Path) -> List[Dict[str, Any]]:
    """
    Build the tools metadata array for the OpenAI client. Each tool is defined
    with a name, description, and JSON schema of its input. A 'handler' key
    is also attached for local routing of tool calls.
    """

    def wrap_run_daily_digest(arguments: Dict[str, Any]) -> Dict[str, Any]:
        return tool_run_daily_digest_impl(
            config_dir=config_dir,
            data_dir=data_dir,
            log_dir=log_dir,
            as_of_date_str=arguments["as_of_date"],
            mode=arguments.get("mode", "summary"),
        )

    def wrap_run_weekly_summary(arguments: Dict[str, Any]) -> Dict[str, Any]:
        return tool_run_weekly_summary_impl(
            log_dir=log_dir,
            week_ending_date_str=arguments["week_ending_date"],
        )

    def wrap_simulate_scenario(arguments: Dict[str, Any]) -> Dict[str, Any]:
        return tool_simulate_scenario_impl(
            config_dir=config_dir,
            data_dir=data_dir,
            as_of_date_str=arguments["as_of_date"],
            one_off_spend=arguments.get("one_off_spend"),
            envelope_adjustments=arguments.get("envelope_adjustments"),
        )

    def wrap_explain_log_entry(arguments: Dict[str, Any]) -> Dict[str, Any]:
        return tool_explain_log_entry_impl(
            log_dir=log_dir,
            date_str=arguments["date"],
        )

    tools: List[Dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "run_daily_digest",
                "description": (
                    "Run the financial controller for a given date and return a structured digest."
                ),
                "parameters": run_daily_digest_input_schema,
            },
            "handler": wrap_run_daily_digest,
        },
        {
            "type": "function",
            "function": {
                "name": "run_weekly_summary",
                "description": "Summarize the last seven days of controller activity.",
                "parameters": run_weekly_summary_input_schema,
            },
            "handler": wrap_run_weekly_summary,
        },
        {
            "type": "function",
            "function": {
                "name": "simulate_scenario",
                "description": (
                    "Simulate a what-if scenario by adjusting envelopes or adding a one-off spend."
                ),
                "parameters": simulate_scenario_input_schema,
            },
            "handler": wrap_simulate_scenario,
        },
        {
            "type": "function",
            "function": {
                "name": "explain_log_entry",
                "description": (
                    "Explain what happened on a specific date according to the controller log."
                ),
                "parameters": explain_log_entry_input_schema,
            },
            "handler": wrap_explain_log_entry,
        },
    ]

    return tools


def _find_tool_handler(tools: List[Dict[str, Any]], tool_name: str):
    """
    Find the handler function for a given tool name in the tools list.
    """
    for tool in tools:
        if tool["function"]["name"] == tool_name:
            return tool["handler"]
    raise ValueError(f"No handler found for tool '{tool_name}'.")


def run_financial_controller_chat(
    config_dir: Path,
    data_dir: Path,
    log_dir: Path,
) -> None:
    """
    Run an interactive chat loop with the Financial Controller Agent.

    This function:
      1. Initializes the OpenAI client.
      2. Registers tools that wrap the controller adapter functions.
      3. Starts a command-line loop where the user can ask questions.
      4. Handles tool calls from the model and routes them to the appropriate
         Python handlers.
      5. Prints the model's responses and continues until the user exits.
    """
    client = _get_client()
    tools = _build_tools(config_dir, data_dir, log_dir)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT},
    ]

    print("Financial Controller Agent chat started. Type 'exit' to quit.")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting Financial Controller Agent chat.")
            break

        messages.append({"role": "user", "content": user_input})

        raw_tools_metadata = [
            {"type": t["type"], "function": t["function"]} for t in tools
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=raw_tools_metadata,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": getattr(assistant_message, "tool_calls", None),
            }
        )

        tool_calls = getattr(assistant_message, "tool_calls", None)

        if tool_calls:
            # Handle each tool call
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments or "{}")

                handler = _find_tool_handler(tools, tool_name)
                tool_result = handler(arguments)

                tool_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result),
                }
                messages.append(tool_result_message)

            # Follow-up call so the model can see tool results and produce a final answer.
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
            )
            assistant_message = response.choices[0].message
            messages.append(
                {"role": "assistant", "content": assistant_message.content or ""}
            )
            print(f"Agent: {assistant_message.content}")
        else:
            print(f"Agent: {assistant_message.content or ''}")