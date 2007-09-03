#include <windows.h>
#include "wcurses.h"
#include "interface.h"

wcurses_t g_wc;

int 
init(void)
{
 return wcurses_init(&g_wc);
}

int
deinit(void)
{
 return wcurses_deinit(&g_wc);
} 

int
noecho(void)
{
 return wcurses_noecho(&g_wc);
}

int 
echo(void)
{
 return wcurses_echo(&g_wc);
}

int 
move(int x, int y)
{
 COORD xy;
 xy.X = x;
 xy.Y = y;
 return wcurses_move(&g_wc, &xy);
}

int
getxy(int *x, int *y)
{
 int ret;
 COORD xy;
 
 ret = wcurses_getxy(&g_wc, &xy);
 
 *x = xy.X;
 *y = xy.Y;
 
 return ret;
}

int
get_screen_size(int *x, int *y)
{
 int ret;
 COORD xy;
 
 ret = wcurses_get_screen_size(&g_wc, &xy);
 
 *x = xy.X;
 *y = xy.Y;
 
 return ret;
}

int
getch(void)
{
 int ch;
 
 wcurses_getch(&g_wc, NULL, &ch);
 
 return ch;
}

int
write_row_attrs(int x, int y, int len, unsigned short *attrs)
{
 COORD xy;
 
 xy.X = x;
 xy.Y = y;
 
 return wcurses_write_row_attrs(&g_wc, &xy, len, attrs);
}

int
write_row_chars(int x, int y, int len, unsigned short *s)
{
 COORD xy;
 
 xy.X = x;
 xy.Y = y;
 
 return wcurses_write_row_chars(&g_wc, &xy, len, s);
}