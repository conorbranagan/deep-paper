import logging
import os
from pydantic import BaseModel
from dotenv import load_dotenv
import litellm
from smolagents import LiteLLMModel


load_dotenv()

AVAILABLE_MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-3-5-sonnet-latest",
    "anthropic/claude-3-5-haiku-latest",
    "vertex/gemini-1.5-flash",
]


class Settings(BaseModel):
    DEFAULT_MODEL: str = "openai/gpt-4o-mini"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY")

    def agent_model(self, model_name, temperature, **kwargs):
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
        elif model_name.startswith("vertex/"):
            return LiteLLMModel(
                model_name,
                temperature=temperature,
                # TODO: add vertex config
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

    # Traces go to Langsmith
    litellm.success_callback = ["langsmith"]
