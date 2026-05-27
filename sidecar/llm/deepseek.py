"""DeepSeek 官方 API 客户端 (OpenAI 兼容协议)。

DeepSeek 在标准 OpenAI 响应基础上扩展了 prompt_cache_hit_tokens / prompt_cache_miss_tokens,
我们直接读取这两个字段, 不需要 SDK。
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from llm.base import ChatResponse, ProviderError, TokenUsage


class DeepSeekProvider:
    name = "deepseek"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key 不能为空")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek-chat",
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        start = time.perf_counter()
        try:
            resp = await self._client.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.HTTPError as e:
            raise ProviderError(self.name, f"HTTP 请求失败: {e}") from e

        latency_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code != 200:
            raise ProviderError(
                self.name,
                f"HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
            usage_raw = data["usage"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(self.name, f"响应格式异常: {e}; body={data}") from e

        usage = TokenUsage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            prompt_cache_hit_tokens=usage_raw.get("prompt_cache_hit_tokens", 0),
            prompt_cache_miss_tokens=usage_raw.get("prompt_cache_miss_tokens", 0),
        )

        return ChatResponse(
            content=content,
            model=data.get("model", model),
            usage=usage,
            latency_ms=latency_ms,
            provider=self.name,
            raw=data,
        )

    async def health_check(self) -> bool:
        """简单 ping: 用 1 token 的请求测可达性 + 鉴权。"""
        try:
            await self.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="deepseek-chat",
                max_tokens=1,
                temperature=0.0,
            )
            return True
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "DeepSeekProvider":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
