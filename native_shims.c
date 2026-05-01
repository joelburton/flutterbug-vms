#include <string.h>
#include <unistd.h>

char *emglken_getcwd(char *buf, size_t len) {
    return getcwd(buf, len);
}
