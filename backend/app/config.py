import logging
import os
import json

from pydantic import BaseModel
from dotenv import load_dotenv
from smolagents import LiteLLMModel
from ddtrace.llmobs import LLMObs
from ddtrace import patch_all
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_vertexai import ChatVertexAI
from google.oauth2 import service_account

load_dotenv()

AVAILABLE_MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-3-5-sonnet-latest",
    "anthropic/claude-3-5-haiku-latest",
    "vertex_ai/gemini-2.0-flash-001",
    "vertex_ai/gemini-2.0-flash-lite-001",
    "vertex_ai/gemini-2.0-pro-exp-02-05",
]


class Settings(BaseModel):
    DEFAULT_MODEL: str = "openai/gpt-4o-mini"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    QDRANT_URL: str = os.getenv(
        "QDRANT_URL",
        "file://" + os.path.join(os.path.dirname(__file__), "data", "qdrant"),
    )
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    VERTEX_CREDENTIALS_JSON: str = os.getenv("VERTEX_CREDENTIALS_JSON", "")

    def smolagents_model(self, model_name, temperature):
        if model_name.startswith("openai/"):
            return LiteLLMModel(
                model_name,
                temperature=temperature,
                api_key=self.OPENAI_API_KEY,
            )
        elif model_name.startswith("anthropic/"):
            return LiteLLMModel(
                model_name,
                temperature=temperature,
                api_key=self.ANTHROPIC_API_KEY,
            )
        elif model_name.startswith("vertex_ai/"):
            return LiteLLMModel(
                model_name,
                temperature=temperature,
                vertex_credentials=self.VERTEX_CREDENTIALS_JSON,
            )
        else:
            raise Exception(f"unhandled model name: {model_name}")

    def langchain_model(self, model_name):
        if model_name.startswith("openai/"):
            return ChatOpenAI(model=model_name[len("openai/") :])
        elif model_name.startswith("anthropic/"):
            model_name = model_name[len("anthropic/") :]
            # FIXME: Something weird with typing here requires settings all these values.,
            # we're on an older version of this library due to browser-use, might be fixed in a newer one.
            return ChatAnthropic(
                model_name=model_name,
                timeout=None,
                stop=None,
                max_retries=2,
            )
        elif model_name.startswith("vertex_ai/"):
            # Create google credentials from JSON in VERTEX_CREDENTIALS_JSON
            return ChatVertexAI(
                model=model_name[len("vertex_ai/") :],
                credentials=service_account.Credentials.from_service_account_info(
                    json.loads(self.VERTEX_CREDENTIALS_JSON)
                ),
            )
        else:
            raise Exception(f"unhandled model name: {model_name}")


settings = Settings()


def init_config():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    init_dd_obs()

    # Traces go to Langsmith
    # litellm.success_callback = ["langsmith"]


def init_dd_obs():
    patch_all()

    # Traces go to Datadog
    LLMObs.enable(ml_app="deep-paper")
