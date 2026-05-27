use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

pub struct SidecarHandle {
    pub port: u16,
    pub pid: u32,
    child: Child,
}

impl SidecarHandle {
    pub fn shutdown(mut self) {
        tracing::info!(pid = self.pid, "Shutting down sidecar");
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[derive(Deserialize)]
struct HealthResponse {
    version: String,
}

pub async fn start_sidecar() -> Result<SidecarHandle> {
    let port = portpicker::pick_unused_port().context("failed to find a free TCP port")?;
    let paths = resolve_sidecar_paths()?;

    tracing::info!(
        python = %paths.python_bin,
        script = %paths.main_script.display(),
        port,
        "Starting sidecar"
    );

    let mut cmd = Command::new(&paths.python_bin);
    cmd.arg(&paths.main_script)
        .env("LONGAGENT_SIDECAR_PORT", port.to_string())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    let child = cmd.spawn().with_context(|| {
        format!(
            "failed to spawn sidecar (cmd: {} {})",
            paths.python_bin,
            paths.main_script.display()
        )
    })?;
    let pid = child.id();

    let deadline = Instant::now() + Duration::from_secs(15);
    let mut last_err: Option<anyhow::Error> = None;
    loop {
        if Instant::now() > deadline {
            return Err(anyhow!(
                "sidecar did not become ready within 15s; last error: {}",
                last_err
                    .map(|e| format!("{:#}", e))
                    .unwrap_or_else(|| "n/a".into())
            ));
        }
        match health_check(port).await {
            Ok(_) => break,
            Err(e) => last_err = Some(e),
        }
        tokio::time::sleep(Duration::from_millis(250)).await;
    }

    Ok(SidecarHandle { port, pid, child })
}

pub async fn health_check(port: u16) -> Result<String> {
    let url = format!("http://127.0.0.1:{}/health", port);
    let resp = reqwest::Client::new()
        .get(&url)
        .timeout(Duration::from_millis(500))
        .send()
        .await
        .context("health check request failed")?
        .error_for_status()
        .context("health check returned error status")?
        .json::<HealthResponse>()
        .await
        .context("failed to parse health response")?;
    Ok(resp.version)
}

struct SidecarPaths {
    python_bin: String,
    main_script: PathBuf,
}

fn resolve_sidecar_paths() -> Result<SidecarPaths> {
    let cwd = std::env::current_dir().context("failed to get current_dir")?;

    // 开发模式查找候选路径（运行目录可能是项目根或 src-tauri/）
    let candidates = vec![
        cwd.join("sidecar/main.py"),
        cwd.join("../sidecar/main.py"),
    ];

    let main_script = candidates
        .iter()
        .find(|p| p.exists())
        .ok_or_else(|| {
            anyhow!(
                "未找到 sidecar/main.py。已尝试: {:?}",
                candidates.iter().map(|p| p.display().to_string()).collect::<Vec<_>>()
            )
        })?
        .canonicalize()
        .context("failed to canonicalize sidecar script path")?;

    let python_bin = std::env::var("LONGAGENT_PYTHON").unwrap_or_else(|_| {
        if cfg!(windows) {
            "python".into()
        } else {
            "python3".into()
        }
    });

    Ok(SidecarPaths {
        python_bin,
        main_script,
    })
}
