#include <stdio.h>
#include <windows.h>
#include "wcurses.h"

static int wcurses_grok_extent(wcurses_t *wc);
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
wcurses_getxy(wcurses_t *wc, COORD *xy)
{
    CONSOLE_SCREEN_BUFFER_INFO  csbi;
    
    GetConsoleScreenBufferInfo(wc->std_o, &csbi);
    
    xy->X = csbi.dwCursorPosition.X - wc->extent.Left;
    xy->Y = csbi.dwCursorPosition.Y - wc->extent.Top;
    
    return 0;
}

int
wcurses_move_raw(wcurses_t *wc, COORD *xy)
{
 SetConsoleCursorPosition(wc->std_o, *xy);
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

 do {
	 do { 
		 ReadConsoleInput(wc->std_i, &rec, 1, &nof_read);
		} while (rec.EventType != KEY_EVENT); /* XXX ignore everything but key events for now */
	} while (!rec.Event.KeyEvent.bKeyDown  ||  (!rec.Event.KeyEvent.uChar.AsciiChar  &&
	         (rec.Event.KeyEvent.wVirtualKeyCode == VK_SHIFT  ||
	          rec.Event.KeyEvent.wVirtualKeyCode == VK_CONTROL  ||
	          rec.Event.KeyEvent.wVirtualKeyCode == VK_NUMLOCK  ||
	          rec.Event.KeyEvent.wVirtualKeyCode == VK_SCROLL  ||
	          rec.Event.KeyEvent.wVirtualKeyCode == VK_MENU)));
	          
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
