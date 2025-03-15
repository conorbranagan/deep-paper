from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser
import asyncio
import os
import queue
import threading


from app.agents.deep_research.tools import ResearchTool
from app.agents.dd_llmobs import SmolLLMObs

# Don't send telemetry to browser-use for now.
os.environ["ANONYMIZED_TELEMETRY"] = "false"


@SmolLLMObs.wrapped_tool
class BrowserUseWebAgent(ResearchTool):
    name = "web_browser"
    description = "Use this tool to browse the web with a full browser. It will take many steps in the browser in one call to this tool."

    inputs = {
        "task": {
            "type": "string",
            "description": "A multi-step task to complete in the browser. It should include (a) set of actions to take and (b) the data to return back at the end",
        }
    }
    output_type = "string"

    def __init__(
        self,
        message_queue: queue.Queue,
        queue_lock: threading.Lock,
        browser_config: BrowserConfig,
    ):
        super().__init__(message_queue, queue_lock)
        self.browser_config = browser_config

    def forward(self, task: str) -> str:
        browser = Browser(config=self.browser_config)
        llm = ChatOpenAI(model="gpt-4o-mini")
        agent = Agent(
            task=task,
            llm=llm,
            sensitive_data=None,
            browser=browser,
        )
        # Run the async function in a synchronous context
        return str(asyncio.run(agent.run()))
