fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to run AI Company desktop app");
}
