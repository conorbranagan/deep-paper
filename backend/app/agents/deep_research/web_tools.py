from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
import os


from app.agents.deep_research.tools import ResearchTool
from app.agents.dd_llmobs import SmolLLMObs

# Don't send telemetry to browser-use for now.
os.environ["ANONYMIZED_TELEMETRY"] = "false"


@SmolLLMObs.wrapped_tool
class WebAgentTool(ResearchTool):
    name = "web_agent"
    description = "Use this tool to browse the web with a full browser. It will take many steps in the browser in one call to this tool."

    inputs = {
        "task": {
            "type": "string",
            "description": "A multi-step task to complete in the browser. It should include (a) set of actions to take and (b) the data to return back at the end",
        }
    }
    output_type = "string"

    def forward(self, task: str) -> str:
        llm = ChatOpenAI(model="gpt-4o-mini")
        agent = Agent(
            task=task,
            llm=llm,
            sensitive_data=None,
        )
        # Run the async function in a synchronous context
        return str(asyncio.run(agent.run()))
