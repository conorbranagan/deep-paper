from datetime import datetime
from enum import Enum
import threading
import queue
import logging
from typing import Generator

from smolagents import (
    LiteLLMModel,
    CodeAgent,
    ToolCallingAgent,
)
from smolagents.monitoring import LogLevel
from browser_use import BrowserConfig

from app.pipeline.vector_store import QdrantVectorStore
from app.pipeline.embedding import Embedding
from app.agents.dd_llmobs import wrap_llmobs
from app.agents.deep_research.message import (
    ResearchStatusMessage,
    ResearchContentMessage,
    ResearchError,
    ResearchMessage,
)
from app.agents.deep_research.tools import (
    PaperRetriever,
    GoogleSearchTool,
    VisitWebpageTool,
)
from app.agents.deep_research.web_tools import BrowserUseWebAgent

wrap_llmobs()

log = logging.getLogger(__name__)


DEEP_RESEARCH_PROMPT_TPL = """
You are a research assistant tasked with analyzing an Arxiv paper and creating a comprehensive research report.
Your goal is to research the paper's topic, find external sources that reference it, and collect them for later use.

You will analyze the paper at: {arxiv_url}.

1. Begin by reading the Arxiv paper provided at.
   a. Read the paper thoroughly, paying attention to the main thesis, methodology, and conclusions.
   b. Identify key concepts, theories, and terminology used in the paper.

2. Explore external sources which reference this paper:
   a. Search for blog posts, articles, and academic discussions that cite the Arxiv paper URL. Make sure you fetch the pages you find most interesting.
   b. Focus on sources from Substack, Medium, and academic blogs.
   c. Collect at least 5 relevant external sources that provide substantial analysis or discussion of the paper.
   d. Try to find both sources that are around the time of the paper and those that are newer where they put it in context.

3. Write a report of your findings using Markdown formatting. Structure your research report as follows:
   a. Introduction: Provide an overview of the topic and its significance.
   b. Background: Offer necessary context and foundational information, use the paper's content to generate this.
   c. Key Findings: Discuss the key findings from your sources, organized by themes or subtopics.
   d. Discussion: Analyze the implications of the research, highlight any controversies or debates, and discuss potential future directions.
   e. Conclusion: Summarize the main points and provide closing thoughts.

- Try to use paragraphs rather than bullet points. You can use bullets or numbered lists if you need to, but sparingly.
- Use in-text citations to credit your sources. For ArXiv papers, use the format (Author et al., Year). For supplementary sources, use (Source Name, Year). Include a "References" section at the end of your report with full citations for all sources used.
- Write your research report, aiming for a comprehensive yet concise presentation of the topic. The report should be between 1000-1500 words.

Make sure code blocks are formatted correctly using py.
"""


# HACK: This is a way to inject a status for writing the research report. When
# we are done browsing we _should_ be moving on to the report. This doesn't
# quite work if there are multiple iterations on the web browser agent though.
def wrap_browser_agent(
    cls: ToolCallingAgent, message_queue: queue.Queue, queue_lock: threading.Lock
):
    original_provide_final_answer = cls.provide_final_answer

    def wrapped_provide_final_answer(self, *args, **kwargs) -> str:
        with queue_lock:
            message_queue.put(
                ResearchStatusMessage(
                    type="status",
                    message="Writing research report...",
                )
            )
        return str(original_provide_final_answer(self, *args, **kwargs))

    cls.provide_final_answer = wrapped_provide_final_answer
    return cls


class AgentMode(Enum):
    BROWSER_USE = "browser_use"
    BROWSER_USE_HEADLESS = "browser_use_headless"
    TEXT_BROWSER = "text_browser"


def run_agent(
    mode: AgentMode,
    paper_url: str,
    model: LiteLLMModel,
    verbosity_level=LogLevel.OFF,
    max_steps=10,
) -> Generator[ResearchMessage, None, None]:
    yield ResearchStatusMessage(type="status", message="Starting the agent...")
    log.info(f"Running the deep research agent, url={paper_url}, mode={mode}")
    collection_name = f"paper_sources_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
    embedding_config = Embedding.default()
    vector_store = QdrantVectorStore.instance(
        collection_name=collection_name,
        embedding_config=embedding_config,
    )

    # Create a thread-safe queue for messages
    message_queue: queue.Queue[ResearchMessage] = queue.Queue()
    # Create a flag to signal when the agent is done
    # Create a lock for thread safety
    queue_lock = threading.Lock()

    browser_agent_tools = []
    if mode == AgentMode.BROWSER_USE:
        browser_agent_tools = [
            BrowserUseWebAgent(
                message_queue, queue_lock, BrowserConfig(headless=False)
            ),
        ]
    elif mode == AgentMode.BROWSER_USE_HEADLESS:
        browser_agent_tools = [
            BrowserUseWebAgent(message_queue, queue_lock, BrowserConfig(headless=True)),
        ]
    elif mode == AgentMode.TEXT_BROWSER:
        browser_agent_tools = [
            GoogleSearchTool(message_queue, queue_lock),
            VisitWebpageTool(vector_store, embedding_config, message_queue, queue_lock),
        ]

    browser_agent = ToolCallingAgent(
        name="WebBrowser",
        tools=browser_agent_tools,
        model=model,
        max_steps=7,
        verbosity_level=verbosity_level,
        description="""A team member that will search the internet to answer your question.
            Ask them for all your questions that require browsing the web. Ensure they visit the most important pages they find before including them in the response.
            Provide them as much context as possible, in particular if you need to search on a specific timeframe!
            And don't hesitate to provide them with a complex search task, like finding a difference between two webpages.
            Your request must be a real sentence, not a google search! Like "Find me this information (...)" rather than a few keywords.""",
    )
    browser_agent.prompt_templates["managed_agent"][
        "task"
    ] += """
        In order to provide a comprehensive answer, you must visit the most important pages you find.
        In your final response you MUST include URLs alongside any other information about the sources you found.
    """
    browser_agent = wrap_browser_agent(browser_agent, message_queue, queue_lock)

    agent_done = threading.Event()
    paper_agent = ToolCallingAgent(
        name="PaperAnalyzer",
        tools=[PaperRetriever(message_queue, queue_lock)],
        model=model,
        max_steps=2,
        verbosity_level=verbosity_level,
        description="A team member agent who can analyze Arxiv papers. Provide it with an Arxiv URL and any areas you want it to focus on.",
    )

    manager_agent = CodeAgent(
        name="Manager",
        tools=[],
        model=model,
        max_steps=max_steps,
        verbosity_level=verbosity_level,
        managed_agents=[paper_agent, browser_agent],
    )
    prompt = DEEP_RESEARCH_PROMPT_TPL.format(arxiv_url=paper_url)

    # Function to run the agent in a separate thread
    def run_agent_thread():
        try:
            result = manager_agent.run(prompt, stream=False)
            with queue_lock:
                message_queue.put(
                    ResearchContentMessage(type="content", content=result)
                )
        except Exception as e:
            log.exception("Error running agent")
            # Put any errors in the queue
            with queue_lock:
                message_queue.put(
                    ResearchError(
                        type="error", error=f"Agent execution failed: {str(e)}"
                    )
                )
        finally:
            agent_done.set()
            with queue_lock:
                message_queue.put(
                    ResearchStatusMessage(
                        type="status",
                        message="Research completed",
                    )
                )

    # Start the agent in thread, as daemon so it exits when main thread exits
    agent_thread = threading.Thread(target=run_agent_thread)
    agent_thread.daemon = True

    agent_thread.start()

    while not agent_done.is_set() or not message_queue.empty():
        try:
            message = message_queue.get(timeout=0.1)
            yield message
            message_queue.task_done()
        except queue.Empty:
            continue

    agent_thread.join(timeout=1.0)
