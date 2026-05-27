"""LongAgent Python sidecar - M0/M1 Sprint 1.1 PoC.

最小可用的 FastAPI 服务：
- 从环境变量 LONGAGENT_SIDECAR_PORT 拿到端口
- 提供 /health 供 Tauri Core 做生命周期检查
- 后续 M1 Sprint 1.2+ 接入 Ollama / 模型路由 / 工具
"""
from __future__ import annotations

import os
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

VERSION = "0.0.1-poc"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print(f"[sidecar] LongAgent sidecar v{VERSION} starting", flush=True)
    yield
    print("[sidecar] LongAgent sidecar shutting down", flush=True)


app = FastAPI(title="LongAgent Sidecar", version=VERSION, lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/version")
async def version() -> dict[str, str]:
    return {"version": VERSION}


def _install_signal_handlers() -> None:
    def _shutdown(_sig: int, _frame: object | None) -> None:
        print("[sidecar] Received shutdown signal", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)


def main() -> None:
    port_str = os.environ.get("LONGAGENT_SIDECAR_PORT")
    if not port_str:
        print(
            "[sidecar] ERROR: 环境变量 LONGAGENT_SIDECAR_PORT 未设置",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    try:
        port = int(port_str)
    except ValueError:
        print(
            f"[sidecar] ERROR: LONGAGENT_SIDECAR_PORT 不是合法整数: {port_str!r}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    print(f"[sidecar] Binding to 127.0.0.1:{port}", flush=True)
    _install_signal_handlers()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
