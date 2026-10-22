// A controlled loader interposition verifies Go calls the libc socket entry.
// Actual default network/VPN behavior still requires a provisioned app/device.
#include <errno.h>
#include <sys/socket.h>
int socket(int family, int type, int protocol) {
    (void)family; (void)type; (void)protocol;
    errno = EPERM;
    return -1;
}
