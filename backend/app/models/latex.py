# stdlib
import pathlib
import os
import tarfile
from contextlib import contextmanager
from pydantic import BaseModel
from typing import Optional
import re
import logging

# 3p
import bibtexparser
import requests
from pylatexenc.latex2text import LatexNodes2Text
from pylatexenc import latexwalker
from pylatexenc.latexnodes import nodes as latexnodes, parsers as latexparser

CACHE_PATH = "/tmp/deep-paper-arxiv-cache"

log = logging.getLogger(__name__)


class LatexTexFile(BaseModel):
    filename: str
    content: str


class LatexMetaFile(BaseModel):
    filename: str


class SubSectionNode(BaseModel):
    title: str
    content: str


class SectionNode(BaseModel):
    title: str
    subsections: list[SubSectionNode]
    content: str


class Citation(BaseModel):
    id: Optional[str] = None
    title: str
    author: str
    year: Optional[int] = None
    url: Optional[str] = None


class LatexPaper(BaseModel):
    title: str
    abstract: str
    sections: list[SectionNode]
    citations: list[Citation]

    @classmethod
    def from_arxiv_id(cls, arxiv_id: int) -> "LatexPaper":
        # Fetch the raw tex files and metadata files.
        raw_tex_files, meta_files = _fetch_files(arxiv_id)

        # Inline all the \input and \include directives.
        tex_files = _inline_latex_includes(arxiv_id, raw_tex_files, meta_files)

        # Extract metadata like title and abstract.
        title, abstract = MetadataParser.parse(tex_files)
        if title == "":
            title = f"Unknown Title (Arxiv ID: {arxiv_id})"

        # Parse the sections and subsections.
        sections = SectionParser.parse(tex_files)

        # Fetch the citations using the bibtex file.
        # For now ignore the citations if we can't find the bibtex file.
        # FIXME: Need another approach, bbl file is an option or something else.
        try:
            citations = fetch_citations(arxiv_id)
        except FileNotFoundError:
            log.warning(f"no citations found for title={title}, arxvid={arxiv_id}")
            citations = []

        return LatexPaper(
            title=title, abstract=abstract, sections=sections, citations=citations
        )

    def print_tree(self):
        print(f"Title: {self.title}")
        print(f"Abstract: {self.abstract}")
        for section in self.sections:
            print(f"Section: {section.title}")
            for subsection in section.subsections:
                print(f"  Subsection: {subsection.title}")


def _fetch_files(arxiv_id: int) -> tuple[list[LatexTexFile], list[LatexMetaFile]]:
    tex_files = []
    meta_files = []
    with fetch_tar(arxiv_id) as tar:
        # Seems that this keeps ordering by top-level -> deeper levels?
        for filepath in tar.getnames():
            if filepath.endswith(".tex"):
                latex_content = tar.extractfile(filepath).read().decode("utf-8")
                tex_files.append(LatexTexFile(filename=filepath, content=latex_content))
            else:
                meta_files.append(LatexMetaFile(filename=filepath))

    return tex_files, meta_files


def _inline_latex_includes(
    arxiv_id: str, tex_files: list[LatexTexFile], meta_files: list[LatexMetaFile]
) -> list[LatexTexFile]:
    """
    Read through the tex files and inline all the \input and \include directives
    """
    filename_to_tex = {tex_file.filename: tex_file for tex_file in tex_files}
    meta_filenames = {meta_file.filename for meta_file in meta_files}
    merged_files = set()

    # Pattern to match \input{...} or \include{...} commands
    # This handles various formats like \input{file}, \input {file}, \input{directory/file} etc.
    input_pattern = re.compile(r"\\(input|include)\s*\{([^}]+)\}")
    # Pattern for \includeonly{...} which we'll just track for now
    includeonly_pattern = re.compile(r"\\includeonly\s*\{([^}]+)\}")

    resolved_tex_files = {}

    for tex_file in tex_files:
        content = tex_file.content

        # Process all \input and \include directives
        def replace_include(match):
            command = match.group(1)  # 'input' or 'include'
            filename = match.group(2).strip()

            if not filename.endswith(".tex"):
                filename_with_tex = filename + ".tex"
            else:
                filename_with_tex = filename

            possible_filenames = [
                filename,
                filename_with_tex,
                # Handle directories in the repository
                # f"documents/{filename}",
                # f"documents/{filename_with_tex}",
            ]

            for possible_name in possible_filenames:
                if possible_name in filename_to_tex:
                    target_file = filename_to_tex[possible_name]
                    # print(
                    #    f"Replacing \\{command}{{{filename}}} with content from {possible_name}"
                    # )
                    merged_files.add(possible_name)
                    return target_file.content

            for possible_name in possible_filenames:
                if possible_name in meta_filenames:
                    # print(
                    #    f"Found reference to meta file in \\{command}{{{filename}}}, but not replacing it"
                    # )
                    return match.group(0)  # Return the original directive

            # If we can't find the file, just keep the original directive
            log.warning(
                f"Warning: Could not find file for \\{command}{{{filename}}}, arxvid={arxiv_id}"
            )
            return match.group(0)

        # Replace all \input and \include directives
        new_content = input_pattern.sub(replace_include, content)

        # Log any \includeonly directives but don't modify them
        for match in includeonly_pattern.finditer(content):
            included_files = match.group(1).split(",")
            print(
                f"Found \\includeonly directive with files: {', '.join(included_files)}"
            )

        # Add the resolved file to our result list if it hasn't been processed as an include/input
        if tex_file.filename not in merged_files:
            resolved_tex_files[tex_file.filename] = LatexTexFile(
                filename=tex_file.filename, content=new_content
            )

    # Remove any files that were processed as includes/inputs
    for filename in merged_files:
        if filename in resolved_tex_files:
            del resolved_tex_files[filename]

    return list(resolved_tex_files.values())


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


class MetadataParser(latexnodes.LatexNodesVisitor):
    def __init__(self):
        self.abstract = ""
        self.title = ""

    @classmethod
    def parse(cls, latex_files: list[LatexTexFile]) -> tuple[str, str]:
        title, abstract = "", ""
        for lf in latex_files:
            nodelist, _ = latexwalker.LatexWalker(lf.content).parse_content(
                parser=latexparser.LatexGeneralNodesParser()
            )
            if isinstance(nodelist, latexnodes.LatexNode):
                nodelist = latexnodes.LatexNodeList([nodelist])
            for node in nodelist.nodelist:
                mp = cls()
                mp.start(node)

                if mp.abstract:
                    abstract = mp.abstract
                if mp.title:
                    title = mp.title

        return title, abstract

    def visit_macro_node(self, node: latexwalker.LatexMacroNode, **kwargs):
        if node.macroname == "title":
            self.title = (
                LatexNodes2Text()
                .nodelist_to_text(node.nodeargd.argnlist[0].nodelist)
                .replace("\n", "")
                .replace("  ", " ")
            )

    def visit_environment_node(self, node: latexwalker.LatexEnvironmentNode, **kwargs):
        if node.environmentname == "abstract":
            try:
                # Remove line breaks since it should be a paragraph
                self.abstract = (
                    LatexNodes2Text().nodelist_to_text(node.nodelist).replace("\n", " ")
                ).strip()
            except Exception:
                # Some papers have formats that break our library. We fall back to a crappy but workable solution
                char_nodes = [
                    n
                    for n in node.nodelist
                    if isinstance(n, latexwalker.LatexCharsNode)
                ]
                self.abstract = " ".join(c.chars for c in char_nodes).strip()


class SectionParser(latexnodes.LatexNodesVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.sections: list[SectionNode] = []
        self.current_section: SectionNode | None = None
        self.current_section_content: list[str] = []
        self.current_subsection: SubSectionNode | None = None
        self.current_subsection_content: list[str] = []

    @classmethod
    def parse(cls, latex_files: list[LatexTexFile]) -> list[SectionNode]:
        sections: list[SectionNode] = []
        for lf in latex_files:
            nodelist, _ = latexwalker.LatexWalker(lf.content).parse_content(
                parser=latexparser.LatexGeneralNodesParser()
            )
            if isinstance(nodelist, latexwalker.LatexNode):
                nodelist = latexnodes.LatexNodeList([nodelist])

            for node in nodelist.nodelist:
                sp = cls(lf.filename)
                sp.start(node)
                sp.finish()
                by_name = {s.title: s for s in sections}
                # Merge sections with the same title.
                for section in sp.sections:
                    if section.title in by_name:
                        by_name[section.title].content += section.content
                        by_name[section.title].subsections.extend(section.subsections)
                    else:
                        sections.append(section)

        return sections

    def _parse_section(self, node: latexwalker.LatexMacroNode) -> str:
        name_node = node.nodeargd.argnlist[2]
        if isinstance(name_node, latexwalker.LatexGroupNode):
            return "".join(
                c.chars
                for c in node.nodeargd.argnlist[2].nodelist
                if isinstance(c, latexwalker.LatexCharsNode)
            )
        else:
            return node.nodeargd.argnlist[2].nodelist[0].chars

    def _parse_subsection(self, node: latexwalker.LatexMacroNode) -> str:
        name_node = node.nodeargd.argnlist[2]
        if isinstance(name_node, latexwalker.LatexGroupNode):
            return "".join(
                c.chars
                for c in node.nodeargd.argnlist[2].nodelist
                if isinstance(c, latexwalker.LatexCharsNode)
            )
        else:
            return node.nodeargd.argnlist[2].nodelist[0].chars

    def visit(self, node, **kwargs):
        # Called for all nodes that don't have a specific handler.
        try:
            text = LatexNodes2Text().node_to_text(node).replace("\n", " ")
        except Exception:
            text = ""
        if hasattr(node, "nodelist"):
            try:
                text += (
                    LatexNodes2Text().nodelist_to_text(node.nodelist).replace("\n", " ")
                )
            except Exception:
                text += ""
        if self.current_section is not None:
            self.current_section_content.append(text)
        if self.current_subsection is not None:
            self.current_subsection_content.append(text)

    def visit_macro_node(self, node: latexwalker.LatexMacroNode, **kwargs):
        if node.macroname == "section":
            # Close out the current section and subsection.
            if self.current_subsection is not None:
                self.current_subsection.content = "\n".join(
                    self.current_subsection_content
                )
                self.current_section.subsections.append(self.current_subsection)

            if self.current_section is not None:
                self.current_section.content = "\n".join(self.current_section_content)
                self.sections.append(self.current_section)

            # Start a new section.
            self.current_section = SectionNode(
                title=self._parse_section(node), subsections=[], content=""
            )
            self.current_section_content = []
            self.current_subsection = None
            self.current_subsection_content = []
        elif node.macroname == "subsection":
            # Close out the current subsection.
            if self.current_subsection is not None:
                self.current_subsection.content = "\n".join(
                    self.current_subsection_content
                )
                # We can have cases where the section never starts, this means we have it in the filename.
                if self.current_section is None:
                    self.current_section = SectionNode(
                        title=self.filename, subsections=[], content=""
                    )
                self.current_section.subsections.append(self.current_subsection)

            # Start a new subsection.
            self.current_subsection = SubSectionNode(
                title=self._parse_subsection(node), content=""
            )
            self.current_subsection_content = []

    def finish(self):
        if self.current_subsection is not None:
            self.current_subsection.content = "\n".join(self.current_subsection_content)
            if self.current_section is None:
                self.current_section = SectionNode(
                    title=self.filename, subsections=[], content=""
                )
            self.current_section.subsections.append(self.current_subsection)

        if self.current_section is not None:
            self.current_section.content = "\n".join(self.current_section_content)
            self.sections.append(self.current_section)
