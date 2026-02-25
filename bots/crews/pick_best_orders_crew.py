from crewai import Crew, Task

from bots.agents.game_state_assessor_agent import game_state_assessor_agent
from bots.agents.order_agent import build_order_agent


def build_pick_best_orders_crew(tools) -> Crew:
    gsa_agent = game_state_assessor_agent(tools=[])
    assess_game_state_task = Task(
        description=(
            "Assess the state of the game from the perspective of {power_name}.\n"
            "Use the provided context:\n"
            "- game_snapshot: {game_snapshot}\n"
            "- position_metrics: {position_metrics}\n"
            "If validation_feedback is present, include what must be corrected:\n"
            "- validation_feedback: {validation_feedback}\n"
            "- previous_orders: {previous_orders}\n"
            "Provide a concise strategic assessment with opportunities and threats."
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
            "Use the provided context:\n"
            "- game_snapshot: {game_snapshot}\n"
            "- position_metrics: {position_metrics}\n"
            "If validation_feedback is provided, fix only invalid orders while preserving valid intent.\n"
            "- validation_feedback: {validation_feedback}\n"
            "- previous_orders: {previous_orders}\n"
            "Only output orders that are legal in game_snapshot.possible_orders.\n"
            "Return only JSON "
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
