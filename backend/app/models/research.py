from pydantic import BaseModel
from typing import Optional

class Research(BaseModel):
    id: str
    url: str


class MemoryDB:
    def __init__(self):
        self.values: dict[str, Research] = {}
    
    def set(self, id: str, research: Research):
        self.values[id] = research
    
    def get(self, id: str) -> Optional[Research]:
        return self.values.get(id)


RESEARCH_DB = MemoryDB()
