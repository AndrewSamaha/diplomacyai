from crewai import Crew, Task

from bots.agents.order_agent import build_order_agent


def build_random_orders_crew(tools) -> Crew:
    agent = build_order_agent(tools=tools)
    task = Task(
        description=(
            "Select legal orders for power {power_name}.\n"
            "First call `get_game_snapshot` (no arguments) to fetch state.\n"
            "Then call `get_random_order` with:\n"
            "- orderable_locations: from snapshot.orderable_locations\n"
            "- possible_orders: from snapshot.possible_orders\n"
            "Return only JSON with the shape: {\"orders\": [\"<order>\", ...]}."
        ),
        expected_output="A JSON object with key `orders` containing a list of legal orders.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], verbose=False)
