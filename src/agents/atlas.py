"""Atlas Agent — Product Owner + Scrum Master.

Outputs: sprint plans, gate readiness checks, blocker escalations.
Orchestrates all other agents and manages the 5 human approval gates.
"""

from dataclasses import dataclass


@dataclass
class GateStatus:
    gate_id: str
    passed: bool
    blockers: list[str]


class AtlasAgent:
    """Orchestrator agent that manages sprint execution and gate approvals."""

    def check_gate(self, gate_id: str) -> GateStatus:
        raise NotImplementedError
