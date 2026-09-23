"""Base class for all analytics agents."""
import time
import structlog
from abc import ABC, abstractmethod
from models.schemas import AgentStep

logger = structlog.get_logger()


class BaseAgent(ABC):
    agent_id: str
    label: str

    async def run(self, context: dict) -> dict:
        """Execute agent, track timing, return updated context."""
        start = time.monotonic()
        logger.info("Agent starting", agent=self.agent_id)
        try:
            result = await self._execute(context)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("Agent complete", agent=self.agent_id, duration_ms=duration_ms)
            result["_agent_steps"] = context.get("_agent_steps", []) + [
                AgentStep(agent_id=self.agent_id, label=self.label, status="done", duration_ms=duration_ms)
            ]
            return result
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("Agent error", agent=self.agent_id, error=str(e))
            context["_agent_steps"] = context.get("_agent_steps", []) + [
                AgentStep(agent_id=self.agent_id, label=self.label, status="error", duration_ms=duration_ms)
            ]
            raise

    @abstractmethod
    async def _execute(self, context: dict) -> dict:
        """Override in each agent."""
        ...
