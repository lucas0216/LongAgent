"""火山方舟 API 客户端 (OpenAI 兼容协议)。

按 ADR-0005, 火山方舟是首选云端 provider。协议与 DeepSeek 完全一致, 仅 base_url 和
默认 model 名（endpoint ID 形如 ep-20260520-xxxxx）不同, 因此继承自 DeepSeekProvider。

火山方舟实际模型名是用户在控制台创建的"在线推理"endpoint 的 ID,
通过环境变量 LONGAGENT_VOLCANO_MODEL 注入。
"""
from __future__ import annotations

import os

from llm.deepseek import DeepSeekProvider


class VolcanoProvider(DeepSeekProvider):
    name = "volcano"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, timeout=timeout)

    async def health_check(self) -> bool:
        """火山方舟需要具体的 endpoint ID 才能调通, 用 env 变量或跳过。"""
        model = os.environ.get("LONGAGENT_VOLCANO_MODEL")
        if not model:
            # 没配 endpoint, 跳过 health check（认为可达, 由 chat() 实际调用时报错）
            return True
        try:
            await self.chat(
                messages=[{"role": "user", "content": "hi"}],
                model=model,
                max_tokens=1,
                temperature=0.0,
            )
            return True
        except Exception:
            return False
