import asyncio
import json
import os
import random
from dotenv import load_dotenv

load_dotenv()

from langfuse import propagate_attributes
from bots.crews.adapters import (
    CREW_PICK_BEST,
    CREW_TACTICAL,
    DEFAULT_CREW,
    NOCREW_RANDOM,
    build_crew,
    is_no_crew_strategy,
)
from bots.instrumentation import init_langfuse_tracing
from bots.utils.crew_output import extract_orders, serialize_for_trace

POWER_TO_CREW = {
    "AUSTRIA": CREW_TACTICAL,
    "ENGLAND": NOCREW_RANDOM,
    "GERMANY": NOCREW_RANDOM,
    "RUSSIA": NOCREW_RANDOM,
    "TURKEY": NOCREW_RANDOM,
    "ITALY": NOCREW_RANDOM,
    "FRANCE": CREW_PICK_BEST,
}

MAX_VALIDATION_RETRIES = 2


async def play_comparison_powers(hostname="localhost", port=8432, langfuse=None):
    """Compare random vs pick-best crews across fixed power assignments."""
    from diplomacy.client.connection import connect
    from diplomacy.utils import constants

    from bots.tools.get_position_metrics import GetPositionMetricsTool
    from bots.tools.move_validation import validate_orders
    from bots.utils.game_state import get_human_controlled_powers, get_recent_messages, format_messages_for_context
    from bots.utils.random_orders import get_random_orders

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

            human_powers = get_human_controlled_powers(game)
            taunt_target = random.choice(human_powers) if human_powers and not game.no_press else None

            message_queue = []
            crew_name = POWER_TO_CREW.get(power_name, DEFAULT_CREW)

            if is_no_crew_strategy(crew_name):
                orders = get_random_orders(game, power_name)
                print(f"  {power_name} ({game.get_current_phase()} | {crew_name}): {orders}")
                await game.set_orders(power_name=power_name, orders=orders, wait=False)
                continue

            crew = build_crew(
                crew_name,
                game=game,
                power_name=power_name,
                message_queue=message_queue,
                taunt_target=taunt_target,
            )

            possible_orders = game.get_all_possible_orders()
            possible_orders_list = [
                {"location": loc, "orders": possible_orders.get(loc, [])}
                for loc in orderable_locations
            ]
            game_snapshot = {
                "phase": game.get_current_phase(),
                "power_name": power_name,
                "orderable_locations": orderable_locations,
                "units_by_power": {
                    power.name: list(power.units) for power in game.powers.values()
                },
                "centers_by_power": {
                    power.name: list(power.centers) for power in game.powers.values()
                },
                "human_controlled_powers": human_powers,
            }

            metrics_tool = GetPositionMetricsTool(game=game)
            position_metrics = json.loads(
                metrics_tool._run(powers=[power_name])
            )

            my_power = game.get_power(power_name)
            target_power = game.get_power(taunt_target) if taunt_target else None

            recent_messages = get_recent_messages(game, limit=20)
            messages_context = format_messages_for_context(recent_messages)

            base_inputs = {
                "power_name": power_name,
                "crew_name": crew_name,
                "game_snapshot": game_snapshot,
                "position_metrics": position_metrics,
                "possible_orders": possible_orders_list,
                "validation_feedback": None,
                "previous_orders": None,
                "phase": game.get_current_phase(),
                "human_controlled_powers": ", ".join(human_powers) if human_powers else "none",
                "taunt_target": taunt_target or "none",
                "target_units": ", ".join(target_power.units) if target_power else "none",
                "target_centers": ", ".join(target_power.centers) if target_power else "none",
                "my_units": ", ".join(my_power.units) if my_power.units else "none",
                "my_centers": ", ".join(my_power.centers) if my_power.centers else "none",
                "recent_messages": messages_context,
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
                                "crew": crew_name,
                                "power": power_name,
                                "phase": game.get_current_phase(),
                            }
                        ):
                            result = crew.kickoff(inputs=attempt_inputs)
                            orders = extract_orders(result)
                            raw_output = getattr(result, "raw", result)
                            observation.update(output=serialize_for_trace(raw_output))
                    langfuse.flush()
                else:
                    result = crew.kickoff(inputs=attempt_inputs)
                    orders = extract_orders(result)

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

            for msg_text in message_queue:
                try:
                    global_message = game.new_global_message(msg_text)
                    await game.send_game_message(message=global_message)
                    print(f"  {power_name}: Sent taunt: {msg_text}")
                except Exception as e:
                    print(f"  {power_name}: Failed to send message: {e}")

    print("\nDone.")


if __name__ == "__main__":
    langfuse = init_langfuse_tracing(service_name="diplomacyai-comparisonbot")
    asyncio.run(play_comparison_powers(langfuse=langfuse))
