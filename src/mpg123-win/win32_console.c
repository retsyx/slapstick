#include <time.h>
#include <windows.h>
#include "win32_console.h"

DWORD WINAPI threadProc(
  LPVOID lpParameter
)
{
 struct win32_console_data *cd;
 BOOL res;
 DWORD bytes_read;
 char buf[1];
 
 cd = (struct win32_console_data *)lpParameter;
 
 do {
	 WaitForSingleObject(cd->evt_p, INFINITE);
     res = ReadFile(cd->hnd, buf, 0, &bytes_read, NULL);
     SetEvent(cd->evt_c);
    } while (res);
  
 return 0;
}


int
console_init(struct win32_console_data *cd)
{
 cd->hnd = GetStdHandle(STD_INPUT_HANDLE);
 cd->evt_p = CreateEvent(NULL, FALSE, FALSE, NULL);
 cd->evt_c = CreateEvent(NULL, FALSE, FALSE, NULL);
 cd->thread = CreateThread(NULL, 0, threadProc, cd, 0, NULL);
 
 if (cd->hnd == INVALID_HANDLE_VALUE  ||
     cd->evt_p == INVALID_HANDLE_VALUE  ||
     cd->evt_c == INVALID_HANDLE_VALUE  ||
     cd->thread == INVALID_HANDLE_VALUE)
  {
   CloseHandle(cd->hnd);
   CloseHandle(cd->evt_p);
   CloseHandle(cd->evt_c);
   CloseHandle(cd->thread);
   return -1;
  }
  
 return 0; 
}

void
console_deinit(struct win32_console_data *cd)
{
 CloseHandle(cd->hnd);
 CloseHandle(cd->evt_p);
 CloseHandle(cd->evt_c);
 CloseHandle(cd->thread);
}

int 
console_wait(struct win32_console_data *cd, struct timeval *timeout)
{
 DWORD win32_timeout, s;

 if (!timeout)
  {
   win32_timeout = INFINITE;
  } else
  {
   win32_timeout = timeout->tv_sec * 1000 + timeout->tv_usec / 1000;
  }
  
 ResetEvent(cd->evt_c); // ensure there is nothing left over from an earlier call
 SetEvent(cd->evt_p);
 s = WaitForSingleObject(cd->evt_c, win32_timeout);
 if (s == WAIT_TIMEOUT)
  {
   return 0;
  } 
  
 return 1;
}

int 
console_read(struct win32_console_data *cd, int *nof_bytes, char *buf, struct timeval *timeout)
{
 DWORD win32_timeout, s;
 BOOL res;
 
 if (!timeout)
  {
   win32_timeout = INFINITE;
  } else
  {
   win32_timeout = timeout->tv_sec * 1000 + timeout->tv_usec / 1000;
  }
   
 SetEvent(cd->evt_p);
 s = WaitForSingleObject(cd->evt_c, win32_timeout);
 if (s == WAIT_TIMEOUT)
  {
   return 0;
  } 
  
 res = ReadFile(cd->hnd, buf, *nof_bytes, nof_bytes, NULL);
 if (!res)
  {
   return -1;
  }
 
 return *nof_bytes; 
}

/* silly example showing how to use this
void
console_echo(void)
{
 struct win32_console_data cd;
 struct timeval tv = {5, 0};
 char buf[1];
 int i, n, nof_bytes;
 
 console_init(&cd);
 while (1)
  {
   nof_bytes = 1;
   n = console_read(&cd, &nof_bytes, buf, &tv);
   if (n < 0)
    {
     printf("done\n");
     return;
    } else if (n > 0)
    {
     for (i = 0;i < n; i++)
       {
        printf("%c", buf[i]);
       }
     printf("\n");  
    } else
    {
     printf(".\n");
    } 
  }
}
*/