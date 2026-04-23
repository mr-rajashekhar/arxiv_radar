"""
TRAPI LLM client — ported from try_trapi.py.

Auth: ChainedTokenCredential(AzureCli, ManagedIdentity) → api://trapi/.default
Endpoint: https://trapi.research.microsoft.com/{api_path}
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any

from openai import AzureOpenAI
from azure.identity import (
    ChainedTokenCredential,
    AzureCliCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)

log = logging.getLogger(__name__)


class TrapiClient:
    def __init__(
        self,
        api_path: str = "gcr/shared",
        model: str = "gpt-5_2025-08-07",
        api_version: str = "2025-04-01-preview",
        scope: str = "api://trapi/.default",
    ) -> None:
        self.model = model
        endpoint = os.environ.get(
            "TRAPI_ENDPOINT",
            f"https://trapi.research.microsoft.com/{api_path}",
        )
        credential = get_bearer_token_provider(
            ChainedTokenCredential(
                AzureCliCredential(),
                ManagedIdentityCredential(),
            ),
            scope,
        )
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=credential,
            api_version=api_version,
            timeout=120.0,      # per-request timeout (seconds)
            max_retries=0,      # we handle retries ourselves
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_retries: int = 5,
        initial_wait: float = 10.0,
        **kwargs: Any,
    ) -> str:
        """Call chat.completions with exponential backoff; return assistant text."""
        wait = initial_wait
        last_err: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                log.warning(
                    "LLM call attempt %d/%d failed: %s. Retrying in %.1fs",
                    attempt, max_retries, e, wait,
                )
                time.sleep(wait)
                wait *= 1.7
        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")


def ping() -> str:
    """Smoke test."""
    logging.basicConfig(level=logging.INFO)
    c = TrapiClient()
    return c.chat([{"role": "user", "content": "Give a one word answer: capital of France?"}])


if __name__ == "__main__":
    print(ping())
