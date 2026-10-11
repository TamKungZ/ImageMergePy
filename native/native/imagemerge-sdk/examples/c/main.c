#include <stdio.h>
#include "imagemerge.h"

int main(void) {
#ifdef _WIN32
    const char *executable = "runtime\\ImageMerge\\ImageMerge.exe";
#elif defined(__APPLE__)
    const char *executable = "runtime/ImageMerge/ImageMerge";
#else
    const char *executable = "runtime/ImageMerge/ImageMerge";
#endif
#ifdef _WIN32
    const char *request =
        "{\"inputs\":[{\"path\":\"C:\\\\media\\\\trip\",\"prefix\":\"trip\"}],"
        "\"output\":\"C:\\\\media\\\\merged\","
        "\"mode\":\"copy_keep\","
        "\"safe_temp\":true}";
#else
    const char *request =
        "{\"inputs\":[{\"path\":\"/media/trip\",\"prefix\":\"trip\"}],"
        "\"output\":\"/media/merged\","
        "\"mode\":\"copy_keep\","
        "\"safe_temp\":true}";
#endif

    char *result = imagemerge_sdk_run(executable, request);
    if (result == NULL) {
        fputs("ImageMerge SDK returned no result\n", stderr);
        return 1;
    }

    puts(result);
    imagemerge_sdk_free_string(result);
    return 0;
}
