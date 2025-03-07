"""
Embedding and vector storage for papers.
"""

import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
import openai


class EmbeddingFunction:
    @staticmethod
    def sbert_mini_lm(text: str):
        """Get embeddings using a local BERT model with HuggingFace transformers."""
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
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
        return np.array(embeddings[0].numpy(), dtype=np.float32)

    @staticmethod
    def openai_ada_002(text: str) -> np.ndarray:
        """Get embeddings using OpenAI's API."""
        try:
            response = openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002",  # You can change this to a different model if needed
            )
            embedding = response.data[0].embedding
            return np.array(embedding)
        except Exception as e:
            raise e
