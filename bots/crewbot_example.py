import asyncio
from dotenv import load_dotenv

load_dotenv()

from bots.instrumentation import init_langfuse_tracing
from bots.utils.crew_output import extract_orders, serialize_for_trace


async def play_crew_powers(hostname="localhost", port=8432, langfuse=None):
    """Connect as the private bot, ask a CrewAI agent for orders, and submit them."""
    from diplomacy.client.connection import connect
    from diplomacy.utils import constants

    from bots.crews.random_orders_crew import build_random_orders_crew
    from bots.tools.get_game_snapshot import GameSnapshotTool
    from bots.tools.get_random_order import GetRandomOrderTool

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
                    orders = extract_orders(result)
                    raw_output = getattr(result, "raw", result)
                    observation.update(output=serialize_for_trace(raw_output))
                    if not orders:
                        print(f"  {power_name}: Crew did not return orders")
                        continue
                langfuse.flush()
            else:
                result = crew.kickoff(inputs=inputs)
                orders = extract_orders(result)
                if not orders:
                    print(f"  {power_name}: Crew did not return orders")
                    continue
            print(f"  {power_name} ({game.get_current_phase()}): {orders}")
            await game.set_orders(power_name=power_name, orders=orders, wait=False)

    print("\nDone.")


if __name__ == "__main__":
    langfuse = init_langfuse_tracing(service_name="diplomacyai-crewbot")
    asyncio.run(play_crew_powers(langfuse=langfuse))
