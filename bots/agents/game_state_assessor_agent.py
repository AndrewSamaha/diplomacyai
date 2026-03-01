import os

from crewai import Agent
from crewai import LLM

MAX_COMPLETION_TOKENS=500

openai_model = LLM(
    model=os.getenv('OPENAI_MODEL_NAME'),
    max_tokens=MAX_COMPLETION_TOKENS,
    max_completion_tokens=MAX_COMPLETION_TOKENS
)

def game_state_assessor_agent(tools=None) -> Agent:
    tools = tools or []
    return Agent(
        role="Game State Assessment",
        goal=(
            "Return a plain english description of the game state that includes "
            "the top the greatest two opporunities for expansion (e.g., nearby "
            "territories that have supply centers, nearby territories that are "
            "undefended) and the greatest two threats to your own territory that"
            "call for defense, e.g., RUSSIA is growing a front-line near our "
            "supply center at ANK, TURKEY has broken our front line at NAP, etc. "
            "Your output should be no more than 5 short sentences. Do NOT "
            "include a list of orderable locations in your output. "
        ),
        backstory=(
            "You are an expert at the game of Diplomacy and excel at interpreting"
            " the game state to identify opportunities and threats."
        ),
        tools=tools,
        allow_delegation=False,
        verbose=False,
        LLM=openai_model
    )
