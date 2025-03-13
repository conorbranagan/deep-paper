"""
Embedding for papers.
"""

from pydantic import BaseModel
from typing import Callable

import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
import openai
import tiktoken


class TextTooLongError(Exception):
    """Exception raised when a text is too long to be embedded."""

    pass


class EmbeddingConfig(BaseModel):
    """Configuration for embedding functions."""

    name: str
    size: int
    max_tokens: int
    token_encoder: Callable[[str], list[int]] | None = None
    embedding_fn: Callable[[str], list[float]]


def _embed_sbert_mini_lm(text: str) -> list[float]:
    """Get embeddings using a local BERT model with HuggingFace transformers."""
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

    # Tokenize and prepare for the model
    inputs = tokenizer(
        text, padding=True, truncation=True, return_tensors="pt", max_length=512
    )

    # Get embeddings
    with torch.no_grad():
        outputs = model(**inputs)
        # Use mean pooling to get a single vector for the text
        embeddings = outputs.last_hidden_state.mean(dim=1)

    # Convert to numpy array with explicit type
    return list(np.array(embeddings[0].numpy(), dtype=np.float32))


def _embed_openai_ada_002(text: str) -> list[float]:
    """Get embeddings using OpenAI's API."""
    token_encoder = tiktoken.get_encoding("cl100k_base")
    tokens = token_encoder.encode(text)
    if len(tokens) > 8192:
        raise TextTooLongError(
            f"Text is too long to be embedded. {len(tokens)} tokens found."
        )

    try:
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-ada-002",  # You can change this to a different model if needed
        )
        embedding = response.data[0].embedding
        return list(np.array(embedding, dtype=np.float32))
    except Exception as e:
        raise e


class Embedding:
    OPENAI_ADA_002 = EmbeddingConfig(
        name="openai_ada_002",
        size=1536,
        max_tokens=8192,
        token_encoder=tiktoken.get_encoding("cl100k_base").encode,
        embedding_fn=_embed_openai_ada_002,
    )

    SBERT_MINI_LM = EmbeddingConfig(
        name="sbert_mini_lm",
        size=384,
        max_tokens=512,
        embedding_fn=_embed_sbert_mini_lm,
    )

    @classmethod
    def default(cls):
        return cls.SBERT_MINI_LM
