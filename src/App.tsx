import { useEffect, useState } from "react";
import { getSidecarStatus, type SidecarStatus } from "./lib/sidecar";

export default function App() {
  const [status, setStatus] = useState<SidecarStatus | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const s = await getSidecarStatus();
        setStatus(s);
      } catch (err) {
        setStatus({ connected: false, error: String(err) });
      }
    };
    check();
    const id = setInterval(check, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="text-center max-w-md w-full">
        <h1 className="text-3xl font-bold mb-2">LongAgent</h1>
        <p className="text-neutral-400 mb-8 text-sm">
          M0/M1 Sprint 1.1 PoC · Tauri ↔ Python Sidecar
        </p>

        <StatusCard status={status} />

        {status?.connected && (
          <div className="mt-6 text-xs text-neutral-500 space-y-1">
            <div>Port: {status.port}</div>
            <div>PID: {status.pid}</div>
            <div>Version: {status.version}</div>
          </div>
        )}

        <div className="mt-12 text-xs text-neutral-600">
          下一步: M1 Sprint 1.2 集成 Ollama 本地推理
        </div>
      </div>
    </div>
  );
}

function StatusCard({ status }: { status: SidecarStatus | null }) {
  if (!status) {
    return (
      <div className="border border-neutral-800 rounded-xl p-6 bg-neutral-900">
        <div className="flex items-center gap-3 justify-center">
          <Spinner />
          <span className="text-neutral-400">检查 Sidecar 状态…</span>
        </div>
      </div>
    );
  }

  if (status.connected) {
    return (
      <div className="border border-emerald-700/50 rounded-xl p-6 bg-emerald-950/40">
        <div className="flex items-center gap-3 justify-center">
          <span className="text-2xl">✅</span>
          <span className="text-emerald-300 font-medium">Sidecar 已连接</span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-red-700/50 rounded-xl p-6 bg-red-950/40">
      <div className="flex items-center gap-3 justify-center mb-2">
        <span className="text-2xl">❌</span>
        <span className="text-red-300 font-medium">Sidecar 未连接</span>
      </div>
      {status.error && (
        <pre className="text-xs text-red-400/70 text-left overflow-auto max-h-32 mt-3 p-2 bg-red-950/60 rounded">
          {status.error}
        </pre>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <div className="h-4 w-4 border-2 border-neutral-600 border-t-neutral-200 rounded-full animate-spin" />
  );
}
