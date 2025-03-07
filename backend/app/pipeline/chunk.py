"""
Strategies for chunking papers into pieces for our vector database.
"""
# stdlib
from abc import ABC, abstractmethod

# app
from app.models.paper import Paper


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, paper: Paper) -> list[str]:
        pass


class SectionChunkingStrategy(ChunkingStrategy):
    def chunk(self, paper: Paper) -> list[str]:
        chunks = []
        for section in paper.latex.sections:
            if len(section.subsections) == 0:
                chunks.append(f"Section: {section.title}\n{section.content}")
            else:
                for subsection in section.subsections:
                    chunks.append(f"Section: {section.title}\nSubsection: {subsection.title}\n{subsection.content}")
        return chunks

