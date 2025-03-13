from pydantic import BaseModel
import litellm

from app.models.paper import Paper
from app.models.latex import Citation
from app.config import settings

SUMMARIZE_TOPICS_PROMPT = """
{paper_contents}

END PAPER

What are {n_topics} key topics from this paper? Focus on topics oriented towards the paper's abstract and not topics that
would be in every single paper.

When a reference is made with a format like arXiv:1502.05698 you should extract the arxiv id for the url.
Only provide the arxiv url when it's available.
"""

SUMMARIZE_PAPER_PROMPT = """
{paper_contents}

END PAPER

Summarize this paper in 4 bullet points, one sentence per bullet point. Focus on the novel findings from the paper and explain why it's useful.
"""


class TopicSummary(BaseModel):
    topic: str
    summary: str
    further_reading: list[Citation]


class KeyTopics(BaseModel):
    topics: list[TopicSummary]


class PaperSummary(BaseModel):
    title: str
    abstract: str
    summary: str
    topics: list[TopicSummary]


def summarize_paper(paper: Paper, model: str = settings.DEFAULT_MODEL) -> PaperSummary:
    formatted_prompt = SUMMARIZE_TOPICS_PROMPT.format(
        n_topics=5, paper_contents=paper.contents()
    )
    topics_response = (
        litellm.completion(
            model=model,
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.3,
            response_format=KeyTopics,
            vertex_credentials=settings.VERTEX_CREDENTIALS_JSON,
        )
        .choices[0]
        .message.content
    )

    # FIXME (Conor): This can throw an error if JSON coming back is in valid.
    # We'll just let it fail for now so we see this occuring.
    # In practice we can do some retries in case our LLM provider is flaky.
    key_topics = KeyTopics.model_validate_json(topics_response)

    # Sometimes we create citations without URLs but we need one for the frontend.
    for topic in key_topics.topics:
        topic.further_reading = [c for c in topic.further_reading if c.url is not None]

    formatted_prompt = SUMMARIZE_PAPER_PROMPT.format(paper_contents=paper.contents())
    summary_response = (
        litellm.completion(
            model=model,
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.3,
        )
        .choices[0]
        .message.content
    )

    return PaperSummary(
        title=paper.latex.title,
        abstract=paper.latex.abstract,
        summary=summary_response,
        topics=key_topics.topics,
    )


SUMMARIZE_PAPER_FOR_TOPIC_PROMPT = """
{paper_contents}

END PAPER

Explain how this paper covers _specifically_ the topic "{topic}". You do not need to restate the paper name.

Summaries should be no more than 2 paragraphs and must focus on the topic described.
You may also reference key citations relevant to that topic by Author+Year in the usual format for a paper.

If the topic is not mentioned in the paper return "This topic is not mentioned in this paper".
"""


def summarize_topic(paper: Paper, topic: str, model: str = settings.DEFAULT_MODEL):
    formatted_prompt = SUMMARIZE_PAPER_FOR_TOPIC_PROMPT.format(
        topic=topic, paper_contents=paper.contents()
    )
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": formatted_prompt}],
        temperature=0.3,
        stream=True,
        vertex_credentials=settings.VERTEX_CREDENTIALS_JSON,
    )
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk
