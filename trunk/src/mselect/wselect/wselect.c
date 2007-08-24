#include <conio.h>
#include <time.h>
#include <windows.h>
#include <Python.h>
#include "wselect.h"

#if 0

#define WS_MAX_HANDLES MAX_HANDLES

typedef struct wselect_data_t {
	HANDLE hnd;
	HANDLE evt_p;
	HANDLE evt_c;
	HANDLE thread;
} wselect_data_t;

struct {
	wselect_data_t wsd[WS_MAX_HANDLES]; 
} g_ws;

int inited;

DWORD WINAPI 
threadProc(LPVOID lpParameter)
{
 wselect_data_t *wsd;
 BOOL res;
 DWORD bytes_read;
 char buf[1];
 DWORD nof_read;
 INPUT_RECORD inp[1];
 
 wsd = (wselect_data_t *)lpParameter;
 
 do {
	 WaitForSingleObject(wsd->evt_p, INFINITE);
     res = ReadFile(wsd->hnd, buf, 0, &bytes_read, NULL);
     //printf("res, bytes_read %d %d\n", res, bytes_read);
     /* Extract more info for console */
	 inp[0].EventType = 0;
	 res = PeekConsoleInput(wsd->hnd, inp, 1, &nof_read);
	 if (res)
	  {
	   //printf("nof_read=%d, 0x%X\n", nof_read, inp[0].EventType); 
	   if (!nof_read)
	    {
	     continue;
	    }
	   if (inp[0].EventType == KEY_EVENT)
	    {
	     if (!inp[0].Event.KeyEvent.bKeyDown)
	      {
           continue;
	      }
	    } 
	  }
	 res = TRUE; 
	 SetEvent(wsd->evt_c);
    } while (res);
  
 return 0;
}


int
init(void)
{
 int i;
 wselect_data_t *wsd;
 
 if (inited) return 0;
 
 /* Setup threads
 */
 for (i = 0; i < WS_MAX_HANDLES; i++)
   {
    wsd = &g_ws.wsd[i]; 
	wsd->hnd = INVALID_HANDLE_VALUE;
	wsd->evt_p = CreateEvent(NULL, FALSE, FALSE, NULL);
	wsd->evt_c = CreateEvent(NULL, TRUE, FALSE, NULL);
	wsd->thread = CreateThread(NULL, 0, threadProc, wsd, 0, NULL);
 
	if (wsd->evt_p == INVALID_HANDLE_VALUE  ||
		wsd->evt_c == INVALID_HANDLE_VALUE  ||
		wsd->thread == INVALID_HANDLE_VALUE)
	 {
	  CloseHandle(wsd->evt_p);
      CloseHandle(wsd->evt_c);
      TerminateThread(wsd->thread, 0);
      CloseHandle(wsd->thread);
      return -1;
     }
   }
 
 inited = 1;
     
 return 0; 
}

int
deinit(void)
{
 int i;
 wselect_data_t *wsd;
 
 if (!inited) return 0;
 
 for (i = 0; i < WS_MAX_HANDLES; i++)
   {
    wsd = &g_ws.wsd[i];
    wsd->hnd = INVALID_HANDLE_VALUE;
    CloseHandle(wsd->evt_p);
    CloseHandle(wsd->evt_c);
    TerminateThread(wsd->thread, 0);
    CloseHandle(wsd->thread);
   } 
 return 0;
}

int
wselect1(int nof_fds, int *fds, int timeout_ms)
{
 int i;
 HANDLE evts[WS_MAX_HANDLES];
 DWORD ret;
 if (!inited) return -1;
 
 if (nof_fds > WS_MAX_HANDLES) return -1;
 for (i = 0; i < nof_fds; i++)
   {
    //g_ws.wsd[i].hnd = (HANDLE)_get_osfhandle(fds[i]); // XXX Crashes for an unknown reason
    g_ws.wsd[i].hnd = (HANDLE)fds[i];
    evts[i] = g_ws.wsd[i].evt_c;
    ResetEvent(g_ws.wsd[i].evt_c);
    SetEvent(g_ws.wsd[i].evt_p);
   }

 ret = WaitForMultipleObjects(nof_fds, evts, FALSE, timeout_ms);
 
 if (ret == WAIT_FAILED)
  {
    return -1;
  }
 if (ret == WAIT_TIMEOUT)
  {
    return 0;
  }
 return ret - WAIT_OBJECT_0 + OFFSET; // +1 to differentiate from timeout
}

#endif

int
wselect(int nof_fds, int *fds, int timeout_ms)
{
 HANDLE c_hnd, p_hnd;
 BOOL res;
 DWORD bytes_avail;
 
 /* XXX hideous hack to pretend we have select for the purposes
    XXX of our app
    XXX assume first fd is console, second fd is pipe
 */
 if (nof_fds > 0)
    c_hnd = (HANDLE)fds[0];
 else
    return 0;   
 if (nof_fds > 1)
    p_hnd = (HANDLE)fds[1];
 else
    p_hnd = INVALID_HANDLE_VALUE;
 do {
     if (p_hnd != INVALID_HANDLE_VALUE)
      {
       bytes_avail = 0;
       res = PeekNamedPipe(p_hnd, NULL, 0, NULL, &bytes_avail, NULL);
       if (bytes_avail) return 1+OFFSET;
      } 
     if (_kbhit()) return 0+OFFSET;
     Sleep(100);
     timeout_ms -= 100;
    } while (timeout_ms > 0);
 
 return 0;   
}


