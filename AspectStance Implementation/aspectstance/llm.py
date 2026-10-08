"""Thin, cached wrapper around the OpenAI API for GPT-6 Luna calls.

The paper calls the model with ``reasoning effort = medium`` and every other parameter at the
provider's defaults (Section 5.4); this wrapper sends exactly that and nothing else.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Optional, Sequence

from .cache import KVCache, make_key
from .config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Calls a chat/reasoning model and caches every response on disk.

    Parameters
    ----------
    config:
        Model id, reasoning effort, API flavour and concurrency.
    cache:
        Optional :class:`KVCache`. Responses are keyed on (namespace, model, effort, api, prompt).
    client:
        Optional pre-built client (any object exposing ``responses.create`` or
        ``chat.completions.create``). Defaults to ``openai.OpenAI()``, which reads
        ``OPENAI_API_KEY`` from the environment.
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        cache: Optional[KVCache] = None,
        client: Any = None,
    ):
        self.config = config or LLMConfig()
        self.cache = cache
        if client is None:
            from openai import OpenAI

            client = OpenAI(max_retries=self.config.max_retries)
        self.client = client

    # ------------------------------------------------------------------------------------------
    def _key(self, prompt: str, namespace: str) -> str:
        c = self.config
        return make_key("llm", namespace, c.model, c.reasoning_effort, c.api, prompt)

    def _call(self, prompt: str) -> str:
        c = self.config
        if c.api == "responses":
            kwargs = {"model": c.model, "input": prompt}
            if c.reasoning_effort:
                kwargs["reasoning"] = {"effort": c.reasoning_effort}
            response = self.client.responses.create(**kwargs)
            text = response.output_text
        elif c.api == "chat":
            kwargs = {"model": c.model, "messages": [{"role": "user", "content": prompt}]}
            if c.reasoning_effort:
                kwargs["reasoning_effort"] = c.reasoning_effort
            response = self.client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
        else:
            raise ValueError(f"Unknown API flavour '{c.api}' (expected 'responses' or 'chat')")
        return (text or "").strip()

    def complete(self, prompt: str, namespace: str = "default") -> str:
        key = self._key(prompt, namespace)
        if self.cache is not None:
            cached = self.cache.get_text(key)
            if cached is not None:
                return cached
        text = self._call(prompt)
        if self.cache is not None:
            self.cache.set_text(key, text)
        return text

    def complete_many(
        self,
        prompts: Sequence[str],
        namespace: str = "default",
        desc: str = "LLM",
        progress: bool = True,
    ) -> List[str]:
        """Complete many prompts concurrently; cached prompts are not re-sent."""
        results: List[Optional[str]] = [None] * len(prompts)
        pending: List[int] = []
        if self.cache is not None:
            keys = [self._key(p, namespace) for p in prompts]
            found = self.cache.get_many(keys)
            for i, key in enumerate(keys):
                if key in found:
                    results[i] = found[key].decode("utf-8")
                else:
                    pending.append(i)
        else:
            pending = list(range(len(prompts)))

        if pending:
            logger.info("%s: %d cached, %d to request", desc, len(prompts) - len(pending), len(pending))
            bar = None
            if progress:
                from tqdm.auto import tqdm

                bar = tqdm(total=len(pending), desc=desc)
            with ThreadPoolExecutor(max_workers=max(1, self.config.workers)) as pool:
                futures = {pool.submit(self.complete, prompts[i], namespace): i for i in pending}
                for future in as_completed(futures):
                    results[futures[future]] = future.result()
                    if bar is not None:
                        bar.update(1)
            if bar is not None:
                bar.close()
        return [r if r is not None else "" for r in results]
