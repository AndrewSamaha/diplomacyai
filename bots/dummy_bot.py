import asyncio
import random
from diplomacy.client.connection import connect
from diplomacy.utils import constants


async def play_dummy_powers(hostname='localhost', port=8432):
    """Connect as the private bot, find all dummy powers needing orders, and submit random legal orders."""
    connection = await connect(hostname, port)
    channel = await connection.authenticate(
        constants.PRIVATE_BOT_USERNAME,
        constants.PRIVATE_BOT_PASSWORD
    )

    active_games = {}

    dummy_powers = await channel.get_dummy_waiting_powers(buffer_size=100)

    if not dummy_powers:
        print("No dummy powers waiting for orders.")
        return

    print(f"Found {sum(len(powers) for powers in dummy_powers.values())} dummy powers across {len(dummy_powers)} games")

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
            orders = [
                random.choice(possible_orders[loc])
                for loc in orderable_locations
                if possible_orders[loc]
            ]

            print(f"  {power_name} ({game.get_current_phase()}): {orders}")
            await game.set_orders(power_name=power_name, orders=orders, wait=False)

    print("\nDone.")


if __name__ == '__main__':
    asyncio.run(play_dummy_powers())
