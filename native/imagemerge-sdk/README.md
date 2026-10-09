# ImageMerge Native SDK

The Native SDK exposes a small C ABI for applications written in C, C++, C#,
Rust, and other languages that can call a shared library. It is a process-based
bridge to the existing ImageMerge CLI: the caller supplies the path to an
ImageMerge executable, and the SDK launches it without invoking a shell.

This keeps media processing behavior in the main application instead of
maintaining a second implementation in another language. The CLI executable
must be built for the same operating system and architecture as the SDK.

## Build

Install the Rust stable toolchain, then run from this directory:

```powershell
cargo test
cargo build --release
```

The shared library is written to `target/release`:

- Windows: `imagemerge.dll`
- Linux: `libimagemerge.so`
- macOS: `libimagemerge.dylib`

The Rust crate itself is portable; build it on each target operating system.
Cross-compilation is not configured by this project.

## C ABI

Include [`include/imagemerge.h`](include/imagemerge.h) and link/load the
matching shared library. `imagemerge_sdk_run` takes:

1. The full path to the ImageMerge executable.
2. A UTF-8 JSON request.

For a release SDK archive, point `executable_path` to the executable inside
`runtime/ImageMerge` (`ImageMerge.exe` on Windows, `ImageMerge` on Linux and
macOS).

The shared library must be discoverable by the host application's loader. On
Windows, link `lib/imagemerge.lib` and place `lib/imagemerge.dll` beside the
host executable or add its directory to the DLL search path. On Linux or
macOS, configure the platform's shared-library search path or rpath for the
archive's `lib` directory.

The returned UTF-8 JSON string contains either:

```json
{"ok":true,"exit_code":0,"stdout":"...","stderr":""}
```

or an error/result with a nonzero exit code:

```json
{"ok":false,"exit_code":2,"stdout":"","stderr":"..."}
```

The result is allocated by the SDK; release it exactly once with
`imagemerge_sdk_free_string`. The version string from
`imagemerge_sdk_version` is static and must not be freed.

Request fields:

```json
{
  "inputs": [{"path": "C:/media/trip", "prefix": "trip"}],
  "output": "C:/media/merged",
  "mode": "copy_keep",
  "clear_output": false,
  "remove_duplicates": false,
  "allow_duplicates": false,
  "safe_temp": true,
  "lang": "en"
}
```

`inputs` may be omitted for `main_folder` and `inside_folder`. Other supported
modes are `copy_delete` and `move`. Unknown JSON fields and invalid mode/option
combinations are rejected before starting the application. Paths in `inputs`
must exist and be directories. The `lang` field is optional.

See [`examples/c/main.c`](examples/c/main.c) for a minimal C caller and
[`examples/csharp/Program.cs`](examples/csharp/Program.cs) for a Windows C#
P/Invoke example. Build the latter with `dotnet build
examples/csharp/ImageMergeSdkExample.csproj`. The result contains the CLI's
output; applications can parse it as JSON to inspect the process exit status
and logs. `ok` reflects the executable exit code; inspect the returned logs for
per-file processing errors.

## ABI safety

Pass valid, NUL-terminated UTF-8 C strings for the duration of each call. Do
not keep or free the version pointer. Free every result pointer once using the
SDK function from the same loaded library.

The API starts a child process and waits for it to finish. It is not an
in-process media engine and does not expose GUI operations. A future major
version may add callbacks or asynchronous execution without changing this
synchronous entry point.
