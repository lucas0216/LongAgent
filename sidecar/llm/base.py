"""LLM Provider 抽象基类。

所有云端 LLM 提供商（DeepSeek 官方、火山方舟、阿里云百炼）实现 Provider 协议。
本地推理（Ollama）也实现同一协议，对上层调用方透明。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(Exception):
    """Provider 调用失败（网络 / 限流 / 鉴权 / 模型错误等）。"""

    def __init__(self, provider: str, message: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


@dataclass(frozen=True)
class TokenUsage:
    """单次调用的 token 用量与缓存命中情况。

    DeepSeek API 在 response.usage 里返回 prompt_cache_hit_tokens / prompt_cache_miss_tokens,
    本字段直接映射。其他 provider 如果没有这些字段, 命中数置 0 (按全 miss 算成本上限)。
    """

    prompt_tokens: int
    completion_tokens: int
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中的 input token 占总 input 的比例。0.0-1.0。"""
        if self.prompt_tokens == 0:
            return 0.0
        # 优先用 API 返回的 hit + miss 之和（更精确）
        denominator = self.prompt_cache_hit_tokens + self.prompt_cache_miss_tokens
        if denominator > 0:
            return self.prompt_cache_hit_tokens / denominator
        # 兜底用 prompt_tokens
        return self.prompt_cache_hit_tokens / self.prompt_tokens


# 价目表（人民币 / 百万 tokens）— 来源: docs/07-model-routing-cost.md
# 与 ADR-0005 (火山方舟 + DeepSeek 官方同价) 一致
PRICING_CNY_PER_M = {
    # DeepSeek V4 Pro
    "deepseek-chat": {
        "input_cache_hit": 0.025,
        "input_cache_miss": 3.0,
        "output": 6.0,
    },
    "deepseek-v4-pro": {
        "input_cache_hit": 0.025,
        "input_cache_miss": 3.0,
        "output": 6.0,
    },
    # DeepSeek V4 Flash
    "deepseek-v4-flash": {
        "input_cache_hit": 0.2,
        "input_cache_miss": 1.0,
        "output": 2.0,
    },
}


def estimate_cost_cny(model: str, usage: TokenUsage) -> float:
    """根据 docs/07 的价目表估算单次调用成本。模型未在表里时返回 0 并打日志。"""
    pricing = PRICING_CNY_PER_M.get(model.lower())
    if not pricing:
        import logging

        logging.warning("未知模型 %s, 成本按 0 估算", model)
        return 0.0

    # 如果 hit + miss 加起来不等于 prompt_tokens, 把差额按 cache miss 算（保守估计）
    hit = usage.prompt_cache_hit_tokens
    miss = usage.prompt_cache_miss_tokens
    accounted = hit + miss
    unaccounted = max(0, usage.prompt_tokens - accounted)
    miss += unaccounted

    cost = (
        hit * pricing["input_cache_hit"]
        + miss * pricing["input_cache_miss"]
        + usage.completion_tokens * pricing["output"]
    ) / 1_000_000

    return cost


@dataclass
class ChatResponse:
    """统一的 chat completion 响应。"""

    content: str
    model: str
    usage: TokenUsage
    latency_ms: int
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)  # 原始响应，调试用

    @property
    def cost_cny(self) -> float:
        return estimate_cost_cny(self.model, self.usage)


class Provider(Protocol):
    """所有 LLM provider 必须实现的接口。"""

    name: str

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """发起一次 chat completion 请求。

        Args:
            messages: OpenAI 格式的消息列表 [{"role": "system|user|assistant", "content": "..."}]
            model: 模型名 (如 deepseek-chat / deepseek-v4-pro)
            temperature: 采样温度
            max_tokens: 最大输出 tokens (None = 不限)
            **kwargs: 透传给具体 provider 的额外参数

        Raises:
            ProviderError: 任何失败情况
        """
        ...

    async def health_check(self) -> bool:
        """检查 provider 是否可达。失败返回 False，不抛异常。"""
        ...
