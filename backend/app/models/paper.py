# stdlib
import re
import os
import tarfile
import pathlib
import logging
import tempfile
from typing import Optional
from contextlib import contextmanager

# 3p
import requests
import bibtexparser
from pydantic import BaseModel
from pylatexenc.latex2text import LatexNodes2Text
from pylatexenc.latexwalker import (
    LatexWalker,
    LatexEnvironmentNode,
    LatexMacroNode,
    LatexCharsNode,
    LatexGroupNode,
)
import pymupdf

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


class SubSectionNode(BaseModel):
    title: str
    content: str


class SectionNode(BaseModel):
    title: str
    subsections: list[SubSectionNode]
    content: str


class PDFFile(BaseModel):
    filename: str
    pages: list[str]
    images: list[str]


class LatexFile(BaseModel):
    filename: str
    latex: str
    as_text: str


class Paper(BaseModel):
    arxiv_id: str
    title: str
    abstract: str
    citations: list[Citation]
    sections: list[SectionNode]
    pdf: PDFFile

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

        pdf_file = fetch_pdf_file(arxiv_id)
        paper = Paper(
            arxiv_id=arxiv_id,
            citations=citations,
            pdf=pdf_file,
            title="",
            abstract="",
            sections=[],
        )
        for latex_file in fetch_latex_files(arxiv_id):
            parse_latex_file(paper, latex_file)

        if paper.title == "":
            paper.title = f"Unknown Title (Arxiv ID: {arxiv_id})"

        return paper

    def all_contents(self) -> str:
        return "\n".join(p for p in self.pdf.pages)

    def latex_contents(self) -> str:
        return "\n".join(f.latex for f in self.latex_files)

    def print_tree(self):
        print(f"================ {self.title} ================")
        print(f"ABSTRACT: {self.abstract[:25]}...")
        for section in self.sections:
            print(f"SECTION: {section.title}")
            print(f"    CONTENT: {section.content}")
            for subsection in section.subsections:
                print(f"  SUBSECTION: {subsection.title}")
                print(f"    CONTENT: {subsection.content}")


def parse_arxiv_id(url) -> Optional[str]:
    arxiv_pattern = r"arxiv\.org/abs/(\d+\.\d+)"
    arxiv_match = re.search(arxiv_pattern, url)
    if not arxiv_match:
        raise InvalidPaperURL(url)
    return arxiv_match.group(1)


def _parse_section(node: LatexMacroNode) -> str:
    name_node = node.nodeargd.argnlist[2]
    if isinstance(name_node, LatexGroupNode):
        return "".join(
            c.chars
            for c in node.nodeargd.argnlist[2].nodelist
            if isinstance(c, LatexCharsNode)
        )
    else:
        return node.nodeargd.argnlist[2].nodelist[0].chars


def _parse_subsection(node: LatexMacroNode) -> str:
    name_node = node.nodeargd.argnlist[2]
    if isinstance(name_node, LatexGroupNode):
        return "".join(
            c.chars
            for c in node.nodeargd.argnlist[2].nodelist
            if isinstance(c, LatexCharsNode)
        )
    else:
        return node.nodeargd.argnlist[2].nodelist[0].chars


def parse_latex_file(paper: Paper, latex_file: LatexFile) -> None:
    """
    Parses a single LaTeX file into a list of sections and subsections by walking the AST.
    Captures other metadata like title and abstract along the way.
    This function mutates the paper object in place.
    """
    sections = []
    current_section: SectionNode | None = None
    current_section_content: list[str] = []
    current_subsection: SubSectionNode | None = None
    current_subsection_content: list[str] = []
    abstract = ""
    title = ""

    def _process_nodes(nodes):
        # This is a closure that holds the current section and subsection
        nonlocal current_section, current_section_content
        nonlocal current_subsection, current_subsection_content
        nonlocal abstract, title

        for node in nodes:
            if isinstance(node, LatexMacroNode) and node.macroname == "section":
                # Close out the current section and subsection.
                if current_subsection is not None:
                    current_subsection.content = "\n".join(current_subsection_content)
                    current_section.subsections.append(current_subsection)

                if current_section is not None:
                    current_section.content = "\n".join(current_section_content)
                    sections.append(current_section)

                # Start a new section.
                current_section = SectionNode(
                    title=_parse_section(node), subsections=[], content=""
                )
                current_section_content = []
                current_subsection = None
                current_subsection_content = []

            elif isinstance(node, LatexMacroNode) and node.macroname == "subsection":
                # Close out the current subsection.
                if current_subsection is not None:
                    current_subsection.content = "\n".join(current_subsection_content)
                    # We can have cases where the section never starts, this means we have it in the filename.
                    if current_section is None:
                        current_section = SectionNode(
                            title=latex_file.filename, subsections=[], content=""
                        )
                    current_section.subsections.append(current_subsection)

                # Start a new subsection.
                current_subsection = SubSectionNode(
                    title=_parse_subsection(node), content=""
                )
                current_subsection_content = []

            elif (
                isinstance(node, LatexEnvironmentNode)
                and node.environmentname == "abstract"
            ):
                try:
                    # Remove line breaks since it should be a paragraph
                    abstract = (
                        LatexNodes2Text()
                        .nodelist_to_text(node.nodelist)
                        .replace("\n", " ")
                    ).strip()
                except Exception:
                    # Some papers have formats that break our library. We fall back to a crappy but workable solution
                    char_nodes = [
                        n for n in node.nodelist if isinstance(n, LatexCharsNode)
                    ]
                    abstract = " ".join(c.chars for c in char_nodes).strip()

            # Extract title (assuming it's in a \title{} command)
            elif isinstance(node, LatexMacroNode) and node.macroname == "title":
                title = (
                    LatexNodes2Text()
                    .nodelist_to_text(node.nodeargd.argnlist[0].nodelist)
                    .replace("\n", "")
                    .replace("  ", " ")
                )
            else:
                # Add node to current section or subsection.
                try:
                    text = LatexNodes2Text().node_to_text(node).replace("\n", " ")
                except Exception:
                    text = ""
                if hasattr(node, "nodelist"):
                    try:
                        text += (
                            LatexNodes2Text()
                            .nodelist_to_text(node.nodelist)
                            .replace("\n", " ")
                        )
                    except Exception:
                        text += ""
                if current_section is not None:
                    current_section_content.append(text)
                if current_subsection is not None:
                    current_subsection_content.append(text)

            if hasattr(node, "nodelist") and node.nodelist:
                _process_nodes(node.nodelist)

    walker = LatexWalker(latex_file.latex)
    nodes, _, _ = walker.get_latex_nodes()
    _process_nodes(nodes)

    if current_subsection is not None:
        current_subsection.content = "\n".join(current_subsection_content)
        if current_section is None:
            current_section = SectionNode(
                title=latex_file.filename, subsections=[], content=""
            )
        current_section.subsections.append(current_subsection)

    if current_section is not None:
        sections.append(current_section)

    paper.sections.extend(sections)
    paper.title = title
    paper.abstract = abstract


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
