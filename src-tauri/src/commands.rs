use serde::Serialize;

use crate::AppState;

#[derive(Serialize)]
pub struct SidecarStatus {
    pub connected: bool,
    pub version: Option<String>,
    pub port: Option<u16>,
    pub pid: Option<u32>,
    pub error: Option<String>,
}

#[tauri::command]
pub async fn get_sidecar_status(
    state: tauri::State<'_, AppState>,
) -> Result<SidecarStatus, String> {
    let (port, pid) = {
        let guard = state.sidecar.lock().unwrap();
        match guard.as_ref() {
            Some(handle) => (handle.port, handle.pid),
            None => {
                return Ok(SidecarStatus {
                    connected: false,
                    version: None,
                    port: None,
                    pid: None,
                    error: Some("Sidecar 进程尚未启动 / 启动失败，请查看终端日志".into()),
                });
            }
        }
    };

    match crate::sidecar::health_check(port).await {
        Ok(version) => Ok(SidecarStatus {
            connected: true,
            version: Some(version),
            port: Some(port),
            pid: Some(pid),
            error: None,
        }),
        Err(e) => Ok(SidecarStatus {
            connected: false,
            version: None,
            port: Some(port),
            pid: Some(pid),
            error: Some(format!("{:#}", e)),
        }),
    }
}
