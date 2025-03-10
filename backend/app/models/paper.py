# stdlib
import re
import logging
import tempfile

# 3p
import requests
from pydantic import BaseModel
import pymupdf

# app
from app.models import latex

log = logging.getLogger(__name__)


class PaperNotFound(Exception):
    pass


class InvalidPaperURL(Exception):
    def __init__(self, url):
        self.url = url
        super().__init__(f"Invalid paper URL: {url}")


class PDFFile(BaseModel):
    filename: str
    pages: list[str]
    images: list[str]


class Paper(BaseModel):
    arxiv_id: str
    pdf: PDFFile
    latex: latex.LatexPaper

    @classmethod
    def from_url(cls, url: str):
        arxiv_pattern = r"arxiv\.org/abs/(\d+\.\d+)"
        arxiv_match = re.search(arxiv_pattern, url)
        if not arxiv_match:
            raise InvalidPaperURL(url)
        arxiv_id = arxiv_match.group(1)
        if not arxiv_id:
            raise InvalidPaperURL(url)
        return cls.from_arxiv_id(arxiv_id)

    @classmethod
    def from_arxiv_id(cls, arxiv_id: str):
        return Paper(
            arxiv_id=arxiv_id,
            pdf=PDFFile(filename="", pages=[], images=[]),
            latex=latex.LatexPaper.from_arxiv_id(arxiv_id),
        )

    def latex_contents(self) -> str:
        return self.latex.all_contents

    def print_tree(self):
        self.latex.print_tree()


def fetch_pdf_file(arxiv_id: int) -> PDFFile:
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        url = f"https://arxiv.org/pdf/{arxiv_id}"
        response = requests.get(url)
        if response.status_code == 404:
            raise FileNotFoundError(f"PDF not found for arxiv_id: {arxiv_id}")
        elif response.status_code != 200:
            raise Exception(
                f"Error fetching PDF for arxiv_id: {arxiv_id}, code={response.status_code}, text={response.text}"
            )

        temp_file.write(response.content)
        temp_file_path = temp_file.name

    pdf_file = pymupdf.open(temp_file_path)

    return PDFFile(filename=url, pages=[p.get_text() for p in pdf_file], images=[])
