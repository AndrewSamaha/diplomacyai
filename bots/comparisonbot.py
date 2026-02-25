import asyncio
import base64
import json
import os
from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client, propagate_attributes


def _configure_langfuse_otel():
    """Configure OpenTelemetry exporter for Langfuse if env vars are present."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
    if not (public_key and secret_key and host):
        return False

    host = host.rstrip("/")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", f"{host}/api/public/otel")
    if "OTEL_EXPORTER_OTLP_HEADERS" not in os.environ:
        auth = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("utf-8")
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth}"
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    os.environ.setdefault("OTEL_SERVICE_NAME", "diplomacyai-comparisonbot")
    return True


def _init_openinference():
    """Initialize OpenInference + OTEL exporter for CrewAI spans."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from openinference.instrumentation.crewai import CrewAIInstrumentor
    except Exception as exc:  # pragma: no cover - best-effort instrumentation
        print(f"OpenInference init skipped: {exc}")
        return

    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "ProxyTracerProvider":
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    CrewAIInstrumentor().instrument()

    # Best-effort LLM instrumentation for token usage.
    try:
        from openinference.instrumentation.litellm import LiteLLMInstrumentor
        LiteLLMInstrumentor().instrument()
    except Exception:
        pass
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()
    except Exception:
        pass


def _init_langfuse_tracing():
    """Enable CrewAI tracing to Langfuse when Langfuse env vars are configured."""
    if _configure_langfuse_otel():
        _init_openinference()

    langfuse = get_client()

    # Verify connection
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")
    return langfuse


def _extract_orders(result):
    """Extract orders list from a CrewAI result."""
    raw = getattr(result, "raw", result)
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
    if isinstance(data, dict) and "orders" in data:
        return data["orders"]
    if isinstance(data, list):
        return data
    return None


def _serialize_for_trace(value):
    """Return a JSON-serializable payload for trace output."""
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return str(value)


RANDOM_ORDERS_POWERS = {
    "AUSTRIA",
    "ENGLAND",
    "GERMANY",
    "RUSSIA",
    "TURKEY",
    "ITALY",
}

PICK_BEST_POWERS = {
    "FRANCE",
}

MAX_VALIDATION_RETRIES = 2


async def play_comparison_powers(hostname="localhost", port=8432, langfuse=None):
    """Compare random vs pick-best crews across fixed power assignments."""
    from diplomacy.client.connection import connect
    from diplomacy.utils import constants

    from bots.crews.pick_best_orders_crew import build_pick_best_orders_crew
    from bots.crews.random_orders_crew import build_random_orders_crew
    from bots.tools.get_position_metrics import GetPositionMetricsTool
    from bots.tools.move_validation import validate_orders

    connection = await connect(hostname, port)
    channel = await connection.authenticate(
        constants.PRIVATE_BOT_USERNAME,
        constants.PRIVATE_BOT_PASSWORD,
    )

    active_games = {}

    dummy_powers = await channel.get_dummy_waiting_powers(buffer_size=100)
    if not dummy_powers:
        print("No dummy powers waiting for orders.")
        return

    print(
        f"Found {sum(len(powers) for powers in dummy_powers.values())} dummy powers "
        f"across {len(dummy_powers)} games"
    )

    for game_id, power_names in dummy_powers.items():
        print(f"\nGame: {game_id}")
        for power_name in power_names:
            key = (game_id, power_name)
            game = active_games.get(key)
            if game is None:
                game = await channel.join_game(game_id=game_id, power_name=power_name)
                active_games[key] = game

            orderable_locations = game.get_orderable_locations(power_name)
            if not orderable_locations:
                print(f"  {power_name}: No orderable locations")
                continue

            if power_name in RANDOM_ORDERS_POWERS:
                crew_name = "random_orders_crew"
                tools = []
                crew = build_random_orders_crew(tools=tools)
            elif power_name in PICK_BEST_POWERS:
                crew_name = "pick_best_orders_crew"
                tools = []
                crew = build_pick_best_orders_crew(tools=tools)
            else:
                crew_name = "random_orders_crew"
                tools = []
                crew = build_random_orders_crew(tools=tools)

            possible_orders = game.get_all_possible_orders()
            possible_orders_list = [
                {"location": loc, "orders": possible_orders.get(loc, [])}
                for loc in orderable_locations
            ]
            game_snapshot = {
                "phase": game.get_current_phase(),
                "power_name": power_name,
                "orderable_locations": orderable_locations,
                "possible_orders": possible_orders_list,
                "units_by_power": {
                    power.name: list(power.units) for power in game.powers.values()
                },
                "centers_by_power": {
                    power.name: list(power.centers) for power in game.powers.values()
                },
            }

            metrics_tool = GetPositionMetricsTool(game=game)
            position_metrics = json.loads(
                metrics_tool._run(powers=[power_name])
            )

            base_inputs = {
                "power_name": power_name,
                "crew_name": crew_name,
                "game_snapshot": game_snapshot,
                "position_metrics": position_metrics,
                "validation_feedback": None,
                "previous_orders": None,
            }

            final_orders = None
            validation_feedback = None
            previous_orders = None
            for attempt in range(1, MAX_VALIDATION_RETRIES + 2):
                attempt_inputs = dict(base_inputs)
                attempt_inputs["validation_feedback"] = validation_feedback
                attempt_inputs["previous_orders"] = previous_orders
                attempt_inputs["validation_attempt"] = attempt

                if langfuse is not None:
                    with langfuse.start_as_current_observation(
                        as_type="span",
                        name=f"comparisonbot-{game_id}",
                        input=attempt_inputs
                    ) as observation:
                        with propagate_attributes(
                            metadata={
                                "model": os.getenv('OPENAI_MODEL_NAME'),
                                "crew": "pick_best_orders_crew" if power_name in PICK_BEST_POWERS else "random_orders_crew",
                                "power": power_name
                            }
                        ):
                            result = crew.kickoff(inputs=attempt_inputs)
                            orders = _extract_orders(result)
                            raw_output = getattr(result, "raw", result)
                            observation.update(output=_serialize_for_trace(raw_output))
                    langfuse.flush()
                else:
                    result = crew.kickoff(inputs=attempt_inputs)
                    orders = _extract_orders(result)

                if not orders:
                    validation_feedback = {
                        "valid": False,
                        "errors": [
                            {
                                "code": "invalid_agent_output",
                                "message": "Agent did not return an orders array.",
                            }
                        ],
                        "summary": "Output format invalid. Return JSON object with `orders` list.",
                    }
                    previous_orders = orders
                    if attempt <= MAX_VALIDATION_RETRIES:
                        continue
                    print(f"  {power_name}: Crew did not return orders")
                    break

                report = validate_orders(
                    game=game,
                    power_name=power_name,
                    orders=orders,
                    require_complete=False,
                )
                if report["valid"]:
                    final_orders = report["normalized_orders"]
                    break

                validation_feedback = report
                previous_orders = orders
                if attempt <= MAX_VALIDATION_RETRIES:
                    continue
                print(
                    f"  {power_name}: Unable to produce valid orders after "
                    f"{MAX_VALIDATION_RETRIES + 1} attempts."
                )
                print(f"  Validation summary: {report.get('summary')}")
                break

            if not final_orders:
                continue

            print(f"  {power_name} ({game.get_current_phase()} | {crew_name}): {final_orders}")
            await game.set_orders(power_name=power_name, orders=final_orders, wait=False)

    print("\nDone.")


if __name__ == "__main__":
    langfuse = _init_langfuse_tracing()
    asyncio.run(play_comparison_powers(langfuse=langfuse))
