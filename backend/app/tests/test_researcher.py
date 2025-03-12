import pytest
from unittest.mock import patch, MagicMock

from app.agents.researcher import PaperRetriever, PaperChunkRetriever, CitationRetriever
from app.models.paper import PaperNotFound
from app.pipeline.vector_store import VectorStore


class TestPaperRetriever:
    @pytest.mark.parametrize(
        "arxiv_id, query, expected_result, paper_exists",
        [
            # Test case 1: Valid paper, no query (full paper)
            (
                "2307.09288",
                "",
                "\nPaper Contents in LaTeX\n\nSample LaTeX content",
                True,
            ),
            # Test case 2: Valid paper with query
            (
                "2307.09288",
                "neural networks",
                "\nRetrieved information:\n\n\n===== Chunk 0 =====\nSample chunk about neural networks",
                True,
            ),
            # Test case 3: Paper not found
            (
                "9999.99999",
                "",
                "Unable to find paper for Arxiv ID 9999.99999",
                False,
            ),
        ],
    )
    def test_paper_retriever(self, arxiv_id, query, expected_result, paper_exists):
        # Arrange
        tool = PaperRetriever()
        
        mock_paper = MagicMock()
        mock_paper.latex_contents = "Sample LaTeX content"
        
        # Mock the Paper.from_arxiv_id method
        with patch("app.agents.researcher.Paper.from_arxiv_id") as mock_from_arxiv:
            if paper_exists:
                mock_from_arxiv.return_value = mock_paper
            else:
                mock_from_arxiv.side_effect = PaperNotFound()
            
            # For the query case, we need to mock the text splitter and retriever
            if query:
                with patch("app.agents.researcher.RecursiveCharacterTextSplitter") as mock_splitter:
                    mock_splitter_instance = MagicMock()
                    mock_splitter.return_value = mock_splitter_instance
                    mock_splitter_instance.split_text.return_value = ["Sample chunk about neural networks"]
                    
                    with patch("app.agents.researcher.BM25Retriever") as mock_retriever_class:
                        mock_retriever = MagicMock()
                        mock_retriever_class.from_texts.return_value = mock_retriever
                        
                        # Act
                        result = tool.forward(arxiv_id, query)
            else:
                # Act
                result = tool.forward(arxiv_id, query)
        
        # Assert
        assert result == expected_result


class TestPaperChunkRetriever:
    @pytest.mark.parametrize(
        "query, search_results, expected_output",
        [
            # Test case 1: Basic query with results
            (
                "transformer architecture",
                [
                    MagicMock(metadata={"title": "Paper 1"}, document="Content about transformers"),
                    MagicMock(metadata={"title": "Paper 2"}, document="More content about transformers"),
                ],
                "\nRetrieved documents:\n\n\n===== Document 0 =====\n{'title': 'Paper 1'}\n\nContent about transformers\n\n===== Document 1 =====\n{'title': 'Paper 2'}\n\nMore content about transformers",
            ),
            # Test case 2: Query with no results
            (
                "quantum computing",
                [],
                "\nRetrieved documents:\n",
            ),
        ],
    )
    def test_paper_chunk_retriever(self, query, search_results, expected_output):
        # Arrange
        mock_vector_store = MagicMock(spec=VectorStore)
        mock_vector_store.search.return_value = search_results
        
        tool = PaperChunkRetriever(vector_store=mock_vector_store)
        
        # Act
        result = tool.forward(query)
        
        # Assert
        assert result == expected_output
        mock_vector_store.search.assert_called_once_with(query, top_k=10)


class TestCitationRetriever:
    @pytest.mark.parametrize(
        "arxiv_id, citation_ids, paper_exists, matching_citations, expected_output",
        [
            # Test case 1: Valid paper with matching citations
            (
                "2307.09288",
                ["ref1", "ref2"],
                True,
                [
                    MagicMock(id="ref1", title="Citation 1", author="Author 1", year="2020", url="http://example.com/1"),
                    MagicMock(id="ref2", title="Citation 2", author="Author 2", year="2021", url=None),
                ],
                "\n==== Citation Details ====\nID: ref1\nTitle: Citation 1\nAuthor: Author 1\nYear: 2020\nURL: http://example.com/1\n==== Citation Details ====\nID: ref2\nTitle: Citation 2\nAuthor: Author 2\nYear: 2021\nURL: None",
            ),
            # Test case 2: Valid paper with no matching citations
            (
                "2307.09288",
                ["nonexistent"],
                True,
                [],
                "Unable to find citations for Arxiv ID 2307.09288 and IDs ['nonexistent']",
            ),
            # Test case 3: Paper not found
            (
                "9999.99999",
                ["ref1"],
                False,
                [],
                "Unable to find paper for Arxiv ID 9999.99999",
            ),
            # Test case 4: Missing inputs
            (
                "",
                [],
                False,
                [],
                "Must provide both arxiv and citation ids",
            ),
        ],
    )
    def test_citation_retriever(self, arxiv_id, citation_ids, paper_exists, matching_citations, expected_output):
        # Arrange
        tool = CitationRetriever()
        
        # Skip the actual API call if inputs are missing
        if not arxiv_id or not citation_ids:
            # Act
            result = tool.forward(arxiv_id, citation_ids)
            # Assert
            assert result == expected_output
            return
        
        # Mock the Paper.from_arxiv_id method
        with patch("app.agents.researcher.Paper.from_arxiv_id") as mock_from_arxiv:
            if not paper_exists:
                mock_from_arxiv.side_effect = PaperNotFound()
                # Act
                result = tool.forward(arxiv_id, citation_ids)
            else:
                mock_paper = MagicMock()
                mock_latex = MagicMock()
                mock_latex.citations = matching_citations
                mock_paper.latex = mock_latex
                mock_from_arxiv.return_value = mock_paper
                
                # Act
                result = tool.forward(arxiv_id, citation_ids)
        
        # Assert
        assert result == expected_output


if __name__ == "__main__":
    pytest.main(["-xvs", "test_researcher.py"]) 