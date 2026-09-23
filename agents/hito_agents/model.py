"""The model: Bedrock when there are AWS credentials, OpenRouter otherwise.

Strands is AWS's SDK and Bedrock is its native provider, so that is the
default; OpenRouter stays as the class's fallback through the OpenAI-
compatible provider. `HITO_LLM=bedrock|openrouter` forces one. Every key
comes from the environment and nowhere else — this repo holds no secrets.

Bedrock, the simple way: a Bedrock API key from the console in
`AWS_BEARER_TOKEN_BEDROCK`, and `AWS_REGION`. The usual `~/.aws` credentials
work too. OpenRouter: `OPENROUTER_API_KEY`.
"""
import os

# Left unset, a provider reserves the model's whole output window against
# the account's balance before answering, and a class account with a few
# dollars on it is refused outright (402). The analyst writes notes.
DEFAULT_MAX_TOKENS = int(os.environ.get("HITO_MAX_TOKENS", "2000"))

OPENROUTER_URL = os.environ.get("HITO_LLM_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = "anthropic/claude-sonnet-5"


def aws_credentials():
    """Whether boto3 can find any credentials (env, ~/.aws, a role)."""
    try:
        import boto3
        return boto3.session.Session().get_credentials() is not None
    except Exception:
        return False


def bedrock(model_id=None, **params):
    from strands.models.bedrock import BedrockModel
    key = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    kw = {"api_key": key} if key else {}
    mid = model_id or os.environ.get("HITO_MODEL")
    if mid:
        kw["model_id"] = mid      # otherwise Strands' own default for the region
    return BedrockModel(region_name=os.environ.get("AWS_REGION"),
                        max_tokens=DEFAULT_MAX_TOKENS, **kw, **params)


def openrouter(model_id=None, **params):
    from strands.models.openai import OpenAIModel
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("HITO_LLM_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set. It lives in the environment, never in the repo.")
    return OpenAIModel(
        client_args={"api_key": key, "base_url": OPENROUTER_URL},
        model_id=model_id or os.environ.get("HITO_MODEL", OPENROUTER_MODEL),
        params={"max_tokens": DEFAULT_MAX_TOKENS, **params},
    )


def pick(model_id=None, **params):
    which = os.environ.get("HITO_LLM", "").lower()
    if not which:
        if os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or aws_credentials():
            which = "bedrock"
        elif os.environ.get("OPENROUTER_API_KEY") or os.environ.get("HITO_LLM_API_KEY"):
            which = "openrouter"
        else:
            raise SystemExit("No model: set AWS_BEARER_TOKEN_BEDROCK (Bedrock) or OPENROUTER_API_KEY (OpenRouter). "
                             "Keys live in the environment, never in the repo.")
    if which == "bedrock":
        return bedrock(model_id, **params)
    if which == "openrouter":
        return openrouter(model_id, **params)
    raise SystemExit(f"HITO_LLM={which!r}: expected bedrock or openrouter")
