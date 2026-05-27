mod commands;
mod sidecar;

use std::sync::Mutex;
use tauri::Manager;

use sidecar::SidecarHandle;

pub struct AppState {
    pub sidecar: Mutex<Option<SidecarHandle>>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "longagent=debug,info".into()),
        )
        .init();

    tauri::Builder::default()
        .manage(AppState {
            sidecar: Mutex::new(None),
        })
        .setup(|app| {
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                match sidecar::start_sidecar().await {
                    Ok(handle) => {
                        tracing::info!(
                            port = handle.port,
                            pid = handle.pid,
                            "Sidecar started"
                        );
                        let state = app_handle.state::<AppState>();
                        *state.sidecar.lock().unwrap() = Some(handle);
                    }
                    Err(e) => {
                        tracing::error!("Failed to start sidecar: {:#}", e);
                    }
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<AppState>();
                if let Some(handle) = state.sidecar.lock().unwrap().take() {
                    handle.shutdown();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![commands::get_sidecar_status])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
