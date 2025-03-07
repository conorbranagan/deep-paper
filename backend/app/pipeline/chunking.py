"""
Strategies for chunking papers into pieces for our vector database.
"""

from abc import ABC, abstractmethod
from app.models.paper import Paper


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, paper: Paper) -> list[str]:
        pass




if __name__ == "__main__":
    with open("ids.txt", "r") as f:
        for line in f:
            arxiv_id = line.strip()
            if arxiv_id.startswith("#"):
                continue
            paper = Paper.from_arxvid_id(arxiv_id)
            paper.print_tree()     
            print("\n\n")   