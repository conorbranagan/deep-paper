"""
Strategies for chunking papers into pieces for our vector database.
"""

# stdlib
from abc import ABC, abstractmethod
from typing import Any, Callable
from pydantic import BaseModel
import uuid

# app
from app.models.paper import Paper
from app.pipeline.embedding import EmbeddingConfig


class Document(BaseModel):
    text: str
    chunk_id: str

    def __str__(self) -> str:
        return f"{self.chunk_id}: {self.text}"


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, object: Any) -> list[Document]:
        pass


class SectionChunkingStrategy(ChunkingStrategy):
    def chunk(self, object: Any) -> list[Document]:
        chunks = []
        if not isinstance(object, Paper):
            raise ValueError("Object must be a Paper to use SectionChunkingStrategy")

        paper = object
        for section in paper.latex.sections:
            if len(section.subsections) == 0:
                chunks.append(
                    Document(
                        text=f"Section: {section.title}\n{section.content}",
                        chunk_id=section.title,
                    )
                )
            else:
                for subsection in section.subsections:
                    chunks.append(
                        Document(
                            text=f"Section: {section.title}\nSubsection: {subsection.title}\n{subsection.content}",
                            chunk_id=f"{section.title}_{subsection.title}",
                        )
                    )
        return chunks


class MaxLengthChunkingStrategy(ChunkingStrategy):
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    def chunk(self, object: Any) -> list[Document]:
        if not isinstance(object, str):
            raise ValueError("Object must be a string to use MaxLengthChunkingStrategy")
        text = object
        chunks = []
        while len(text) > self.max_tokens:
            chunks.append(
                Document(text=text[: self.max_tokens], chunk_id=str(uuid.uuid4()))
            )
            text = text[self.max_tokens :]
        return chunks


class AdaptiveChunker:
    def __init__(
        self,
        chunking_strategy: ChunkingStrategy,
        embedding_config: EmbeddingConfig,
        overlap: int = 0,
    ):
        self.primary_chunker = chunking_strategy
        self.token_encoder: Callable[[str], list[int]] | None = (
            embedding_config.token_encoder
        )
        self.max_tokens = embedding_config.max_tokens
        self.overlap = overlap

    def chunk(self, paper: Paper) -> list[Document]:
        """
        Two-phase chunking:
        1. Use primary chunker to create semantic/logical chunks
        2. If needed, further split chunks that exceed max_tokens
        """
        # Primary chunking (semantic/logical)
        primary_chunks = self.primary_chunker.chunk(paper)
        if self.token_encoder is None:
            return primary_chunks

        # Doing this to make mypy happy, otherwise it complains about none not being callable.
        token_encoder = self.token_encoder
        max_tokens = self.max_tokens

        # Secondary chunking (token limit enforcement)
        final_chunks = []
        for chunk in primary_chunks:
            text = chunk.text
            token_count = len(self.token_encoder(text))

            if token_count <= max_tokens:
                final_chunks.append(chunk)
            else:
                # Need to split further using recursive approach
                chunk_counter = 0

                def split_text(text_to_split, base_id_suffix):
                    tokens = len(token_encoder(text_to_split))

                    if tokens <= max_tokens:
                        # This chunk fits within token limit
                        new_chunk = Document(
                            text=text_to_split,
                            chunk_id=f"{chunk.chunk_id}_{base_id_suffix}",
                        )
                        return [new_chunk]

                    # Find a good split point (roughly in the middle)
                    mid_point = len(text_to_split) // 2

                    # Try to find a natural break point (period, newline, etc.)
                    split_candidates = [
                        text_to_split.rfind("\n\n", 0, mid_point),
                        text_to_split.rfind(". ", 0, mid_point),
                        text_to_split.rfind("? ", 0, mid_point),
                        text_to_split.rfind("! ", 0, mid_point),
                        text_to_split.rfind("; ", 0, mid_point),
                        text_to_split.rfind(" ", 0, mid_point),
                    ]

                    # Use the best split point found
                    split_point = max(
                        filter(lambda x: x != -1, split_candidates), default=mid_point
                    )
                    if split_point == -1:
                        split_point = mid_point

                    # Add overlap if needed
                    overlap_text = ""
                    if self.overlap > 0:
                        # Find a few words for overlap
                        words = text_to_split[: split_point + 1].split()
                        if len(words) > self.overlap:
                            overlap_text = " ".join(words[-self.overlap :]) + " "

                    # Split the text and process recursively
                    first_half = text_to_split[: split_point + 1]
                    second_half = overlap_text + text_to_split[split_point + 1 :]

                    # Check if second_half with overlap exceeds max_tokens
                    second_half_tokens = len(token_encoder(second_half))
                    if second_half_tokens > max_tokens and self.overlap > 0:
                        # Reduce overlap until it fits or overlap becomes 0
                        for reduced_overlap in range(self.overlap - 1, -1, -1):
                            if reduced_overlap == 0:
                                overlap_text = ""
                                second_half = text_to_split[split_point + 1 :]
                                break

                            words = text_to_split[: split_point + 1].split()
                            if len(words) > reduced_overlap:
                                new_overlap_text = (
                                    " ".join(words[-reduced_overlap:]) + " "
                                )
                                new_second_half = (
                                    new_overlap_text + text_to_split[split_point + 1 :]
                                )
                                if len(token_encoder(new_second_half)) <= max_tokens:
                                    overlap_text = new_overlap_text
                                    second_half = new_second_half
                                    break

                    # Recursively split both halves
                    result = []
                    result.extend(split_text(first_half, f"{base_id_suffix}a"))
                    result.extend(split_text(second_half, f"{base_id_suffix}b"))
                    return result

                # Start the recursive splitting process
                final_chunks.extend(split_text(text, str(chunk_counter)))
                chunk_counter += 1

        return final_chunks
