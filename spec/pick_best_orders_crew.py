import argparse
import difflib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from bots.crews.pick_best_orders_crew import build_pick_best_orders_crew
from bots.tools.send_message import SendGlobalMessageTool

load_dotenv()


ELEMENT_ALIASES = {
    "crew": "crew",
    "all": "crew",
    "game_state_assessor_agent": "game_state_assessor_agent",
    "game_state_assessor_agen": "game_state_assessor_agent",
    "assessor": "game_state_assessor_agent",
    "assess_game_state_task": "game_state_assessor_agent",
    "order_agent": "order_agent",
    "pick_the_best_orders_task": "order_agent",
    "order_selector": "order_agent",
    "taunt_agent": "taunt_agent",
    "taunt_task": "taunt_agent",
}


def _prefix10(value: str | None) -> str:
    if not value:
        return "<missing>"
    return value[:10]


def _print_env_debug() -> None:
    # Debug info goes to stderr so stdout remains machine-readable JSON.
    print(
        "ENV DEBUG "
        f"OPEN_AI_BASE_URL={_prefix10(os.getenv('OPENAI_BASE_URL'))} "
        f"OPENAI_API_KEY={_prefix10(os.getenv('OPENAI_API_KEY'))} "
        f"OPENAI_MODEL_NAME={_prefix10(os.getenv('OPENAI_MODEL_NAME'))}",
        file=sys.stderr,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uv run -m crews.pick_best_orders_crew",
        description="Run pick_best_orders_crew or one of its elements with mock JSON input.",
    )
    parser.add_argument(
        "--element",
        required=True,
        help="Element to run (crew, game_state_assessor_agent, order_agent, taunt_agent).",
    )
    parser.add_argument(
        "--mock-input",
        required=True,
        help="JSON source: file path, '-', or inline JSON string.",
    )
    parser.add_argument(
        "--include-taunt",
        action="store_true",
        help="Build crew with taunt task enabled.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser


def _load_mock_input(source: str) -> dict[str, Any]:
    if source == "-":
        payload = json.load(sys.stdin)
    else:
        path = Path(source)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = json.loads(source)

    if not isinstance(payload, dict):
        raise ValueError("Mock input must be a JSON object.")
    return payload


def _resolve_element(name: str) -> str:
    key = name.strip().lower()
    if key in ELEMENT_ALIASES:
        return ELEMENT_ALIASES[key]

    all_names = sorted(set(ELEMENT_ALIASES.keys()) | set(ELEMENT_ALIASES.values()))
    suggestion = difflib.get_close_matches(key, all_names, n=1)
    if suggestion:
        raise ValueError(f"Unknown element '{name}'. Did you mean '{suggestion[0]}'?")
    raise ValueError(f"Unknown element '{name}'.")


def _serialize_output(output: Any) -> Any:
    if output is None:
        return None

    if hasattr(output, "json_dict") and getattr(output, "json_dict") is not None:
        return getattr(output, "json_dict")

    if hasattr(output, "pydantic") and getattr(output, "pydantic") is not None:
        model = getattr(output, "pydantic")
        if hasattr(model, "model_dump"):
            return model.model_dump()
        if hasattr(model, "dict"):
            return model.dict()

    raw = getattr(output, "raw", output)
    if isinstance(raw, (dict, list, int, float, bool)) or raw is None:
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return str(raw)


def _extract_token_metadata(output: Any) -> dict[str, Any] | None:
    usage = getattr(output, "token_usage", None)
    if usage is None:
        return None

    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if hasattr(usage, "dict"):
        return usage.dict()

    values: dict[str, Any] = {}
    for key in dir(usage):
        if key.startswith("_"):
            continue
        val = getattr(usage, key)
        if callable(val):
            continue
        if isinstance(val, (str, int, float, bool, type(None))):
            values[key] = val
    return values or None


def _json_char_len(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False))


def _task_output_payload(
    task_output: Any,
    element: str,
    inputs: dict[str, Any],
    latency_ms: float,
    token_metadata: dict[str, Any] | None = None,
    dependency_latency_ms: float = 0.0,
) -> dict[str, Any]:
    output_value = _serialize_output(task_output)
    return {
        "element": element,
        "output": output_value,
        "metadata": {
            "latency_ms": round(latency_ms, 3),
            "dependency_latency_ms": round(dependency_latency_ms, 3),
            "input_token_length": token_metadata.get("prompt_tokens") if token_metadata else None,
            "output_token_length": token_metadata.get("completion_tokens") if token_metadata else None,
            "total_token_length": token_metadata.get("total_tokens") if token_metadata else None,
            "input_char_length": _json_char_len(inputs),
            "output_char_length": _json_char_len(output_value),
        },
    }


def _run_element(
    element: str,
    inputs: dict[str, Any],
    include_taunt: bool,
) -> dict[str, Any]:
    message_queue: list[str] = []
    taunt_tools = None
    if include_taunt:
        taunt_tools = [
            SendGlobalMessageTool(
                power_name=str(inputs.get("power_name", "UNKNOWN")),
                message_queue=message_queue,
            )
        ]
    crew = build_pick_best_orders_crew(tools=[], taunt_tools=taunt_tools)

    assess_task = crew.tasks[0]
    taunt_task = crew.tasks[1] if include_taunt and len(crew.tasks) == 3 else None
    order_task = crew.tasks[-1]

    if element == "crew":
        started = time.perf_counter()
        result = crew.kickoff(inputs=inputs)
        latency_ms = (time.perf_counter() - started) * 1000
        output_value = _serialize_output(result)
        tokens = _extract_token_metadata(result)
        return {
            "element": element,
            "output": output_value,
            "metadata": {
                "latency_ms": round(latency_ms, 3),
                "input_token_length": tokens.get("prompt_tokens") if tokens else None,
                "output_token_length": tokens.get("completion_tokens") if tokens else None,
                "total_token_length": tokens.get("total_tokens") if tokens else None,
                "input_char_length": _json_char_len(inputs),
                "output_char_length": _json_char_len(output_value),
            },
        }

    if element == "game_state_assessor_agent":
        assess_task.interpolate_inputs_and_add_conversation_history(inputs)
        started = time.perf_counter()
        result = assess_task.execute_sync(agent=assess_task.agent, tools=assess_task.agent.tools)
        latency_ms = (time.perf_counter() - started) * 1000
        return _task_output_payload(result, element, inputs, latency_ms)

    if element == "taunt_agent":
        if taunt_task is None:
            raise ValueError(
                "taunt_agent requested but taunt task is not enabled. Pass --include-taunt."
            )
        assess_task.interpolate_inputs_and_add_conversation_history(inputs)
        assess_started = time.perf_counter()
        assess_result = assess_task.execute_sync(agent=assess_task.agent, tools=assess_task.agent.tools)
        assess_latency_ms = (time.perf_counter() - assess_started) * 1000

        taunt_task.interpolate_inputs_and_add_conversation_history(inputs)
        started = time.perf_counter()
        result = taunt_task.execute_sync(
            agent=taunt_task.agent,
            context=getattr(assess_result, "raw", None),
            tools=taunt_task.agent.tools,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        payload = _task_output_payload(
            result,
            element,
            inputs,
            latency_ms=latency_ms,
            dependency_latency_ms=assess_latency_ms,
        )
        payload["metadata"]["queued_messages"] = list(message_queue)
        return payload

    if element == "order_agent":
        assess_task.interpolate_inputs_and_add_conversation_history(inputs)
        assess_started = time.perf_counter()
        assess_result = assess_task.execute_sync(agent=assess_task.agent, tools=assess_task.agent.tools)
        assess_latency_ms = (time.perf_counter() - assess_started) * 1000

        order_task.interpolate_inputs_and_add_conversation_history(inputs)
        started = time.perf_counter()
        result = order_task.execute_sync(
            agent=order_task.agent,
            context=getattr(assess_result, "raw", None),
            tools=order_task.agent.tools,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return _task_output_payload(
            result,
            element,
            inputs,
            latency_ms=latency_ms,
            dependency_latency_ms=assess_latency_ms,
        )

    raise ValueError(f"Unhandled element '{element}'.")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    _print_env_debug()

    try:
        inputs = _load_mock_input(args.mock_input)
        element = _resolve_element(args.element)
        response = _run_element(element, inputs, include_taunt=args.include_taunt)
    except Exception as exc:
        error = {"error": str(exc)}
        print(json.dumps(error, indent=2))
        return 1

    if args.pretty:
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
