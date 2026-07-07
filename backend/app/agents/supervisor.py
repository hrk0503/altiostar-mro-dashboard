from typing import Any

from pydantic import BaseModel


# Supervisor state node (Task A2)
class SupervisorState(BaseModel):
    history: list[dict[str, Any]] = []
    current_action: dict[str, Any] = {}
    requires_approval: bool = False
    is_approved: bool = False

class Supervisor:
    def __init__(self):
        self.state = SupervisorState()

    def route_to_agent(self, user_query: str) -> str:
        """Evaluate user query and route to Spectrum, Explainer, or NOC Copilot."""
        if "spec" in user_query.lower() or "standards" in user_query.lower():
            return "spectrum"
        elif "explain" in user_query.lower() or "why" in user_query.lower():
            return "explainer"
        else:
            return "noc_copilot"

    def gate_action(self, action: dict[str, Any]) -> bool:
        """Interrupt gate for safety validation before updating baseband settings."""
        self.state.current_action = action
        # Trigger human intervention if offset is significant
        if abs(action.get("cio_delta", 0)) > 1.5:
            self.state.requires_approval = True
            print("⚠️ Action requires operator approval: large CIO delta.")
            return False
        self.state.is_approved = True
        return True
