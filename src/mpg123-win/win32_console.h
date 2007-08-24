#ifndef __WIN32_CONSOLE_H
#define __WIN32_CONSOLE_H

#ifdef WIN32

struct win32_console_data {
	HANDLE hnd;
	HANDLE evt_p;
	HANDLE evt_c;
	HANDLE thread;
};

int console_init(struct win32_console_data *cd);
void console_deinit(struct win32_console_data *cd);
int console_wait(struct win32_console_data *cd, struct timeval *timeout);
int console_read(struct win32_console_data *cd, int *nof_bytes, char *buf, struct timeval *timeout);

#else

struct win32_console_data {
	int a;
};
	
#define console_init(cd) (0)
#define console_deinit(cd)
#define console_wait(cd) (0)
#define console_read(cd, nof_bytes, buf, timeout) (0)

#endif

#endif