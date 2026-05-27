import { invoke } from "@tauri-apps/api/core";

export interface SidecarStatus {
  connected: boolean;
  version?: string;
  port?: number;
  pid?: number;
  error?: string;
}

export async function getSidecarStatus(): Promise<SidecarStatus> {
  return invoke<SidecarStatus>("get_sidecar_status");
}
