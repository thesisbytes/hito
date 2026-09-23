"""Memory: what the analyst learned in earlier sessions, kept by mem0.

A session of the analyst is a few turns and then the process ends. Without
memory every session re-derives the same things from the same table and
re-reports the bugs the maintainer already knows about. So the analyst has
a long-term memory, and it is wired in as a Strands *memory store* rather
than a tool bolted on the side:

- **injection** — before a model call, the harness searches the store with
  the current question and prepends what it finds as a `<memory>` block;
- **extraction** — after each invocation, the harness hands the turn's
  messages to the store, and mem0 distils them into facts with its own LLM;
- **tools** — `search_memory` and `add_memory`, for when the model wants to
  look something up or write a decision down on purpose.

mem0 is configured from the same environment `model.pick()` reads: Bedrock
for its LLM and embeddings (Titan) when Bedrock is the provider, otherwise
OpenRouter for the LLM and Gemini for embeddings. Vectors and history live
under agents/out/memory, on disk, and `python -m hito_agents.memory` prints
everything remembered — nothing lives only in a vector store.

Memories are scoped by `user_id`. The default scope is `maintainer`: the
analyst's own notes across sessions. A device id scopes what was learned
about one hand. Never a ranking, never a claim about anyone else.
"""
import asyncio
import atexit
import json
import logging
import os
import sys

# mem0 phones home by default; the agents do not.
os.environ.setdefault("MEM0_TELEMETRY", "False")
# It also warns, at import, about every optional extra it was not given.
logging.getLogger("mem0").setLevel(logging.ERROR)

from strands.memory import ExtractionConfig, InvocationTrigger, MemoryEntry, MemoryManager

from . import model as M
from .hooks import OUT

STORE = OUT / "memory"
TITAN = "amazon.titan-embed-text-v2:0"
GEMINI_EMBED = "models/gemini-embedding-001"


def who():
    return os.environ.get("HITO_MEMORY_USER", "maintainer")


def mem0_config(provider=None):
    """mem0's config, derived from the same environment the model is."""
    provider = provider or M.provider()
    region = os.environ.get("AWS_REGION", "us-west-2")
    if provider == "bedrock":
        llm = {"provider": "aws_bedrock", "config": {
            "model": os.environ.get("HITO_MODEL", M.BEDROCK_MODEL), "aws_region": region,
            "max_tokens": M.max_tokens()}}
        embedder = {"provider": "aws_bedrock", "config": {
            "model": TITAN, "aws_region": region, "embedding_dims": 1024}}
        dims = 1024
    elif provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("HITO_LLM_API_KEY")
        llm = {"provider": "openai", "config": {
            "model": os.environ.get("HITO_MODEL", M.OPENROUTER_MODEL), "api_key": key,
            "openrouter_base_url": M.OPENROUTER_URL, "max_tokens": M.max_tokens()}}
        gem = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not gem:
            raise SystemExit("mem0 needs an embedder. OpenRouter serves none: use Bedrock (Titan) once the "
                             "account is verified, or set GEMINI_API_KEY.")
        embedder = {"provider": "gemini", "config": {"model": GEMINI_EMBED, "api_key": gem, "embedding_dims": 768}}
        dims = 768
    else:
        raise SystemExit(f"no mem0 config for provider {provider!r}")
    return {
        "llm": llm,
        "embedder": embedder,
        # One collection per embedder: vectors from different models must never
        # be searched together, so the embedder's name is in the collection's.
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": f"hito_{embedder['provider']}_{dims}", "embedding_model_dims": dims,
            "path": str(STORE / "qdrant"), "on_disk": True}},
        "history_db_path": str(STORE / "history.db"),
        "version": "v1.1",
    }


def text_of(message):
    return "\n".join(b["text"] for b in message.get("content", []) if isinstance(b, dict) and "text" in b).strip()


class Mem0Store:
    """A Strands MemoryStore over a mem0 Memory (or anything with its
    add / search / get_all). mem0 2.x takes the scope as `user_id` on add
    and as `filters={"user_id": ...}` on search and get_all."""

    name = "hito"
    description = ("what earlier sessions learned: about the hands in the events table, "
                   "the project's known bugs, and decisions the maintainer made")
    max_search_results = 5
    writable = True
    extraction = ExtractionConfig(trigger=[InvocationTrigger()])

    def __init__(self, client=None, scope=None):
        self._client = client
        self.scope = scope or who()

    @property
    def client(self):
        if self._client is None:
            STORE.mkdir(parents=True, exist_ok=True)
            from mem0 import Memory
            self._client = Memory.from_config(mem0_config())
            # The embedded vector store closes itself at interpreter exit, after
            # the modules it needs are gone. Close it while they are still here.
            atexit.register(self.close)
        return self._client

    def close(self):
        c, self._client = self._client, None
        try:
            vs = getattr(c, "vector_store", None)
            client = getattr(vs, "client", None)
            if client is not None and hasattr(client, "close"):
                client.close()
        except Exception:
            pass

    @staticmethod
    def _entries(res):
        rows = res.get("results", res) if isinstance(res, dict) else res
        out = []
        for r in rows or []:
            text = r.get("memory") or r.get("text") or ""
            if text:
                out.append(MemoryEntry(content=text, metadata={k: r[k] for k in ("id", "score", "created_at") if k in r}))
        return out

    async def search(self, query, options=None):
        k = (options or {}).get("max_search_results") or self.max_search_results
        res = await asyncio.to_thread(self.client.search, query, filters={"user_id": self.scope}, top_k=k)
        return self._entries(res)

    async def add(self, content, metadata=None):
        # The model already wrote the fact; keep it as written, no extraction.
        return await asyncio.to_thread(self.client.add, content, user_id=self.scope,
                                       metadata=metadata or None, infer=False)

    async def add_messages(self, messages, context=None):
        msgs = [{"role": m["role"], "content": text_of(m)} for m in messages]
        msgs = [m for m in msgs if m["content"]]
        if not msgs:
            return None
        return await asyncio.to_thread(self.client.add, msgs, user_id=self.scope, infer=True)

    def everything(self):
        return self._entries(self.client.get_all(filters={"user_id": self.scope}, top_k=1000))


def manager(store=None):
    return MemoryManager(stores=[store or Mem0Store()], search_tool_config=True,
                         add_tool_config=True, injection=True)


def main(argv=None):
    """Print everything remembered, or add a note by hand.

        python -m hito_agents.memory                 # list, as JSON lines
        python -m hito_agents.memory --add "..."     # remember this, verbatim
    """
    argv = sys.argv[1:] if argv is None else argv
    store = Mem0Store()
    if argv and argv[0] == "--add":
        asyncio.run(store.add(" ".join(argv[1:])))
        print("remembered")
        return
    for e in store.everything():
        print(json.dumps({"memory": e.content, **(e.metadata or {})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
