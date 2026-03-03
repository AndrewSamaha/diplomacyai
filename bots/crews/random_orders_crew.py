from crewai import Crew, Task

from bots.agents.order_agent import build_order_agent


def build_random_orders_crew(tools) -> Crew:
    agent = build_order_agent(tools=tools)
    task = Task(
        description=(
            "Draft orders for power {power_name}.\n"
            "Use the provided context:\n"
            "- game_snapshot: {game_snapshot}\n"
            "- position_metrics: {position_metrics}\n"
            "If validation_feedback is provided, fix only the invalid parts:\n"
            "- validation_feedback: {validation_feedback}\n"
            "- previous_orders: {previous_orders}\n"
            "Only output orders that are legal in game_snapshot.possible_orders.\n"
            "Return only JSON with the shape: {\"orders\": [\"<order>\", ...]}."
        ),
        expected_output="A JSON object with key `orders` containing a list of legal orders.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], verbose=False)
