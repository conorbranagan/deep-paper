import argparse
from pydantic import BaseModel
import litellm
import json
import sys

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
        n_topics=5, paper_contents=paper.all_contents()
    )
    topics_response = (
        litellm.completion(
            model=model,  # You can change this to your preferred model
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.3,
            response_format=KeyTopics,
        )
        .choices[0]
        .message.content
    )
    try:
        key_topics = KeyTopics.model_validate_json(topics_response)
    except json.JSONDecodeError:
        raise  # TODO

    formatted_prompt = SUMMARIZE_PAPER_PROMPT.format(
        paper_contents=paper.all_contents()
    )
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
        title=paper.title,
        abstract=paper.abstract,
        summary=summary_response,  # You might want to generate a separate summary
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


def summarize_paper_topic(
    paper: Paper, topic: str, model: str = settings.DEFAULT_MODEL
):
    formatted_prompt = SUMMARIZE_PAPER_FOR_TOPIC_PROMPT.format(
        topic=topic, paper_contents=paper.all_contents()
    )
    response = litellm.completion(
        model=model,  # You can change this to your preferred model
        messages=[{"role": "user", "content": formatted_prompt}],
        temperature=0.3,
        stream=True,
    )
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic paper processing tools")
    parser.add_argument(
        "--model",
        type=str,
        default=settings.DEFAULT_MODEL,
        help="Model to use for summarization",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Parse paper command
    summarize_parser = subparsers.add_parser(
        "parse_paper", help="Just parses a paper and prints the tree"
    )
    summarize_parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the paper to summarize"
    )

    # Summarize paper command
    summarize_parser = subparsers.add_parser(
        "summarize_paper", help="Summarize an academic paper"
    )
    summarize_parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the paper to summarize"
    )
    # Summarize a paper for a specific topic
    summarize_topic_parser = subparsers.add_parser(
        "summarize_paper_topic", help="Summarize an academic paper for a topic"
    )
    summarize_topic_parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the paper to summarize"
    )
    summarize_topic_parser.add_argument(
        "-t", "--topic", type=str, help="Topic to focus on"
    )

    args = parser.parse_args()

    if args.command == "summarize_paper":
        paper = Paper.from_url(args.url)
        summary = summarize_paper(paper, model=args.model)
        print(f"Paper Summary: {paper.title}")
        print(f"\nAbstract:\n{summary.abstract}")
        print(f"\nSummary:\n{summary.summary}")
        print("\nTopics:")
        for topic in summary.topics:
            print(f"- {topic.topic}: {topic.summary}")
            print("  Further Reading:")
            for fr in topic.further_reading:
                print(f"  - {fr.title}: {fr.author}, {fr.url}")

    elif args.command == "summarize_paper_topic":
        paper = Paper.from_url(args.url)
        for chunk in summarize_paper_topic(paper, args.topic, model=args.model):
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="")
        print("\n")

    elif args.command == "parse_paper":
        paper = Paper.from_url(args.url)
        paper.print_tree()

    elif args.command is None:
        parser.print_help()
        sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)
