from crewai import Crew, Task

from bots.agents.game_state_assessor_agent import game_state_assessor_agent
from bots.agents.order_agent import build_order_agent
from bots.agents.taunt_agent import build_taunt_agent


def build_pick_best_orders_crew(tools, taunt_tools=None) -> Crew:
    gsa_agent = game_state_assessor_agent(tools=[])
    assess_game_state_task = Task(
        description=(
            "Assess the state of the game from the perspective of {power_name}.\n"
            "Use the provided context:\n"
            "- game_snapshot: {game_snapshot}\n"
            "- position_metrics: {position_metrics}\n"
            "If validation_feedback is present, include what must be corrected:\n"
            "- validation_feedback: {validation_feedback}\n"
            "- previous_orders: {previous_orders}\n\n"
            "Provide:\n"
            "1. A strategic assessment with opportunities and threats\n"
            "2. The orderable locations and their legal orders from game_snapshot"
        ),
        expected_output=(
            "A summary containing: (1) strategic assessment of opportunities and threats "
            "for {power_name}, and (2) the orderable locations with their possible orders."
        ),
        agent=gsa_agent,
    )

    bo_agent = build_order_agent(tools=tools)
    pick_the_best_orders_task = Task(
        description=(
            "Select the best legal orders for {power_name} based on the strategic "
            "assessment provided in your context.\n\n"
            "Balance guarding against threats while pursuing expansion opportunities.\n"
            "If validation_feedback is provided, fix only the invalid orders:\n"
            "- validation_feedback: {validation_feedback}\n"
            "- previous_orders: {previous_orders}\n\n"
            "Return only JSON with the shape: {{\"orders\": [\"<order>\", ...]}}."
        ),
        expected_output="A JSON object with key `orders` containing a list of legal orders.",
        agent=bo_agent,
        context=[assess_game_state_task]
    )


    agents = [gsa_agent, bo_agent]
    tasks = [assess_game_state_task]

    if taunt_tools:
        taunt_agent = build_taunt_agent(tools=taunt_tools)
        taunt_task = Task(
            description=(
                "You are playing as {power_name}. "
                "Send a taunt to {taunt_target} using the send_global_message tool.\n\n"
                "Game context:\n"
                "- Current phase: {phase}\n"
                "- Human players: {human_controlled_powers}\n"
                "- {taunt_target}'s units: {target_units}\n"
                "- {taunt_target}'s centers: {target_centers}\n"
                "- Your units: {my_units}\n"
                "- Your centers: {my_centers}\n\n"
                "Recent messages in the game:\n{recent_messages}\n\n"
                "Craft a short taunt (under 50 tokens) that:\n"
                "1. Addresses {taunt_target} by name\n"
                "2. References something specific about the game state or recent messages\n"
                "3. Is witty but not crude\n\n"
                "Use the send_global_message tool to send your taunt."
            ),
            expected_output="Confirmation that the taunt message was sent.",
            agent=taunt_agent,
            context=[assess_game_state_task]
        )
        agents.append(taunt_agent)
        tasks.append(taunt_task)

    tasks.append(pick_the_best_orders_task)

    return Crew(agents=agents, tasks=tasks, verbose=False)
