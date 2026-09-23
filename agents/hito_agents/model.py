"""The model, through OpenRouter.

Strands talks to OpenRouter through its OpenAI-compatible provider; only the
base URL and the key differ. The key comes from the environment and nowhere
else — this repo holds no secrets, and the agents are the first thing in it
that needs one.
"""
import os

from strands.models.openai import OpenAIModel

BASE_URL = os.environ.get("HITO_LLM_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = "anthropic/claude-sonnet-5"
# Left unset, OpenRouter reserves the model's whole output window against the
# account's balance before answering, and a class account with a few dollars
# on it is refused outright (402). The analyst writes notes, not novels.
DEFAULT_MAX_TOKENS = int(os.environ.get("HITO_MAX_TOKENS", "2000"))


def openrouter(model_id=None, **params):
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("HITO_LLM_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set. It lives in the environment, never in the repo.")
    return OpenAIModel(
        client_args={"api_key": key, "base_url": BASE_URL},
        model_id=model_id or os.environ.get("HITO_MODEL", DEFAULT_MODEL),
        params={"max_tokens": DEFAULT_MAX_TOKENS, **params},
    )
