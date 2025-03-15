import asyncio
import queue
import threading
import logging

from browser_use import Agent, BrowserConfig, Browser
from browser_use.browser.views import BrowserState
from browser_use.agent.views import AgentOutput

from app.agents.deep_research.tools import ResearchTool
from app.agents.dd_llmobs import SmolLLMObs
from app.agents.deep_research.message import ResearchSourceMessage
from app.config import settings

log = logging.getLogger(__name__)


def _is_valid_source(url: str) -> bool:
    if url == "about:blank":
        return False
    if "google.com" in url:
        return False
    return True


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
        model: str,
        browser_config: BrowserConfig,
    ):
        super().__init__(message_queue, queue_lock)
        self.model = model
        self.browser_config = browser_config
        self.visited_urls: dict[str, str] = {}

    def forward(self, task: str) -> str:
        browser = Browser(config=self.browser_config)
        llm = settings.langchain_model(self.model)

        async def new_step_callback(
            browser_state: BrowserState, agent_output: AgentOutput, step_index: int
        ):
            if not _is_valid_source(browser_state.url):
                return

            if browser_state.url not in self.visited_urls:
                log.info(f"Visited source: {browser_state.url}")
                with self.queue_lock:
                    self.message_queue.put(
                        ResearchSourceMessage(
                            type="source",
                            url=browser_state.url,
                            title=browser_state.title,
                            favicon=f"http://www.google.com/s2/favicons?domain={browser_state.url}",
                            summary="",
                        )
                    )
                    self.visited_urls[browser_state.url] = browser_state.title

        agent = Agent(
            task=task,
            llm=llm,
            sensitive_data=None,
            browser=browser,
            register_new_step_callback=new_step_callback,
        )
        # Run the async function in a synchronous context
        return str(asyncio.run(agent.run()))
