#include <stdio.h>
#include <windows.h>
#include "wcurses.h"

static int wcurses_grok_extent(wcurses_t *wc);
static int wcurses_getxy_raw(wcurses_t *wc, COORD *xy);
static int wcurses_move_raw(wcurses_t *wc, COORD *xy);

int
wcurses_init(wcurses_t *wc)
{
	DWORD mode;

	wc->std_i = GetStdHandle(STD_INPUT_HANDLE);
	wc->std_o = GetStdHandle(STD_OUTPUT_HANDLE);
	wc->std_e = GetStdHandle(STD_ERROR_HANDLE);
	wcurses_grok_extent(wc);
	
	GetConsoleMode(wc->std_i, &mode);
	/* Disabling line input requires disabling echo,
	   otherwise Windows throws an error 87, invalid 
	   parameter.
	   Disabling processed input gives us ESC, etc.
	*/
	mode &= ~(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_PROCESSED_INPUT);
	SetConsoleMode(wc->std_i, mode);
    return 0;
}

int
wcurses_deinit(wcurses_t *wc)
{
	DWORD mode;

	GetConsoleMode(wc->std_i, &mode);
	mode |= ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT;
	SetConsoleMode(wc->std_i, mode);

	return 0;
}

int
wcurses_grok_extent(wcurses_t *wc)
{
	CONSOLE_SCREEN_BUFFER_INFO ci;
	
	GetConsoleScreenBufferInfo(wc->std_o, &ci);
	wc->extent = ci.srWindow;
	
	return 0;
} 

int
wcurses_get_screen_size(wcurses_t *wc, COORD *xy)
{
 xy->X = wc->extent.Right - wc->extent.Left;
 xy->Y = wc->extent.Bottom - wc->extent.Top;
 
 return 0;
}

int
wcurses_move(wcurses_t *wc, COORD *xy0)
{
	COORD xy;
	
	xy = *xy0;
	
	xy.X += wc->extent.Left;
	xy.Y += wc->extent.Top;
	
	if (xy.X < wc->extent.Left  ||  xy.X >= wc->extent.Right) return -1;
	if (xy.Y < wc->extent.Top  ||  xy.Y >= wc->extent.Bottom) return -1;
	
	SetConsoleCursorPosition(wc->std_o, xy);
	
	return 0;
}

int
wcurses_move_raw(wcurses_t *wc, COORD *xy)
{
 SetConsoleCursorPosition(wc->std_o, *xy);
 return 0;
}

int
wcurses_getxy(wcurses_t *wc, COORD *xy)
{
 wcurses_getxy_raw(wc, xy);
 xy->X -= wc->extent.Left;
 xy->Y -= wc->extent.Top;
	
 return 0;
}

int
wcurses_getxy_raw(wcurses_t *wc, COORD *xy)
{
	CONSOLE_SCREEN_BUFFER_INFO ci;
	
	GetConsoleScreenBufferInfo(wc->std_o, &ci);
	
	*xy = ci.dwCursorPosition;
	
	return 0;
}

int
wcurses_clear_region(wcurses_t *wc, SMALL_RECT *region0)
{
 SMALL_RECT region;
 COORD xy;
 int y;
 char buf[512];
 
 region = *region0;
 
 region.Top += wc->extent.Top;
 region.Bottom += wc->extent.Top;
 region.Left += wc->extent.Left;
 region.Right += wc->extent.Left;
 
 if (region.Bottom < wc->extent.Top  ||
	 region.Bottom >= wc->extent.Bottom  ||
	 region.Top < wc->extent.Top  ||
	 region.Top >= wc->extent.Bottom  ||
	 region.Left < wc->extent.Left  ||
	 region.Left >= wc->extent.Right  ||
	 region.Right < wc->extent.Left  ||
	 region.Right >= wc->extent.Right) return -1;

 memset(buf, ' ', sizeof(buf));
 buf[region.Right - region.Left] = 0;
 xy.X = region.Left;
 for (y = region.Top; y < region.Bottom; y++)
   {
    xy.Y = y;
    wcurses_move_raw(wc, &xy);
    printf(buf);
   }
   
 return 0;
}

int
wcurses_print(wcurses_t *wc, char *str)
{
 COORD xy;
 int len;
 DWORD bla;
 
 wcurses_getxy_raw(wc, &xy);
 
 len = wc->extent.Right - xy.X;
 
 WriteConsole(wc->std_o, str, len, &bla, NULL);
 
 return 0;
}

int
wcurses_get_attr(wcurses_t *wc, int *attr)
{
 CONSOLE_SCREEN_BUFFER_INFO ci;
 
 GetConsoleScreenBufferInfo(wc->std_o, &ci);
 
 *attr = ci.wAttributes;
 
 return 0;
}

int 
wcurses_set_attr(wcurses_t *wc, int attr)
{
 SetConsoleTextAttribute(wc->std_o, attr);
 
 return 0;
}

int
wcurses_getch(wcurses_t *wc, COORD *xy, int *ch)
{
 //char buf[1];
 DWORD nof_read;
 INPUT_RECORD rec;
 
 if (xy)
  {
   wcurses_move(wc, xy);
  }

 // ReadConsole doesn't provide enough control
 //ReadConsole(wc->std_i, buf, 1, &nof_read, NULL); 
 //*ch = buf[0];

 do {
	 do { 
		 ReadConsoleInput(wc->std_i, &rec, 1, &nof_read);
		} while (rec.EventType != KEY_EVENT); /* XXX ignore everything but key events for now */
	} while (!rec.Event.KeyEvent.bKeyDown  ||  (!rec.Event.KeyEvent.uChar.AsciiChar  &&
	         (rec.Event.KeyEvent.wVirtualKeyCode != VK_UP  &&  rec.Event.KeyEvent.wVirtualKeyCode != VK_DOWN  &&
	          rec.Event.KeyEvent.wVirtualKeyCode != VK_LEFT  &&  rec.Event.KeyEvent.wVirtualKeyCode != VK_RIGHT  &&
	          rec.Event.KeyEvent.wVirtualKeyCode != VK_PRIOR  &&  rec.Event.KeyEvent.wVirtualKeyCode != VK_NEXT)));
	
 *ch = rec.Event.KeyEvent.uChar.AsciiChar;
 
 /* If special key, ascii will be 0
 */
 if (!*ch)
  {
	*ch = 256 + rec.Event.KeyEvent.wVirtualKeyCode;
  } else
  {
   /* If this is a letter we have lowercase ascii regardless of shift state so we need
	  to process shift/ctrl/caps lock state ourselves
	*/
	if (rec.Event.KeyEvent.dwControlKeyState & (RIGHT_CTRL_PRESSED | LEFT_CTRL_PRESSED))
	 {
		if (isalpha(*ch))
     {
		*ch -= 'a' + 1;
     }
	} else if (rec.Event.KeyEvent.dwControlKeyState & CAPSLOCK_ON)
	{
		if (!rec.Event.KeyEvent.dwControlKeyState & SHIFT_PRESSED)
		 {
			*ch = toupper(*ch);
		 }
	} else if (rec.Event.KeyEvent.dwControlKeyState & SHIFT_PRESSED)
	{
		*ch = toupper(*ch);
	}
  }
  
 return 0;
}

int
wcurses_noecho(wcurses_t *wc)
{
 DWORD mode;
 BOOL res;
 
 GetConsoleMode(wc->std_i, &mode);
 mode &= ~ENABLE_ECHO_INPUT;
 res = SetConsoleMode(wc->std_i, mode);

 return 0;
}

int
wcurses_echo(wcurses_t *wc)
{
 DWORD mode;
 GetConsoleMode(wc->std_i, &mode);
 mode |= ENABLE_ECHO_INPUT;
 SetConsoleMode(wc->std_i, mode);
 
 return 0;
}

int 
wcurses_write_row_attrs(wcurses_t *wc, COORD *xy0, int len, WORD *attrs)
{
 DWORD written;
 COORD xy;
 
 xy.X = xy0->X + wc->extent.Left;
 xy.Y = xy0->Y + wc->extent.Top;
 
 WriteConsoleOutputAttribute(wc->std_o, attrs, len, xy, &written);
  
 return 0;
}

int
wcurses_write_row_chars(wcurses_t *wc, COORD *xy0, int len, WORD *s)
{
 DWORD written;
 COORD xy;
 
 xy.X = xy0->X + wc->extent.Left;
 xy.Y = xy0->Y + wc->extent.Top;

 WriteConsoleOutputCharacter(wc->std_o, s, len, xy, &written);
 
 return 0;
}

int
wcurses_delch(wcurses_t *wc, COORD *xy)
{
 TCHAR buf[65536];
 DWORD drop_len;
 COORD xxy;
 
 wcurses_move(wc, xy);
 
 xxy = *xy;
 xxy.X -= wc->extent.Left - 1;
 xxy.Y -= wc->extent.Top;
 
 drop_len = wc->extent.Right - wc->extent.Left - xy->X; 
 ReadConsoleOutputCharacter(wc->std_o, 
						    buf, 
						    drop_len,
						    xxy,
						    &drop_len);
 xxy.X--;
 // XXX add blank character at end
 WriteConsoleOutputCharacter(wc->std_o,
							 buf,
							 drop_len,
							 xxy,
							 &drop_len);
 							 					     
 return 0;
}

int
wcurses_inch(wcurses_t *wc, COORD *xy, TCHAR *ch)
{
 COORD xxy;
 DWORD drop_len;
 
 wcurses_move(wc, xy);
 
 xxy = *xy;
 xxy.X -= wc->extent.Left;
 xxy.Y -= wc->extent.Top;
 
 drop_len = 1;
 ReadConsoleOutputCharacter(wc->std_o, 
						    ch, 
						    drop_len,
						    xxy,
						    &drop_len);
 return 0;
}
