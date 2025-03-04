# stdlib
import re
import os
import tarfile
import pathlib
import logging
from typing import Optional
from contextlib import contextmanager

# 3p
import requests
import bibtexparser
from pydantic import BaseModel
from pylatexenc.latex2text import LatexNodes2Text
from pylatexenc.latexwalker import LatexWalker, LatexEnvironmentNode, LatexMacroNode, LatexCharsNode

CACHE_PATH = "/tmp/deep-paper-arxiv-cache"

log = logging.getLogger(__name__)


class PaperNotFound(Exception):
    pass


class InvalidPaperURL(Exception):
    def __init__(self, url):
        self.url = url
        super().__init__(f"Invalid paper URL: {url}")


class Citation(BaseModel):
    id: Optional[str] = None
    title: str
    author: str
    year: Optional[int] = None
    url: Optional[str] = None


class LatexFile(BaseModel):
    filename: str
    latex: str
    as_text: str


class Paper(BaseModel):
    arxiv_id: str
    title: str
    citations: list[Citation]
    abstract: str
    # references: list["Paper"]
    contents: list[LatexFile]

    @classmethod
    def from_url(cls, url: str):
        return cls.from_arxvid_id(parse_arxiv_id(url))

    @classmethod
    def from_arxvid_id(cls, arxiv_id: str):
        try:
            citations = fetch_citations(arxiv_id)
        except FileNotFoundError:
            log.warning(f"no citations found for arxvid={arxiv_id}")
            citations = []

        references = []
        # Fetch papers one layer deep in citations
        # TODO: Concurrently fetch a bunch at once.
        # for cit in citations:
        #    if not cit.url:
        #        continue
        #    arxiv_id = parse_arxiv_id(cit.url)
        #    if not arxiv_id:
        #        print(f"Skipping cituation url: {cit.url}")
        #        continue
        #    print(f"Fetching cituation: {url}")
        #    references.append(Paper.from_url(url))
        latex_files = fetch_latex_files(arxiv_id)
        all_latex = "\n".join(f.latex for f in latex_files)
        meta = parse_latex_metadata(all_latex, latex_files)

        return Paper(
            arxiv_id=arxiv_id,
            title=meta.title,
            abstract=meta.abstract,
            contents=latex_files,
            citations=citations,
            references=references,
        )

    def all_contents(self) -> str:
        return "\n".join(c.latex for c in self.contents)


def parse_arxiv_id(url) -> Optional[str]:
    arxiv_pattern = r"arxiv\.org/abs/(\d+\.\d+)"
    arxiv_match = re.search(arxiv_pattern, url)
    if not arxiv_match:
        raise InvalidPaperURL(url)
    return arxiv_match.group(1)


class LatexMeta(BaseModel):
    abstract: Optional[str]
    title: Optional[str]


def parse_latex_metadata(latex_str: str, files: list[LatexFile]) -> LatexMeta:
    walker = LatexWalker(latex_str)
    nodes, _, _ = walker.get_latex_nodes()
    meta = LatexMeta(abstract="", title="")

    def _parse_meta_in_nodes(nodes, meta):
        for node in nodes:
            # Extract abstract - this can be in the latex
            if (
                isinstance(node, LatexEnvironmentNode)
                and node.environmentname == "abstract"
            ):
                try:
                    # Remove line breaks since it should be a paragraph
                    meta.abstract = (
                        LatexNodes2Text().nodelist_to_text(node.nodelist).replace("\n", " ")
                    )
                except Exception:
                    # Some papers have formats that break our library. We fall back to a crappy but workable solution
                    char_nodes = [n for n in node.nodelist if isinstance(n, LatexCharsNode)]
                    meta.abstract = " ".join(c.chars for c in char_nodes)

            # Extract title (assuming it's in a \title{} command)
            if (
                isinstance(node, LatexMacroNode)
                and node.macroname == "title"
                and node.nodeargd
                and node.nodeargd.argnlist
            ):
                meta.title = (
                    LatexNodes2Text()
                    .nodelist_to_text(node.nodeargd.argnlist[0].nodelist)
                    .replace("\n", "")
                    .replace("  ", " ")
                )

            if hasattr(node, "nodelist") and node.nodelist:
                _parse_meta_in_nodes(node.nodelist, meta)

        return meta

    meta = _parse_meta_in_nodes(nodes, meta)

    # Also check for a file call "abstract" in case it's referenced.
    # This is super brittle!
    for f in files:
        if f.filename == "abstract.tex":
            meta.abstract = f.as_text

    return meta


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
                id=entry.get("ID"),
                title=entry.get("title"),
                author=entry.get("author"),
                year=entry.get("year"),
                url=entry.get("author"),
            )
            for entry in entries
        ]


def fetch_latex_files(arxiv_id: int) -> list[LatexFile]:
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
                        filename=pathlib.Path(filepath).name,
                        latex=latex_content,
                        as_text=text_content,
                    )
                )
    return files
