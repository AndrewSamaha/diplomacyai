from crewai import Crew, Task

from bots.agents.game_state_assessor_agent import game_state_assessor_agent
from bots.agents.order_agent import build_order_agent


def build_pick_best_orders_crew(tools) -> Crew:
    gsa_agent = game_state_assessor_agent(tools=tools)
    assess_game_state_task = Task(
        description=(
            "Assess the state of the game from the perspective of {power_name}.\n"
            "First call `get_game_snapshot` (no arguments) to fetch state.\n"
            "Then call `get_position_metrics` to evaluate position strength\n"
            "(all metrics or any subset you need).\n"
            "Then call `get_random_order_candidates` with:\n"
            "- orderable_locations: from snapshot.orderable_locations\n"
            "- possible_orders: from snapshot.possible_orders\n"
            "- n_candidates: 10\n"
            "Choose the best candidate based on position and return only JSON\n"
            "with the shape: {\"orders\": [\"<order>\", ...]}."
        ),
        expected_output=(
            "A plain english summary of the game state from the perspective of "
            "{power_name} including opportunities for expansion and threats."
        ),
        agent=gsa_agent,
    )

    bo_agent = build_order_agent(tools=tools)
    pick_the_best_orders_task = Task(
        description=(
            "Select the best legal orders balances guarding against threats\n"
            "while aggressively pursuing opportunities for expansion for power\n"
            " {power_name}.\n"
            "Then call `get_random_order_candidates` with:\n"
            "- orderable_locations: from snapshot.orderable_locations\n"
            "- possible_orders: from snapshot.possible_orders\n"
            "- n_candidates: 10\n"
            "Choose the best candidate based on position and return only JSON "
            "with the shape: {\"orders\": [\"<order>\", ...]}."
        ),
        expected_output="A JSON object with key `orders` containing a list of legal orders.",
        agent=bo_agent,
        context=[assess_game_state_task]
    )
    return Crew(agents=[gsa_agent, bo_agent], tasks=[
        assess_game_state_task,
        pick_the_best_orders_task
    ], verbose=False)
