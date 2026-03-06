from crewai import Agent, Crew, Task



def build_tactical_crew(tools=None) -> Crew:
    """Build a two-step tactical crew.

    Step 1: derive the best query plan for tactical annotations and instructions
    for interpreting output.
    Step 2: execute the tactical annotation query and choose the best legal move.
    """
    tools = tools or []

    tactical_query_planner = Agent(
        role="Tactical Query Planner",
        goal=(
            "Design the most useful tactical annotation query for the current board state "
            "and define strict instructions for selecting one best move."
        ),
        backstory=(
            "You are a deterministic decision engineer for Diplomacy. "
            "You translate a board snapshot into a precise data query and a clear scoring policy "
            "for selecting one tactical move."
        ),
        tools=[],
        allow_delegation=False,
        verbose=False,
    )

    plan_tactical_query_task = Task(
        description=(
            "Use game_snapshot to produce a tactical query plan for {power_name}.\n\n"
            "You MUST output only JSON with this shape:\n"
            "{\n"
            "  \"power_name\": \"{power_name}\",\n"
            "  \"annotations\": [\"...\"],\n"
            "  \"include_non_moves\": true,\n"
            "  \"beam_width\": 32,\n"
            "  \"selection_instructions\": [\"...\"],\n"
            "  \"tie_break_rules\": [\"...\"]\n"
            "}\n\n"
            "Rules:\n"
            "- Build `annotations` as a subset supported by get_tactical_move_annotations.\n"
            "- Prefer annotations that balance reward and bounce risk.\n"
            "- `selection_instructions` must explain how to choose ONE best move from tool output.\n"
            "- `tie_break_rules` must be deterministic and final (no ambiguity).\n"
            "- Do not propose orders here. Only provide query + decision policy.\n"
            "- Context source: game_snapshot = {game_snapshot}\n"
        ),
        expected_output=(
            "A JSON object defining tactical annotation query parameters and deterministic "
            "instructions for selecting one best move."
        ),
        agent=tactical_query_planner,
    )

    tactical_move_selector = Agent(
        role="Tactical Move Selector",
        goal=(
            "Use deterministic tactical annotation data to choose one best legal move "
            "that improves the power's position."
        ),
        backstory=(
            "You are a practical Diplomacy tactician. You follow explicit decision policy, "
            "call tactical tools, and return one legal move without inventing unavailable orders."
        ),
        tools=tools,
        allow_delegation=False,
        verbose=False,
    )

    choose_best_tactical_move_task = Task(
        description=(
            "Read the previous task output JSON and follow it strictly.\n"
            "Then call `get_tactical_order_bundle` exactly once with:\n"
            "- power_name\n"
            "- annotations\n"
            "- include_non_moves\n\n"
            "- beam_width\n\n"
            "Use BOTH:\n"
            "1) the tool output (`recommended_orders` and bundle scoring), and\n"
            "2) `selection_instructions` and `tie_break_rules` from previous task\n"
            "to finalize one legal order per orderable location for {power_name}.\n\n"
            "Output must be only JSON with shape:\n"
            "{\n"
            "  \"power_name\": \"{power_name}\",\n"
            "  \"orders\": [\"<legal order>\", \"...\"],\n"
            "  \"selection_summary\": \"<2-3 sentences citing used metrics and bundle score>\"\n"
            "}\n\n"
            "Hard constraints:\n"
            "- Use `recommended_orders` as the baseline unless a deterministic tie-break rule requires adjustment.\n"
            "- Return one order per orderable location.\n"
            "- Do not output markdown, bullets, or extra keys."
        ),
        expected_output=(
            "A JSON object containing a legal full order set and a short metric-based summary."
        ),
        agent=tactical_move_selector,
        context=[plan_tactical_query_task],
    )

    return Crew(
        agents=[tactical_query_planner, tactical_move_selector],
        tasks=[plan_tactical_query_task, choose_best_tactical_move_task],
        verbose=False,
    )
