import argparse
from pydantic import BaseModel, TypeAdapter
import litellm
import json
import sys

from app.models.paper import Paper, Citation

MODEL = "openai/gpt-4o-mini"

SUMMARIZE_TOPICS_PROMPT = """
{paper_contents}

END PAPER

What are {n_topics} key topics from this paper? Focus on topics oriented towards the paper's abstract and not topics that
would be in every single paper.

Use the JSON response format:

{{"key_topics": [
    {{
        "topic": "<short topic name>"
        "summary": "<1 sentence on relevancy of topic to this paper>"
        "further_reading": [
            # Up to 5 Citations
            {{
                "title": <paper title>,
                "author": <paper author>,
                "year": <paper year>,
                "url": <if available give a url>
            }},
            ...
        ]
    }}, ...
]}}
"""

SUMMARIZE_PAPER_PROMPT = """
{paper_contents}

END PAPER

Summarize this paper in 1 paragraph. Focus on the novel findings from the paper and explain why it's useful.
No more than 5 sentences in the paragraph.
"""


class TopicSummary(BaseModel):
    topic: str
    summary: str
    further_reading: list[Citation]


class PaperSummary(BaseModel):
    abstract: str
    summary: str
    topics: list[TopicSummary]


def summarize_paper(paper: Paper) -> PaperSummary:
    formatted_prompt = SUMMARIZE_TOPICS_PROMPT.format(
        n_topics=5, paper_contents=paper.all_contents()
    )
    topics_response = (
        litellm.completion(
            model=MODEL,  # You can change this to your preferred model
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        .choices[0]
        .message.content
    )
    try:
        response = json.loads(topics_response)
        ta = TypeAdapter(list[TopicSummary])
        topic_summaries = ta.validate_python(response["key_topics"])
    except json.JSONDecodeError:
        raise  # TODO

    formatted_prompt = SUMMARIZE_PAPER_PROMPT.format(
        paper_contents=paper.all_contents()
    )
    summary_response = (
        litellm.completion(
            model=MODEL,
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.3,
        )
        .choices[0]
        .message.content
    )

    return PaperSummary(
        abstract=paper.abstract,
        summary=summary_response,  # You might want to generate a separate summary
        topics=topic_summaries,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic paper processing tools")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Summarize paper command
    summarize_parser = subparsers.add_parser(
        "summarize_paper", help="Summarize an academic paper"
    )
    summarize_parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the paper to summarize"
    )
    summarize_parser.add_argument(
        "-o", "--output", type=str, help="Output file path for the summary (optional)"
    )

    args = parser.parse_args()

    if args.command == "summarize_paper":
        paper = Paper.from_url(args.url)
        summary = summarize_paper(paper)
        #print(f"Paper Summary: {paper.title}")
        print(f"\nAbstract:\n{summary.abstract}")
        print(f"\nSummary:\n{summary.summary}")
        print("\nTopics:")
        for topic in summary.topics:
            print(f"- {topic.topic}: {topic.summary}")
            print(f"  Further Reading:")
            for fr in topic.further_reading:
                print(f"  - {fr.title}: {fr.author}, {fr.url}")


    elif args.command is None:
        parser.print_help()
        sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)
