use serde::Deserialize;
use serde_json::{json, Value};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::path::Path;
use std::process::{Command, Output};

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    output: String,
    mode: String,
    #[serde(default)]
    inputs: Vec<Input>,
    #[serde(default)]
    clear_output: bool,
    #[serde(default)]
    remove_duplicates: bool,
    #[serde(default)]
    allow_duplicates: bool,
    #[serde(default = "default_true")]
    safe_temp: bool,
    #[serde(default)]
    lang: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    path: String,
    #[serde(default)]
    prefix: String,
}

fn default_true() -> bool {
    true
}

fn validate_request(request: &Request) -> Result<(), String> {
    const MODES: &[&str] = &[
        "copy_keep",
        "copy_delete",
        "move",
        "main_folder",
        "inside_folder",
    ];

    if !MODES.contains(&request.mode.as_str()) {
        return Err(format!("Unsupported mode: {}", request.mode));
    }
    if request.output.trim().is_empty() {
        return Err("Output path cannot be empty".to_owned());
    }
    if request.inputs.is_empty()
        && !matches!(request.mode.as_str(), "main_folder" | "inside_folder")
    {
        return Err("At least one input directory is required for this mode".to_owned());
    }
    if request.remove_duplicates && request.mode != "inside_folder" {
        return Err("remove_duplicates is only valid with inside_folder mode".to_owned());
    }
    if request.remove_duplicates && request.allow_duplicates {
        return Err("remove_duplicates cannot be combined with allow_duplicates".to_owned());
    }
    if request.clear_output && request.mode == "inside_folder" {
        return Err("clear_output cannot be used with inside_folder mode".to_owned());
    }
    for input in &request.inputs {
        if input.path.trim().is_empty() {
            return Err("Input path cannot be empty".to_owned());
        }
        if !Path::new(&input.path).is_dir() {
            return Err(format!(
                "Input path is not an existing directory: {}",
                input.path
            ));
        }
    }
    if let Some(lang) = &request.lang {
        if lang.trim().is_empty() {
            return Err("Language cannot be empty when specified".to_owned());
        }
    }

    Ok(())
}

fn cli_arguments(request: &Request) -> Vec<String> {
    let mut args = vec!["--cli".to_owned()];
    for input in &request.inputs {
        let entry = if input.prefix.is_empty() {
            input.path.clone()
        } else {
            format!("{}::{}", input.path, input.prefix)
        };
        args.extend(["--input".to_owned(), entry]);
    }
    args.extend(["--output".to_owned(), request.output.clone()]);
    args.extend(["--mode".to_owned(), request.mode.clone()]);

    if request.clear_output {
        args.push("--clear-output".to_owned());
    }
    if request.remove_duplicates {
        args.push("--remove-duplicates".to_owned());
    }
    if request.allow_duplicates {
        args.push("--allow-duplicates".to_owned());
    }
    if !request.safe_temp {
        args.push("--no-safe-temp".to_owned());
    }
    if let Some(lang) = &request.lang {
        args.extend(["--lang".to_owned(), lang.clone()]);
    }

    args
}

fn output_json(output: Output) -> Value {
    json!({
        "ok": output.status.success(),
        "exit_code": output.status.code(),
        "stdout": String::from_utf8_lossy(&output.stdout),
        "stderr": String::from_utf8_lossy(&output.stderr),
    })
}

fn execute(executable: &Path, request_json: &str) -> Value {
    let request: Request = match serde_json::from_str(request_json) {
        Ok(request) => request,
        Err(error) => {
            return json!({"ok": false, "error": format!("Invalid request JSON: {error}")})
        }
    };
    if let Err(error) = validate_request(&request) {
        return json!({"ok": false, "error": error});
    }
    if !executable.is_file() {
        return json!({
            "ok": false,
            "error": format!("ImageMerge executable not found: {}", executable.display())
        });
    }

    match Command::new(executable)
        .args(cli_arguments(&request))
        .output()
    {
        Ok(output) => output_json(output),
        Err(error) => json!({
            "ok": false,
            "error": format!("Could not start ImageMerge: {error}")
        }),
    }
}

fn into_c_string(value: Value) -> *mut c_char {
    let serialized = serde_json::to_string(&value)
        .unwrap_or_else(|error| format!(r#"{{"ok":false,"error":"{error}"}}"#));
    CString::new(serialized)
        .expect("JSON serialization must not contain interior NUL bytes")
        .into_raw()
}

fn read_c_string(value: *const c_char, label: &str) -> Result<String, String> {
    if value.is_null() {
        return Err(format!("{label} must not be null"));
    }
    // The caller must pass a valid, NUL-terminated C string for this call.
    unsafe { CStr::from_ptr(value) }
        .to_str()
        .map(str::to_owned)
        .map_err(|error| format!("{label} is not valid UTF-8: {error}"))
}

/// Returns the SDK version as a static, NUL-terminated string.
#[no_mangle]
pub extern "C" fn imagemerge_sdk_version() -> *const c_char {
    concat!(env!("CARGO_PKG_VERSION"), "\0").as_ptr().cast()
}

/// Runs ImageMerge and returns an owned JSON result. Release it with
/// `imagemerge_sdk_free_string`.
///
/// # Safety
/// `executable_path` and `request_json` must each point to valid,
/// NUL-terminated UTF-8 strings for the duration of this call.
#[no_mangle]
pub unsafe extern "C" fn imagemerge_sdk_run(
    executable_path: *const c_char,
    request_json: *const c_char,
) -> *mut c_char {
    let result = std::panic::catch_unwind(|| {
        let executable = read_c_string(executable_path, "executable_path")?;
        let request = read_c_string(request_json, "request_json")?;
        Ok::<Value, String>(execute(Path::new(&executable), &request))
    });

    match result {
        Ok(Ok(value)) => into_c_string(value),
        Ok(Err(error)) => into_c_string(json!({"ok": false, "error": error})),
        Err(_) => into_c_string(json!({"ok": false, "error": "Internal SDK panic"})),
    }
}

/// Releases a result returned by `imagemerge_sdk_run`.
///
/// # Safety
/// `value` must be null or a pointer previously returned by
/// `imagemerge_sdk_run` that has not already been freed.
#[no_mangle]
pub unsafe extern "C" fn imagemerge_sdk_free_string(value: *mut c_char) {
    if !value.is_null() {
        drop(CString::from_raw(value));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cli_arguments_map_request_options() {
        let request: Request = serde_json::from_str(
            r#"{
                "inputs": [{"path": "input folder", "prefix": "Trip"}],
                "output": "output folder",
                "mode": "copy_keep",
                "allow_duplicates": true,
                "safe_temp": false,
                "lang": "en"
            }"#,
        )
        .unwrap();

        assert_eq!(
            cli_arguments(&request),
            [
                "--cli",
                "--input",
                "input folder::Trip",
                "--output",
                "output folder",
                "--mode",
                "copy_keep",
                "--allow-duplicates",
                "--no-safe-temp",
                "--lang",
                "en",
            ]
        );
    }

    #[test]
    fn safe_temp_is_enabled_by_default() {
        let request: Request =
            serde_json::from_str(r#"{"output":"out","mode":"main_folder"}"#).unwrap();

        assert!(request.safe_temp);
        assert!(!cli_arguments(&request).contains(&"--no-safe-temp".to_owned()));
    }

    #[test]
    fn rejects_unknown_request_keys() {
        let result = serde_json::from_str::<Request>(
            r#"{"output":"out","mode":"main_folder","unexpected":true}"#,
        );

        assert!(result.is_err());
    }

    #[test]
    fn rejects_in_place_clear_before_launching() {
        let request: Request =
            serde_json::from_str(r#"{"output":"out","mode":"inside_folder","clear_output":true}"#)
                .unwrap();

        assert_eq!(
            validate_request(&request).unwrap_err(),
            "clear_output cannot be used with inside_folder mode"
        );
    }

    #[test]
    fn ffi_reports_null_arguments_as_json_errors() {
        let request = CString::new(r#"{"output":"out","mode":"main_folder"}"#).unwrap();
        let result = unsafe { imagemerge_sdk_run(std::ptr::null(), request.as_ptr()) };
        assert!(!result.is_null());

        let parsed: Value =
            serde_json::from_str(unsafe { CStr::from_ptr(result) }.to_str().unwrap()).unwrap();
        assert_eq!(parsed["ok"], false);
        assert_eq!(parsed["error"], "executable_path must not be null");

        unsafe { imagemerge_sdk_free_string(result) };
    }
}
