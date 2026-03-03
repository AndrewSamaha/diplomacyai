from crewai import Agent


def build_order_agent(tools=None) -> Agent:
    tools = tools or []
    return Agent(
        role="Order Selector",
        goal="Return a set of legal orders for the current power.",
        backstory=(
            "You are a Diplomacy assistant that strictly selects legal orders. "
            "Use the provided tool to generate a valid order list."
        ),
        tools=tools,
        allow_delegation=False,
        verbose=False,
    )
