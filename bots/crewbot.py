import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from diplomacy.client.connection import connect
from diplomacy.utils import constants

from bots.crews.random_orders_crew import build_random_orders_crew
from bots.tools.get_game_snapshot import GameSnapshotTool
from bots.tools.get_random_order import GetRandomOrderTool
from langfuse import get_client

def _init_langfuse_tracing():
    """Enable CrewAI tracing to Langfuse when Langfuse env vars are configured."""
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


async def play_crew_powers(hostname="localhost", port=8432, langfuse=None):
    """Connect as the private bot, ask a CrewAI agent for orders, and submit them."""
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

            tools = [
                GameSnapshotTool(game=game, power_name=power_name),
                GetRandomOrderTool(),
            ]
            crew = build_random_orders_crew(tools=tools)
            inputs = {
                "power_name": power_name,
            }
            if langfuse is not None:
                with langfuse.start_as_current_observation(
                    as_type="span", name="crewai-index-trace", input=inputs
                ) as observation:
                    result = crew.kickoff(inputs=inputs)
                    orders = _extract_orders(result)
                    raw_output = getattr(result, "raw", result)
                    observation.update(output=_serialize_for_trace(raw_output))
                    if not orders:
                        print(f"  {power_name}: Crew did not return orders")
                        continue
                langfuse.flush()
            else:
                result = crew.kickoff(inputs=inputs)
                orders = _extract_orders(result)
                if not orders:
                    print(f"  {power_name}: Crew did not return orders")
                    continue
            print(f"  {power_name} ({game.get_current_phase()}): {orders}")
            await game.set_orders(power_name=power_name, orders=orders, wait=False)

    print("\nDone.")


if __name__ == "__main__":
    langfuse = _init_langfuse_tracing()
    asyncio.run(play_crew_powers(langfuse=langfuse))
