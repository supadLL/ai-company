use std::sync::Mutex;

use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct ApiSidecar(Mutex<Option<CommandChild>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let sidecar_command = app.shell().sidecar("binaries/ai-company-api")?;
            let (mut receiver, child) = sidecar_command.spawn()?;
            app.manage(ApiSidecar(Mutex::new(Some(child))));

            tauri::async_runtime::spawn(async move {
                while let Some(event) = receiver.recv().await {
                    println!("api sidecar: {event:?}");
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to run AI Company desktop app");
}
