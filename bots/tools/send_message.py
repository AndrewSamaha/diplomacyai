"""Tool for sending in-game messages."""
import json
from typing import Any, List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


class SendGlobalMessageInput(BaseModel):
    message: str = Field(..., description="The message text to send to all players.")


class SendGlobalMessageTool(BaseTool):
    """
    Compose a global message (to all players) in the game.
    
    This tool queues the message to be sent after the crew completes.
    The caller is responsible for actually sending queued messages.
    
    Uses result_as_answer=True so the agent's task completes
    immediately after calling it.
    """
    name: str = "send_global_message"
    description: str = (
        "Send a message to ALL players in the game. "
        "The message will be visible to everyone. "
        "Use this to taunt, announce intentions, or communicate publicly."
    )
    args_schema: Type[BaseModel] = SendGlobalMessageInput
    result_as_answer: bool = True

    _power_name: str = PrivateAttr()
    _message_queue: List[str] = PrivateAttr()

    def __init__(self, power_name: str, message_queue: List[str]):
        super().__init__()
        self._power_name = power_name
        self._message_queue = message_queue

    def _run(self, message: str) -> str:
        self._message_queue.append(message)
        return f"Message queued: {message}"
