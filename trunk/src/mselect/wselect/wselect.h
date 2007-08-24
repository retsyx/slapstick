#ifndef __WSELECT_H
#define __WSELECT_H

#define MAX_HANDLES 2
#define OFFSET 1
#undef INFINITE /* Dance a little dance to get the value while keeping the compiler quiet */
#define INFINITE (0xFFFFFFFF)

int wselect(int nof_fds, int *fds, int timeout_ms);

#endif