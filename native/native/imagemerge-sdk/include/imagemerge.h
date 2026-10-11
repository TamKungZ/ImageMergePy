#ifndef IMAGEMERGE_SDK_H
#define IMAGEMERGE_SDK_H

#include <stdint.h>

#ifdef _WIN32
#  if defined(IMAGEMERGE_SDK_BUILD)
#    define IMAGEMERGE_API __declspec(dllexport)
#  else
#    define IMAGEMERGE_API __declspec(dllimport)
#  endif
#else
#  define IMAGEMERGE_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

IMAGEMERGE_API const char *imagemerge_sdk_version(void);

/*
 * Runs the ImageMerge CLI and returns a UTF-8 JSON result.
 *
 * Request example:
 * {"inputs":[{"path":"C:\\media","prefix":"trip"}],
 *  "output":"C:\\merged","mode":"copy_keep"}
 *
 * Supported optional keys: clear_output, remove_duplicates,
 * allow_duplicates, safe_temp (default true), lang.
 * The returned string is owned by the SDK and must be released with
 * imagemerge_sdk_free_string.
 */
IMAGEMERGE_API char *imagemerge_sdk_run(
    const char *executable_path,
    const char *request_json
);

IMAGEMERGE_API void imagemerge_sdk_free_string(char *value);

#ifdef __cplusplus
}
#endif

#endif
