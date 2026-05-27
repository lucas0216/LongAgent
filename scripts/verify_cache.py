#!/usr/bin/env python3
"""验证 LongAgent system prompt 的缓存命中率达标。

根据 docs/07-model-routing-cost.md, 生产环境缓存命中率必须 > 70%, 否则成本结构崩盘。
本脚本用真实 DeepSeek/火山方舟 API 跑一组测试, 测量并报告命中率。

使用:
    # DeepSeek 官方
    export DEEPSEEK_API_KEY=sk-...
    python scripts/verify_cache.py

    # 火山方舟（需要先在控制台创建 endpoint）
    export VOLCANO_API_KEY=...
    export LONGAGENT_VOLCANO_MODEL=ep-20260520-xxxxx
    python scripts/verify_cache.py --provider volcano

    # 自定义参数
    python scripts/verify_cache.py --runs 15 --model deepseek-chat

预期输出:
    [1/10] cache_hit=0     miss=3164  hit_rate=0.0%   latency=1240ms  cost=¥0.0098
    [2/10] cache_hit=3000  miss=164   hit_rate=94.8%  latency=890ms   cost=¥0.0005
    ...

    === Aggregate (warm, excluding first call) ===
    Avg cache hit rate: 92.3%
    ✅ PASS (>= 70%)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# 让脚本能从项目根目录跑
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sidecar"))

from llm import ChatResponse, DeepSeekProvider, VolcanoProvider  # noqa: E402
from prompts import load_system_prompt  # noqa: E402

# 一组真实用户可能问的问题, 覆盖典型场景。
# 每个 query 都会和同一份 system prompt 组合发请求。
# 缓存命中应发生在 system prompt 那部分 (前缀稳定), 不应该命中 user message。
TEST_QUERIES = [
    "你好，介绍一下你能做什么",
    "我有一份 PDF 报告需要总结，能帮我吗？",
    "怎么把一堆截图按内容分类？",
    "Excel 数据怎么生成图表？",
    "本地模式和云端模式有什么区别？",
    "做了的事情可以撤销吗？",
    "这个工具收费吗？",
    "支持哪些文件格式？",
    "你是 ChatGPT 吗？",
    "我断网了能用吗？",
    "你怎么保护我的隐私？",
    "我可以让你写代码吗？",
    "你能帮我整理桌面上的乱七八糟的文件吗？",
    "把 Word 转 PDF 怎么操作？",
    "我想要批量改文件名，可以吗？",
]


def fmt_row(idx: int, total: int, resp: ChatResponse) -> str:
    return (
        f"[{idx:>2}/{total}] "
        f"cache_hit={resp.usage.prompt_cache_hit_tokens:>5} "
        f"miss={resp.usage.prompt_cache_miss_tokens:>5} "
        f"hit_rate={resp.usage.cache_hit_rate:>6.1%}  "
        f"latency={resp.latency_ms:>5}ms  "
        f"cost=¥{resp.cost_cny:.5f}"
    )


async def run_verification(
    provider_name: str,
    model: str,
    runs: int,
    *,
    prompt_file: str = "system_v1.md",
) -> int:
    print(f"=== LongAgent 缓存命中率验证 ===")
    print(f"Provider:   {provider_name}")
    print(f"Model:      {model}")
    print(f"Prompt:     resources/prompts/{prompt_file}")
    print(f"Test runs:  {runs}")
    print()

    system_prompt = load_system_prompt(prompt_file)
    sys_chars = len(system_prompt)
    print(f"System prompt: {sys_chars} chars (估算 ~{sys_chars // 3} tokens, 中英混合)")
    print()

    provider = _build_provider(provider_name)

    print("开始测试...")
    print("-" * 90)

    results: list[ChatResponse] = []
    queries = (TEST_QUERIES * ((runs // len(TEST_QUERIES)) + 1))[:runs]

    for i, query in enumerate(queries, 1):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        try:
            resp = await provider.chat(
                messages=messages,
                model=model,
                max_tokens=100,
                temperature=0.7,
            )
            results.append(resp)
            print(fmt_row(i, runs, resp))
        except Exception as e:
            print(f"[{i:>2}/{runs}] FAILED: {e}")

    await provider.aclose()
    print("-" * 90)

    if not results:
        print("\n❌ 全部失败, 无法评估")
        return 1

    return _print_aggregate(results, target_hit_rate=0.70)


def _build_provider(name: str):
    if name == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            print("ERROR: 环境变量 DEEPSEEK_API_KEY 未设置")
            print("访问 https://platform.deepseek.com/ 获取 API key")
            sys.exit(2)
        return DeepSeekProvider(api_key=api_key)
    elif name == "volcano":
        api_key = os.environ.get("VOLCANO_API_KEY", "")
        if not api_key:
            print("ERROR: 环境变量 VOLCANO_API_KEY 未设置")
            print("访问 https://www.volcengine.com/product/ark 获取 API key")
            sys.exit(2)
        return VolcanoProvider(api_key=api_key)
    else:
        print(f"ERROR: 未知 provider: {name}")
        sys.exit(2)


def _print_aggregate(results: list[ChatResponse], target_hit_rate: float) -> int:
    """打印汇总报告。第 1 次调用是 cold start, 通常缓存全 miss, 不计入。"""
    if len(results) > 1:
        warm = results[1:]
        note = "(warm, excluding first cold-start call)"
    else:
        warm = results
        note = "(only 1 call, no cold/warm distinction)"

    total_input = sum(r.usage.prompt_tokens for r in warm)
    total_hit = sum(r.usage.prompt_cache_hit_tokens for r in warm)
    total_miss = sum(r.usage.prompt_cache_miss_tokens for r in warm)
    total_output = sum(r.usage.completion_tokens for r in warm)
    total_cost = sum(r.cost_cny for r in warm)
    avg_latency = sum(r.latency_ms for r in warm) / len(warm)

    overall_hit_rate = (
        total_hit / (total_hit + total_miss) if (total_hit + total_miss) else 0.0
    )

    print()
    print(f"=== Aggregate {note} ===")
    print(f"Calls:              {len(warm)}")
    print(f"Total input tokens: {total_input:,}")
    print(f"  - cache hit:      {total_hit:,} ({overall_hit_rate:.1%})")
    print(f"  - cache miss:     {total_miss:,}")
    print(f"Total output:       {total_output:,}")
    print(f"Total cost:         ¥{total_cost:.4f}")
    print(f"Avg cost/call:      ¥{total_cost / len(warm):.5f}")
    print(f"Avg latency:        {avg_latency:.0f}ms")
    print()

    if overall_hit_rate >= target_hit_rate:
        print(f"✅ PASS (cache hit rate {overall_hit_rate:.1%} >= target {target_hit_rate:.0%})")
        print()
        print("含义: 此 prompt 设计可以达成 docs/07 假设的成本目标。")
        return 0
    else:
        print(f"❌ FAIL (cache hit rate {overall_hit_rate:.1%} < target {target_hit_rate:.0%})")
        print()
        print("可能原因:")
        print("  1. system prompt 在测试间被意外修改 (检查 resources/prompts/system_v1.md)")
        print("  2. provider 的缓存策略与预期不符 (检查 API 文档)")
        print("  3. 测试 query 之间间隔太长, 缓存已过期 (DeepSeek 缓存默认保留几小时)")
        print("  4. 不同 query 触发了不同的 prompt 路径 (本测试不应该这样)")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--provider",
        choices=["deepseek", "volcano"],
        default="deepseek",
        help="LLM provider (默认 deepseek)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="模型名 (默认 deepseek-chat 或 LONGAGENT_VOLCANO_MODEL)",
    )
    parser.add_argument("--runs", type=int, default=10, help="测试次数 (默认 10)")
    parser.add_argument("--prompt", default="system_v1.md", help="prompt 文件名")
    args = parser.parse_args()

    model = args.model
    if model is None:
        if args.provider == "deepseek":
            model = "deepseek-chat"
        else:
            model = os.environ.get("LONGAGENT_VOLCANO_MODEL", "")
            if not model:
                print("ERROR: 火山方舟需要通过 --model 或 LONGAGENT_VOLCANO_MODEL 指定 endpoint ID")
                return 2

    return asyncio.run(
        run_verification(args.provider, model, args.runs, prompt_file=args.prompt)
    )


if __name__ == "__main__":
    sys.exit(main())
