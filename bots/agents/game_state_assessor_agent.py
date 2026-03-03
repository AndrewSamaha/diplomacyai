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
        role="Diplomacy Game State Assessor",
        goal=(
            "Given a Diplomacy game snapshot and optional metrics, produce a concise, "
            "plain-English strategic posture assessment for the specified power. "
            "Focus on identifying expansion opportunities and defensive threats. "
            "Use only the provided context; do not invent positions, units, or rules outcomes."
        ),
        backstory=(
            "You are an expert Diplomacy strategist. You quickly read board states, "
            "spot supply-center opportunities, detect tactical vulnerabilities, and "
            "summarize what matters without noise."
        ),
        tools=tools,
        allow_delegation=False,
        verbose=False,
        LLM=openai_model,
    )

