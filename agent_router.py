
import time
from typing import Optional


class AgentRouter:

    def __init__(
        self,
        publish_event,
        agent_engine=None,
    ):

        self.publish_event = publish_event
        self.agent_engine = agent_engine

        self.agents = {
            "research": "RESEARCH_AGENT",
            "coding": "CODING_AGENT",
            "analysis": "ANALYSIS_AGENT",
        }

        print("NOVA Agent Router initialized")
        print("✓ Research Agent")
        print("✓ Coding Agent")
        print("✓ Analysis Agent")

    # ========================================================
    # ROUTE REQUEST
    # ========================================================

    async def route(
        self,
        request: str,
        parent_event_id: Optional[int] = None,
    ):

        if not request or not request.strip():

            return {
                "agent": None,
                "result": None,
                "event_id": None,
                "parent_event_id": parent_event_id,
            }

        request = request.strip()
        text = request.lower()

        agent = self.detect_agent(text)

        if agent is None:
            agent = "ANALYSIS_AGENT"

        # ----------------------------------------------------
        # CREATE ROUTING EVENT
        # ----------------------------------------------------

        routing_event_id = int(
            time.time() * 1000
        )

        routing_event = {
            "id": routing_event_id,
            "type": "AGENT_ROUTED",
            "source": "AGENT_ROUTER",
            "message": f"Request routed to {agent}",
            "timestamp": time.strftime("%H:%M:%S"),
            "color": "#facc15",
            "parent_event_id": parent_event_id,
            "observation": {
                "request": request,
                "agent": agent,
                "parent_event_id": parent_event_id,
            },
        }

        # ----------------------------------------------------
        # PUBLISH ROUTING EVENT
        # ----------------------------------------------------

        await self.publish_event(
            routing_event
        )

        # ----------------------------------------------------
        # EXECUTE AGENT
        # ----------------------------------------------------

        result = None
        execution_event_id = None

        if self.agent_engine:

            result = await self.agent_engine.execute(
                agent,
                request,
                parent_event_id=routing_event_id,
            )

        return {
            "agent": agent,
            "result": result,
            "event_id": routing_event_id,
            "parent_event_id": parent_event_id,
        }

    # ========================================================
    # AGENT DETECTION
    # ========================================================

    def detect_agent(
        self,
        text: str,
    ):

        # ----------------------------------------------------
        # CODING
        # ----------------------------------------------------

        coding_keywords = [
            "code",
            "coding",
            "program",
            "programming",
            "python",
            "javascript",
            "typescript",
            "react",
            "html",
            "css",
            "debug",
            "error",
            "bug",
            "function",
            "api",
            "database",
            "sql",
            "backend",
            "frontend",
        ]

        if any(
            keyword in text
            for keyword in coding_keywords
        ):
            return "CODING_AGENT"

        # ----------------------------------------------------
        # RESEARCH
        # ----------------------------------------------------

        research_keywords = [
            "research",
            "search",
            "find",
            "latest",
            "news",
            "information",
            "source",
            "sources",
            "paper",
            "study",
            "compare",
            "investigate",
        ]

        if any(
            keyword in text
            for keyword in research_keywords
        ):
            return "RESEARCH_AGENT"

        # ----------------------------------------------------
        # ANALYSIS
        # ----------------------------------------------------

        analysis_keywords = [
            "analyze",
            "analysis",
            "explain",
            "why",
            "reason",
            "calculate",
            "evaluate",
            "understand",
            "summarize",
            "assess",
        ]

        if any(
            keyword in text
            for keyword in analysis_keywords
        ):
            return "ANALYSIS_AGENT"

        return None

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):

        return {
            "status": "online",
            "agents": self.agents,
            "engine": self.agent_engine is not None,
        }