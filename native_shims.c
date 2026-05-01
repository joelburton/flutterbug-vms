#include <string.h>

#ifdef _WIN32
#include <direct.h>

char *emglken_getcwd(char *buf, size_t len) {
    /* MSVC's _getcwd takes int, not size_t. */
    return _getcwd(buf, (int)len);
}
#else
#include <unistd.h>

char *emglken_getcwd(char *buf, size_t len) {
    return getcwd(buf, len);
}
#endif
