from crewai import Agent

from bots.tools.get_random_order import GetRandomOrderTool


def build_order_agent() -> Agent:
    return Agent(
        role="Order Selector",
        goal="Return a set of legal orders for the current power.",
        backstory=(
            "You are a Diplomacy assistant that strictly selects legal orders. "
            "Use the provided tool to generate a valid order list."
        ),
        tools=[GetRandomOrderTool()],
        allow_delegation=False,
        verbose=False,
    )
