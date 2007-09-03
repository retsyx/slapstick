#ifndef __INTERFACE_H
#define __INTERFACE_H

extern int init(void);
extern int deinit(void);
extern int noecho(void);
extern int echo(void);
extern int move(int x, int y);
extern int getxy(int *x, int *y);
extern int get_screen_size(int *x, int *y);
extern int getch(void);
extern int write_row_attrs(int x, int y, int len, unsigned short *attrs);
extern int write_row_chars(int x, int y, int len, unsigned short *s);

#endif