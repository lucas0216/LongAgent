"""从 resources/prompts/ 加载 prompt 文件。

System prompt 是缓存命中率的命门, 加载时不做任何修改 (连 \\r\\n → \\n 都不动),
确保跨平台一致。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _find_prompts_dir() -> Path:
    """从当前文件位置向上查找 resources/prompts 目录。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "resources" / "prompts",
        Path.cwd() / "resources" / "prompts",
        Path.cwd().parent / "resources" / "prompts",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    raise FileNotFoundError(
        f"未找到 resources/prompts/ 目录, 已尝试: {[str(c) for c in candidates]}"
    )


@lru_cache(maxsize=8)
def load_system_prompt(filename: str = "system_v1.md") -> str:
    """加载 system prompt 文件 (缓存避免重复 IO)。

    返回原始字符串, 不做 strip/normalize/replace, 保证字节级稳定供 API 缓存命中。
    """
    prompts_dir = _find_prompts_dir()
    file_path = prompts_dir / filename
    if not file_path.is_file():
        raise FileNotFoundError(f"Prompt 文件不存在: {file_path}")

    # 用 binary 读再 decode, 避免 Windows 的 newline 转换
    return file_path.read_bytes().decode("utf-8")
