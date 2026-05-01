#include <string.h>

#ifdef _WIN32
#include <direct.h>
#define getcwd _getcwd
#else
#include <unistd.h>
#endif

char *emglken_getcwd(char *buf, size_t len) {
    return getcwd(buf, len);
}
