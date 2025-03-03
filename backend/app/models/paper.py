# stdlib
import re
import os
import tarfile
import pathlib
from typing import Optional
from contextlib import contextmanager

# 3p
import requests
import bibtexparser
from pydantic import BaseModel
from pylatexenc.latex2text import LatexNodes2Text

CACHE_PATH = "/tmp/deep-paper-arxiv-cache"


class PaperNotFound(Exception):
    pass

class Citation(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    url: Optional[str] = None


class LatexFile(BaseModel):
    name: str
    latex: str
    as_text: str


class Paper(BaseModel):
    arxiv_id: str
    citations: list[Citation]
    references: list["Paper"]
    contents: list[LatexFile]

    @classmethod
    def from_arxvid_id(cls, arxiv_id: str):
        citations = fetch_citations(arxiv_id)
        references = []

        # Fetch papers one layer deep in citations
        # TODO: Concurrently fetch a bunch at once.
        #for cit in citations:
        #    if not cit.url:
        #        continue
        #    arxiv_id = parse_arxiv_id(cit.url)
        #    if not arxiv_id:
        #        print(f"Skipping cituation url: {cit.url}")
        #        continue
        #    print(f"Fetching cituation: {url}")
        #    references.append(Paper.from_url(url))

        return Paper(
            arxiv_id=arxiv_id,
            contents=fetch_contents(arxiv_id),
            citations=citations,
            references=references,
        )


def parse_arxiv_id(url) -> Optional[str]:
    arxiv_pattern = r"arxiv\.org/abs/(\d+\.\d+)"
    arxiv_match = re.search(arxiv_pattern, url)
    return arxiv_match.group(1)


@contextmanager
def fetch_tar(arxiv_id: int):
    pathlib.Path(CACHE_PATH).mkdir(parents=True, exist_ok=True)
    cache_filepath = f"{CACHE_PATH}/{arxiv_id}"
    if not os.path.exists(cache_filepath):
        url = f"https://arxiv.org/src/{arxiv_id}"
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(cache_filepath, "wb") as f:
            f.write(response.content)

    try:
        f = tarfile.open(cache_filepath)
        yield f
    finally:
        f.close()


def fetch_citations(arxiv_id: int) -> list[Citation]:
    with fetch_tar(arxiv_id) as tar:
        bib_file_path = None
        for file_path in tar.getnames():
            if file_path.endswith("references.bib"):
                bib_file_path = file_path
                break

        if not bib_file_path:
            raise FileNotFoundError("references.bib not found in the tar.gz archive")

        bib_file = tar.extractfile(bib_file_path)
        bib_content = bib_file.read().decode("utf-8")

        # Parse the BibTeX file
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        entries = bibtexparser.loads(bib_content, parser).entries
        return [
            Citation(
                title=entry.get("title"),
                author=entry.get("author"),
                year=entry.get("year"),
                url=entry.get("author"),
            )
            for entry in entries
        ]


def fetch_contents(arxiv_id: int) -> list[LatexFile]:
    files = []
    l2t = LatexNodes2Text()
    with fetch_tar(arxiv_id) as tar:
        for filepath in tar.getnames():
            if filepath.endswith(".tex"):
                latex_content = tar.extractfile(filepath).read().decode("utf-8")
                try:
                    text_content = l2t.latex_to_text(latex_content)
                except Exception:
                    # Seem to hit this sometimes: https://github.com/phfaist/pylatexenc/issues/99
                    # fallback to latext content
                    text_content = latex_content
                files.append(
                    LatexFile(
                        name=pathlib.Path(filepath).stem,
                        latex=latex_content,
                        as_text=text_content,
                    )
                )
    return files
