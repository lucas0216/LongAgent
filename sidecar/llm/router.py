"""多供应商 fallback 路由。

按 ADR-0005 的优先级: 火山方舟 (主) → DeepSeek 官方 (备) → 阿里云百炼 (兜底)
任何一家失败自动降到下一家。Provider 顺序按构造时的列表。
"""
from __future__ import annotations

import logging
from typing import Any

from llm.base import ChatResponse, Provider, ProviderError

logger = logging.getLogger(__name__)


class LLMRouter:
    """按顺序尝试 providers, 直到成功或全部失败。"""

    def __init__(self, providers: list[Provider]) -> None:
        if not providers:
            raise ValueError("至少要有一个 provider")
        self.providers = providers

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> ChatResponse:
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                logger.info("尝试 provider=%s model=%s", provider.name, model)
                resp = await provider.chat(messages, model=model, **kwargs)
                logger.info(
                    "成功 provider=%s tokens=%d cost=¥%.4f latency=%dms hit_rate=%.1f%%",
                    provider.name,
                    resp.usage.total_tokens,
                    resp.cost_cny,
                    resp.latency_ms,
                    resp.usage.cache_hit_rate * 100,
                )
                return resp
            except ProviderError as e:
                logger.warning("provider %s 失败, 尝试下一个: %s", provider.name, e)
                last_error = e
                continue

        assert last_error is not None
        raise ProviderError("router", f"所有 provider 都失败, 最后错误: {last_error}")
