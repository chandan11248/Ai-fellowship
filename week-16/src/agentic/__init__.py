"""
Agentic system package for Week 16 assignment.
"""

from src.agentic.dossier import EvidenceDossier
from src.agentic.skills_manager import skills_manager
from src.agentic.multi_agent import MultiAgentSystem, AgenticExecutionTrace
from src.agentic.single_agent import SingleAgentLoop, SingleAgentExecutionTrace

__all__ = [
    "EvidenceDossier",
    "skills_manager",
    "MultiAgentSystem",
    "AgenticExecutionTrace",
    "SingleAgentLoop",
    "SingleAgentExecutionTrace",
]
