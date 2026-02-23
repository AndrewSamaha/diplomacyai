from crewai import Crew, Task

from bots.agents.order_agent import build_order_agent


def build_random_orders_crew() -> Crew:
    agent = build_order_agent()
    task = Task(
        description=(
            "Select legal orders for power {power_name} in phase {phase}.\n"
            "Use ONLY the tool `get_random_order` with:\n"
            "- orderable_locations: {orderable_locations}\n"
            "- possible_orders: {possible_orders}\n"
            "Return only JSON with the shape: {\"orders\": [\"<order>\", ...]}."
        ),
        expected_output="A JSON object with key `orders` containing a list of legal orders.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], verbose=False)
