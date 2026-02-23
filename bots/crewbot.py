import asyncio
import json
import os
from base64 import b64encode
from dotenv import load_dotenv

load_dotenv()

from diplomacy.client.connection import connect
from diplomacy.utils import constants

from bots.crews.random_orders_crew import build_random_orders_crew


def _init_langfuse_tracing():
    """Enable CrewAI tracing to Langfuse when Langfuse env vars are configured."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
    missing = []
    if not public_key:
        missing.append("LANGFUSE_PUBLIC_KEY")
    if not secret_key:
        missing.append("LANGFUSE_SECRET_KEY")
    if not host:
        missing.append("LANGFUSE_HOST or LANGFUSE_BASE_URL")
    if missing:
        print(
            "Langfuse tracing disabled: missing env var(s): "
            + ", ".join(missing)
        )
        return

    try:
        import openlit
    except ImportError:
        print(
            "Langfuse env vars detected, but `openlit` is not installed. "
            "Run `uv sync` to install tracing dependencies."
        )
        return

    host = host.rstrip("/")
    if host.endswith("/api/public/otel"):
        otlp_endpoint = host
    else:
        otlp_endpoint = f"{host}/api/public/otel"

    # Diagnostic mode: export to Langfuse OTLP and local console spans.
    os.environ.setdefault("OTEL_TRACES_EXPORTER", "otlp,console")
    print(f"Langfuse tracing endpoint: {otlp_endpoint}")
    print(f"OTEL_TRACES_EXPORTER={os.environ.get('OTEL_TRACES_EXPORTER')}")

    basic_auth = b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("utf-8")
    openlit.init(
        otlp_endpoint=otlp_endpoint,
        otlp_headers={"Authorization": f"Basic {basic_auth}"},
    )


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


async def play_crew_powers(hostname="localhost", port=8432):
    """Connect as the private bot, ask a CrewAI agent for orders, and submit them."""
    connection = await connect(hostname, port)
    channel = await connection.authenticate(
        constants.PRIVATE_BOT_USERNAME,
        constants.PRIVATE_BOT_PASSWORD,
    )

    crew = build_random_orders_crew()
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

            possible_orders = game.get_all_possible_orders()
            inputs = {
                "power_name": power_name,
                "phase": game.get_current_phase(),
                "orderable_locations": orderable_locations,
                "possible_orders": [
                    {"location": loc, "orders": possible_orders.get(loc, [])}
                    for loc in orderable_locations
                ],
            }

            result = crew.kickoff(inputs=inputs)
            orders = _extract_orders(result)
            if not orders:
                print(f"  {power_name}: Crew did not return orders")
                continue

            print(f"  {power_name} ({game.get_current_phase()}): {orders}")
            await game.set_orders(power_name=power_name, orders=orders, wait=False)

    print("\nDone.")


if __name__ == "__main__":
    _init_langfuse_tracing()
    asyncio.run(play_crew_powers())
